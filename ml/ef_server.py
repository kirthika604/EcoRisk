#!/usr/bin/env python3
"""Local server for the EcoForecast demo page (stdlib only; run: python3 ml/ef_server.py).
GET /            demo page            GET /api/sites     site list + metadata
GET /api/results validation metrics   GET /api/sample?site=ID&end=YYYY-MM-DD  sample weather CSV
POST /api/predict  JSON {csv, site | slope+elevation+coastal}  -> predictions
"""
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))
import ef_predict
from ef_data import STATIC

MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
        ".json": "application/json", ".jpg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml", ".csv": "text/csv; charset=utf-8"}
STATIC_DIRS = ("dashboard", "demo", "awareness", "ecorisk-ai")  # the original EcoRisk pages, served unchanged
RISK = json.load(open(os.path.join(ROOT, "ml", "model_results.json")))
PAGE = os.path.join(ROOT, "ecorisk-ai", "index.html")
FT = pd.read_csv(os.path.join(ROOT, "ml", "feature_table.csv"))
FT = FT[FT["status"].str.startswith("REAL")].dropna(subset=["latitude"]).set_index("site_id")
MAX_BYTES = 5_000_000
# Typical day per site x month (real feature medians) = the starting point for the calculator.
_ART = ef_predict.runtime_artifacts()  # precomputed by ml/build_runtime.py (no 77 MB CSV at runtime)
BASE = _ART["base_rows"]
EXTREME_MM = _ART["extreme_mm"]
RANGES = _ART["slider_ranges"]


