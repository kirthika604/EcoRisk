#!/usr/bin/env python3
"""7-day early-warning model, validated leave-one-SITE-out on ml/site_days.csv.

Every held-out site is scored by a model that never saw that site (no site-identity or event
leakage). Compares a rainfall-only baseline against rainfall + land-change vulnerability, and
reports, per real event: was an alert raised in the 7 days before it, and with how much lead
time. The alert threshold is chosen on the TRAINING sites only (target: ~1% of days alerted),
then applied unchanged to the held-out site. Output: ml/forecast_results.json.
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HORIZON = 7
ALERT_RATE = 0.01  # fraction of training days allowed to alert
RAIN = ["rain_1d", "rain_3d", "rain_7d", "rain_14d", "rain_30d", "rain_7d_anom"]
LAND = ["ndvi_trend_slope", "ndbi_trend_slope", "mean_slope_degrees", "elevation_mean_m",
        "terrain_is_coastal"]
CONFIGS = {"rainfall_only": RAIN, "rainfall_plus_land": RAIN + LAND}


def design(df, cols):
    X = df[cols].copy()
    for c in RAIN[:5]:
        X[c] = np.log1p(X[c].clip(lower=0))
    return X.to_numpy(float)


def fit(df, cols):
    m = make_pipeline(StandardScaler(),
                      LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000))
    m.fit(design(df, cols), df["y"])
    return m


def run(df, cols):
    sites = sorted(df["site_id"].unique())
    parts, events = [], []
    for s in sites:
        tr, te = df[df["site_id"] != s], df[df["site_id"] == s].copy()
        m = fit(tr, cols)
        thr = np.quantile(m.predict_proba(design(tr, cols))[:, 1], 1 - ALERT_RATE)
        te["p"] = m.predict_proba(design(te, cols))[:, 1]
        te["alert"] = te["p"] >= thr
        parts.append(te)
        if te["y"].sum():
            w = te[te["y"] == 1]
            hit = w[w["alert"]]
            # percentile of the best pre-event score within the site's own history
            pct = float((te["p"] < w["p"].max()).mean() * 100)
            events.append({
                "site_id": s,
                "event_date": str((pd.to_datetime(w["date"]) + pd.to_timedelta(w["days_to_event"].astype(int), unit="D")).iloc[0].date()),
                "alerted": bool(len(hit)),
                "lead_days": int(hit["days_to_event"].astype(int).max()) if len(hit) else None,
                "peak_pre_event_prob": round(float(w["p"].max()), 4),
                "peak_percentile_in_site_history": round(pct, 1),
            })
    allp = pd.concat(parts)
    neg = allp[allp["y"] == 0]
    years = len(neg) / 365.25
    return {
        "roc_auc": round(float(roc_auc_score(allp["y"], allp["p"])), 4),
        "pr_auc": round(float(average_precision_score(allp["y"], allp["p"])), 4),
        "pr_auc_chance": round(float(allp["y"].mean()), 5),
        "events_total": len(events),
        "events_alerted": sum(e["alerted"] for e in events),
        "false_alert_days_per_site_year": round(float(neg["alert"].sum() / years), 2),
        "events": events,
    }


def main():
    df = pd.read_csv(os.path.join(ROOT, "ml", "site_days.csv"))
    out = {"horizon_days": HORIZON, "alert_rate_target": ALERT_RATE,
           "validation": "leave-one-site-out; threshold set on training sites only",
           "n_site_days": len(df), "n_positive_days": int(df["y"].sum()),
           "n_sites": int(df["site_id"].nunique())}
    for name, cols in CONFIGS.items():
        out[name] = run(df, cols)
        r = out[name]
        print(f"{name:<20} AUC={r['roc_auc']}  PR-AUC={r['pr_auc']} (chance {r['pr_auc_chance']})  "
              f"events alerted {r['events_alerted']}/{r['events_total']}  "
              f"false-alert days/site-yr={r['false_alert_days_per_site_year']}")
    # final deployable model + coefficients for the dashboard
    cols = CONFIGS["rainfall_plus_land"]
    m = fit(df, cols)
    thr = float(np.quantile(m.predict_proba(design(df, cols))[:, 1], 1 - ALERT_RATE))
    sc, lr = m[0], m[1]
    out["final_model"] = {"features": cols, "log1p_features": RAIN[:5],
                          "coefficients": [round(float(c), 4) for c in lr.coef_[0]],
                          "intercept": round(float(lr.intercept_[0]), 4),
                          "scaler_mean": [round(float(x), 6) for x in sc.mean_],
                          "scaler_scale": [round(float(x), 6) for x in sc.scale_],
                          "alert_threshold": round(thr, 4)}
    with open(os.path.join(ROOT, "ml", "forecast_results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("wrote ml/forecast_results.json")
    for e in out["rainfall_plus_land"]["events"]:
        print(e)


if __name__ == "__main__":
    main()
