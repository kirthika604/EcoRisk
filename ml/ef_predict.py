#!/usr/bin/env python3
"""EcoForecast step 3: predict on UNSEEN data.

Input: a CSV of daily weather for one location with columns
    date, rain, T2M, RH2M, PS, WS2M, T2MDEW      (same units as NASA POWER: mm, C, %, kPa, m/s, C)
at least 30 consecutive days. Static terrain features come from --site (a site id in
ml/feature_table.csv) or from --slope/--elevation/--coastal for a new location.

Output: for every day with enough history, the probability of an extreme-rainfall day within the
next 3 days, an alert flag (threshold fixed from validation, never from the input), and the top
factors pushing that day's probability up (feature-ablation vs. training medians).

    python3 ml/ef_predict.py weather.csv --site wayanad [--window 24|48|72] [--out preds.csv]
"""
import argparse
import json
import os
import pickle

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys_path = os.path.join(ROOT, "ml")
import sys

sys.path.insert(0, sys_path)
from ef_data import STATIC, features  # noqa: E402



# Column understanding for outside data. Each model input is found by meaning (tokens in the
# column name), not by one exact spelling, and converted from whatever unit the name declares.
_RULES = {
    "date": {"any": {"date", "time", "datetime", "day", "timestamp", "dt"}, "avoid": set()},
    "rain": {"any": {"rain", "rainfall", "precip", "precipitation", "prcp", "prectotcorr", "ppt", "precipitationcal"},
             "avoid": {"hours", "probability", "prob", "snow", "snowfall", "showers", "intensity", "max", "flag"}},
    "T2M": {"any": {"t2m", "temp", "temperature", "tavg", "tmean", "tas"},
            "avoid": {"dew", "dewpoint", "max", "min", "apparent", "soil", "feels", "wet", "bulb", "tmax", "tmin"}},
    "RH2M": {"any": {"rh", "rh2m", "humidity", "relativehumidity", "hurs"}, "avoid": {"specific", "max", "min", "soil"}},
    "PS": {"any": {"ps", "pressure", "press", "pres", "slp", "msl", "mslp"}, "avoid": {"vapour", "vapor", "max", "min", "tendency"}},
    "WS2M": {"any": {"ws", "ws2m", "ws10m", "wind", "windspeed", "wspd", "sfcwind"}, "avoid": {"gust", "gusts", "direction", "dir", "max", "min"}},
    "T2MDEW": {"any": {"t2mdew", "dew", "dewpoint", "tdew", "td"}, "avoid": {"max", "min", "depression"}},
}
_PREFER = {"rain": {"sum", "total", "precipitation"}, "T2M": {"mean", "avg"}, "RH2M": {"mean", "avg"},
           "PS": {"surface", "mean"}, "WS2M": {"mean", "avg", "2m"}, "T2MDEW": {"mean", "avg"}}


def _tokens(name):
    """'wind_speed_10m_mean (km/h)' -> ({'wind','speed','10m','mean','windspeed'}, 'km/h')."""
    import re
    unit = ""
    m = re.search(r"[\(\[]([^\)\]]+)[\)\]]", name)
    if m:
        unit = m.group(1).strip().lower()
        name = name[:m.start()] + name[m.end():]
    parts = [t for t in re.split(r"[^a-z0-9%]+", name.lower()) if t]
    toks = set(parts)
    toks |= {a + b for a, b in zip(parts, parts[1:])}  # 'wind','speed' -> 'windspeed'
    return toks, unit


def _unit_of(toks, unit):
    u = unit.replace(" ", "").replace("°", "")
    tags = toks | {u}
    if tags & {"km/h", "kmh", "kph", "kmph"}: return "kmh"
    if tags & {"mph"}: return "mph"
    if tags & {"kn", "kt", "kts", "knots", "knot"}: return "knots"
    if tags & {"f", "degf", "fahrenheit"}: return "F"
    if tags & {"k", "kelvin"}: return "K"
    if tags & {"in", "inch", "inches"}: return "in"
    if tags & {"cm"}: return "cm"
    if tags & {"hpa", "mb", "mbar", "millibar"}: return "hPa"
    if tags & {"pa"}: return "Pa"
    if tags & {"inhg"}: return "inHg"
    if tags & {"kpa"}: return "kPa"
    return ""


