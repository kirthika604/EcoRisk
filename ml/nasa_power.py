#!/usr/bin/env python3
"""Thin wrapper around the NASA POWER daily-point REST API (power.larc.nasa.gov).
No API key needed. Used to pull real daily precipitation for any site's coordinates --
this is reachable directly (unlike Earth Engine, which needs credentials this
environment doesn't have), so it's used to fill rainfall_anomaly_pct in the multi-site
feature table for every candidate site with known coordinates."""
import datetime as dt
import json
import urllib.request

API = "https://power.larc.nasa.gov/api/temporal/daily/point"


def fetch_daily_precip(lat, lon, start_date, end_date, timeout=30):
    """start_date/end_date: datetime.date. Returns {date: mm} dict, -999 (missing) values dropped."""
    params = (
        f"?parameters=PRECTOTCORR&community=AG"
        f"&longitude={lon}&latitude={lat}"
        f"&start={start_date.strftime('%Y%m%d')}&end={end_date.strftime('%Y%m%d')}"
        f"&format=JSON"
    )
    with urllib.request.urlopen(API + params, timeout=timeout) as r:
        data = json.load(r)
    series = data["properties"]["parameter"]["PRECTOTCORR"]
    out = {}
    for k, v in series.items():
        if v is None or v <= -900:
            continue
        d = dt.date(int(k[:4]), int(k[4:6]), int(k[6:8]))
        out[d] = float(v)
    return out


def rainfall_anomaly_pct(lat, lon, anchor_date, baseline_years=5, recent_days=90):
    """anchor_date: datetime.date -- typically the disaster date (or a fixed reference for
    control sites). Computes % deviation of the `recent_days` immediately before anchor_date
    vs. the mean over the `baseline_years` before anchor_date. Real NASA POWER data only --
    returns None if too little data comes back (e.g. before POWER's coverage starts)."""
    baseline_start = anchor_date.replace(year=anchor_date.year - baseline_years)
    series = fetch_daily_precip(lat, lon, baseline_start, anchor_date)
    if len(series) < 365:  # not enough real data to trust a baseline
        return None, len(series)
    baseline_mean = sum(series.values()) / len(series)
    recent_start = anchor_date - dt.timedelta(days=recent_days)
    recent_vals = [v for d, v in series.items() if d >= recent_start]
    if not recent_vals:
        return None, len(series)
    recent_mean = sum(recent_vals) / len(recent_vals)
    if baseline_mean == 0:
        return None, len(series)
    return (recent_mean - baseline_mean) / baseline_mean * 100, len(series)


if __name__ == "__main__":
    import sys
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    anchor = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date.today()
    pct, n = rainfall_anomaly_pct(lat, lon, anchor)
    print(f"rainfall_anomaly_pct={pct}, n_days_pulled={n}")
