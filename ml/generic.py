#!/usr/bin/env python3
"""EcoRisk AI: "bring your own dataset". The same predict-what-happens-next pipeline for ANY table.

    profile(df)            -> column types, missing values, IDs, leakage suspects, suggested target
    train(df, target, ...) -> cleaning, feature engineering, baseline vs logistic vs gradient boosting
                              (chosen on VALIDATION), honest TEST metrics, top drivers, model_id
    predict(model_id, df)  -> predictions + the main reason for each new row

Design choices (all reported back to the user):
  * IDs (row counters, near-unique text such as product codes) are dropped: they let a model memorise.
  * Leakage guard: a column that on its own almost perfectly reveals the target (a 0/1 flag that
    implies it, or a feature with single-column AUC >= 0.98), or a sibling outcome flag recorded
    next to such columns, is excluded by default. E.g. AI4I 2020: TWF/HDF/PWF/OSF/RNF are the failure
    modes OF "Machine failure", not causes of it.
  * Split: by time if a date column exists (no look-ahead), else stratified 60/20/20 with a fixed seed.
  * Model and decision threshold are chosen on the validation split; the test split is scored once.
"""
import io
import re
import uuid
from collections import OrderedDict

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             mean_absolute_error, mean_squared_error, precision_score, r2_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

MAX_ROWS = 200_000
MAX_MODELS = 5
_MODELS = OrderedDict()  # model_id -> trained bundle (small in-memory store, oldest evicted)
SEED = 42


# ---------------------------------------------------------------- reading + profiling
def read_csv(text):
    """Any CSV text: strips a byte-order mark, sniffs , ; or tab."""
    text = text.lstrip("﻿")
    if not text.strip():
        raise ValueError("No columns to parse from file")
    first = text.splitlines()[0]
    sep = max([",", ";", "\t"], key=first.count)
    df = pd.read_csv(io.StringIO(text), sep=sep)
    df.columns = [str(c).strip().lstrip("﻿") for c in df.columns]
    if len(df) > MAX_ROWS:
        raise ValueError(f"file too large: {len(df):,} rows (limit {MAX_ROWS:,})")
    if len(df.columns) < 2:
        raise ValueError("need at least two columns (features and a target)")
    return df


def _is_datetime(s):
    if s.dtype.kind == "M":
        return True
    if s.dtype != object:
        return False
    sample = s.dropna().astype(str).head(50)
    if sample.empty or not sample.str.contains(r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}").mean() > 0.8:
        return False
    return pd.to_datetime(sample, errors="coerce").notna().mean() > 0.9


def _kind(s, name):
    n, nun = len(s), s.nunique(dropna=True)
    if nun <= 1:
        return "constant"
    if _is_datetime(s):
        return "datetime"
    if pd.api.types.is_numeric_dtype(s):
        v = s.dropna()
        if nun == n and (v.diff().dropna() > 0).all() and (np.allclose(v, v.round())):
            return "id"  # a row counter (e.g. UDI)
        if nun == 2 and set(v.unique()) <= {0, 1, True, False}:
            return "binary"
        return "numeric"
    if nun / max(n, 1) > 0.9 or re.search(r"(^|[_\s])id$|^id[_\s]|identifier|uuid", name, re.I):
        return "id"  # near-unique text, e.g. product codes
    return "categorical"


def suggest_target(df, kinds):
    pref = re.compile(r"fail|target|label|class|outcome|default|churn|fraud|disease|diagnos|survived|^y$|result|status|is_|has_", re.I)
    cands = [c for c in df.columns if kinds[c] in ("binary", "categorical", "numeric")]
    named = [c for c in cands if pref.search(c)]
    named.sort(key=lambda c: (kinds[c] != "binary", not re.search(r"fail|target|label", c, re.I)))
    if named:
        return named[0]
    binaries = [c for c in cands if kinds[c] == "binary"]
    return binaries[-1] if binaries else cands[-1]


def profile(df):
    kinds = {c: _kind(df[c], c) for c in df.columns}
    target = suggest_target(df, kinds)
    cols = [{"name": c, "kind": kinds[c], "missing": int(df[c].isna().sum()), "unique": int(df[c].nunique()),
             "example": None if df[c].dropna().empty else str(df[c].dropna().iloc[0])[:24]} for c in df.columns]
    return {"rows": len(df), "columns": cols, "suggested_target": target}


