"""Reliability checks for EcoForecast: python3 -m pytest ml/test_ef.py"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(__file__))
import ef_predict
import urllib.error
from ef_data import TRAIN_END

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = {"ndvi_trend_slope": 0.0, "ndbi_trend_slope": 0.0, "mean_slope_degrees": 20.0,
          "elevation_mean_m": 500.0, "terrain_type": "hill"}


def weather(days=45):
    w = pd.read_csv(os.path.join(ROOT, "datasourceSIH", "sites", "wayanad", "weather_daily.csv"),
                    parse_dates=["date"])
    return w[w.date >= "2024-06-01"].head(days)


def test_predicts_valid_probabilities():
    out = ef_predict.predict(weather(), STATIC)
    assert len(out) > 0 and out.prob_extreme_rain_next_3d.between(0, 1).all()


def test_rejects_short_history():
    with pytest.raises(ValueError):
        ef_predict.predict(weather(20), STATIC)


def test_rejects_gaps():
    with pytest.raises(ValueError):
        ef_predict.predict(weather().drop(index=weather().index[10]), STATIC)


def test_rejects_missing_columns():
    with pytest.raises(ValueError):
        ef_predict.predict(weather().drop(columns=["RH2M"]), STATIC)


def test_label_threshold_uses_train_years_only():
    df = pd.read_csv(os.path.join(ROOT, "ml", "ef_features.csv"), parse_dates=["date"])
    for s, g in df.groupby("site_id"):
        w = pd.read_csv(os.path.join(ROOT, "datasourceSIH", "sites", s, "weather_daily.csv"),
                        parse_dates=["date"], index_col="date")
        assert abs(g.extreme_threshold_mm.iloc[0] - w.loc[:TRAIN_END, "rain"].quantile(0.99)) < 1e-9


def test_alias_mapping_and_unit_fix():
    w = weather().rename(columns={"rain": "Precipitation", "T2M": "temp", "RH2M": "humidity",
                                  "PS": "pressure", "WS2M": "wind", "date": "Date"})
    w["pressure"] = w["pressure"] * 10  # hPa
    w = w.drop(columns=["T2MDEW"])
    out = ef_predict.predict(w, STATIC)
    ref = ef_predict.predict(weather(), STATIC)
    assert len(out) == len(ref) and out.prob_extreme_rain_next_3d.between(0, 1).all()


def _serve():
    import threading
    from http.server import ThreadingHTTPServer
    import ef_server
    srv = ThreadingHTTPServer(("127.0.0.1", 0), ef_server.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _post(srv, body):
    import json, urllib.request, urllib.error
    req = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}/api/predict",
                                 json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_server_predict_ok_and_errors():
    srv = _serve()
    try:
        csv = weather().to_csv(index=False)
        code, d = _post(srv, {"csv": csv, "site": "wayanad"})
        assert code == 200 and len(d["rows"]) > 0
        assert _post(srv, {"csv": csv, "site": "nope"})[0] == 400
        assert _post(srv, {"csv": "a,b\n1,2", "site": "wayanad"})[0] == 400
        assert _post(srv, {"csv": csv})[0] == 400  # no site and no terrain
    finally:
        srv.shutdown()


def test_server_serves_old_ecorisk_pages_and_valid_json():
    import json, urllib.request
    srv = _serve()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        for path in ("/dashboard/", "/demo/", "/awareness/", "/dashboard/app.js"):
            assert urllib.request.urlopen(base + path).status == 200
        risk = json.load(urllib.request.urlopen(base + "/api/risk"))  # strict parse: no NaN
        assert len(risk["ranking"]) == 19
        sites = json.load(urllib.request.urlopen(base + "/api/sites"))
        assert len(sites) > 0
        try:
            urllib.request.urlopen(base + "/dashboard/%2e%2e/ml/ef_server.py")
            assert False, "path traversal should 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        srv.shutdown()


def test_whatif_more_rain_raises_probability():
    import json, urllib.request
    srv = _serve()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        row = json.load(urllib.request.urlopen(base + "/api/base?site=wayanad&month=7"))["row"]
        def score(r):
            req = urllib.request.Request(base + "/api/whatif", json.dumps({"row": r}).encode(),
                                         {"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req))["prob"]
        dry = score(row)
        wet = score({**row, "rain_1d": 60, "rain_3d": 120, "rain_7d": 200})
        assert 0 <= dry < wet <= 1
    finally:
        srv.shutdown()


def test_bad_values_give_clear_400_not_a_crash():
    srv = _serve()
    try:
        w = weather()
        w["rain"] = w["rain"].astype(object)
        w.iloc[5, w.columns.get_loc("rain")] = "abc"
        code, d = _post(srv, {"csv": w.to_csv(index=False), "site": "wayanad"})
        assert code == 400 and "non-numeric" in d["error"]
        w2 = weather().astype({"date": str})
        w2.iloc[3, w2.columns.get_loc("date")] = "not-a-date"
        code, d = _post(srv, {"csv": w2.to_csv(index=False), "site": "wayanad"})
        assert code == 400 and "date" in d["error"]
    finally:
        srv.shutdown()


# ---------- outside data formats ----------
def _ref():
    return ef_predict.predict(weather(), STATIC)


def test_open_meteo_download_with_metadata_block():
    w = weather()
    rows = "\n".join(f"{d.date()},{r:.2f},{t:.1f},{h:.0f},{p*10:.1f},{ws*3.6/0.748:.1f},{td:.1f}"
                     for d, r, t, h, p, ws, td in zip(w.date, w.rain, w.T2M, w.RH2M, w.PS, w.WS2M, w.T2MDEW))
    text = ("latitude,longitude,elevation,utc_offset_seconds,timezone,timezone_abbreviation\n"
            "11.45,76.08,630.0,19800,Asia/Kolkata,IST\n\n"
            "time,precipitation_sum (mm),temperature_2m_mean (°C),relative_humidity_2m_mean (%),"
            "surface_pressure_mean (hPa),wind_speed_10m_mean (km/h),dew_point_2m_mean (°C)\n" + rows)
    raw = ef_predict.read_weather_csv(text)
    out = ef_predict.predict(raw, STATIC)
    ref = _ref()
    assert len(out) == len(ref)
    assert (out.prob_extreme_rain_next_3d - ref.prob_extreme_rain_next_3d).abs().max() < 0.02


def test_us_units_semicolon_and_precip_hours_ignored():
    w = weather()
    df = pd.DataFrame({"Date": w.date.dt.strftime("%Y-%m-%d"), "precipitation_hours": 5,
                       "Precip (in)": w.rain / 25.4, "Temp (F)": w.T2M * 9 / 5 + 32, "Humidity (%)": w.RH2M,
                       "Pressure (inHg)": w.PS / 3.38639, "Wind (mph)": w.WS2M / 0.44704, "Dew Point (F)": w.T2MDEW * 9 / 5 + 32})
    out = ef_predict.predict(ef_predict.read_weather_csv(df.to_csv(index=False, sep=";")), STATIC)
    assert (out.prob_extreme_rain_next_3d - _ref().prob_extreme_rain_next_3d).abs().max() < 0.005


def test_nasa_power_csv_export_and_sea_level_pressure():
    w = weather()
    body = pd.DataFrame({"YEAR": w.date.dt.year, "DOY": w.date.dt.dayofyear, "PRECTOTCORR": w.rain, "T2M": w.T2M,
                         "RH2M": w.RH2M, "PS": w.PS, "WS2M": w.WS2M, "T2MDEW": w.T2MDEW}).to_csv(index=False)
    text = "-BEGIN HEADER-\nNASA/POWER CERES/MERRA2 ...\n-END HEADER-\n" + body
    out = ef_predict.predict(ef_predict.read_weather_csv(text), STATIC)
    assert (out.prob_extreme_rain_next_3d - _ref().prob_extreme_rain_next_3d).abs().max() < 1e-9
    msl = weather().rename(columns={"PS": "msl_pressure (hPa)"})
    msl["msl_pressure (hPa)"] = msl["msl_pressure (hPa)"] * 10 * np.exp(STATIC["elevation_mean_m"] / 8434.0)
    out2 = ef_predict.predict(msl, STATIC)
    assert (out2.prob_extreme_rain_next_3d - _ref().prob_extreme_rain_next_3d).abs().max() < 0.002


def test_long_outside_file_is_recalibrated_short_one_is_flagged():
    path = os.path.join(ROOT, "ecorisk-ai", "samples", "shimla_2023-08-13_openmeteo.csv")
    st = {**STATIC, "mean_slope_degrees": 21.0, "elevation_mean_m": 2095.0}
    long_out = ef_predict.predict(ef_predict.read_weather_csv(open(path).read()), st)
    assert long_out.attrs["recalibrated"] and "recalibrated" in long_out.attrs["notes"][0]
    assert long_out.prob_extreme_rain_next_3d.between(0, 1).all()
    short_out = ef_predict.predict(weather(), STATIC)
    assert not short_out.attrs["recalibrated"] and "NASA POWER" in short_out.attrs["notes"][0]
    raw_only = ef_predict.predict(weather(), STATIC, adapt=False)
    assert raw_only.attrs["notes"] == []


# ---------- prediction relevance / outliers ----------
def test_impossible_values_are_rejected():
    for col, val in (("RH2M", 140), ("rain", -5), ("T2M", 75), ("PS", 5)):
        w = weather()
        w.loc[w.index[12], col] = val
        with pytest.raises(ValueError, match="impossible value"):
            ef_predict.predict(w, STATIC)


def test_unfamiliar_inputs_are_flagged_and_normal_days_are_not():
    normal = ef_predict.predict(weather(), STATIC)
    assert (normal.unfamiliar == "").all()
    w = weather()
    w.loc[w.index[-1], "rain"] = 400  # far beyond the ~87 mm/day the model has seen
    odd = ef_predict.predict(w, STATIC)
    assert "rain_1d=400.0" in odd.unfamiliar.iloc[-1]
    assert any("beyond the training experience" in n for n in odd.attrs["notes"])


def test_more_rain_never_lowers_the_forecast():
    """Monotonic constraints: sweeping today's rain upward on real days never reduces probability."""
    import json, urllib.request
    srv = _serve()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        for site, month in (("wayanad", 7), ("kedarnath", 6), ("chennai", 11), ("jaisalmer", 1)):
            row = json.load(urllib.request.urlopen(f"{base}/api/base?site={site}&month={month}"))["row"]
            probs = []
            for v in (0, 5, 15, 30, 60, 100, 150):
                r = {**row, "rain_1d": v, "rain_3d": max(row["rain_3d"], v)}
                r["rain_7d"] = max(row["rain_7d"], r["rain_3d"]); r["rain_14d"] = max(row["rain_14d"], r["rain_7d"])
                r["rain_30d"] = max(row["rain_30d"], r["rain_14d"]); r["rain_accel"] = r["rain_3d"] - (r["rain_7d"] - r["rain_3d"]) * 3 / 4
                req = urllib.request.Request(base + "/api/whatif", json.dumps({"row": r}).encode(), {"Content-Type": "application/json"})
                probs.append(json.load(urllib.request.urlopen(req))["prob"])
            assert all(b >= a - 1e-9 for a, b in zip(probs, probs[1:])), (site, probs)
    finally:
        srv.shutdown()


