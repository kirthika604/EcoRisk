# EcoRisk AI — ALG-DATA-02 "Predict What Happens Next"

**Idea:** human activity weakens the land; weather pulls the trigger. EcoRisk AI predicts what
happens next at a site by combining two learned models: a **structural model** (how fragile the
land is, from land-change and terrain data; the original EcoRisk model) and a **72-hour model**
(will an extreme-rainfall trigger arrive in the next 1–3 days; code in `ml/ef_*.py`, historically
named EcoForecast). Demo page: `ecorisk-ai/index.html`, served by `ml/ef_server.py`.

## One product, two models
The demo page (`python3 ml/ef_server.py`, then http://localhost:8765) has a site map coloured by structural risk, a replay of any date, prediction on uploaded unseen data, the pipeline and the validation. It combines:
- **EcoRisk (structural risk):** the original model, unchanged. It scores how fragile each of 19
  real sites is from land change, slope, elevation and rainfall history (leave-one-out 14/19,
  bootstrap intervals). Shown per site, with a full ranking table and feature-importance bars.
- **72-hour model (what happens next):** the time-series model below.
- **Combined outlook:** a plain rule, not a third model: high/moderate structural risk
  (>=70% / 40-70%) crossed with whether today's forecast is above the validation-set alert threshold.
- **What-if calculator:** sliders for the weather trigger (rain over 1/3/7/30 days, wet days,
  humidity, pressure change, temperature, month) and the land (vegetation and construction trends,
  slope, elevation, seasonal rainfall). It starts from a real site's typical day for that month
  (median of its real feature rows). The 72 h value comes from the same trained model via
  `POST /api/whatif`. Structural risk is computed in the browser from the exact published logistic
  coefficients, which reproduce every site's score. Slider ranges stay inside the observed training range.
- **Stay safe:** action levels (Normal / Watch / Act) that follow the latest outlook, landslide and
  flash-flood warning signs, India helplines (112, 1078, 1070, 1077), a live "what human activity
  does to this site" comparison, and a 4-question quiz whose answers come from the models.
- The original EcoRisk pages are served by the same server: `/dashboard/` (evidence),
  `/demo/` (Joshimath deep-dive), `/awareness/` (2030 projections).

## Business layer: Predict -> Impact -> Act
The top of the demo page is one decision panel with three cards:
1. **Predict** (model output): location, "as of" date and a **24 h / 48 h / 72 h** window give
   P(extreme rainfall within the window). It also shows the **relative risk**: "12x the normal
   chance for Wayanad in July", against the observed site x month base rate, 1995-2018. Plus the
   model alert line and structural (land) fragility.
2. **Impact** (your inputs x model): a published ladder, not a model. Severe = model alert + worth
   acting + fragile land or exposed routes. High = alert, or worth acting with exposure.
   Moderate = worth acting, or a raised chance (>= 3x normal and >= half the alert line).
   Low otherwise. Exposure x probability gives the expected units disrupted and the expected loss.
   Fragile land and exposed terrain only amplify a weather trigger; on their own they are not a
   disruption.
3. **Act** (decision rule): **act when probability > cost / loss** (the standard cost-loss rule),
   using the cost of the protective action and the loss if hit unprotected from the profile.
   Act now / Prepare / Monitor, with 2-3 actions from a playbook per business type (logistics,
   warehouse, retail, construction), plus a "Copy action plan" button.
- **Operations profile:** units exposed, value at risk, cost of protection, an optional
  alternate route, and terrain exposure. It is saved in the browser. Example profiles are marked
  as such. EcoRisk AI holds no business data of its own.

**Prediction windows** (`python3 ml/ef_horizons.py`, same recipe and split as 72 h; test 2022-25):

| Window | ROC-AUC | PR-AUC (climatology) | Brier (climatology) | Alert precision / recall |
|---|---|---|---|---|
| 24 h | 0.934 | 0.239 (0.042) | 0.0122 (0.0138) | 27% / 39% |
| 48 h | 0.889 | 0.215 (0.067) | 0.0209 (0.0229) | 25% / 35% |
| 72 h | 0.867 | 0.219 (0.090) | 0.0290 (0.0313) | 20% / 48% |

**Cross-window consistency:** an event within 72 h includes one within 48 h, so p72 >= p48 >= p24
is enforced (running maximum). Separate models broke this on 2-4% of days, by up to 28 points.
The fix slightly improved test skill.

**Business value** (test years): the relative economic value of acting when p > C/L, versus the
best fixed policy (always or never protect). 0 = no better, 1 = perfect foresight. It peaks at
0.72 (24 h), 0.60 (48 h) and 0.55 (72 h). The page shows the curve and the user's own ratio. For
the example logistics profile (5,000 / 60,000 = 8.3%) the 24 h forecast captured 32% of
perfect-foresight savings. At ratios where the forecast adds little, the page says so.

## Pipeline (run in order)
```
python3 ml/ef_data.py      # pull + cache NASA POWER weather, build features/labels -> ml/ef_features.csv
python3 ml/ef_model.py     # 72 h model: train, validate, test -> ml/ef_results.json, ml/ef_model.pkl
python3 ml/ef_horizons.py  # 24/48 h models, value curves, base rates -> ml/ef_horizons.json
python3 ml/ef_server.py    # demo page at http://localhost:8765 (upload / paste an unseen record)
python3 ml/ef_predict.py weather.csv --site wayanad     # same prediction from the command line
python3 -m pytest ml/test_ef.py                          # 20 reliability tests
```

## Data
Real daily weather, 1995-2025, 22 sites (hill, coastal, plains, desert across India), from the
NASA POWER API: rain (PRECTOTCORR), T2M, RH2M, PS, WS2M, T2MDEW. NASA's missing-value sentinel is
set to NaN, never imputed. Static terrain features (slope, elevation, NDVI/NDBI trend, coastal)
come from Sentinel-2 / SRTM pulls via Earth Engine in `ml/feature_table.csv`.

## Features (all use data up to the prediction day only)
Rain over 1/3/7/14/30 days, wet days in last 7, rain acceleration, temperature, humidity,
dew-point spread, surface pressure and its 1/3-day change, humidity change, season (sin/cos),
terrain features. Rain sums are log-transformed.

## Target and leakage control
Label = an extreme day (>= that site's 99th percentile of daily rain, computed on 1995-2018 only)
occurs in the next 3 days. The threshold never sees validation/test years (enforced by a test).

## Validation (strictly temporal)
Train 1995-2018 | validation 2019-2021 (model choice and alert threshold) | **test 2022-2025,
untouched until the final report.** The deployed model is refit on train+validation only.

## Results on the held-out test years (32,076 site-days, 3.4% positive)
| Model | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|
| Persistence | 0.574 | 0.086 | 0.0373 |
| Climatology (site x month) | 0.792 | 0.090 | 0.0313 |
| Logistic regression | 0.842 | 0.193 | 0.0295 |
| **Gradient boosting, monotonic (chosen on validation)** | **0.866** | **0.217** | **0.0290** |

Alert threshold from validation: precision 20%, recall 47%. Calibration table and permutation
importances are in `ml/ef_results.json`. Backtest on recorded disasters in the test years:
alert raised before 6 of 7 (Chennai, Dharali, Guna, Jakhau, Silchar, Wayanad); the miss is
Joshimath, a subsidence event not driven by rain.

## External validation: unseen places, a different data source
`python3 ml/external_validation.py`. Nine Indian places the model never saw (Shimla, Darjeeling,
Gangtok, Srinagar, Itanagar, Dehradun, Mumbai, Mangaluru, Guwahati), weather from **ERA5 via
Open-Meteo** instead of NASA POWER, terrain from the Copernicus 90 m DEM, scored 2022-2024
(9,855 days). Labels use the same rule as training, computed from the new source.

| Model | ROC-AUC | PR-AUC | Brier | Mean P vs. observed 2.5% |
|---|---|---|---|---|
| Climatology | 0.823 | 0.074 | 0.0236 | – |
| EcoRisk AI, raw | 0.857 | 0.145 | 0.0326 | 7.3% |
| **EcoRisk AI, recalibrated to the source** | **0.882** | **0.228** | **0.0215** | **2.7%** |

The raw model ranks days well on a new source (it beats climatology at 7 of 9 places) but
over-states probabilities about 3x, because ERA5 and NASA POWER report rainfall differently. Fix:
when an upload has 5+ years of history, `adapt_to_source()` fits a Platt map on logit(p) using
labels from the file's OWN rainfall, on history before the displayed window only. In the
validation it is fitted on 1995-2021 only. Recalibrated alerts: 8.1% of days, precision 17%,
recall 56%. Per-place ROC-AUC is unchanged (the map is monotone); the gain is honest probabilities
and alert thresholds that compare fairly across places. Shorter outside files are flagged.

Case study, in the demo ("Try a real external file"): an Open-Meteo download for Shimla ending
13 Aug 2023, the day before the Shimla landslides. Recalibrated on its own 28 years of history,
EcoRisk AI alerts the day before (17% on 13 Aug). ERA5 recorded 51 mm on 14 Aug, above
Shimla's 43.4 mm extreme threshold. Without that history (a 60-day excerpt) it gives 10%, just
under the default alert line: a near-miss.

**Outside file formats handled** (`read_weather_csv` + `normalise`): metadata blocks above the
header (Open-Meteo, NASA POWER `-END HEADER-`, YEAR/DOY columns), `,` `;` or tab separators,
columns found by meaning (e.g. `precipitation_sum (mm)`; `precipitation_hours` is not rain),
unit conversion from the name or `(unit)`: km/h, mph and knots to m/s, 10 m wind to 2 m (FAO-56),
°F and K to °C, inches and cm to mm, hPa, Pa and inHg to kPa, 0-1 humidity to %,
sea-level pressure to surface pressure using elevation, -999 sentinels treated as missing.

## Prediction relevance and outlier audit
- **Physically consistent:** monotonic constraints mean more rain, wetter air or a falling barometer can
  never lower the forecast. Before: 1.6% of real days dipped by >5 points when rain was added (worst
  -16 points). After: 0% on 3,000 real days (and a test enforces it), at equal accuracy.
- **No altitude/site proxies:** absolute surface pressure (mostly altitude) was replaced by pressure
  anomaly vs. the location's own 30 days; land-change trends were removed from the 72 h model (they
  only identified sites; ablation showed no loss). Land change drives the structural model only.
- **Distribution:** test-year probabilities median 1.1%, 99th pct ~27%, max ~69% (Jakhau monsoon
  downpours); zero high forecasts on dry days.
- **Impossible inputs rejected** (e.g. humidity 140%, negative rain, pressure 5 kPa) with the row named.
- **Unfamiliar inputs flagged:** any input outside the 0.1-99.9th percentile of training is listed
  and the forecast is marked as an extrapolation (page shows a dashed amber note and ring). Notably the
  days before Jakhau (Biparjoy), Guna and Silchar were beyond training experience, and the model
  still alerted for all three.

## Honest limitations
- ~80% of alerts are false alarms; this is a screening tool, not a precise warning.
- Probabilities are mildly under-confident in mid ranges and over-confident above 40%.
- On a new data source without 5+ years of its history, probabilities run about 3x high (ranking is still useful).
- NASA POWER is a ~50 km grid, so nearby sites (e.g. Joshimath/Kedarnath) share weather inputs.
- Forecast skill comes from today's observed conditions; there is no numerical weather forecast
  input, so skill beyond ~3 days is not claimed.
- Land-change features (the EcoRisk finding) are a minor predictor here.

## Disclosure
- **Datasets/APIs:** NASA POWER API (weather); Sentinel-2 and SRTM via Google Earth Engine
  (static terrain features); NOAA IBTrACS (cyclone data, earlier project); recorded disaster dates
  from news/academic sources cited per site in `ml/feature_table.csv`.
- **AI assistance:** the code in `ml/ef_*.py`, `ecorisk-ai/index.html` and this README was written
  with Claude Code (Anthropic) and reviewed/run by the team. No LLM is used at prediction time.
- **Lineage:** reuses EcoRisk's site list, terrain features and NASA POWER wrapper
  (`ml/nasa_power.py`, `ml/feature_table.csv`). The prediction target, features, split, models and
  UI here are new for this problem statement.