# ---------------------------------------------------------------- leakage + features
def _leakage(df, target, kinds, y_bin):
    """Columns that almost perfectly reveal a binary target on their own -> excluded by default."""
    out = {}
    if y_bin is None:
        return out
    flagged_binary = []
    for c in df.columns:
        if c == target or kinds[c] in ("id", "constant", "datetime"):
            continue
        s = df[c]
        if kinds[c] == "binary":
            on = s == 1
            if on.sum() >= 5 and y_bin[on].mean() >= 0.95:
                out[c] = f"whenever {c} = 1 the target is positive ({y_bin[on].mean():.0%}): recorded as part of the outcome"
                flagged_binary.append(c)
                continue
        if kinds[c] in ("numeric", "binary"):
            v = s.fillna(s.median())
            try:
                auc = roc_auc_score(y_bin, v)
            except ValueError:
                continue
            if max(auc, 1 - auc) >= 0.98:
                out[c] = f"alone predicts the target almost perfectly (AUC {max(auc, 1 - auc):.2f}): likely leakage"
    if len(flagged_binary) >= 2:  # sibling 0/1 flags recorded next to the leaked ones (e.g. AI4I's RNF)
        for c in df.columns:
            if c not in out and c != target and kinds[c] == "binary" and len(c) <= 6 and c.isupper() and \
                    all(f.isupper() and len(f) <= 6 for f in flagged_binary):
                out[c] = f"another outcome flag recorded alongside {', '.join(flagged_binary)}"
    return out


def _domain_features(X):
    """Physically meaningful extras when the columns are recognisable (reported to the user)."""
    added = []
    low = {c: c.lower() for c in X.columns}
    torque = next((c for c, l in low.items() if "torque" in l), None)
    speed = next((c for c, l in low.items() if "rpm" in l or "rotational speed" in l or l.startswith("speed")), None)
    if torque and speed:
        X["power [W] (torque x speed)"] = X[torque] * X[speed] * 2 * np.pi / 60
        added.append("power [W] = torque x rotational speed")
    temps = [c for c, l in low.items() if "temp" in l and pd.api.types.is_numeric_dtype(X[c])]
    if len(temps) == 2:
        X["temperature difference"] = X[temps[1]] - X[temps[0]]
        added.append(f"temperature difference = {temps[1]} - {temps[0]}")
    wear = next((c for c, l in low.items() if "wear" in l), None)
    if wear and torque:
        X["strain (wear x torque)"] = X[wear] * X[torque]
        added.append("strain = tool wear x torque")
    return added


def _preprocessor(num, cat, scale):
    steps_num = [("impute", SimpleImputer(strategy="median"))] + ([("scale", StandardScaler())] if scale else [])
    return ColumnTransformer([
        ("num", Pipeline(steps_num), num),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore", max_categories=30))]), cat),
    ])


# ---------------------------------------------------------------- planning
def _exclusions(df, target, kinds, y_bin):
    excluded = {}
    for c in df.columns:
        if c == target:
            continue
        if kinds[c] == "id":
            excluded[c] = "identifier (unique per row): would let the model memorise rows"
        elif kinds[c] == "constant":
            excluded[c] = "constant: carries no information"
        elif df[c].isna().mean() > 0.6:
            excluded[c] = f"{df[c].isna().mean():.0%} missing"
    for c, why in _leakage(df.drop(columns=list(excluded)), target, kinds, y_bin).items():
        excluded[c] = why
    return excluded


def _task(y_raw, kind):
    nun = y_raw.nunique()
    if nun == 2:
        return "binary"
    if nun <= 20 and (kind != "numeric" or np.allclose(y_raw.dropna(), y_raw.dropna().round())):
        return "multiclass"
    return "regression"


def plan(df, target):
    """What training WOULD do for this target: task type, columns used, columns excluded and why."""
    if target not in df.columns:
        raise ValueError(f"target column '{target}' not found")
    d = df[df[target].notna()]
    kinds = {c: _kind(d[c], c) for c in d.columns}
    task = _task(d[target], kinds[target])
    y_bin = None
    if task == "binary":
        classes = sorted(d[target].unique(), key=str)
        pos = 1 if 1 in classes else True if True in classes else classes[-1]
        y_bin = (d[target] == pos).astype(int)
    excl = _exclusions(d, target, kinds, y_bin)
    X = d[[c for c in d.columns if c != target and c not in excl]].copy()
    return {"target": target, "task": task, "excluded": excl, "engineered": _domain_features(X),
            "positive_rate": None if y_bin is None else round(float(y_bin.mean()), 4)}


