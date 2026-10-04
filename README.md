# EcoRisk AI: predict what happens next

**ALGOTHON26 · ALG-DATA-02 "Predict What Happens Next" · base dataset: AI4I 2020 Predictive Maintenance (UCI)**

EcoRisk AI predicts what happens next and what to do about it. On the official dataset (AI4I 2020,
10,000 milling machines) it predicts **whether a machine will fail, which failure it will be, how many
production runs it has left, and what maintenance should do**. The same engine also forecasts
extreme-rainfall risk from 30 years of real weather and land data (module 2), and runs on any CSV.

Live: https://ecorisk-ai.onrender.com

## Machine module (AI4I 2020): the ALG-DATA-02 pipeline (`ml/ai4i_model.py`)
1. **Exploration & cleaning:** 10,000 rows, 0 missing values, 0 duplicates, 3.4% failures; physical
   range checks; IDs (UDI, Product ID) dropped. **TWF/HDF/PWF/OSF/RNF are excluded as inputs**,
   because they are failure modes recorded as part of the outcome; they serve only as targets for the
   failure-type models.
2. **Feature engineering from the documented failure mechanisms:**
   - power = torque x speed (power failure outside 3.5-9 kW)
   - temperature difference (heat dissipation below 8.6 K at < 1,380 rpm)
   - strain = wear x torque and its ratio to the per-type limit (overstrain above 11/12/13k minNm for L/M/H)
   - tool past 200 min (tool wear failure at 200-240 min)
3. **Model selection:** stratified 80/20 split; the 2,000-machine test set is untouched until the end.
   5-fold CV on the training set compares baseline, logistic regression, random forest and gradient
   boosting, each with and without the engineered features.

   | 5-fold CV PR-AUC | raw sensors | + engineered |
   |---|---|---|
   | logistic regression | 0.443 | 0.513 |
   | gradient boosting | 0.798 | 0.881 |
   | **random forest (chosen)** | 0.760 | **0.897** |
4. **Held-out test (2,000 machines, used once):** **PR-AUC 0.879** (baseline 0.034),
   ROC-AUC 0.971, precision 97%, recall 82%: **56 of 68
   failures caught, 2 false alarms**. The alert threshold comes from out-of-fold training predictions.
   9 of the 12 misses are tool-wear failures, which the documentation says happen at a random point
   between 200 and 240 min.
5. **Failure type:** one model per mode (test PR-AUC): heat dissipation 1.00, power
   0.98, overstrain 0.97, tool wear 0.06 (random by design).
6. **What happens next:** each production run adds 2/3/5 min of tool wear (L/M/H). Projecting wear
   forward gives *runs until the failure risk crosses the alert line* and *runs until the tool enters
   its 200-240 min window*. Risk never falls as the tool wears.
7. **Act:** maintenance action per mechanism (cooling, power band, torque or tool change), plus a
   cost rule: act when chance of failure > maintenance cost / failure cost.
8. **Predict unseen machines:** upload any AI4I-format CSV (renamed columns are matched); if it
   includes "Machine failure", predictions are scored against it. Samples: the 2,000 held-out test
   machines with and without answers (`ecorisk-ai/samples/ai4i_unseen_machines*.csv`).

Note: AI4I 2020 is a synthetic dataset that reflects real predictive-maintenance data (per UCI).

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
Product ID. On 2,000 held-out machines, gradient boosting reaches **PR-AUC 0.894** (baseline 0.034),
ROC-AUC 0.978, precision 89% and recall 85%: 58 of 68 failures caught with 7 false alarms. Top drivers
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
python3 -m pytest ml/test_ef.py  # 28 tests (needs ml/ef_features.csv: python3 ml/ef_data.py)
```

## Deploy
- **Render (free, no Docker):** New + > Blueprint > this repo > Apply. [`render.yaml`](render.yaml) installs
  `requirements.txt` and runs `python ml/ef_server.py`; it redeploys on every push to `main`.
- **Hugging Face Spaces (Docker SDK):** add the two files in [`deploy/huggingface/`](deploy/huggingface/);
  the Space pulls this repo at build time.
- **Any Docker host:** the root [`Dockerfile`](Dockerfile) serves on `$PORT`.

## Rebuild the models from scratch
```bash
python3 ml/ai4i_model.py      # machine module (AI4I 2020): EDA, CV model selection, test, samples
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
