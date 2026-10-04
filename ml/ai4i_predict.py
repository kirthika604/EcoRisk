#!/usr/bin/env python3
"""Predict machine failures for new (unseen) AI4I-format rows with the model from ml/ai4i_model.py.

For each machine: failure probability, alert (threshold chosen on training folds), the most likely
failure type, a plain-language reason tied to the documented failure mechanisms, what happens next
(production runs until the alert line / until the tool enters its 200-240 min wear window), and a
maintenance action. If the file also contains "Machine failure", the predictions are scored against it.
"""
import io
import os
import pickle
import re

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

from ai4i_model import COLMAP, FEATS, MODES, STRAIN_LIMIT, WEAR_PER_RUN, features, physical_checks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_B = {}
MODE_NAME = {"TWF": "tool wear failure", "HDF": "heat dissipation failure", "PWF": "power failure", "OSF": "overstrain failure"}
ACTION = {
    "TWF": "Replace the tool now, or schedule a tool change before the next shift.",
    "HDF": "Improve cooling: lower process temperature or raise speed above 1,380 rpm.",
    "PWF": "Bring power back into the 3.5-9 kW band by adjusting torque or speed.",
    "OSF": "Reduce torque or change the tool: wear x torque is at the overstrain limit.",
}
# tolerant column matching, in case an evaluation file renames AI4I columns
PATTERNS = {"Type": r"^(product[\s_]*)?type$|quality", "Air temperature [K]": r"air",
            "Process temperature [K]": r"process", "Rotational speed [rpm]": r"rotation|rpm|speed",
            "Torque [Nm]": r"torque", "Tool wear [min]": r"wear", "Machine failure": r"machine[\s_]*failure|^failure$|^target$"}


def bundle():
    if "b" not in _B:
        with open(os.path.join(ROOT, "ml", "ai4i_models.pkl"), "rb") as f:
            _B["b"] = pickle.load(f)
    return _B["b"]


def read(text):
    text = text.lstrip("﻿")
    if not text.strip():
        raise ValueError("No columns to parse from file")
    sep = max([",", ";", "\t"], key=text.splitlines()[0].count)
    df = pd.read_csv(io.StringIO(text), sep=sep)
    df.columns = [str(c).strip() for c in df.columns]
    ren, used = {}, set()
    for canon, pat in PATTERNS.items():
        if canon in df.columns:
            used.add(canon)
            continue
        hit = next((c for c in df.columns if c not in used and c not in ren and re.search(pat, c, re.I)), None)
        if hit:
            ren[hit] = canon
            used.add(hit)
    df = df.rename(columns=ren)
    if len(df) > 100_000:
        raise ValueError("file too large (limit 100,000 machines)")
    return df, ren


def _reason(x, mode_p):
    """Human reason, tied to the documented mechanism of the most likely failure type."""
    checks = []
    if x.temp_diff_K < 8.6 and x.rpm < 1380:
        checks.append(("HDF", f"heat: temperature difference {x.temp_diff_K:.1f} K with speed {x.rpm:.0f} rpm (risk zone: < 8.6 K and < 1,380 rpm)"))
    if x.power_W < 3500 or x.power_W > 9000:
        checks.append(("PWF", f"power {x.power_W / 1000:.1f} kW is outside the safe 3.5-9 kW band"))
    if x.strain_ratio >= 0.9:
        checks.append(("OSF", f"strain {x.strain:,.0f} minNm is {x.strain_ratio:.0%} of this type's limit"))
    if x.wear_min >= 200:
        checks.append(("TWF", f"tool wear {x.wear_min:.0f} min is inside the 200-240 min failure window"))
    if checks:
        checks.sort(key=lambda c: -mode_p.get(c[0], 0))
        return checks[0][1]
    top = max(mode_p, key=mode_p.get)
    return f"closest mechanism: {MODE_NAME[top]} ({mode_p[top]:.0%})" if mode_p[top] >= 0.05 else "all readings in normal operating ranges"