# ---------------------------------------------------------------- training
def train(df, target, use=None):
    if target not in df.columns:
        raise ValueError(f"target column '{target}' not found")
    df = df[df[target].notna()].copy()
    if len(df) < 50:
        raise ValueError("need at least 50 rows with a target value")
    kinds = {c: _kind(df[c], c) for c in df.columns}
    y_raw = df[target]
    task = _task(y_raw, kinds[target])
    if task == "binary":
        classes = sorted(y_raw.unique(), key=str)
        pos = 1 if 1 in classes else True if True in classes else classes[-1]
        y = (y_raw == pos).astype(int)
    elif task == "multiclass":
        y = y_raw.astype(str)
    else:
        y = pd.to_numeric(y_raw, errors="coerce")
        if y.isna().any():
            raise ValueError("target has non-numeric values; pick a category column instead")

    excluded = _exclusions(df, target, kinds, y if task == "binary" else None)
    if use is not None:  # user overrides: explicit feature list wins (target never)
        excluded = {c: w for c, w in excluded.items() if c not in use}
        for c in df.columns:
            if c != target and c not in use and c not in excluded:
                excluded[c] = "left out by you"
    feats = [c for c in df.columns if c != target and c not in excluded]
    if not feats:
        raise ValueError("no usable feature columns left")

    date_col = next((c for c in feats if kinds[c] == "datetime"), None)
    X = df[feats].copy()
    if date_col:
        X[date_col] = pd.to_datetime(X[date_col], errors="coerce")
        X["month"] = X[date_col].dt.month
        X["day of week"] = X[date_col].dt.dayofweek
    added = _domain_features(X)
    num = [c for c in X.columns if c != date_col and pd.api.types.is_numeric_dtype(X[c])]
    cat = [c for c in X.columns if c != date_col and c not in num]
    for c in cat:
        X[c] = X[c].astype(str)

    if date_col:  # temporal split: past -> future
        order = np.argsort(X[date_col].values)
        n = len(X)
        tr, va, te = order[:int(n * .6)], order[int(n * .6):int(n * .8)], order[int(n * .8):]
        split = f"by time on '{date_col}': oldest 60% train, next 20% validation, newest 20% test"
    else:
        idx = np.arange(len(X))
        strat = y if task != "regression" else None
        tr, rest = train_test_split(idx, test_size=0.4, random_state=SEED, stratify=strat)
        va, te = train_test_split(rest, test_size=0.5, random_state=SEED, stratify=None if strat is None else strat.iloc[rest])
        split = "stratified random 60% train / 20% validation / 20% test (seed 42)" if strat is not None else \
                "random 60% train / 20% validation / 20% test (seed 42)"
    Xf = X.drop(columns=[date_col]) if date_col else X
    Xtr, Xva, Xte = Xf.iloc[tr], Xf.iloc[va], Xf.iloc[te]
    ytr, yva, yte = y.iloc[tr], y.iloc[va], y.iloc[te]

    if task == "regression":
        cands = {"baseline (mean)": Pipeline([("pre", _preprocessor(num, cat, True)), ("m", DummyRegressor())]),
                 "ridge regression": Pipeline([("pre", _preprocessor(num, cat, True)), ("m", Ridge(alpha=1.0))]),
                 "gradient boosting": Pipeline([("pre", _preprocessor(num, cat, False)),
                                                ("m", HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, random_state=SEED))])}
    else:
        cands = {"baseline (most frequent / base rate)": Pipeline([("pre", _preprocessor(num, cat, True)), ("m", DummyClassifier(strategy="prior"))]),
                 "logistic regression": Pipeline([("pre", _preprocessor(num, cat, True)),
                                                  ("m", LogisticRegression(max_iter=3000, class_weight="balanced"))]),
                 "gradient boosting": Pipeline([("pre", _preprocessor(num, cat, False)),
                                                ("m", HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, random_state=SEED,
                                                                                     class_weight="balanced" if task == "binary" else None))])}

    def score(m, X_, y_, thr=None):
        if task == "regression":
            p = m.predict(X_)
            return {"r2": round(float(r2_score(y_, p)), 4), "mae": round(float(mean_absolute_error(y_, p)), 4),
                    "rmse": round(float(np.sqrt(mean_squared_error(y_, p))), 4)}
        if task == "binary":
            p = m.predict_proba(X_)[:, 1]
            r = {"pr_auc": round(float(average_precision_score(y_, p)), 4)}
            try:
                r["roc_auc"] = round(float(roc_auc_score(y_, p)), 4)
            except ValueError:
                r["roc_auc"] = None
            if thr is not None:
                yh = (p >= thr).astype(int)
                r.update(precision=round(float(precision_score(y_, yh, zero_division=0)), 4),
                         recall=round(float(recall_score(y_, yh, zero_division=0)), 4),
                         f1=round(float(f1_score(y_, yh, zero_division=0)), 4),
                         accuracy=round(float(accuracy_score(y_, yh)), 4))
            return r
        yh = m.predict(X_)
        return {"accuracy": round(float(accuracy_score(y_, yh)), 4),
                "macro_f1": round(float(f1_score(y_, yh, average="macro", zero_division=0)), 4)}

    key = {"binary": "pr_auc", "multiclass": "macro_f1", "regression": "r2"}[task]
    table, fitted = [], {}
    for name, m in cands.items():
        m.fit(Xtr, ytr)
        fitted[name] = m
        table.append({"model": name, "validation": score(m, Xva, yva)})
    real = [r for r in table if not r["model"].startswith("baseline")]
    chosen = max(real, key=lambda r: r["validation"][key] if r["validation"][key] is not None else -1)["model"]
    m = fitted[chosen]

    thr = None
    if task == "binary":  # decision threshold = best F1 on VALIDATION
        pv = m.predict_proba(Xva)[:, 1]
        qs = np.unique(np.quantile(pv, np.linspace(0.5, 0.995, 120)))
        thr = float(max(qs, key=lambda q: f1_score(yva, (pv >= q).astype(int), zero_division=0)))
    for r in table:
        r["test"] = score(fitted[r["model"]], Xte, yte, thr if r["model"] == chosen else (0.5 if task == "binary" else None))
    test = next(r["test"] for r in table if r["model"] == chosen)
    if task == "binary":
        cm = confusion_matrix(yte, (m.predict_proba(Xte)[:, 1] >= thr).astype(int), labels=[0, 1]).tolist()
    elif task == "multiclass":
        labels = sorted(y.unique().tolist())
        cm = {"labels": labels, "matrix": confusion_matrix(yte, m.predict(Xte), labels=labels).tolist()}
    else:
        cm = None

    sub = Xte.sample(min(len(Xte), 3000), random_state=SEED)
    pi = permutation_importance(m, sub, yte.loc[sub.index], n_repeats=3, random_state=SEED,
                                scoring={"binary": "average_precision", "multiclass": "f1_macro", "regression": "r2"}[task])
    drivers = sorted(({"feature": c, "importance": round(float(v), 4)} for c, v in zip(Xf.columns, pi.importances_mean)),
                     key=lambda d: -d["importance"])[:8]

    # demo rows for "predict on new rows": taken from the TEST split, which the deployed model never sees
    # (it is refit on train + validation only). Mix in positives so a rare class is visible.
    te_df = df.iloc[te]
    if task == "binary":
        pos_idx = te_df.index[y.iloc[te] == 1][:8].tolist()
        neg_idx = te_df.index[y.iloc[te] == 0][:25 - len(pos_idx)].tolist()
        demo = df.loc[pos_idx + neg_idx]
    else:
        demo = te_df.head(25)
    demo_csv = demo.drop(columns=[target]).to_csv(index=False)
    demo_actual = demo[target].astype(str).tolist()

    # deployable model: refit the chosen recipe on train + validation (test stays unseen)
    trv = np.concatenate([tr, va])
    final = cands[chosen].fit(Xf.iloc[trv], y.iloc[trv])
    mid = uuid.uuid4().hex[:12]
    _MODELS[mid] = {"model": final, "features": feats, "date_col": date_col, "task": task, "threshold": thr,
                    "target": target, "columns": list(Xf.columns), "num": num, "cat": cat,
                    "ref": {c: (float(Xf.iloc[trv][c].median()) if c in num else Xf.iloc[trv][c].mode().iloc[0]) for c in Xf.columns},
                    "stats": {c: (float(Xf.iloc[trv][c].mean()), float(Xf.iloc[trv][c].std() or 1.0)) for c in num}}
    while len(_MODELS) > MAX_MODELS:
        _MODELS.popitem(last=False)
    return {"model_id": mid, "task": task, "target": target, "positive_rate": round(float(y.mean()), 4) if task == "binary" else None,
            "rows": len(df), "features_used": feats, "engineered": added, "excluded": excluded, "split": split,
            "sizes": {"train": len(tr), "validation": len(va), "test": len(te)}, "models": table, "chosen": chosen,
            "selection_metric": key, "threshold": None if thr is None else round(thr, 4), "test": test,
            "confusion": cm, "drivers": drivers, "demo_rows_csv": demo_csv, "demo_actual": demo_actual}