# ---------- prediction windows ----------
def test_windows_are_consistent_24_le_48_le_72():
    outs = {h: ef_predict.predict(weather(), STATIC, horizon=h) for h in (24, 48, 72)}
    p24, p48, p72 = (outs[h].prob_extreme_rain_next_3d.to_numpy() for h in (24, 48, 72))
    assert (p48 >= p24 - 1e-9).all() and (p72 >= p48 - 1e-9).all()
    assert outs[24].window.iloc[0] == "next 24 h"
    with pytest.raises(ValueError):
        ef_predict.load_model(36)


def test_server_window_and_horizons_endpoint():
    import json, urllib.request
    srv = _serve()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        hz = json.load(urllib.request.urlopen(base + "/api/horizons"))
        for h in ("24", "48", "72"):
            w = hz["windows"][h]
            assert w["roc_auc"] > w["climatology"]["roc_auc"] and w["pr_auc"] > w["climatology"]["pr_auc"]
            assert len(w["value_curve_test"]) == 40 and w["peak_value"]["value"] > 0
        csv = weather().to_csv(index=False)
        p = {h: _post(srv, {"csv": csv, "site": "wayanad", "horizon": h})[1]["rows"][-1]["prob_extreme_rain_next_3d"] for h in (24, 72)}
        assert p[72] >= p[24]
        assert _post(srv, {"csv": csv, "site": "wayanad", "horizon": 36})[0] == 400
    finally:
        srv.shutdown()


