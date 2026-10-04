#!/usr/bin/env python3
"""EcoRisk AI: 24 h / 48 h / 72 h prediction windows, business value, and base rates.

1. Trains the 24 h and 48 h models with exactly the 72 h recipe (ml/ef_model.py): same features,
   monotonic gradient boosting, train <= 2018 / validation 2019-2021 / TEST 2022-2025, alert
   threshold chosen on validation. The 72 h model itself comes from ef_model.py, unchanged.
2. Cost-loss value on the TEST years for every window: a business pays C to protect, or loses L
   if hit unprotected. Acting when p > C/L is the standard decision rule. Relative economic value
   V = (E_climatology - E_forecast) / (E_climatology - E_perfect): 1 = perfect foresight, 0 = no
   better than the best fixed policy (always act / never act).
3. Base rates for "relative risk": observed rate of the event per site x month (train years) and
   per month across all sites, so a prediction can be read as "N x the normal chance".

Output: ml/ef_horizons.json, ml/ef_model_24.pkl, ml/ef_model_48.pkl
"""
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))
from ef_model import FEATS, MONOTONIC, SKEWED, TEST_START, VAL_START, best_f1_threshold, metrics, prep  # noqa: E402

LABEL = {24: "y_24h", 48: "y_48h", 72: "y"}
RATIOS = [round(float(r), 4) for r in np.geomspace(0.005, 0.8, 40)]


def value_curve(y, p, ratios=RATIOS):
    """Relative economic value of acting when p > C/L, per cost/loss ratio (expenses in units of L)."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    ybar = y.mean()
    out = []
    for r in ratios:
        act = p >= r
        e_f = np.mean(np.where(act, r, y))
        e_c = min(r, ybar)
        e_p = ybar * r
        v = (e_c - e_f) / (e_c - e_p) if e_c > e_p else 0.0
        out.append({"ratio": r, "value": round(float(v), 4), "expense_forecast": round(float(e_f), 6),
                    "expense_best_fixed": round(float(e_c), 6), "expense_perfect": round(float(e_p), 6)})
    return out


def main():
    df = pd.read_csv(os.path.join(ROOT, "ml", "ef_features.csv"), parse_dates=["date"])
    tr, va, te = df[df.date < VAL_START], df[(df.date >= VAL_START) & (df.date < TEST_START)], df[df.date >= TEST_START]
    with open(os.path.join(ROOT, "ml", "ef_model.pkl"), "rb") as f:
        m72 = pickle.load(f)
    res = {"split": {"train": "1995-2018", "validation": "2019-2021", "test": "2022-2025"},
           "event": "extreme-rainfall day (>= site's train-years 99th percentile of daily rain)", "windows": {}}
    mk = lambda: HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=250, l2_regularization=1.0,
                                                random_state=0, monotonic_cst=[MONOTONIC.get(c, 0) for c in FEATS])
    fitted = {h: mk().fit(prep(tr), tr[lab]) for h, lab in LABEL.items()}  # train only -> honest test scores
    PV, PT = {}, {}
    run_v = run_t = None
    for h in sorted(LABEL):  # same cross-window consistency as the product: p72 >= p48 >= p24
        pv, pt = fitted[h].predict_proba(prep(va))[:, 1], fitted[h].predict_proba(prep(te))[:, 1]
        run_v = pv if run_v is None else np.maximum(run_v, pv)
        run_t = pt if run_t is None else np.maximum(run_t, pt)
        PV[h], PT[h] = run_v, run_t
    for h, lab in LABEL.items():
        pv, pt = PV[h], PT[h]
        thr = best_f1_threshold(va[lab], pv) if h != 72 else m72["threshold"]
        r = metrics(te[lab], pt, thr)
        clim = tr.assign(mo=tr.date.dt.month).groupby(["site_id", "mo"])[lab].mean()
        pc = te.assign(mo=te.date.dt.month).join(clim.rename("c"), on=["site_id", "mo"])["c"].fillna(tr[lab].mean())
        r["climatology"] = {"roc_auc": round(float(roc_auc_score(te[lab], pc)), 4),
                            "pr_auc": round(float(average_precision_score(te[lab], pc)), 4),
                            "brier": round(float(brier_score_loss(te[lab], pc)), 5)}
        r["threshold_from_validation"] = round(float(thr), 4)
        r["test_positive_rate"] = round(float(te[lab].mean()), 4)
        r["value_curve_test"] = value_curve(te[lab], pt)
        best = max(r["value_curve_test"], key=lambda x: x["value"])
        r["peak_value"] = {"ratio": best["ratio"], "value": best["value"]}
        r["base_rate_site_month"] = {s: {int(mo): round(float(v), 5) for (ss, mo), v in clim.items() if ss == s}
                                     for s in sorted(df.site_id.unique())}
        r["base_rate_month_all"] = {int(k): round(float(v), 5) for k, v in tr.groupby(tr.date.dt.month)[lab].mean().items()}
        res["windows"][str(h)] = r
        print(f"{h:>2} h  TEST AUC={r['roc_auc']} PR-AUC={r['pr_auc']} (clim {r['climatology']['pr_auc']}) "
              f"Brier={r['brier']} (clim {r['climatology']['brier']}) P={r['precision']} R={r['recall']} "
              f"base={r['test_positive_rate']}  peak value {best['value']:.2f} at C/L={best['ratio']}")
        if h != 72:  # deployable 24/48 h models: refit on train+val, test stays unseen (same as 72 h)
            trv = pd.concat([tr, va])
            with open(os.path.join(ROOT, "ml", f"ef_model_{h}.pkl"), "wb") as f:
                pickle.dump({"model": mk().fit(prep(trv), trv[lab]), "features": FEATS, "skewed": SKEWED,
                             "threshold": thr, "name": "grad_boost", "horizon_h": h}, f)
    res["consistency"] = "p(within 72 h) >= p(within 48 h) >= p(within 24 h), enforced by running maximum"
    with open(os.path.join(ROOT, "ml", "ef_horizons.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("wrote ml/ef_horizons.json, ml/ef_model_24.pkl, ml/ef_model_48.pkl")


if __name__ == "__main__":
    main()
