#!/usr/bin/env python3
"""Precompute the small summaries the live server needs from the 77 MB training table, so a deployment
ships ml/runtime_artifacts.json (tens of KB) instead of ml/ef_features.csv.

Contents (all computed from ml/ef_features.csv, i.e. the real training rows):
  base_rows       typical day per site x month (feature medians): the what-if calculator's start point
  slider_ranges   0.5-99.5th percentile of the calculator's weather inputs
  extreme_mm      each site's extreme-rain threshold (train years 99th percentile)
  ref_medians     training medians of every model input (the 'typical day' for factor explanations)
  ood_ranges      0.1-99.9th percentile of each input (the model's 'experience' for unfamiliar flags)

Run after ml/ef_data.py:  python3 ml/build_runtime.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))
from ef_model import FEATS, SKEWED  # noqa: E402

OOD_FEATS = ["rain_1d", "rain_3d", "rain_7d", "rain_30d", "t2m", "ws2m",
             "ps_anom", "ps_chg_1d", "ps_chg_3d", "mean_slope_degrees", "elevation_mean_m"]
SLIDERS = ("rain_1d", "rain_3d", "rain_7d", "rain_30d", "rh2m", "ps_chg_3d", "t2m")


def main():
    f = pd.read_csv(os.path.join(ROOT, "ml", "ef_features.csv"), parse_dates=["date"])
    f["month"] = f["date"].dt.month
    num = f.drop(columns=["date", "event_date"]).select_dtypes("number").columns.drop("month")
    base = f.groupby(["site_id", "month"])[list(num)].median()
    ref = f[FEATS].median()
    ref[SKEWED] = np.log1p(ref[SKEWED].clip(lower=0))
    out = {
        "source": "ml/ef_features.csv via ml/build_runtime.py",
        "base_rows": {f"{s}|{m}": {k: round(float(v), 6) for k, v in row.items() if pd.notna(v)}
                      for (s, m), row in base.iterrows()},
        "slider_ranges": {c: [float(f[c].quantile(0.005)), float(f[c].quantile(0.995))] for c in SLIDERS},
        "extreme_mm": f.groupby("site_id")["extreme_threshold_mm"].first().round(1).to_dict(),
        "ref_medians": {k: float(v) for k, v in ref.items()},
        "ood_ranges": {c: [float(f[c].quantile(0.001)), float(f[c].quantile(0.999))] for c in OOD_FEATS},
    }
    path = os.path.join(ROOT, "ml", "runtime_artifacts.json")
    with open(path, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB)")


if __name__ == "__main__":
    main()