# ---------------------------------------------------------------- prediction on new rows
def predict(model_id, df, explain_rows=200):
    b = _MODELS.get(model_id)
    if b is None:
        raise ValueError("model not found (it may have expired): train again")
    missing = [c for c in b["features"] if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    X = df[b["features"]].copy()
    if b["date_col"]:
        X[b["date_col"]] = pd.to_datetime(X[b["date_col"]], errors="coerce")
        X["month"] = X[b["date_col"]].dt.month
        X["day of week"] = X[b["date_col"]].dt.dayofweek
    _domain_features(X)
    for c in b["cat"]:
        X[c] = X[c].astype(str)
    X = X[b["columns"]]
    m, task = b["model"], b["task"]
    if task == "binary":
        p = m.predict_proba(X)[:, 1]
        label = (p >= b["threshold"]).astype(int)
        score_fn = lambda Z: m.predict_proba(Z)[:, 1]
    elif task == "multiclass":
        proba = m.predict_proba(X)
        p = proba.max(axis=1)
        label = m.predict(X)
        cls = list(m.classes_)
        score_fn = lambda Z: m.predict_proba(Z)[np.arange(len(Z)), [cls.index(l) for l in label[:len(Z)]]]
    else:
        p = m.predict(X)
        label = p
        score_fn = lambda Z: m.predict(Z)
    reasons = [""] * len(X)
    k = min(len(X), explain_rows)
    if k:
        base = score_fn(X.iloc[:k])
        deltas = {}
        for c in X.columns:  # how much does resetting this input to a typical value change the score?
            Z = X.iloc[:k].copy()
            Z[c] = b["ref"][c]
            deltas[c] = base - score_fn(Z)
        scale = 100 if task != "regression" else 1
        floor = 0.5 if task != "regression" else 1e-9 + 0.01 * float(np.std(base) or 1)
        for i in range(k):
            c, v = max(((c, deltas[c][i]) for c in X.columns), key=lambda t: abs(t[1]))
            if abs(v * scale) < floor:
                # no single input moves the score: either everything is typical, or several inputs act together
                z = sorted(((c2, (X.iloc[i][c2] - b["stats"][c2][0]) / b["stats"][c2][1]) for c2 in b["stats"]),
                           key=lambda t: -abs(t[1]))[:2]
                flagged = (task == "binary" and label[i] == 1) or (task == "regression" and abs(base[i] - np.mean(base)) > np.std(base))
                if flagged and z and abs(z[0][1]) >= 1.5:
                    reasons[i] = "several inputs together; most unusual: " + ", ".join(
                        f"{c2} = {X.iloc[i][c2]:.4g} ({zz:+.1f} SD)" for c2, zz in z if abs(zz) >= 1)
                else:
                    reasons[i] = "no single input stands out (typical values)"
                continue
            val = X.iloc[i][c]
            val = f"{val:.4g}" if isinstance(val, (int, float, np.number)) else str(val)
            reasons[i] = f"{c} = {val} ({'+' if v > 0 else ''}{v * scale:.1f}{' pts' if task != 'regression' else ''})"
    out = pd.DataFrame({"row": np.arange(1, len(X) + 1)})
    if task == "binary":
        out["probability"] = np.round(p, 4)
        out["predicted"] = label
    elif task == "multiclass":
        out["predicted"] = label
        out["confidence"] = np.round(p, 4)
    else:
        out["predicted"] = np.round(p, 4)
    out["main_reason"] = reasons
    return out
