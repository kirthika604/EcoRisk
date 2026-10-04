#!/usr/bin/env python3
"""EcoForecast step 2: train, validate and test the next-3-day extreme-rainfall forecaster.

Strictly temporal split (no shuffling):  train <= 2018 | validation 2019-2021 | TEST 2022-2025
(the test years are never used for fitting, model selection, or the alert threshold).
Baselines: climatology (site x season base rate) and persistence (extreme today -> extreme soon).
Output: ml/ef_results.json and ml/ef_model.pkl (the model used by ml/ef_predict.py).
"""
import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, precision_score,
                             recall_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAL_START, TEST_START = pd.Timestamp("2019-01-01"), pd.Timestamp("2022-01-01")
FEATS = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d", "wet_days_7d", "rain_accel",
         "t2m", "rh2m", "ws2m", "dew_spread", "ps_anom", "ps_chg_1d", "ps_chg_3d", "rh_chg_3d",
         "doy_sin", "doy_cos", "mean_slope_degrees",
         "elevation_mean_m", "terrain_is_coastal"]
SKEWED = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d"]
# Physical direction constraints: more rain / wetter air / a falling barometer can never LOWER the
# forecast. Removes tree-model artefacts where adding rain dipped the probability (audit: 1.6% of
# days dipped >5 points before; 0% after), at no measurable cost in accuracy.
# Land-change trends (NDVI/NDBI) are NOT inputs here: they are constant per site, so in a daily
# weather model they can only act as site identifiers. Ablation: removing them left in-source PR-AUC
# 0.209 -> 0.217 and external recalibrated PR-AUC 0.232 -> 0.236. Land change belongs to the
# structural (EcoRisk) model; this model reads weather + terrain.
MONOTONIC = {"rain_1d": 1, "rain_3d": 1, "rain_7d": 1, "rain_14d": 1, "rain_30d": 1, "wet_days_7d": 1,
             "rain_accel": 1, "rh2m": 1, "dew_spread": -1, "ps_anom": -1, "ps_chg_1d": -1, "ps_chg_3d": -1}


def prep(df):
    X = df[FEATS].copy()
    X[SKEWED] = np.log1p(X[SKEWED].clip(lower=0))
    return X


def metrics(y, p, thr):
    yhat = p >= thr
    return {"roc_auc": round(float(roc_auc_score(y, p)), 4),
            "pr_auc": round(float(average_precision_score(y, p)), 4),
            "brier": round(float(brier_score_loss(y, np.clip(p, 0, 1))), 5),
            "precision": round(float(precision_score(y, yhat, zero_division=0)), 4),
            "recall": round(float(recall_score(y, yhat)), 4),
            "alert_rate": round(float(yhat.mean()), 4)}


def climatology(train, df):
    """Base rate per site x month, from train years only."""
    t = train.assign(m=train["date"].dt.month).groupby(["site_id", "m"])["y"].mean().rename("c")
    return df.assign(m=df["date"].dt.month).join(t, on=["site_id", "m"])["c"].fillna(train["y"].mean()).to_numpy()


def best_f1_threshold(y, p):
    qs = np.unique(np.quantile(p, np.linspace(0.80, 0.995, 80)))
    f1 = [(2 * precision_score(y, p >= q, zero_division=0) * recall_score(y, p >= q) /
           max(precision_score(y, p >= q, zero_division=0) + recall_score(y, p >= q), 1e-9), q) for q in qs]
    return max(f1)[1]


