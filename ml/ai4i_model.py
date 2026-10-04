#!/usr/bin/env python3
"""EcoRisk AI · machine module: predict what happens next on AI4I 2020 (ALG-DATA-02 base dataset).

Pipeline (every number on the page comes from this script's output, ml/ai4i_results.json):
  1. Exploration & cleaning: class balance, failure modes, distributions, missing values, duplicates,
     physical range checks; IDs (UDI, Product ID) dropped; failure-mode columns (TWF/HDF/PWF/OSF/RNF)
     excluded as INPUTS because they are part of the outcome (they are used only as separate targets).
  2. Feature engineering from the dataset's documented failure mechanisms:
       power [W] = torque x speed (PWF outside 3.5-9 kW) · temperature difference (HDF below 8.6 K at
       < 1380 rpm) · strain = tool wear x torque and its ratio to the per-type limit (OSF above
       11/12/13k minNm for L/M/H) · tool wear itself (TWF at 200-240 min).
  3. Model selection: stratified 80/20 split; the 20% TEST set is untouched until the end. On the 80%
     train set, 5-fold stratified cross-validation compares a baseline, logistic regression, random
     forest and gradient boosting, with and without engineered features (ablation). Chosen by CV PR-AUC.
     The alert threshold is chosen on out-of-fold train predictions (best F1), never on test.
  4. Test: the chosen model, refit on all train rows, is scored once on the test set.
  5. Failure type: one model per mode (TWF, HDF, PWF, OSF), same split. RNF is random by design.
  6. What happens next: each production run adds 2/3/5 min of tool wear (L/M/H); projecting wear
     forward gives "runs until the failure risk crosses the alert line".

Outputs: ml/ai4i_results.json, ml/ai4i_models.pkl, ecorisk-ai/samples/ai4i_unseen_machines.csv
(held-out test machines, failure columns removed) and ..._with_answers.csv.
"""
import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "ecorisk-ai", "samples", "ai4i2020.csv")
SEED = 42
RAW = ["type_code", "air_K", "process_K", "rpm", "torque_Nm", "wear_min"]
ENG = ["power_W", "temp_diff_K", "strain", "strain_ratio", "wear_ge_200"]
FEATS = RAW + ENG
MODES = ["TWF", "HDF", "PWF", "OSF"]
TYPE_CODE = {"L": 0, "M": 1, "H": 2}
STRAIN_LIMIT = {0: 11000.0, 1: 12000.0, 2: 13000.0}   # minNm, per AI4I documentation
WEAR_PER_RUN = {0: 2, 1: 3, 2: 5}                       # min of tool wear added per run (L/M/H)
COLMAP = {"Type": "type", "Air temperature [K]": "air_K", "Process temperature [K]": "process_K",
          "Rotational speed [rpm]": "rpm", "Torque [Nm]": "torque_Nm", "Tool wear [min]": "wear_min"}
NICE = {"type_code": "product type (L/M/H)", "air_K": "air temperature", "process_K": "process temperature",
        "rpm": "rotational speed", "torque_Nm": "torque", "wear_min": "tool wear", "power_W": "power (torque x speed)",
        "temp_diff_K": "temperature difference", "strain": "strain (wear x torque)",
        "strain_ratio": "strain vs. type limit", "wear_ge_200": "tool past 200 min"}


def load(path=DATA):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    return df


def features(df):
    """Raw AI4I columns (original names) -> model inputs. Raises a clear error for missing columns."""
    missing = [c for c in COLMAP if c not in df.columns]
    if missing:
        raise ValueError(f"missing AI4I columns: {missing}")
    X = pd.DataFrame(index=df.index)
    t = df["Type"].astype(str).str.strip().str.upper()
    bad = ~t.isin(TYPE_CODE)
    if bad.any():
        raise ValueError(f"Type must be L, M or H (row {int(bad.idxmax()) + 1} has '{df['Type'].iloc[int(bad.argmax())]}')")
    X["type_code"] = t.map(TYPE_CODE)
    for src, dst in list(COLMAP.items())[1:]:
        v = pd.to_numeric(df[src], errors="coerce")
        if v.isna().any():
            raise ValueError(f"'{src}' has missing or non-numeric values (row {int(v.isna().values.argmax()) + 1})")
        X[dst] = v
    X["power_W"] = X.torque_Nm * X.rpm * 2 * np.pi / 60
    X["temp_diff_K"] = X.process_K - X.air_K
    X["strain"] = X.wear_min * X.torque_Nm
    X["strain_ratio"] = X.strain / X.type_code.map(STRAIN_LIMIT)
    X["wear_ge_200"] = (X.wear_min >= 200).astype(int)
    return X


