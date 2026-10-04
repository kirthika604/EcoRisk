#!/usr/bin/env python3
"""Build the site-day dataset for the 7-day early-warning model.

Each row is one (site, day). Features describe rainfall up to and including that day plus the
site's static vulnerability; the label is whether the site's recorded disaster begins in the
next 1..HORIZON days. Daily rainfall is real NASA POWER data, cached per site under
datasourceSIH/sites/<site_id>/rain_daily.csv. Output: ml/site_days.csv.
"""
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from nasa_power import fetch_daily_precip

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HORIZON = 7
START, END = dt.date(1995, 1, 1), dt.date(2025, 12, 31)
STATIC = ["ndvi_trend_slope", "ndbi_trend_slope", "mean_slope_degrees", "elevation_mean_m"]


def rain_series(site_id, lat, lon):
    path = os.path.join(ROOT, "datasourceSIH", "sites", site_id, "rain_daily.csv")
    if os.path.exists(path):
        s = pd.read_csv(path, parse_dates=["date"]).set_index("date")["precip_mm"]
        return s
    raw = fetch_daily_precip(lat, lon, START, END, timeout=120)
    s = pd.Series(raw, name="precip_mm")
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s.rename_axis("date").to_csv(path)
    return s


def site_frame(row, rain):
    rain = rain.asfreq("D")  # missing days stay NaN, no silent interpolation
    df = pd.DataFrame({"rain_1d": rain})
    for w in (3, 7, 14, 30):
        df[f"rain_{w}d"] = rain.rolling(w, min_periods=w).sum()
    # Anomaly of the 7-day total vs. the same calendar-day-of-year climatology of THIS site,
    # computed from earlier years only so a day never sees its own future.
    doy = df.index.dayofyear
    clim = df.groupby(doy)["rain_7d"].transform(lambda x: x.expanding().mean().shift(1))
    df["rain_7d_anom"] = df["rain_7d"] - clim
    for c in STATIC:
        df[c] = row[c]
    df["terrain_is_coastal"] = int(row["terrain_type"] == "coastal")
    df["site_id"] = row["site_id"]
    df["y"] = 0
    if row["disaster_occurred"] == 1 and isinstance(row["disaster_date"], str):
        ev = pd.Timestamp(row["disaster_date"])
        df["days_to_event"] = (ev - df.index).days
        df.loc[(df["days_to_event"] >= 1) & (df["days_to_event"] <= HORIZON), "y"] = 1
    else:
        df["days_to_event"] = pd.NA
    return df.dropna(subset=["rain_30d", "rain_7d_anom"]).rename_axis("date").reset_index()


def main():
    ft = pd.read_csv(os.path.join(ROOT, "ml", "feature_table.csv"))
    ft = ft[ft["status"].str.startswith("REAL")].dropna(subset=["latitude"])
    frames = []
    for _, row in ft.iterrows():
        try:
            rain = rain_series(row["site_id"], row["latitude"], row["longitude"])
        except Exception as e:  # report, don't hide: the site is excluded from the dataset
            print(f"SKIP {row['site_id']}: {e}")
            continue
        f = site_frame(row, rain)
        print(f"{row['site_id']:<20} days={len(f):>6} positives={int(f['y'].sum())}")
        frames.append(f)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(os.path.join(ROOT, "ml", "site_days.csv"), index=False)
    print(f"wrote ml/site_days.csv rows={len(out)} positives={int(out['y'].sum())}")


if __name__ == "__main__":
    main()