def main():
    df = pd.read_csv(os.path.join(ROOT, "ml", "ef_features.csv"), parse_dates=["date"])
    tr, va, te = df[df.date < VAL_START], df[(df.date >= VAL_START) & (df.date < TEST_START)], df[df.date >= TEST_START]
    print(f"train {len(tr)}  val {len(va)}  TEST {len(te)}  (test positive rate {te.y.mean():.3f})")

    models = {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=3000)),
        "grad_boost": HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=250,
                                                     l2_regularization=1.0, random_state=0,
                                                     monotonic_cst=[MONOTONIC.get(c, 0) for c in FEATS]),
    }
    res = {"split": {"train": "1995-2018", "validation": "2019-2021", "test": "2022-2025"},
           "target": "extreme-rainfall day (>= site's train-years 99th pct) within next 3 days",
           "n_train": len(tr), "n_val": len(va), "n_test": len(te),
           "test_positive_rate": round(float(te.y.mean()), 4), "models": {}}

    # baselines scored on validation (threshold) then test
    base = {}
    pc_va, pc_te = climatology(tr, va), climatology(tr, te)
    base["climatology"] = (pc_va, pc_te)
    base["persistence"] = ((va.rain_1d >= va.extreme_threshold_mm).astype(float).to_numpy(),
                           (te.rain_1d >= te.extreme_threshold_mm).astype(float).to_numpy())
    fitted, val_scores = {}, {}
    for name, m in models.items():
        m.fit(prep(tr), tr.y)
        fitted[name] = m
        base[name] = (m.predict_proba(prep(va))[:, 1], m.predict_proba(prep(te))[:, 1])
    for name, (pv, pt) in base.items():
        thr = 0.5 if name == "persistence" else best_f1_threshold(va.y, pv)
        r = metrics(te.y, pt, thr)
        r["threshold_from_validation"] = round(float(thr), 4)
        r["val_roc_auc"] = round(float(roc_auc_score(va.y, pv)), 4)
        res["models"][name] = r
        val_scores[name] = r["val_roc_auc"]
        print(f"{name:<12} TEST AUC={r['roc_auc']} PR-AUC={r['pr_auc']} Brier={r['brier']} "
              f"P={r['precision']} R={r['recall']} alerts={r['alert_rate']}")
    clim_brier = res["models"]["climatology"]["brier"]
    for name in ("logistic", "grad_boost"):
        res["models"][name]["brier_skill_vs_climatology"] = round(1 - res["models"][name]["brier"] / clim_brier, 4)

    chosen = max(("logistic", "grad_boost"), key=lambda k: val_scores[k])  # chosen on VALIDATION only
    res["chosen_model"] = chosen
    print("chosen on validation:", chosen)

    # permutation importance on the test set (drop in PR-AUC) for the chosen model
    pi = permutation_importance(fitted[chosen], prep(te.sample(min(len(te), 20000), random_state=0)),
                                te.sample(min(len(te), 20000), random_state=0).y, scoring="average_precision",
                                n_repeats=3, random_state=0)
    imp = sorted(zip(FEATS, pi.importances_mean), key=lambda t: -t[1])
    res["permutation_importance_pr_auc_drop"] = [{"feature": f, "drop": round(float(v), 5)} for f, v in imp]
    print("top features:", [(f, round(v, 4)) for f, v in imp[:6]])

    # reliability: do predicted probabilities match observed frequencies on the TEST set?
    pt = base[chosen][1]
    bins = [0, 0.02, 0.05, 0.1, 0.2, 0.4, 1.0001]
    cat = pd.cut(pt, bins, right=False)
    rel = pd.DataFrame({"b": cat, "p": pt, "y": te.y.to_numpy()}).groupby("b", observed=True).agg(
        n=("y", "size"), mean_predicted=("p", "mean"), observed_rate=("y", "mean"))
    res["calibration_test"] = [{"bin": str(i), "n": int(r.n), "mean_predicted": round(float(r.mean_predicted), 4),
                                "observed_rate": round(float(r.observed_rate), 4)} for i, r in rel.iterrows()]
    print(rel.round(3).to_string())

    # real-event backtest on test years: peak forecast probability in the 3 days before the event
    thr = res["models"][chosen]["threshold_from_validation"]
    te = te.assign(p=base[chosen][1])
    ev = []
    for s, g in te.dropna(subset=["event_date"]).groupby("site_id"):
        d0 = pd.Timestamp(g.event_date.iloc[0])
        if not (TEST_START <= d0 <= pd.Timestamp("2025-12-31")):
            continue
        w = g[(g.date >= d0 - pd.Timedelta(days=3)) & (g.date < d0)]
        site_all = g.p
        ev.append({"site_id": s, "event_date": str(d0.date()), "peak_prob_3d_before": round(float(w.p.max()), 4),
                   "alert_raised": bool((w.p >= thr).any()),
                   "percentile_in_site_test_history": round(float((site_all < w.p.max()).mean() * 100), 1)})
    res["recorded_event_backtest"] = ev
    for e in ev:
        print(e)

    with open(os.path.join(ROOT, "ml", "ef_results.json"), "w") as f:
        json.dump(res, f, indent=2)
    # deployable model: refit on train+val only (test stays unseen)
    trv = pd.concat([tr, va])
    final = models[chosen].fit(prep(trv), trv.y)
    with open(os.path.join(ROOT, "ml", "ef_model.pkl"), "wb") as f:
        pickle.dump({"model": final, "features": FEATS, "skewed": SKEWED, "threshold": thr,
                     "name": chosen}, f)
    print("wrote ml/ef_results.json, ml/ef_model.pkl")


if __name__ == "__main__":
    main()