def _project_all(model, X, thr, fs):
    """Run-ahead projection for every machine in ONE model call (wear grows 2/3/5 min per run)."""
    inc = X.type_code.map(WEAR_PER_RUN).to_numpy()
    kmax = np.maximum(0, (260 - X.wear_min.to_numpy()) // inc).astype(int)
    rep = kmax + 1
    owner = np.repeat(np.arange(len(X)), rep)
    k = np.concatenate([np.arange(r) for r in rep]) if len(rep) else np.array([], int)
    P = X.iloc[owner].reset_index(drop=True).copy()
    P["wear_min"] = P.wear_min.to_numpy() + k * inc[owner]
    P["strain"] = P.wear_min * P.torque_Nm
    P["strain_ratio"] = P.strain / P.type_code.map(STRAIN_LIMIT)
    P["wear_ge_200"] = (P.wear_min >= 200).astype(int)
    p = model.predict_proba(P[fs])[:, 1] if len(P) else np.array([])
    starts = np.concatenate([[0], np.cumsum(rep)[:-1]])
    out = []
    for i in range(len(X)):
        # tool wear only accumulates damage: with everything else fixed, risk cannot fall as the tool
        # wears, so dips (random-forest artefacts in sparse regions) are removed by a running maximum
        seg = np.maximum.accumulate(p[starts[i]:starts[i] + rep[i]]) if rep[i] else p[starts[i]:starts[i]]
        hit = np.where(seg >= thr)[0]
        w0 = X.wear_min.iloc[i]
        out.append((int(hit[0]) if len(hit) else None, 0 if w0 >= 200 else int(np.ceil((200 - w0) / inc[i])),
                    P.wear_min.iloc[starts[i]:starts[i] + rep[i]].tolist(), seg.round(4).tolist()))
    return out


def predict(df, curves=False):
    b = bundle()
    model, fs, thr = b["model"], b["features"], b["threshold"]
    issues = physical_checks(df) if all(c in df.columns for c in COLMAP) else []
    X = features(df)
    p = model.predict_proba(X[fs])[:, 1]
    mp = {m: b["modes"][m].predict_proba(X[b["mode_features"]])[:, 1] for m in MODES}
    proj = _project_all(model, X, thr, fs)
    rows = []
    for i in range(len(X)):
        x = X.iloc[i]
        mode_p = {m: float(mp[m][i]) for m in MODES}
        alert = bool(p[i] >= thr)
        likely = max(mode_p, key=mode_p.get)
        to_alert, to_window, wear, pw = proj[i]
        if alert:
            act = ACTION[likely] if mode_p[likely] >= 0.05 else "Stop and inspect: failure risk is above the alert line."
        elif to_alert is not None and to_alert <= 20:
            act = f"Plan maintenance within {to_alert} runs: risk will cross the alert line."
        elif to_window == 0:
            act = ACTION["TWF"]
        else:
            act = f"Keep running. Re-check in {min(to_window, 25)} runs."
        r = {"row": i + 1, "type": "LMH"[int(x.type_code)], "failure_probability": round(float(p[i]), 4), "alert": alert,
             "likely_failure_type": MODE_NAME[likely] if (alert or mode_p[likely] >= 0.2) else "none",
             "reason": _reason(x, mode_p), "runs_until_alert": to_alert, "runs_until_tool_window": to_window, "action": act,
             **{f"p_{m}": round(mode_p[m], 4) for m in MODES}}
        if curves:
            r["projection"] = {"wear": wear, "p": pw}
        rows.append(r)
    out = {"n": len(rows), "alerts": int(sum(r["alert"] for r in rows)), "threshold": round(float(thr), 4),
           "physical_issues": issues, "rows": rows}
    if "Machine failure" in df.columns:  # labelled file (e.g. a hidden evaluation set): score ourselves
        y = pd.to_numeric(df["Machine failure"], errors="coerce").fillna(0).astype(int).values
        yh = (p >= thr).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, yh, labels=[0, 1]).ravel()
        sc = {"n": int(len(y)), "failures": int(y.sum()), "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
              "precision": round(float(precision_score(y, yh, zero_division=0)), 4), "recall": round(float(recall_score(y, yh, zero_division=0)), 4),
              "f1": round(float(f1_score(y, yh, zero_division=0)), 4), "accuracy": round(float((y == yh).mean()), 4)}
        if 0 < y.sum() < len(y):
            sc["pr_auc"] = round(float(average_precision_score(y, p)), 4)
            sc["roc_auc"] = round(float(roc_auc_score(y, p)), 4)
        out["score"] = sc
        for r, yy in zip(rows, y):
            r["actual"] = int(yy)
    return out


def to_csv(result):
    keep = [k for k in result["rows"][0] if k != "projection"] if result["rows"] else []
    return pd.DataFrame([{k: r[k] for k in keep} for r in result["rows"]]).to_csv(index=False)