def read_weather_csv(text):
    """Read a weather CSV from outside sources: skips metadata lines above the real header
    (e.g. Open-Meteo/NASA POWER downloads) and accepts ',' ';' or tab separators."""
    import csv
    import io
    text = text.lstrip("\ufeff")  # byte-order mark from Excel / some exports
    lines = [l for l in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    if not any(l.strip() for l in lines):
        raise ValueError("No columns to parse from file")
    sample = "\n".join(l for l in lines[:50] if l.strip())
    try:
        sep = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        sep = ","
    start = 0
    for i, l in enumerate(lines[:200]):
        first = l.split(sep)[0].strip().strip('"').lower()
        if _tokens(first)[0] & _RULES["date"]["any"] and len(l.split(sep)) >= 3:
            start = i
            break
    if "-END HEADER-" in text:  # NASA POWER CSV export
        start = next(i for i, l in enumerate(lines) if "-END HEADER-" in l) + 1
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])), sep=sep)
    if {"YEAR", "DOY"} <= set(df.columns) and "date" not in [c.lower() for c in df.columns]:
        df.insert(0, "date", pd.to_datetime(df["YEAR"].astype(int).astype(str) + df["DOY"].astype(int).astype(str).str.zfill(3), format="%Y%j"))
    elif {"YEAR", "MO", "DY"} <= set(df.columns):
        df.insert(0, "date", pd.to_datetime(dict(year=df.YEAR, month=df.MO, day=df.DY)))
    return df


