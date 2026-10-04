# EcoRisk AI: predict what happens next

**ALGOTHON26 · ALG-DATA-02 "Predict What Happens Next"**

Human activity weakens the land; weather pulls the trigger. EcoRisk AI learns both from 30 years of
real satellite and weather data, then predicts what happens next at a site and what to do about it:

1. **Predict:** the chance of an extreme-rainfall day within the next **24 / 48 / 72 h**, with
   relative risk ("12x the normal chance for this place and month").
2. **Impact:** what it means for an operation (logistics, warehouse, retail, construction), from
   the user's own operations profile.
3. **Act:** a cost-loss decision (*act when probability > cost / loss*) with 2-3 concrete actions.

It also includes a structural land-fragility model (the original EcoRisk model), a what-if
calculator, prediction on uploaded unseen data (any common weather CSV format), community safety
guidance, and full validation on held-out years.

## Results (held-out test years 2022-2025)
| Window | ROC-AUC | PR-AUC (climatology) |
|---|---|---|
| 24 h | 0.934 | 0.239 (0.042) |
| 48 h | 0.889 | 0.215 (0.067) |
| 72 h | 0.867 | 0.219 (0.090) |

Alerts were raised before 6 of 7 recorded disasters in the test years. On 9 unseen places with a
different data source (ERA5 via Open-Meteo), after recalibration to that source: PR-AUC 0.237,
which beats climatology. Limitations are reported on the page and in the methodology file.

## Run locally
```bash
pip install -r requirements.txt
python3 ml/ef_server.py          # http://localhost:8765
python3 -m pytest ml/test_ef.py  # 21 tests (needs ml/ef_features.csv: python3 ml/ef_data.py)
```

## Deploy
- **Hugging Face Spaces:** create a *Docker* Space and add the two files in
  [`deploy/huggingface/`](deploy/huggingface/). The Space pulls this repo at build time.
- **Any Docker host** (Render, Railway, Fly, ...): the root [`Dockerfile`](Dockerfile) serves on `$PORT`.
  [`render.yaml`](render.yaml) is a ready Render blueprint.

## Rebuild the models from scratch
```bash
python3 ml/ef_data.py         # pull NASA POWER weather, build features (writes ml/ef_features.csv, 77 MB, not in git)
python3 ml/ef_model.py        # 72 h model + validation
python3 ml/ef_horizons.py     # 24/48 h models, value curves, base rates
python3 ml/build_runtime.py   # small runtime summaries used by the server
python3 ml/external_validation.py
```

## Methodology, data and disclosure
See [`ml/EcoForecast_README.md`](ml/EcoForecast_README.md): data sources (NASA POWER, Sentinel-2 and SRTM
via Google Earth Engine, NOAA IBTrACS, Open-Meteo/ERA5, cited disaster records), validation, the
outlier audit, and AI-assistance disclosure. The original EcoRisk pages are in `dashboard/`, `demo/`
and `awareness/`.
