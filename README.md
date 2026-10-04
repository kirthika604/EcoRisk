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

## Any dataset: bring your own
The same pipeline runs on **any CSV** (section "Any dataset" on the page, `ml/generic.py`). You pick the
column to predict, and it does the rest:
- **Profiling and cleaning:** column types, missing values, IDs dropped (row counters, product codes),
  constant columns dropped.
- **Leakage guard:** columns that reveal the answer on their own are excluded, with the reason shown.
- **Feature engineering:** category encoding, plus physical features when recognisable (power =
  torque x speed, temperature difference, strain).
- **Splitting:** by date when a date column exists, otherwise stratified 60/20/20.
- **Model selection:** baseline vs logistic/ridge vs gradient boosting, chosen on validation.
- **Reporting:** test metrics, confusion matrix, top drivers.
- **Prediction:** new rows get a per-row "main reason", and you can download a CSV.

**AI4I 2020 predictive maintenance** (UCI, 10,000 machines, 3.4% failures; included as a one-click sample).
The failure-mode columns TWF/HDF/PWF/OSF/RNF are detected as leakage and excluded, as are UDI and
Product ID. On 2,000 held-out machines, gradient boosting reaches **PR-AUC 0.891** (baseline 0.034),
ROC-AUC 0.977, precision 91% and recall 85%: 58 of 68 failures caught with 6 false alarms. Top drivers
are rotational speed, temperature difference, strain and power. Also tested on Iris (multiclass),
Diabetes (regression), Breast cancer (binary with an ID column) and a dated sales file (time split,
leaky column caught).

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
python3 -m pytest ml/test_ef.py  # 24 tests (needs ml/ef_features.csv: python3 ml/ef_data.py)
```

## Deploy
- **Render (free, no Docker):** New + > Blueprint > this repo > Apply. [`render.yaml`](render.yaml) installs
  `requirements.txt` and runs `python ml/ef_server.py`; it redeploys on every push to `main`.
- **Hugging Face Spaces (Docker SDK):** add the two files in [`deploy/huggingface/`](deploy/huggingface/);
  the Space pulls this repo at build time.
- **Any Docker host:** the root [`Dockerfile`](Dockerfile) serves on `$PORT`.

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
and `awareness/`. AI4I 2020 dataset: S. Matzka, UCI Machine Learning Repository, CC BY 4.0.
