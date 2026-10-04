#!/usr/bin/env python3
"""Computes Joshimath's row in the multi-site ML feature table from the real CSVs already
in datasourceSIH/. No values are invented -- every number here is derived from data that
was actually pulled (Sentinel-2 NDVI/NDBI via GEE, NASA POWER rainfall, DEM slope).

This produces ONE real row. Every other candidate site in sihPlan/dataset-sites.md needs
its own Earth Engine + NASA POWER pull before it can be added -- see ml/feature_table.csv
for the template with those rows left explicitly blank/NOT_PULLED."""
import csv
import json
import os
from datetime import date, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "datasourceSIH")


def linreg_slope(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def lst_features(path):
    """Real Land Surface Temperature trend + mean, from a <site_id>_lst_timeseries.csv
    written by ml/gee_pull_lst.py. Returns None if the file doesn't exist yet -- LST is
    optional everywhere it's used, so the rest of the pipeline keeps working before the
    team runs that pull."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 5:
        return None
    dates = [date.fromisoformat(r["date"]) for r in rows]
    ref = dates[0]
    t = [(d - ref).days for d in dates]
    vals = [float(r["lst_celsius"]) for r in rows]
    slope = linreg_slope(t, vals) * 365.25  # degrees C per year
    mean_c = sum(vals) / len(vals)
    return {"lst_trend_slope": round(slope, 4), "lst_mean_c": round(mean_c, 2), "n_lst_obs": len(rows)}


def compute():
    rows = []
    with open(os.path.join(SRC, "joshimath_merged_timeline.csv")) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    dates = [date.fromisoformat(r["date"]) for r in rows]
    ref = dates[0]
    t = [(d - ref).days for d in dates]
    ndvi = [float(r["ndvi_avg"]) for r in rows]
    ndbi = [float(r["ndbi_avg"]) for r in rows]

    ndvi_trend_slope = linreg_slope(t, ndvi) * 365.25  # per-year
    ndbi_trend_slope = linreg_slope(t, ndbi) * 365.25  # per-year

    with open(os.path.join(SRC, "joshimath_dem_slope.csv")) as f:
        dem = next(csv.DictReader(f))
    mean_slope_degrees = float(dem["slope_slope_mean"])
    elevation_mean_m = float(dem["elev_elevation_mean"])

    rain = {}
    with open(os.path.join(SRC, "POWER_Point_Daily_20190101_20230521_030d56N_079d56E_LST.csv")) as f:
        lines = f.readlines()
    idx = next(i for i, l in enumerate(lines) if l.startswith("YEAR,DOY"))
    for r in csv.DictReader(lines[idx:]):
        d = date(int(r["YEAR"]), 1, 1) + timedelta(days=int(r["DOY"]) - 1)
        rain[d] = float(r["PRECTOTCORR"])
    baseline_mean = sum(rain.values()) / len(rain)
    last_date = max(rain.keys())
    recent_vals = [v for d, v in rain.items() if d > last_date - timedelta(days=90)]
    recent_mean = sum(recent_vals) / len(recent_vals)
    rainfall_anomaly_pct = (recent_mean - baseline_mean) / baseline_mean * 100

    row = {
        "site_id": "joshimath",
        "site_name": "Joshimath, Chamoli",
        "terrain_type": "hill",
        "latitude": 30.5551,
        "longitude": 79.5641,
        "ndvi_trend_slope": round(ndvi_trend_slope, 6),
        "ndbi_trend_slope": round(ndbi_trend_slope, 6),
        "mean_slope_degrees": round(mean_slope_degrees, 2),
        "elevation_mean_m": round(elevation_mean_m, 1),
        "rainfall_anomaly_pct": round(rainfall_anomaly_pct, 2),
        "human_activity_notes": "Rising NDBI (built-up growth) trend; govt expert committee (NDMA/GSI/CBRI) attributed subsidence to drainage failure + anthropogenic activity, not rainfall trigger (see sihPlan/memory.md sec 6).",
        "disaster_occurred": 1,
        "disaster_type": "land_subsidence",
        "disaster_date": "2023-01-02",
        "source_citation": "Deccan Herald/Outlook India/BusinessToday (Jan 2023) citing ISRO/NRSC DInSAR report (secondary source, primary PDF no longer hosted); slope/elevation from project DEM pull; NDVI/NDBI from Sentinel-2 via GEE; rainfall from NASA POWER.",
        "status": "REAL - fully computed from project-collected data",
    }
    lst = lst_features(os.path.join(SRC, "joshimath_lst_timeseries.csv"))
    if lst:
        row["lst_trend_slope"] = lst["lst_trend_slope"]
        row["lst_mean_c"] = lst["lst_mean_c"]
        row["source_citation"] += f" LST: MODIS MOD11A2 via Earth Engine ({lst['n_lst_obs']} obs)."
    return row


def compute_gee_site(site_id, site_dir):
    """Generic version of the NDVI/NDBI-trend + DEM part of compute() above, for any site
    pulled via ml/gee_pull_site.py (which writes <site_id>_ndvi_timeseries.csv,
    <site_id>_ndbi_timeseries.csv, <site_id>_dem_slope.csv into site_dir). Returns only
    the GEE-derived fields -- rainfall_anomaly_pct is pulled separately in
    build_feature_table.py via nasa_power.py, same as for every other site.

    Returns None if the expected files aren't there yet (site not pulled)."""
    ndvi_path = os.path.join(site_dir, f"{site_id}_ndvi_timeseries.csv")
    ndbi_path = os.path.join(site_dir, f"{site_id}_ndbi_timeseries.csv")
    dem_path = os.path.join(site_dir, f"{site_id}_dem_slope.csv")
    if not (os.path.exists(ndvi_path) and os.path.exists(ndbi_path) and os.path.exists(dem_path)):
        return None

    def trend_slope(path, col):
        with open(path) as f:
            rows = list(csv.DictReader(f))
        if len(rows) < 2:
            return None
        dates = [date.fromisoformat(r["date"]) for r in rows]
        ref = dates[0]
        t = [(d - ref).days for d in dates]
        vals = [float(r[col]) for r in rows]
        return linreg_slope(t, vals) * 365.25  # per-year

    ndvi_trend_slope = trend_slope(ndvi_path, "ndvi_avg")
    ndbi_trend_slope = trend_slope(ndbi_path, "ndbi_avg")

    with open(dem_path) as f:
        dem = next(csv.DictReader(f))
    mean_slope_degrees = float(dem["slope_mean"])
    elevation_mean_m = float(dem["elev_mean"])

    result = {
        "ndvi_trend_slope": round(ndvi_trend_slope, 6) if ndvi_trend_slope is not None else "",
        "ndbi_trend_slope": round(ndbi_trend_slope, 6) if ndbi_trend_slope is not None else "",
        "mean_slope_degrees": round(mean_slope_degrees, 2),
        "elevation_mean_m": round(elevation_mean_m, 1),
    }
    lst = lst_features(os.path.join(site_dir, f"{site_id}_lst_timeseries.csv"))
    if lst:
        result["lst_trend_slope"] = lst["lst_trend_slope"]
        result["lst_mean_c"] = lst["lst_mean_c"]
        result["_lst_n_obs"] = lst["n_lst_obs"]  # consumed by build_feature_table.py for the citation line, not a CSV column
    return result


if __name__ == "__main__":
    row = compute()
    print(json.dumps(row, indent=2))