def test_value_curve_math():
    import ef_horizons
    y = np.array([0, 0, 0, 1] * 25)
    perfect = ef_horizons.value_curve(y, y.astype(float), ratios=[0.1, 0.5])
    assert all(abs(v["value"] - 1) < 1e-9 for v in perfect)          # perfect foresight = 1
    useless = ef_horizons.value_curve(y, np.full(len(y), 0.25), ratios=[0.1, 0.5])
    assert all(abs(v["value"]) < 1e-9 for v in useless)              # constant forecast = no value


def test_command_line_reads_outside_files():
    import subprocess
    path = os.path.join(ROOT, "ecorisk-ai", "samples", "shimla_2023-08-13_openmeteo.csv")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "ml", "ef_predict.py"), path, "--slope", "21",
                        "--elevation", "2095", "--window", "24"], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-500:]
    assert "2023-08-13" in r.stdout and "recalibrated" in r.stdout


# ---------- bring your own dataset (ml/generic.py) ----------
def _ai4i():
    import generic
    return generic, generic.read_csv(open(os.path.join(ROOT, "ecorisk-ai", "samples", "ai4i2020.csv"), encoding="utf-8").read())


def test_generic_ai4i_excludes_leakage_and_ids_and_scores_well():
    G, df = _ai4i()
    assert "UDI" in df.columns  # byte-order mark stripped from the first header
    p = G.profile(df)
    assert p["suggested_target"] == "Machine failure"
    r = G.train(df, "Machine failure")
    for c in ("UDI", "Product ID", "TWF", "HDF", "PWF", "OSF", "RNF"):
        assert c in r["excluded"], c
    assert r["chosen"] == "gradient boosting" and r["test"]["pr_auc"] > 0.7 and r["test"]["roc_auc"] > 0.9
    base = next(m for m in r["models"] if m["model"].startswith("baseline"))["test"]["pr_auc"]
    assert r["test"]["pr_auc"] > 10 * base
    assert any("power" in e for e in r["engineered"])
    pred = G.predict(r["model_id"], G.read_csv(r["demo_rows_csv"]))
    assert len(pred) == 25 and pred.probability.between(0, 1).all()
    acc = (pred.predicted.astype(str) == pd.Series(r["demo_actual"])).mean()
    assert acc >= 0.8  # held-out test rows, never seen by the deployed model