def normalise(df):
    """Map outside column names/units to the model's schema; report every change. Returns
    (frame, notes). Never invents measurements except dew point, derived from temperature +
    humidity (Magnus formula) when absent. Sea-level pressure is flagged for conversion to surface
    pressure in predict(), which knows the elevation."""
    notes = []
    out = pd.DataFrame()
    used = set()
    info = {c: _tokens(str(c)) for c in df.columns}
    for canon, rule in _RULES.items():
        cands = []
        for c, (toks, unit) in info.items():
            if c in used or not (toks & rule["any"]) or (toks & rule["avoid"]):
                continue
            score = len(toks & _PREFER.get(canon, set())) + (2 if str(c).strip().lower() == canon.lower() else 0)
            cands.append((score, c))
        if not cands:
            continue
        hit = max(cands, key=lambda t: t[0])[1]
        used.add(hit)
        out[canon] = df[hit]
        if str(hit) != canon:
            notes.append(f"mapped column '{hit}' -> {canon}")
    for c in [c for c in out.columns if c != "date"]:
        num = pd.to_numeric(out[c], errors="coerce")
        bad = num.isna() & out[c].notna() & (out[c].astype(str).str.strip() != "")
        if bad.any():
            raise ValueError(f"non-numeric values in column {c}, e.g. '{out.loc[bad, c].iloc[0]}'")
        out[c] = num.where(num > -900)  # common missing-value sentinels (-999, -9999)
    # unit conversions, driven by the declared unit (name tokens or '(unit)') with value checks
    origin = {}
    for n in notes:
        if n.startswith("mapped column '"):
            col, canon = n[len("mapped column '"):].split("' -> ")
            origin[canon] = col
    for canon in out.columns:
        col = origin.get(canon, canon)
        toks, unit = _tokens(str(col))
        u = _unit_of(toks, unit)
        if canon in ("T2M", "T2MDEW"):
            if u == "F" or (u == "" and out[canon].median() > 60):
                out[canon] = (out[canon] - 32) * 5 / 9; notes.append(f"converted {canon} from °F to °C")
            elif u == "K" or (u == "" and out[canon].median() > 200):
                out[canon] = out[canon] - 273.15; notes.append(f"converted {canon} from K to °C")
        elif canon == "rain":
            if u == "in":
                out[canon] = out[canon] * 25.4; notes.append("converted rain from inches to mm")
            elif u == "cm":
                out[canon] = out[canon] * 10; notes.append("converted rain from cm to mm")
        elif canon == "PS":
            if u == "hPa" or (u == "" and 200 < out[canon].median() < 2000):
                out[canon] = out[canon] / 10; notes.append("converted PS from hPa to kPa")
            elif u == "Pa" or (u == "" and out[canon].median() > 20000):
                out[canon] = out[canon] / 1000; notes.append("converted PS from Pa to kPa")
            elif u == "inHg":
                out[canon] = out[canon] * 3.38639; notes.append("converted PS from inHg to kPa")
            if toks & {"msl", "slp", "mslp", "sea"}:
                out.attrs["ps_is_msl"] = True
        elif canon == "WS2M":
            if u == "kmh":
                out[canon] = out[canon] / 3.6; notes.append("converted wind from km/h to m/s")
            elif u == "mph":
                out[canon] = out[canon] * 0.44704; notes.append("converted wind from mph to m/s")
            elif u == "knots":
                out[canon] = out[canon] * 0.514444; notes.append("converted wind from knots to m/s")
            if toks & {"10m", "ws10m", "10"} or "10m" in str(col).lower():
                out[canon] = out[canon] * 4.87 / np.log(67.8 * 10 - 5.42)  # FAO-56 log profile, 10 m -> 2 m
                notes.append("scaled 10 m wind to 2 m height (FAO-56)")
        if canon == "RH2M" and out[canon].max() <= 1.0:
            out[canon] = out[canon] * 100; notes.append("converted humidity from 0-1 to %")
    blanks = int(out.drop(columns=["date"], errors="ignore").isna().sum().sum())
    if blanks:
        notes.append(f"{blanks} blank value(s) found; days whose rolling windows include a blank are "
                     f"skipped rather than guessed")
    if "date" in out.columns:
        d = pd.to_datetime(out["date"], errors="coerce")
        if d.isna().any():
            raise ValueError(f"unreadable date, e.g. '{out.loc[d.isna(), 'date'].iloc[0]}'")
        out["date"] = d.dt.normalize()
    if "T2MDEW" not in out.columns and {"T2M", "RH2M"} <= set(out.columns):
        a, b = 17.62, 243.12
        g = np.log(out["RH2M"].clip(lower=1) / 100) + a * out["T2M"] / (b + out["T2M"])
        out["T2MDEW"] = b * g / (a - g)
        notes.append("derived T2MDEW from T2M + RH2M (Magnus formula)")
    missing = [c for c in ["date", "rain", "T2M", "RH2M", "PS", "WS2M", "T2MDEW"] if c not in out.columns]
    if missing:
        raise ValueError(f"missing columns (after alias mapping): {missing}")
    check_physical(out)
    return out, notes


# Values outside these bounds cannot be real daily weather on Earth (after unit conversion), so the
# file is rejected rather than silently predicted on. Bounds are generous: world daily rainfall record
# is ~1,825 mm; India's ~1,000 mm.
PHYSICAL = {"rain": (0, 1000, "mm/day"), "T2M": (-60, 60, "°C"), "T2MDEW": (-80, 40, "°C"),
            "RH2M": (0, 100.5, "%"), "PS": (30, 110, "kPa"), "WS2M": (0, 75, "m/s")}
_NICE = {"rain": "rainfall", "T2M": "temperature", "T2MDEW": "dew point", "RH2M": "humidity",
         "PS": "pressure", "WS2M": "wind speed"}