def static_for(body):
    if body.get("site"):
        if body["site"] not in FT.index:
            raise ValueError("unknown site")
        r = FT.loc[body["site"]]
        s = {c: float(r[c]) for c in STATIC}
        s["terrain_type"] = r["terrain_type"]
        return s
    try:
        slope, elev = float(body["slope"]), float(body["elevation"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("choose a site, or give numeric slope and elevation")
    return {"ndvi_trend_slope": 0.0, "ndbi_trend_slope": 0.0, "mean_slope_degrees": slope,
            "elevation_mean_m": elev, "terrain_type": "coastal" if body.get("coastal") else "hill"}


def clean(o):
    """JSON has no NaN: turn NaN/inf into null so browsers can parse the response."""
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


class H(BaseHTTPRequestHandler):
    def send(self, code, payload, ctype="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(clean(payload), allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")  # demo server: always serve the current build
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            return self.send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
        if u.path == "/api/risk":
            keep = ("site_id", "site_name", "terrain_type", "disaster_occurred", "disaster_type",
                    "disaster_date", "predicted_risk_prob", "risk_ci_low", "risk_ci_high",
                    "ndvi_trend_slope", "ndbi_trend_slope", "mean_slope_degrees",
                    "elevation_mean_m", "rainfall_anomaly_pct", "lst_trend_slope")
            return self.send(200, {
                "ranking": [{k: r.get(k) for k in keep} for r in RISK["risk_ranking"]],
                "loocv": {k: RISK["loocv"][k] for k in ("correct", "total", "accuracy")},
                "feature_importance": RISK["feature_importance"],
                "cross_terrain": {k: RISK["cross_terrain"][k] for k in ("n_hill_train", "n_coastal_test", "n_correct")},
                "n_sites_real": RISK["n_sites_real"],
                "model_params": RISK["model_params"]})
        if u.path == "/api/base":
            site, month = q.get("site", [""])[0], q.get("month", ["7"])[0]
            try:
                row = BASE[f"{site}|{int(month)}"]
            except (KeyError, ValueError):
                return self.send(404, {"error": "unknown site or month"})
            return self.send(200, {"row": row, "ranges": RANGES})
        top = u.path.strip("/").split("/")[0]
        if top in STATIC_DIRS:
            rel = u.path.strip("/")
            if u.path == "/" + top:
                self.send_response(302); self.send_header("Location", "/" + top + "/"); self.send_header("Cache-Control", "no-store"); self.end_headers(); return
            full = os.path.realpath(os.path.join(ROOT, rel if not u.path.endswith("/") else rel + "/index.html"))
            base = os.path.realpath(os.path.join(ROOT, top))
            if not full.startswith(base + os.sep) or not os.path.isfile(full):
                return self.send(404, {"error": "not found"})
            return self.send(200, open(full, "rb").read(), MIME.get(os.path.splitext(full)[1], "application/octet-stream"))
        if u.path == "/api/sites":
            return self.send(200, [{"site_id": i, "name": r.site_name, "terrain": r.terrain_type,
                                    "lat": r.latitude, "lon": r.longitude, "extreme_mm": EXTREME_MM.get(i),
                                    "disaster_type": r.disaster_type if r.disaster_occurred == 1 else None,
                                    "disaster_date": r.disaster_date if r.disaster_occurred == 1 else None}
                                   for i, r in FT.iterrows()])
        if u.path in ("/healthz", "/api/health"):
            return self.send(200, {"ok": True})
        if u.path == "/api/horizons":
            return self.send(200, open(os.path.join(ROOT, "ml", "ef_horizons.json"), "rb").read())
        if u.path == "/api/external":
            path = os.path.join(ROOT, "ml", "external_results.json")
            return self.send(200, open(path, "rb").read()) if os.path.exists(path) else self.send(404, {"error": "not run"})
        if u.path == "/api/results":
            return self.send(200, open(os.path.join(ROOT, "ml", "ef_results.json"), "rb").read())
        if u.path == "/api/sample":
            site, end = q.get("site", [""])[0], q.get("end", [""])[0]
            path = os.path.join(ROOT, "datasourceSIH", "sites", site, "weather_daily.csv")
            if site not in FT.index or not os.path.exists(path):
                return self.send(404, {"error": "unknown site"})
            w = pd.read_csv(path, parse_dates=["date"])
            end = pd.Timestamp(end) if end else w.date.max()
            n = min(max(int(q.get("days", ["60"])[0]), 31), 400)
            w = w[(w.date <= end)].tail(n)
            return self.send(200, w.to_csv(index=False).encode(), "text/csv")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/whatif":
            try:
                n = int(self.headers.get("Content-Length", 0))
                if n > 100_000:
                    return self.send(413, {"error": "too large"})
                b = json.loads(self.rfile.read(n))
                return self.send(200, ef_predict.predict_row(b["row"], int(b.get("horizon", 72))))
            except (ValueError, KeyError, TypeError) as e:
                return self.send(400, {"error": f"bad what-if row: {e}"})
        if path != "/api/predict":
            return self.send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > MAX_BYTES:
                return self.send(413, {"error": "file too large"})
            body = json.loads(self.rfile.read(n))
            raw = ef_predict.read_weather_csv(body["csv"])
            _, notes = ef_predict.normalise(raw)
            out = ef_predict.predict(raw, static_for(body), horizon=int(body.get("horizon", 72)))
            notes += out.attrs.get("notes", [])
            attrs = dict(out.attrs)
            out = out.tail(120)  # the page shows the recent window; long uploads stay fast
            out.attrs.update(attrs)
            out["date"] = out["date"].astype(str)
            self.send(200, {"notes": notes, "horizon": int(body.get("horizon", 72)),
                            "threshold": out.attrs.get("threshold", float(ef_predict.load_model(int(body.get("horizon", 72)))["threshold"])),
                            "recalibrated": bool(out.attrs.get("recalibrated")),
                            "rows": out.to_dict("records")})
        except (ValueError, KeyError, pd.errors.ParserError) as e:
            self.send(400, {"error": str(e)})
        except Exception as e:  # never drop the connection: report it to the page instead
            self.send(500, {"error": f"unexpected error: {type(e).__name__}: {e}"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    try:
        # local runs stay private; containers set HOST=0.0.0.0 so the platform can reach the app
        srv = ThreadingHTTPServer((os.environ.get("HOST", "127.0.0.1"), port), H)
    except OSError:
        sys.exit(f"Port {port} is already in use. EcoForecast may already be running at "
                 f"http://localhost:{port}, or pick another port: PORT=8800 python3 ml/ef_server.py")
    # warm up: load all three window models and run one tiny prediction before accepting traffic,
    # so the first visitor does not wait ~10 s for lazy model loading
    for h in ef_predict.HORIZONS:
        ef_predict.load_model(h)
    try:
        ef_predict.predict_row(BASE["wayanad|7"], 72)
    except Exception as e:  # never block startup on the warm-up
        print("warm-up skipped:", e)
    print(f"EcoRisk AI on http://localhost:{port}", flush=True)
    srv.serve_forever()