def test_generic_multiclass_regression_dates_and_errors():
    import generic as G
    from sklearn.datasets import load_diabetes, load_iris
    ir = load_iris(as_frame=True)
    f = ir.frame.copy()
    f["species"] = ir.target_names[f.pop("target")]
    r = G.train(f, "species")
    assert r["task"] == "multiclass" and r["test"]["accuracy"] > 0.8
    d = load_diabetes(as_frame=True).frame
    r = G.train(d, "target")
    assert r["task"] == "regression" and r["test"]["r2"] > 0.2
    rng = np.random.default_rng(0)
    n = 600
    f = pd.DataFrame({"date": pd.date_range("2022-01-01", periods=n).strftime("%Y-%m-%d"),
                      "x": rng.normal(size=n)})
    f["y"] = (f.x + rng.normal(scale=0.5, size=n) > 0).astype(int)
    r = G.train(f, "y")
    assert r["split"].startswith("by time")
    with pytest.raises(ValueError, match="missing columns"):
        G.predict(r["model_id"], f[["date"]])
    with pytest.raises(ValueError):
        G.train(f, "nope")


def test_generic_api_endpoints():
    import json, urllib.request
    srv = _serve()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        def post(action, body):
            req = urllib.request.Request(f"{base}/api/generic/{action}", json.dumps(body).encode(), {"Content-Type": "application/json"})
            try:
                r = urllib.request.urlopen(req, timeout=120)
                return r.status, json.load(r)
            except urllib.error.HTTPError as e:
                return e.code, json.load(e)
        csv = open(os.path.join(ROOT, "ecorisk-ai", "samples", "ai4i2020.csv"), encoding="utf-8").read()
        code, prof = post("profile", {"csv": csv})
        assert code == 200 and prof["plan"]["target"] == "Machine failure" and "TWF" in prof["plan"]["excluded"]
        code, res = post("train", {"csv": csv, "target": "Machine failure"})
        assert code == 200 and res["test"]["roc_auc"] > 0.9
        code, pr = post("predict", {"model_id": res["model_id"], "csv": res["demo_rows_csv"]})
        assert code == 200 and pr["total"] == 25 and "probability" in pr["csv"].splitlines()[0]
        assert post("predict", {"model_id": "nope", "csv": res["demo_rows_csv"]})[0] == 400
        assert post("profile", {"csv": "only_one_column\n1\n2"})[0] == 400
    finally:
        srv.shutdown()
