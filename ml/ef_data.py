#!/usr/bin/env python3
"""EcoForecast step 1: pull real daily weather per site (NASA POWER) and build the feature table.

Target ("what happens next"): will an EXTREME-RAINFALL day occur at this site within the next
HORIZON days? Extreme = daily rainfall above that site's 99th percentile of daily rainfall,
computed on TRAIN years only (<= TRAIN_END) so no test information leaks into the label.
Recorded disaster dates (feature_table.csv) are kept as a separate backtest target.

Output: ml/ef_features.csv  (one row per site-day, features use data up to that day only).
"""
import datetime as dt
import json
import os
import urllib.request

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = ["PRECTOTCORR", "T2M", "RH2M", "PS", "WS2M", "T2MDEW"]
START, END = "19950101", "20251231"
HORIZON = 3
TRAIN_END = pd.Timestamp("2018-12-31")
STATIC = ["ndvi_trend_slope", "ndbi_trend_slope", "mean_slope_degrees", "elevation_mean_m"]


def pull(site_id, lat, lon):
    path = os.path.join(ROOT, "datasourceSIH", "sites", site_id, "weather_daily.csv")
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["date"], index_col="date")
    url = (f"{API}?parameters={','.join(PARAMS)}&community=AG&longitude={lon}&latitude={lat}"
           f"&start={START}&end={END}&format=JSON")
    with urllib.request.urlopen(url, timeout=180) as r:
        data = json.load(r)["properties"]["parameter"]
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.where(df > -900)  # NASA POWER missing-value sentinel -> NaN, never imputed with fake data
    df = df.rename(columns={"PRECTOTCORR": "rain"}).rename_axis("date")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path)
    return df


def features(w, row):
    d = pd.DataFrame(index=w.index)
    d["rain_1d"] = w["rain"]
    for k in (3, 7, 14, 30):
        d[f"rain_{k}d"] = w["rain"].rolling(k, min_periods=k).sum()
    d["wet_days_7d"] = (w["rain"] > 1).rolling(7, min_periods=7).sum()
    d["rain_accel"] = d["rain_3d"] - (d["rain_7d"] - d["rain_3d"]) * 3 / 4  # last 3d vs prior 4d pace
    d["t2m"], d["rh2m"], d["ws2m"] = w["T2M"], w["RH2M"], w["WS2M"]
    d["dew_spread"] = w["T2M"] - w["T2MDEW"]
    d["ps_kpa"] = w["PS"]  # kept for reference only: absolute pressure mostly encodes altitude
    # pressure anomaly vs this location's own last 30 days: the weather signal, altitude removed
    d["ps_anom"] = w["PS"] - w["PS"].rolling(30, min_periods=20).mean()
    d["ps_chg_1d"] = w["PS"].diff(1)
    d["ps_chg_3d"] = w["PS"].diff(3)
    d["rh_chg_3d"] = w["RH2M"].diff(3)
    doy = w.index.dayofyear
    d["doy_sin"], d["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    for c in STATIC:
        d[c] = row[c]
    d["terrain_is_coastal"] = int(row["terrain_type"] == "coastal")
    # label: extreme day within the next HORIZON days (site threshold from train years only)
    thr = w.loc[w.index <= TRAIN_END, "rain"].quantile(0.99)
    ext = (w["rain"] >= thr).astype(float).where(w["rain"].notna())
    fut = pd.concat([ext.shift(-k) for k in range(1, HORIZON + 1)], axis=1)
    d["y"] = fut.max(axis=1).where(fut.notna().all(axis=1))
    # shorter prediction windows (same extreme definition): within 24 h / within 48 h
    d["y_24h"] = ext.shift(-1)
    d["y_48h"] = pd.concat([ext.shift(-1), ext.shift(-2)], axis=1).max(axis=1).where(ext.shift(-2).notna())
    d["extreme_threshold_mm"] = thr
    d["site_id"] = row["site_id"]
    d["event_date"] = row["disaster_date"] if row["disaster_occurred"] == 1 else None
    return d


def main():
    ft = pd.read_csv(os.path.join(ROOT, "ml", "feature_table.csv"))
    ft = ft[ft["status"].str.startswith("REAL")].dropna(subset=["latitude"])
    frames = []
    for _, row in ft.iterrows():
        try:
            w = pull(row["site_id"], row["latitude"], row["longitude"])
        except Exception as e:
            print(f"SKIP {row['site_id']}: {e}")
            continue
        f = features(w, row).dropna(subset=["rain_30d", "ps_chg_3d", "ps_anom", "y"])
        print(f"{row['site_id']:<20} rows={len(f):>6}  extreme>= {f['extreme_threshold_mm'].iloc[0]:.1f} mm"
              f"  pos_rate={f['y'].mean():.3f}")
        frames.append(f.rename_axis("date").reset_index())
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(os.path.join(ROOT, "ml", "ef_features.csv"), index=False)
    print("wrote ml/ef_features.csv", out.shape)


if __name__ == "__main__":
    main()