def physical_checks(df):
    """Values a real milling machine cannot have (used for uploads and reported for the dataset)."""
    rules = {"Air temperature [K]": (250, 350), "Process temperature [K]": (250, 360),
             "Rotational speed [rpm]": (0, 5000), "Torque [Nm]": (0, 200), "Tool wear [min]": (0, 500)}
    issues = []
    for c, (lo, hi) in rules.items():
        v = pd.to_numeric(df[c], errors="coerce")
        n = int(((v < lo) | (v > hi)).sum())
        if n:
            issues.append(f"{c}: {n} values outside {lo}-{hi}")
    return issues


def models():
    return {
        "baseline (failure base rate)": lambda: DummyClassifier(strategy="prior"),
        "logistic regression": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, class_weight="balanced")),
        "random forest": lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=2, class_weight="balanced_subsample",
                                                       n_jobs=-1, random_state=SEED),
        "gradient boosting": lambda: HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, random_state=SEED),
    }


def best_f1_threshold(y, p):
    qs = np.unique(np.quantile(p, np.linspace(0.80, 0.999, 150)))
    return float(max(qs, key=lambda q: f1_score(y, (p >= q).astype(int), zero_division=0)))


def runs_until_alert(model, X_row, thr, max_runs=200):
    """Project tool wear forward run by run (wear grows 2/3/5 min per run for L/M/H)."""
    inc = WEAR_PER_RUN[int(X_row["type_code"])]
    rows = []
    for k in range(max_runs + 1):
        r = X_row.copy()
        r["wear_min"] = X_row["wear_min"] + k * inc
        if r["wear_min"] > 260:  # beyond anything observed (max 253): stop projecting
            break
        rows.append(r)
    P = pd.DataFrame(rows)
    P["strain"] = P.wear_min * P.torque_Nm
    P["strain_ratio"] = P.strain / P.type_code.map(STRAIN_LIMIT)
    P["wear_ge_200"] = (P.wear_min >= 200).astype(int)
    p = model.predict_proba(P[FEATS])[:, 1]
    hit = np.where(p >= thr)[0]
    return (int(hit[0]) if len(hit) else None), P.wear_min.tolist(), p.round(4).tolist()


