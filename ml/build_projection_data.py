#!/usr/bin/env python3
"""Builds awareness/projection-data.js: per-site linear-trend fits of the REAL NDVI/NDBI
time series, for the "if this continues" projection feature.

IMPORTANT, read before touching the awareness page's projection UI: this is NOT the
trained classifier (ml/train_model.py) run further into the future. The classifier's
input features are already trend RATES (e.g. ndvi_trend_slope), and a rate does not
change just because more years pass -- feeding an artificially inflated "N years of
slope" back into a model trained on ~5-year rates would extrapolate it far outside
anything it was ever validated on, producing a confident-looking number with no real
statistical grounding. That would break every honesty commitment already made in this
project (see sihPlan/memory.md).

Instead, this reuses the exact approach already validated and shipped in demo/app.js's
"Current -> BAU 2030 -> Intervention 2030" slider: a plain linear extrapolation of the
REAL observed NDVI/NDBI values themselves, openly labeled as an illustrative index, not
a validated statistical forecast. This script just generalizes that one working method
from Joshimath to every real site, and makes the horizon a variable (5/10/20/30 years)
instead of a fixed date.
"""
import csv
import json
import os
from datetime import date, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES_DIR = os.path.join(BASE, "datasourceSIH", "sites")
JOSHIMATH_DIR = os.path.join(BASE, "datasourceSIH")
OUT = os.path.join(BASE, "awareness", "projection-data.js")

# site_id -> (ndvi_csv_path, ndbi_csv_path, ndvi_col, ndbi_col)
SITE_FILES = {
    "joshimath": (
        os.path.join(JOSHIMATH_DIR, "joshimath_ndvi_timeseries.csv"),
        os.path.join(JOSHIMATH_DIR, "joshimath_ndbi_timeseries.csv"),
        "ndvi_avg", "ndbi_avg",
    ),
}
# chennai's real pull went into a directory named "chennai_test" (see gee_pull_site.py
# usage in sihPlan/memory.md) -- every other site's directory matches its site_id exactly.
SITE_DIR_OVERRIDE = {"chennai": "chennai_test"}
for site_id in [
    "raini", "kedarnath", "wazri", "dharali", "malpa", "auli_control", "sundarbans",
    "odisha_coast", "coastal_control_tbd",
    # added this session -- real NDVI/NDBI already pulled, just never wired into the
    # projection builder (see "IF TODAY'S TREND CONTINUES" gap flagged for jaisalmer)
    "chennai", "wayanad", "jakhau", "ranikhet", "kollam", "pettimudi", "kinnaur",
    "visakhapatnam", "nagapattinam", "guna", "silchar", "jaisalmer",
]:
    dir_name = SITE_DIR_OVERRIDE.get(site_id, site_id)
    d = os.path.join(SITES_DIR, dir_name)
    SITE_FILES[site_id] = (
        os.path.join(d, f"{dir_name}_ndvi_timeseries.csv"),
        os.path.join(d, f"{dir_name}_ndbi_timeseries.csv"),
        "ndvi_avg", "ndbi_avg",
    )


def linreg(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    intercept = (sy - slope * sx) / n
    return slope, intercept


def load_series(path, col):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if r.get("date") and r.get(col)]
    dates = [date.fromisoformat(r["date"]) for r in rows]
    vals = [float(r[col]) for r in rows]
    return dates, vals


def build_site(site_id):
    ndvi_path, ndbi_path, ndvi_col, ndbi_col = SITE_FILES[site_id]
    if not (os.path.exists(ndvi_path) and os.path.exists(ndbi_path)):
        return None
    ndvi_dates, ndvi_vals = load_series(ndvi_path, ndvi_col)
    ndbi_dates, ndbi_vals = load_series(ndbi_path, ndbi_col)
    if len(ndvi_vals) < 5 or len(ndbi_vals) < 5:
        return None

    ref_date = min(ndvi_dates[0], ndbi_dates[0])
    last_date = max(ndvi_dates[-1], ndbi_dates[-1])

    ndvi_t = [(d - ref_date).days for d in ndvi_dates]
    ndbi_t = [(d - ref_date).days for d in ndbi_dates]
    ndvi_slope, ndvi_intercept = linreg(ndvi_t, ndvi_vals)
    ndbi_slope, ndbi_intercept = linreg(ndbi_t, ndbi_vals)

    n_baseline = min(10, len(ndvi_vals))
    ndvi_baseline = sum(ndvi_vals[:n_baseline]) / n_baseline

    return {
        "site_id": site_id,
        "ref_date": ref_date.isoformat(),
        "last_date": last_date.isoformat(),
        "ndvi_slope_per_day": ndvi_slope,
        "ndvi_intercept": ndvi_intercept,
        "ndbi_slope_per_day": ndbi_slope,
        "ndbi_intercept": ndbi_intercept,
        "ndvi_baseline": ndvi_baseline,
        "ndvi_min": min(ndvi_vals),
        "ndvi_max": max(ndvi_vals),
        "ndbi_min": min(ndbi_vals),
        "ndbi_max": max(ndbi_vals),
        "n_ndvi_obs": len(ndvi_vals),
        "n_ndbi_obs": len(ndbi_vals),
    }


def main():
    sites = {}
    for site_id in SITE_FILES:
        result = build_site(site_id)
        if result:
            sites[site_id] = result
            print(f"  {site_id}: {result['n_ndvi_obs']} NDVI obs, {result['ref_date']} to {result['last_date']}")
        else:
            print(f"  {site_id}: SKIPPED (missing or too little data)")

    with open(OUT, "w") as f:
        f.write("// Generated by ml/build_projection_data.py -- do not hand-edit.\n")
        f.write("// Per-site linear-trend fits of REAL NDVI/NDBI time series, for the\n")
        f.write("// \"if this continues\" projection. See the script's docstring for why this\n")
        f.write("// is a transparent trend extrapolation, not the trained classifier re-run.\n")
        f.write("window.PROJECTION_DATA = ")
        json.dump(sites, f, indent=2)
        f.write(";\n")
    print(f"\nWrote {OUT} ({len(sites)} sites)")


if __name__ == "__main__":
    main()
