#!/usr/bin/env python3
"""External validation: does the 72 h model hold up on data it was not built on?

Two shifts at once, the hard case:
  1. NEW LOCATIONS: 9 Indian places not in the training set (and not next to a training site).
  2. NEW DATA SOURCE: ERA5 reanalysis via the Open-Meteo archive API, not NASA POWER. Files are fed
     through the same outside-data reader the demo uses (Open-Meteo names, hPa, km/h at 10 m).
Labels use the same rule as training, computed from the new source itself: an extreme day is
>= that location's 99th percentile of daily rain over 1995-2018. Scored on 2022-2024 only.
Terrain: elevation and mean slope from the Copernicus 90 m DEM (Open-Meteo elevation API).

Output: ml/external_results.json. Raw downloads cached in datasourceSIH/external/.
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))
import ef_predict  # noqa: E402

PLACES = {  # name: (lat, lon, terrain)
    "shimla": (31.104, 77.173, "hill"), "darjeeling": (27.041, 88.266, "hill"),
    "gangtok": (27.330, 88.612, "hill"), "srinagar": (34.083, 74.797, "hill"),
    "itanagar": (27.084, 93.605, "hill"), "dehradun": (30.316, 78.032, "hill"),
    "mumbai": (19.076, 72.877, "coastal"), "mangaluru": (12.914, 74.856, "coastal"),
    "guwahati": (26.144, 91.736, "plains"),
}
DAILY = "precipitation_sum,temperature_2m_mean,relative_humidity_2m_mean,surface_pressure_mean,wind_speed_10m_mean,dew_point_2m_mean"
OUT_DIR = os.path.join(ROOT, "datasourceSIH", "external")
TEST_START, TEST_END, CLIM_END = "2022-01-01", "2024-12-31", "2018-12-31"


def get(url, tries=8):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read().decode()
        except urllib.error.HTTPError as e:
            if k == tries - 1:
                raise
            time.sleep(70 if e.code == 429 else 5 * (k + 1))  # free tier: per-minute request budget
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(5 * (k + 1))


def weather_csv(name, lat, lon):
    path = os.path.join(OUT_DIR, f"{name}_openmeteo.csv")
    if os.path.exists(path) and os.path.getsize(path) < 1000:
        os.remove(path)  # a truncated/empty download from an earlier failed run
    if not os.path.exists(path):
        url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
               f"&start_date=1995-01-01&end_date={TEST_END}&daily={DAILY}&timezone=Asia%2FKolkata&format=csv")
        os.makedirs(OUT_DIR, exist_ok=True)
        text = get(url)  # download fully BEFORE creating the cache file, so a failure leaves nothing behind
        with open(path, "w") as f:
            f.write(text)
    return open(path).read()


def terrain(lat, lon):
    """Mean elevation and mean slope over a ~1 km box from a 5x5 grid of Copernicus DEM samples."""
    step = 0.0025  # ~250 m
    lats = [lat + (i - 2) * step for i in range(5) for _ in range(5)]
    lons = [lon + (j - 2) * step for _ in range(5) for j in range(5)]
    z = np.array(json.loads(get("https://api.open-meteo.com/v1/elevation?latitude=" + ",".join(f"{x:.5f}" for x in lats)
                                + "&longitude=" + ",".join(f"{x:.5f}" for x in lons)))["elevation"]).reshape(5, 5)
    dy = step * 111_320
    dx = step * 111_320 * np.cos(np.radians(lat))
    gy, gx = np.gradient(z, dy, dx)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    return float(z.mean()), float(slope.mean())


def main():
    rows, per = [], []
    for name, (lat, lon, ttype) in PLACES.items():
        raw = ef_predict.read_weather_csv(weather_csv(name, lat, lon))
        w, _ = ef_predict.normalise(raw)
        elev, slope = terrain(lat, lon)
        static = {"ndvi_trend_slope": 0.0, "ndbi_trend_slope": 0.0, "mean_slope_degrees": slope,
                  "elevation_mean_m": elev, "terrain_type": ttype}
        pred = ef_predict.predict(raw, static, adapt=False)  # the same reader/model path an upload takes
        # source recalibration exactly as the product does it, but fitted ONLY on history before 2022
        rs = pred.set_index("date")["rain_mm"]
        pa, aa, _, _ = ef_predict.adapt_to_source(pred.prob_extreme_rain_next_3d.to_numpy(), rs, fit_until=TEST_START)
        pred = pred.assign(p_adapt=pa, alert_adapt=aa)
        rain = w.set_index("date")["rain"]
        thr = rain[:CLIM_END].quantile(0.99)
        ext = (rain >= thr).astype(float)
        fut = pd.concat([ext.shift(-k) for k in (1, 2, 3)], axis=1).max(axis=1)
        df = pred.set_index("date").join(fut.rename("y")).dropna(subset=["y"])
        # climatology baseline from the same source: base rate per calendar month, 1995-2018
        clim = fut[:CLIM_END].groupby(fut[:CLIM_END].index.month).mean()
        df["clim"] = df.index.month.map(clim)
        test = df[TEST_START:TEST_END]
        test = test.assign(site=name)
        rows.append(test)
        per.append({"place": name, "terrain": ttype, "elevation_m": round(elev), "slope_deg": round(slope, 1),
                    "extreme_threshold_mm": round(float(thr), 1), "test_days": len(test),
                    "positive_rate": round(float(test.y.mean()), 4),
                    "roc_auc": round(float(roc_auc_score(test.y, test.prob_extreme_rain_next_3d)), 3),
                    "roc_auc_recalibrated": round(float(roc_auc_score(test.y, test.p_adapt)), 3),
                    "climatology_roc_auc": round(float(roc_auc_score(test.y, test.clim)), 3)})
        print(per[-1])
    allp = pd.concat(rows)
    y, p, c, a = allp.y, allp.prob_extreme_rain_next_3d, allp.clim, allp.alert
    tp = int((a & (y == 1)).sum())
    res = {
        "what": "72 h model on 9 unseen locations, ERA5 (Open-Meteo) weather, 2022-2024; labels from the same source",
        "n_days": len(allp), "positive_rate": round(float(y.mean()), 4),
        "model": {"roc_auc": round(float(roc_auc_score(y, p)), 4), "pr_auc": round(float(average_precision_score(y, p)), 4),
                  "brier": round(float(brier_score_loss(y, p)), 5),
                  "precision_at_alert": round(tp / max(int(a.sum()), 1), 4), "recall_at_alert": round(tp / max(int(y.sum()), 1), 4),
                  "alert_rate": round(float(a.mean()), 4)},
        "model_recalibrated_to_source": {
            "how": "Platt map on logit(p), fitted on each place's own 1995-2021 history with labels from its own rain",
            "roc_auc": round(float(roc_auc_score(y, allp.p_adapt)), 4), "pr_auc": round(float(average_precision_score(y, allp.p_adapt)), 4),
            "brier": round(float(brier_score_loss(y, allp.p_adapt)), 5), "mean_predicted": round(float(allp.p_adapt.mean()), 4),
            "precision_at_alert": round(int((allp.alert_adapt & (y == 1)).sum()) / max(int(allp.alert_adapt.sum()), 1), 4),
            "recall_at_alert": round(int((allp.alert_adapt & (y == 1)).sum()) / max(int(y.sum()), 1), 4),
            "alert_rate": round(float(allp.alert_adapt.mean()), 4)},
        "climatology": {"roc_auc": round(float(roc_auc_score(y, c)), 4), "pr_auc": round(float(average_precision_score(y, c)), 4),
                        "brier": round(float(brier_score_loss(y, c)), 5)},
        "mean_predicted_vs_observed": [round(float(p.mean()), 4), round(float(y.mean()), 4)],
        "per_place": per,
    }
    with open(os.path.join(ROOT, "ml", "external_results.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: v for k, v in res.items() if k != "per_place"}, indent=2))


if __name__ == "__main__":
    main()