def main():
    df = load()
    y = df["Machine failure"].astype(int)
    X = features(df)

    # ---- 1. exploration & cleaning
    eda = {
        "rows": len(df), "columns": len(df.columns), "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()), "physical_issues": physical_checks(df),
        "failure_rate": round(float(y.mean()), 4), "failures": int(y.sum()),
        "mode_counts": {m: int(df[m].sum()) for m in MODES + ["RNF"]},
        "failures_without_mode": int(((y == 1) & (df[MODES + ["RNF"]].sum(axis=1) == 0)).sum()),
        "type_share": df["Type"].value_counts(normalize=True).round(4).to_dict(),
        "failure_rate_by_type": df.groupby("Type")["Machine failure"].mean().round(4).to_dict(),
        "dropped_as_ids": ["UDI", "Product ID"],
        "excluded_as_leakage": {m: f"failure mode recorded as part of the outcome (P(failure | {m}=1) = "
                                   f"{df.loc[df[m] == 1, 'Machine failure'].mean():.2f})" for m in MODES + ["RNF"]},
        "summary": {NICE[c]: {k: round(float(v), 2) for k, v in X[c].describe()[["min", "25%", "50%", "75%", "max"]].items()}
                    for c in ["air_K", "process_K", "rpm", "torque_Nm", "wear_min", "power_W", "temp_diff_K"]},
    }
    curves = {}  # failure rate across bins of the key drivers (for charts)
    for c, bins in {"wear_min": np.arange(0, 270, 20), "temp_diff_K": np.arange(7, 13, 0.5),
                    "power_W": np.arange(2000, 12500, 750), "rpm": np.arange(1150, 2950, 150),
                    "strain_ratio": np.arange(0, 1.45, 0.1)}.items():
        cut = pd.cut(X[c], bins)
        g = pd.DataFrame({"b": cut, "y": y}).groupby("b", observed=True)["y"].agg(["mean", "size"])
        curves[c] = [{"from": round(float(i.left), 3), "to": round(float(i.right), 3), "rate": round(float(r["mean"]), 4),
                      "n": int(r["size"])} for i, r in g.iterrows() if r["size"] >= 15]
    eda["failure_rate_curves"] = curves

    # ---- 2/3. split + cross-validated model selection (with and without engineered features)
    idx_tr, idx_te = train_test_split(np.arange(len(df)), test_size=0.2, random_state=SEED, stratify=y)
    Xtr, Xte, ytr, yte = X.iloc[idx_tr], X.iloc[idx_te], y.iloc[idx_tr], y.iloc[idx_te]
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    table, oof = [], {}
    for name, make in models().items():
        for fs_name, fs in (("raw sensors only", RAW), ("+ engineered", FEATS)):
            if name.startswith("baseline") and fs_name != "+ engineered":
                continue
            per_fold = []
            for f_tr, f_va in cv.split(Xtr, ytr):
                m = make().fit(Xtr.iloc[f_tr][fs], ytr.iloc[f_tr])
                pv = m.predict_proba(Xtr.iloc[f_va][fs])[:, 1]
                per_fold.append((average_precision_score(ytr.iloc[f_va], pv), roc_auc_score(ytr.iloc[f_va], pv)))
            a = np.array(per_fold)
            table.append({"model": name, "features": fs_name, "cv_pr_auc": round(float(a[:, 0].mean()), 4),
                          "cv_pr_auc_sd": round(float(a[:, 0].std()), 4), "cv_roc_auc": round(float(a[:, 1].mean()), 4)})
            print(f"{name:30} {fs_name:18} CV PR-AUC {a[:,0].mean():.3f} ± {a[:,0].std():.3f}  ROC {a[:,1].mean():.3f}")
    real = [r for r in table if not r["model"].startswith("baseline")]
    best = max(real, key=lambda r: r["cv_pr_auc"])
    chosen, fs = best["model"], (FEATS if best["features"] == "+ engineered" else RAW)
    print("chosen:", chosen, best["features"])

    # threshold from out-of-fold predictions on TRAIN
    p_oof = cross_val_predict(models()[chosen](), Xtr[fs], ytr, cv=cv, method="predict_proba")[:, 1]
    thr = best_f1_threshold(ytr, p_oof)

    # ---- 4. test, once
    final = models()[chosen]().fit(Xtr[fs], ytr)
    pt = final.predict_proba(Xte[fs])[:, 1]
    yh = (pt >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(yte, yh, labels=[0, 1]).ravel()
    base = DummyClassifier(strategy="prior").fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    frac, mean_pred = calibration_curve(yte, pt, n_bins=6, strategy="quantile")
    test = {"pr_auc": round(float(average_precision_score(yte, pt)), 4), "roc_auc": round(float(roc_auc_score(yte, pt)), 4),
            "precision": round(float(precision_score(yte, yh, zero_division=0)), 4), "recall": round(float(recall_score(yte, yh)), 4),
            "f1": round(float(f1_score(yte, yh)), 4), "brier": round(float(brier_score_loss(yte, pt)), 5),
            "baseline_pr_auc": round(float(average_precision_score(yte, base)), 4), "baseline_brier": round(float(brier_score_loss(yte, base)), 5),
            "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}, "threshold": round(thr, 4),
            "n_test": len(yte), "test_failures": int(yte.sum()),
            "calibration": [{"predicted": round(float(m_), 4), "observed": round(float(f_), 4)} for m_, f_ in zip(mean_pred, frac)]}
    # missed failures, by mode (honest breakdown)
    te_df = df.iloc[idx_te]
    missed = te_df[(yte.values == 1) & (yh == 0)]
    test["missed_by_mode"] = {m: int(missed[m].sum()) for m in MODES + ["RNF"]}
    test["missed_without_mode"] = int((missed[MODES + ["RNF"]].sum(axis=1) == 0).sum())
    print("TEST", test)

    pi = permutation_importance(final, Xte[fs], yte, scoring="average_precision", n_repeats=5, random_state=SEED)
    drivers = sorted(({"feature": NICE[c], "key": c, "importance": round(float(v), 4)} for c, v in zip(fs, pi.importances_mean)),
                     key=lambda d: -d["importance"])

    # ---- 5. failure type models (modes are TARGETS here, never inputs)
    mode_models, mode_res = {}, {}
    for mname in MODES:
        ym = df[mname].astype(int)
        mm = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, random_state=SEED).fit(Xtr[FEATS], ym.iloc[idx_tr])
        pm = mm.predict_proba(Xte[FEATS])[:, 1]
        mode_models[mname] = mm
        mode_res[mname] = {"test_positives": int(ym.iloc[idx_te].sum()), "pr_auc": round(float(average_precision_score(ym.iloc[idx_te], pm)), 4),
                           "roc_auc": round(float(roc_auc_score(ym.iloc[idx_te], pm)), 4)}
    print("modes", mode_res)

    # ---- 6. what happens next: example on a real held-out machine
    final_all = final  # deployable = trained on train split only (test stays a fair yardstick)
    ex_i = int(np.argmin(np.abs(Xte.wear_min.values - 170) + 1000 * (Xte.type_code.values != 0) + 1000 * (yte.values == 1)))
    k, wears, probs = runs_until_alert(final_all, Xte.iloc[ex_i][FEATS], thr)

    res = {"generated_by": "ml/ai4i_model.py", "dataset": "AI4I 2020 Predictive Maintenance (UCI, S. Matzka, CC BY 4.0)",
           "eda": eda, "split": {"test_size": 0.2, "train": len(idx_tr), "test": len(idx_te), "cv_folds": 5, "seed": SEED, "stratified": True},
           "features": {"raw": [NICE[c] for c in RAW], "engineered": [NICE[c] for c in ENG],
                        "rationale": {"power (torque x speed)": "power failure happens below 3.5 kW or above 9 kW",
                                      "temperature difference": "heat-dissipation failure below 8.6 K at speeds under 1,380 rpm",
                                      "strain (wear x torque)": "overstrain failure above 11,000 / 12,000 / 13,000 minNm (L / M / H)",
                                      "strain vs. type limit": "the same, scaled to each product type's limit",
                                      "tool past 200 min": "tool-wear failure happens between 200 and 240 min"}},
           "model_selection": table, "chosen": {"model": chosen, "features": best["features"]}, "test": test,
           "drivers": drivers, "modes": mode_res,
           "example_projection": {"wear_start": wears[0], "runs_until_alert": k, "wear": wears, "p": probs}}
    with open(os.path.join(ROOT, "ml", "ai4i_results.json"), "w") as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(ROOT, "ml", "ai4i_models.pkl"), "wb") as f:
        pickle.dump({"model": final_all, "features": fs, "threshold": thr, "modes": mode_models, "mode_features": FEATS}, f)
    # unseen-machine samples from the TEST split
    keep = ["UDI", "Product ID"] + list(COLMAP)
    te_df[keep].to_csv(os.path.join(ROOT, "ecorisk-ai", "samples", "ai4i_unseen_machines.csv"), index=False)
    te_df[keep + ["Machine failure"] + MODES + ["RNF"]].to_csv(
        os.path.join(ROOT, "ecorisk-ai", "samples", "ai4i_unseen_machines_with_answers.csv"), index=False)
    print("wrote ml/ai4i_results.json, ml/ai4i_models.pkl, samples")


if __name__ == "__main__":
    main()