def check_physical(w):
    for c, (lo, hi, unit) in PHYSICAL.items():
        bad = w[c].notna() & ((w[c] < lo) | (w[c] > hi))
        if bad.any():
            i = bad.idxmax()
            raise ValueError(f"impossible value: {_NICE[c]} {w.loc[i, c]:.1f} {unit} on "
                             f"{pd.Timestamp(w.loc[i, 'date']).date()} (valid range {lo} to {hi} {unit})")


_RANGES = {}
# dynamic inputs whose unfamiliarity matters (season and terrain are handled elsewhere)
# (humidity and dew-point spread are left out: they sit at natural limits like 100% / 0 °C on
# ordinary wet days, so flagging them would be noise, not a warning)
_OOD_FEATS = ["rain_1d", "rain_3d", "rain_7d", "rain_30d", "t2m", "ws2m",
              "ps_anom", "ps_chg_1d", "ps_chg_3d", "mean_slope_degrees", "elevation_mean_m"]


def runtime_artifacts():
    """Small precomputed summaries of the training table (ml/build_runtime.py). Deployments ship
    this ~130 KB file instead of the 77 MB ml/ef_features.csv."""
    if "a" not in _RANGES:
        with open(os.path.join(ROOT, "ml", "runtime_artifacts.json")) as f:
            _RANGES["a"] = json.load(f)
    return _RANGES["a"]


def training_ranges():
    """0.1-99.9th percentile of each input over ALL training rows: the model's 'experience'."""
    return {c: tuple(v) for c, v in runtime_artifacts()["ood_ranges"].items()}


def unfamiliar(d):
    """Per row: inputs outside the training experience, e.g. 'rain_1d=450.0 (seen up to 112.3)'."""
    R = training_ranges()
    out = [[] for _ in range(len(d))]
    for c in _OOD_FEATS:
        lo, hi = R[c]
        v = d[c].to_numpy(dtype=float)
        for i in np.where((v < lo) | (v > hi))[0]:
            out[i].append(f"{c}={v[i]:.1f} (seen {lo:.1f} to {hi:.1f})")
    return ["; ".join(x) for x in out]


_MEDIANS = {}


def reference_medians(feats, skewed):
    """Training-data medians used as the 'typical day' for factor ablation (cached)."""
    if "x" not in _MEDIANS:  # already log-transformed for the skewed inputs (see ml/build_runtime.py)
        _MEDIANS["x"] = pd.Series(runtime_artifacts()["ref_medians"])[feats]
    return _MEDIANS["x"]


_MODEL = {}


HORIZONS = (24, 48, 72)


def load_model(horizon=72):
    """The trained model for a prediction window: 72 h from ef_model.py, 24/48 h from ef_horizons.py."""
    horizon = int(horizon)
    if horizon not in HORIZONS:
        raise ValueError(f"prediction window must be one of {HORIZONS} hours")
    if horizon not in _MODEL:
        name = "ef_model.pkl" if horizon == 72 else f"ef_model_{horizon}.pkl"
        with open(os.path.join(ROOT, "ml", name), "rb") as f:
            _MODEL[horizon] = pickle.load(f)
    return _MODEL[horizon]


def build(weather, static):
    w = weather.copy()
    w["date"] = pd.to_datetime(w["date"])
    w = w.sort_values("date").set_index("date").rename(columns={"rain": "rain"})
    need = ["rain", "T2M", "RH2M", "PS", "WS2M", "T2MDEW"]
    missing = [c for c in need if c not in w.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    if len(w) < 31:
        raise ValueError("need at least 31 days of history")
    if (w.index.to_series().diff().dropna() != pd.Timedelta(days=1)).any():
        raise ValueError("dates must be consecutive daily rows with no gaps")
    row = {**static, "site_id": "input", "disaster_occurred": 0, "disaster_date": None}
    d = features(w, row)
    return d.dropna(subset=[c for c in d.columns if c not in ("y", "y_24h", "y_48h", "event_date", "extreme_threshold_mm")])


def explain(model, X, p, feats, skewed, top_k=3):
    """Top factors per row: how much the probability drops when one dynamic feature is reset to a
    typical (training-median) day. Batched: one predict call per feature over all rows."""
    Xref = reference_medians(feats, skewed)
    dyn = [c for c in feats if c not in STATIC and c != "terrain_is_coastal"]
    deltas = {}
    for c in dyn:
        x = X.copy()
        x[c] = Xref[c]
        deltas[c] = p - model.predict_proba(x)[:, 1]
    out = []
    for i in range(len(X)):
        top = sorted(((c, deltas[c][i]) for c in dyn), key=lambda t: -t[1])[:top_k]
        out.append("; ".join(f"{c} (+{v:.2f})" for c, v in top if v > 0))
    return out


def consistent_proba(X, horizon):
    """P(event within h) for the requested window, made consistent across windows: an event within
    72 h includes one within 48 h, so p72 >= p48 >= p24. Separate models broke this on 2-4% of days
    (by up to ~28 points); taking the running maximum fixes it and slightly improves test skill."""
    p = None
    for h in HORIZONS:
        if h > int(horizon):
            break
        q = load_model(h)["model"].predict_proba(X)[:, 1]
        p = q if p is None else np.maximum(p, q)
    return p


def predict_row(row, horizon=72):
    """Score ONE hand-built feature row (the what-if calculator). `row` holds every model feature
    in raw units; returns probability, alert flag and top factors from the same trained model."""
    bundle = load_model(horizon)
    model, feats, skewed, thr = bundle["model"], bundle["features"], bundle["skewed"], bundle["threshold"]
    X = pd.DataFrame([{c: float(row[c]) for c in feats}])
    X[skewed] = np.log1p(X[skewed].clip(lower=0))
    p = consistent_proba(X, horizon)
    raw = pd.DataFrame([{c: float(row[c]) for c in _OOD_FEATS if c in row}])
    return {"prob": round(float(p[0]), 4), "alert": bool(p[0] >= thr), "threshold": float(thr),
            "top_factors": explain(model, X, p, feats, skewed)[0],
            "unfamiliar": unfamiliar(raw)[0] if set(_OOD_FEATS) <= set(raw.columns) else ""}


def predict(weather, static, top_k=3, adapt=True, horizon=72):
    weather, _ = normalise(weather)
    if weather.attrs.get("ps_is_msl"):
        weather["PS"] = weather["PS"] * np.exp(-float(static["elevation_mean_m"]) / 8434.0)  # barometric
    bundle = load_model(horizon)
    model, feats, skewed, thr = bundle["model"], bundle["features"], bundle["skewed"], bundle["threshold"]
    d = build(weather, static)
    X = d[feats].copy()
    X[skewed] = np.log1p(X[skewed].clip(lower=0))
    p = consistent_proba(X, horizon)
    # factors explain the base model; only the recent rows are shown, so only those are explained
    k = min(len(X), 400)
    factors = [""] * (len(X) - k) + explain(model, X.iloc[-k:], p[-k:], feats, skewed, top_k)
    notes = []
    p_out, alert = p, p >= thr
    adapted = adapt_to_source(p, d["rain_1d"], horizon=horizon) if adapt else None
    if adapted is not None:
        p_out, alert, n_years, a_thr = adapted
        thr = a_thr
        notes.append(f"recalibrated to this data source using {n_years:.0f} years of its own history")
    elif adapt and len(d) < ADAPT_MIN_DAYS:
        notes.append("probabilities are calibrated to NASA POWER data; for another source, include 5+ years "
                     "of history so EcoRisk AI can recalibrate to it")
    out = pd.DataFrame({"date": d.index, "prob_extreme_rain_next_3d": np.round(p_out, 4),
                        "alert": alert, "top_factors": factors})
    out["window"] = f"next {int(horizon)} h"
    out["rain_mm"] = d["rain_1d"].round(2).to_numpy()
    out["unfamiliar"] = unfamiliar(d)
    n_odd = int((out["unfamiliar"].tail(30) != "").sum())
    if n_odd:
        notes.append(f"{n_odd} of the last {min(30, len(out))} days have inputs beyond the training experience; "
                     f"treat those forecasts with extra caution")
    out.attrs["notes"] = notes
    out.attrs["threshold"] = float(thr)
    out.attrs["recalibrated"] = adapted is not None
    return out


ADAPT_MIN_DAYS = 5 * 365
_HOLDOUT_DAYS = 60  # the displayed recent window is never used to fit the calibrator


def adapt_to_source(p, rain, fit_until=None, horizon=72):
    """Recalibrate the base model to an outside data source using that source's OWN history.

    Labels come from the uploaded rainfall itself (an extreme day = top 1% of its own daily rain;
    target = one occurs in the next 3 days), so no outside information is used. A one-feature
    logistic (Platt) map on logit(p) is fitted on history older than the last 60 days, and the alert
    threshold is set to give the same alert rate the deployed model has on its own validation-tuned
    data. Validated on 9 unseen places with ERA5 data (ml/external_validation.py): PR-AUC 0.141 ->
    0.214, mean predicted 5.2% -> 2.8% vs 2.5% observed. Returns None when history is too short."""
    from sklearn.linear_model import LogisticRegression
    n = len(p)
    # fit only on rows before `cut`: the last 60 days by default, or an explicit date (validation)
    cut = n - _HOLDOUT_DAYS if fit_until is None else int((rain.index < pd.Timestamp(fit_until)).sum()) - 3
    if cut < ADAPT_MIN_DAYS:
        return None
    r = rain.to_numpy(dtype=float)
    hist = slice(0, cut)
    thr_mm = np.nanquantile(r[hist], 0.99)
    ext = (r >= thr_mm).astype(float)
    y = np.full(n, np.nan)
    days = int(horizon) // 24
    for i in range(n - days):
        y[i] = ext[i + 1:i + 1 + days].max()
    m = ~np.isnan(y)
    m[cut:] = False
    if y[m].sum() < 10:  # too few extremes to fit a calibration honestly
        return None
    lg = lambda q: np.log(np.clip(q, 1e-4, 1 - 1e-4) / (1 - np.clip(q, 1e-4, 1 - 1e-4)))
    cal = LogisticRegression(C=1.0).fit(lg(p[m]).reshape(-1, 1), y[m])
    pa = cal.predict_proba(lg(p).reshape(-1, 1))[:, 1]
    rate = _deployed_alert_rate(horizon)
    a_thr = np.quantile(pa[m], 1 - rate)
    return pa, pa >= a_thr, m.sum() / 365.25, float(a_thr)


def _deployed_alert_rate(horizon=72):
    with open(os.path.join(ROOT, "ml", "ef_horizons.json")) as f:
        return float(json.load(f)["windows"][str(int(horizon))]["alert_rate"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--site")
    ap.add_argument("--slope", type=float)
    ap.add_argument("--elevation", type=float)
    ap.add_argument("--coastal", type=int, default=0)
    ap.add_argument("--window", type=int, default=72, choices=HORIZONS, help="prediction window in hours")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.site:
        ft = pd.read_csv(os.path.join(ROOT, "ml", "feature_table.csv")).set_index("site_id").loc[a.site]
        static = {c: ft[c] for c in STATIC}
        static["terrain_type"] = ft["terrain_type"]
    else:
        if a.slope is None or a.elevation is None:
            ap.error("give --site or both --slope and --elevation")
        static = {"ndvi_trend_slope": 0.0, "ndbi_trend_slope": 0.0, "mean_slope_degrees": a.slope,
                  "elevation_mean_m": a.elevation, "terrain_type": "coastal" if a.coastal else "hill"}
    with open(a.csv) as f:  # same outside-data reader as the web page (metadata blocks, units, ...)
        out = predict(read_weather_csv(f.read()), static, horizon=a.window)
    for n in out.attrs.get("notes", []):
        print("note:", n)
    if a.out:
        out.to_csv(a.out, index=False)
    print(out.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
