# Project Memory / Fact Ledger — SIH26206

**Purpose:** ground-truth record of what's REAL (verified, with a citation) vs. INTERPRETED/ILLUSTRATIVE
in this project. Every number that appears in code, the dashboard, or pitch slides must trace back to an
entry here. If a number isn't in this file, it does not go in the demo — either source it and add it here
first, or mark it explicitly as illustrative in the UI (per project-plan.md's own rule: "say so openly").

Update this file every time new data is pulled, a new source is found, or a build decision is made.
Treat it as more current than any earlier chat summary — if the two conflict, this file wins.

---

## 1. Case study — locked

- Location: **Joshimath, Chamoli district, Uttarakhand, India**
- Coordinates used for satellite/DEM/rainfall pulls: **30.5551°N, 79.5641°E** (from POWER file header,
  `datasourceSIH/POWER_Point_Daily_20190101_20230521_030d56N_079d56E_LST.csv`)
- Ground-truth event: two documented subsidence windows, sourced via Sentinel-1 SAR DInSAR analysis
  attributed to ISRO/NRSC:
  - **8.9 cm subsidence over Apr–Nov 2022** (7 months, "slow" window)
  - **5.4 cm subsidence over 27 Dec 2022 – 8 Jan 2023** (12 days, "rapid" window)
  - Source: secondary reporting (Deccan Herald, Outlook India, BusinessToday — Jan 2023) citing an
    NRSC/ISRO PDF report that is **no longer hosted on nrsc.gov.in**. This is a secondary-source
    citation, not the primary document — disclose this if asked "where's your source" in the pitch.
  - File: `datasourceSIH/joshimath_disaster_event_log.csv`

## 2. Confirmed real datasets already collected (datasourceSIH/)

| File | Content | Real / notes |
|---|---|---|
| `joshimath_ndvi_timeseries.csv` | NDVI, 131 dates, 2019-01-12 → 2023-05-21 | Real — Sentinel-2 via Google Earth Engine |
| `joshimath_ndbi_timeseries.csv` | NDBI (built-up index), same dates | Real — same source, GEE |
| `joshimath_merged_timeline.csv` | NDVI + NDBI + daily rainfall + event markers, joined | Real — derived from the above + POWER rainfall |
| `POWER_Point_Daily_...csv` | Daily PRECTOTCORR (corrected precipitation, mm/day), 2019-01-01 → 2023-05-21 | Real — direct NASA POWER (MERRA-2) source |
| `joshimath_dem_slope.csv` | Elevation (max 2755m, mean 1946m, min 1359m) & slope (max 71.44°, mean 29.74°, min 0.0°) | Real values, but **exact DEM source/dataset not documented** — confirm (e.g. SRTM 30m vs other) before citing precisely in the pitch |
| `joshimath_disaster_event_log.csv` | Event dates + subsidence magnitude | Real, secondary-sourced — see §1 |

## 3. Real published risk threshold — VERIFIED 2026-08-31 via WebSearch

**This is the key citation for the threshold/risk-band logic. Region-specific, not generic.**

- **Finding:** for the Chamoli-Joshimath region specifically, landslide initiation is associated with:
  - **10-day antecedent rainfall ≥ 55 mm**
  - **20-day antecedent rainfall ≥ 185 mm**
- **Source:** D. P. Kanungo & Shaifaly Sharma (2014), *"Rainfall thresholds for prediction of shallow
  landslides around Chamoli-Joshimath region, Garhwal Himalayas, India,"* Landslides 11, 629–638.
  DOI: [10.1007/s10346-013-0438-9](https://doi.org/10.1007/s10346-013-0438-9). Authors are CSIR–Central
  Building Research Institute (CBRI), Roorkee. Study based on 128 landslides (2009–2012) in the region,
  81 analyzed to derive the threshold.
- **CAVEAT — important:** the primary paper is paywalled (Springer redirected to a login page when
  fetched). The 55mm/185mm figures come from a **secondary source summarizing the paper's findings**,
  not from reading the primary PDF directly. If challenged in Q&A on exact sourcing, disclose this.
- **Backup/context only, do NOT cite as Joshimath-specific:** a Pithoragarh District (Uttarakhand) study
  found ~45–50mm cumulative rainfall at ~28mm/h intensity as an instability-onset threshold. Different
  district, exact citation not fully verified — usable only as general regional corroboration, never as
  the primary cited number.
- **Contributing-cause statement (not a numeric threshold):** a government expert committee (NDMA + GSI
  + CBRI, 35 members) attributed Joshimath subsidence primarily to "inadequate drainage systems and
  anthropogenic activities" — this supports the project's human-activity framing narratively, but is not
  itself a number to plug into the risk model. Exact report title/date not pinned down — cite as "govt
  expert committee findings, widely reported Jan 2023," not as a specific document.

## 4. NOT sourced — explicitly mocked/interpreted in the demo build

- **No published numeric threshold exists (or has been found) for "NDVI decline %" or "built-up growth %"
  correlated to subsidence/landslide risk in this region.** The demo therefore treats the NDVI/NDBI trend
  as a **qualitative amplifying signal** ("the slow human-activity trend that raises baseline
  vulnerability"), never as a pass/fail numeric threshold. Do not invent one — if this needs a number
  later, search first and add it here.
- The composite "risk index" shown in the dashboard slider is a **hand-built illustrative score**
  (rainfall-vs-cited-threshold proximity, weighted with NDVI/NDBI trend direction) — it is NOT a
  validated statistical or physical model. The UI must label it as illustrative. Never present it as
  peer-reviewed.
- DEM source dataset unconfirmed (see §2).

## 5. Live data layer — build decision

- Plan originally listed OpenWeather / NASA POWER / IMD as live-call candidates.
- **Decision:** using **Open-Meteo** (`api.open-meteo.com`) instead — free, no API key/registration,
  CORS-enabled for direct browser fetch, reliable for a live hackathon demo. This is a deviation from
  the plan's original list; noting it here so it doesn't look like an unvetted swap.
- Pulls current precipitation + today's precipitation sum for 30.5551°N, 79.5641°E.
- If the fetch fails at demo time (offline/network), the dashboard must show a clear fallback state,
  not silently show stale/fake data.

## 6. Computed finding — verified by backtesting real data (2026-08-31)

- Using NASA POWER daily rainfall (real) and the §3 cited threshold (real), the 10-day and 20-day
  antecedent rainfall at both documented subsidence windows was checked:
  - Before the "slow" window start (1 Apr 2022): 10-day and 20-day antecedent rainfall ≈ 0mm.
  - Before the eyewitness-reported "rapid" trigger date (2 Jan 2023, per §1/event log description):
    10-day ≈ 0.5mm, 20-day ≈ 0.5mm.
  - **Neither event crossed the cited rainfall threshold (55mm/10-day, 185mm/20-day).**
- **Interpretation (honest, not overclaimed):** this specific Joshimath subsidence was not rainfall-triggered
  by the Kanungo & Sharma threshold mechanism — consistent with the government expert committee's
  (NDMA/GSI/CBRI) public attribution of the subsidence to hydrological imbalance, drainage failure, and
  anthropogenic activity (see §3) rather than a rainfall spike. The cited threshold remains a real,
  region-relevant landslide-trigger mechanism in general — it just wasn't the proximate cause here.
- **Do not present this as "the model failed to predict the event."** Frame it as: rainfall is one of two
  layers (fast trigger); this case shows the slow human-activity/drainage layer was dominant, which is
  the core pitch angle anyway. This finding is now surfaced directly in the demo UI (section 2 narrative).

## 7. Demo build — status (2026-08-31)

- Working demo built at `demo/index.html` + `demo/app.js` + `demo/data.js` (auto-generated by
  `demo/build_data.py` from the real CSVs — re-run that script if source CSVs change, don't hand-edit
  `data.js`). Local dev server config at `.claude/launch.json` (`python3 -m http.server 8731 --directory demo`).
- Verified working in-browser: NDVI/NDBI trend charts with 2030 extrapolation, rainfall threshold
  backtest (with the §6 finding surfaced honestly in the UI), scenario slider (Current/BAU2030/
  Intervention2030) with consistent rounded numbers, live Open-Meteo fetch confirmed returning real
  current data. No console errors.
- Every number on the page is tagged in the UI as "Real data" / "Real, cited" / "Illustrative index" /
  "Live API call" so nothing is presented as more certain than it is.
- **Still open, not yet built:** DEM/slope data (§2) isn't surfaced in the UI yet; no map view (plan
  mentions "map/slider," only the slider exists); pitch deck/slides not started.

## 8. Rules for this file

1. Before writing any number into code, dashboard copy, or slides — check here first.
2. If it's not here, it doesn't go in the demo.
3. Mark every UI element sourced from §4 (mocked/interpreted) as visibly labeled, not hidden.
4. Update this file in the same sitting as any code change that adds/changes a number.

---

## 9. PLAN PIVOT (2026-08-31) — single-site dashboard → multi-site ML classifier

The team sent updated plan docs (`sih_new.zip` → `sihPlan/project-plan.md`, `data-sources.md`
overwritten; `ml-model-plan.md`, `dataset-sites.md` added). **This is a scope pivot, not a small
tweak** — read the new `project-plan.md` in full before assuming anything from before this date
still holds. Key changes:

- Project is now: train a classifier (Logistic Regression primary, Random Forest backup) across
  **multiple sites** (Himalayan hill + coastal India) to predict `disaster_occurred` from
  NDVI/NDBI trend + terrain + rainfall-anomaly features, with **feature importance as the pitch
  centerpiece** — not a single-location dashboard.
- **Frontend is now explicitly deprioritized** ("Low — minimal effort... do NOT spend hours on UI
  polish"). The `demo/` dashboard built earlier is kept as-is ("Medium priority — keep as the one
  fully-instrumented example the model validates against") but should NOT receive further polish
  time — see `project-plan.md` §2.
- Validation approach: LOOCV (leave-one-out, standard for small N) + cross-terrain validation
  (train on hill sites, test on coastal, and vice versa) — this is the generalization proof. See
  `ml-model-plan.md` for full detail.
- Candidate site list (11 new sites + Joshimath) is in `dataset-sites.md`. **That file's own
  caveat: "verify every citation yourself before finalizing" — coordinates/sources for every site
  except Joshimath are unverified leads, not confirmed facts.**

### Environment constraint — important, don't forget this

**This environment has no Earth Engine access** (`earthengine-api` not installed, no `gcloud`/GEE
credentials). I cannot pull real NDVI/NDBI/slope data for any new site myself. Joshimath is the
only site with real, complete data because it was already pulled by the team before this session.
**Any future work in this project must not fabricate NDVI/NDBI/slope/rainfall numbers for the
other 11 candidate sites** — they must come from the team actually running the Earth Engine +
NASA POWER scripts (same ones used for Joshimath) against each site's coordinates.

### What's built so far (ml/ directory)

- `ml/build_joshimath_features.py` — computes Joshimath's real feature-table row from the
  existing `datasourceSIH/` CSVs (no invented numbers). Computed values (2026-08-31):
  - `ndvi_trend_slope` = -0.00028/year (nearly flat, slight decline)
  - `ndbi_trend_slope` = +0.01115/year (built-up rising — matches the human-activity narrative)
  - `mean_slope_degrees` = 29.74° (from DEM pull, real)
  - `elevation_mean_m` = 1946.3m (from DEM pull, real)
  - `rainfall_anomaly_pct` = -17.58% (last 90 days vs. full 2019-2023 daily mean — drier than
    average; consistent with §6's finding that the subsidence events weren't rainfall-triggered)
- `ml/build_feature_table.py` — builds `ml/feature_table.csv`: Joshimath's real row +
  11 template rows (one per other candidate site from `dataset-sites.md`), each marked
  `status = NOT_PULLED - needs Earth Engine ... + NASA POWER ... pull`. **Do not hand-fill these
  rows with guessed numbers** — regenerate this file only by adding real per-site pulls.
- `ml/train_model.py` — the training pipeline (sklearn: LogisticRegression, LeaveOneOut, standard
  scaler, feature importance chart, cross-terrain check, risk ranking). **Only trains on rows
  whose `status` starts with "REAL"** — refuses to train and prints a clear explanation if fewer
  than `MIN_SITES_TO_TRAIN = 8` real rows exist (per `dataset-sites.md`'s own "8-12 minimum" rule),
  rather than reporting a misleading metric on too little data.
  - As of 2026-08-31: only 1/12 sites (Joshimath) has real data → pipeline correctly refuses to
    train and reports this. **This is expected, not a bug** — it's blocked on the team's GEE pulls
    for the other 10 sites (2 control sites still need identifying per `dataset-sites.md` §D).
  - Pipeline logic itself was verified end-to-end (LOOCV, feature importance, cross-terrain,
    risk ranking) using a throwaway synthetic 14-row table in the scratch dir, never written into
    the project — confirms no code bugs are waiting once real data lands.

### Immediate next blocker

Getting the other sites' real NDVI/NDBI/slope/rainfall data pulled (Earth Engine + NASA POWER,
same scripts as Joshimath, new coordinates) is now the critical path — everything in `ml/` is
ready to consume it the moment it exists. Confirm at least 2-3 non-Joshimath sites end-to-end
first (per `dataset-sites.md` §D's own advice) before running the full list.

## 10. Ocean/cyclone data gap — found and partially filled (2026-08-31)

The multi-site plan's `data-sources.md`/`ml-model-plan.md` never actually specify an ocean/cyclone
data source for the coastal sites — they just reuse the hill-site layers (NDVI/NDBI trend, NASA
POWER rainfall, elevation as a terrain-risk proxy). That's a real gap: cyclone damage severity is
driven by wind/pressure intensity at landfall, not rainfall anomaly. Flagged this and fixed part
of it:

- **Source found and pulled (real, unlike the GEE-blocked layers):** NOAA IBTrACS v04r01
  (`ibtracs.NI.list.v04r01.csv`, North Indian Ocean basin) — public CSV, no login/API key needed,
  reachable directly from this environment (unlike Earth Engine). Downloaded to
  `datasourceSIH/cyclone_landfall_ibtracs.csv`.
- **Extracted real landfall intensity for both coastal disaster sites**, using the IMD/NEWDELHI
  agency track (India's own 3-minute-sustained-wind convention — NOT the JTWC/USA 1-minute
  convention, which reads ~15-25% higher for the same storm; both are in the CSV, IMD is the one
  used elsewhere in the project's citations):
  - **Cyclone Amphan** (Sundarbans site): landfall 2020-05-20 09:00 UTC near 21.4°N 88.1°E —
    IMD wind 90kt = **166.7 km/h**, pressure 960mb, grade **ESCS** (Extremely Severe Cyclonic
    Storm). Matches widely-reported landfall time/location closely (sanity-check passed).
  - **Cyclone Fani** (Odisha coast site): landfall 2019-05-03 03:00 UTC near 19.6°N 85.7°E —
    IMD wind 100kt = **185.2 km/h**, pressure 952mb, grade **ESCS**. Also matches known
    reporting (landfall near Puri, ~08:30 IST).
- Added as new columns (`cyclone_name`, `cyclone_landfall_wind_kmh_imd`,
  `cyclone_landfall_pressure_mb_imd`, `cyclone_grade_imd`, `cyclone_source`) in
  `ml/feature_table.csv` via `ml/build_feature_table.py`. Rows with cyclone data but still-missing
  NDVI/NDBI/slope/rainfall are marked `status = PARTIAL`, distinct from fully `NOT_PULLED` rows.

### Open design question for the team — do NOT resolve this unilaterally

This cyclone data was deliberately **kept as separate evidence/backtest columns, not folded into
the core `FEATURE_COLS` the classifier in `ml/train_model.py` actually trains on**
(`ndvi_trend_slope, ndbi_trend_slope, mean_slope_degrees, elevation_mean_m, rainfall_anomaly_pct,
terrain_hill`). Reason: those 6 features are deliberately terrain-agnostic so one model can train
across hill+coastal and the cross-terrain validation (the plan's generalization proof) means
something. A raw `cyclone_wind_kmh` column would be structurally empty/inapplicable for every
hill site — there's no honest way to zero-fill or impute it without either breaking the unified
feature vector or implicitly claiming "no cyclone risk" for a hill site, which isn't a real
statement. The team should decide, not have this decided for them:
  - **Option A:** keep cyclone intensity as narrative/backtest evidence only (same role rainfall-
    threshold-backtesting plays for Joshimath in the old single-site demo), not an ML input.
  - **Option B:** engineer a single terrain-appropriate "trigger severity" feature — e.g., a 0-1
    score where hill sites use (antecedent rainfall ÷ Kanungo & Sharma threshold) and coastal
    sites use (landfall wind ÷ an IMD cyclone-category threshold, e.g. ESCS ≥166km/h, VSCS
    118-166km/h — these categories are themselves real/citable IMD classifications), so the two
    terrain types get one comparable number instead of two incompatible raw units. This is a real
    feature-engineering decision that changes what the model claims, not a data-sourcing task —
    flag it to the team rather than picking silently.
- **Global Mangrove Watch (GMW) v3.0 — checked 2026-08-31, reachable but site-level use needs the
  team's GEE access, not this environment.**
  - Public dataset, DOI-backed (Bunting et al. 2022), hosted on Zenodo record
    [6894273](https://zenodo.org/records/6894273), no login required.
  - **Per-site mangrove extent (what we'd actually want for Sundarbans specifically) requires
    either (a) Earth Engine, or (b) downloading + spatially clipping the annual vector/raster
    tiles (~65-190MB per year) with `geopandas`/`rasterio`.** Neither is practical from this
    environment right now (no GEE credentials here; GIS libraries not installed and the tiles are
    global-extent, not pre-clipped to India). **This is a job for the team's existing GEE
    workflow**, not something to force through here.
  - **Concrete instructions for whoever pulls this:** GMW is published as public Earth Engine
    assets (source: gee-community-catalog.org, checked 2026-08-31, not independently verified
    beyond that page — confirm the exact path still resolves before relying on it):
    - Raster ImageCollection: `projects/sat-io/open-datasets/GMW/extent/GMW_V3`
    - Year-specific vectors, e.g.: `projects/sat-io/open-datasets/GMW/extent/gmw_v3_2020_vec`
    - Newer 10m Sentinel-2-based version: `projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020`
    - Years available: 1996, 2007–2010, 2015–2020 (11 epochs, not every year)
    - Approach: same pattern as the NDVI/NDBI script — sample/reduce the mangrove extent raster
      or vector within a buffer around each coastal site's coordinates, per available year, to
      get a mangrove-area trend (replacing generic NDVI as the coastal vegetation-loss feature).
  - **What I could pull without GEE (real, but country-level only, not site-specific):**
    downloaded `gmw_v3_country_statistics_ha.xlsx` from Zenodo (242KB, lightweight) and extracted
    India's national mangrove extent time series → saved to
    `datasourceSIH/gmw_india_mangrove_extent_ha.csv`:
    - 1996: 411,119 ha → 2020: 403,785 ha (net −1.8% since 1996, non-monotonic: dipped to
      ~402-403k ha by 2008-2010, partially recovered to ~409k ha by 2018, declined again by 2020)
    - **Do not use this as a per-site ML feature** — it's a national aggregate, not Sundarbans-
      or Odisha-specific, and the two coastal candidate sites could easily move in a different
      direction than the national trend. Usable only as pitch-narrative context ("mangrove cover
      nationally has net-declined since 1996, per GMW/Bunting et al. 2022"), clearly labeled as
      country-level, not site-level.
  - **Side note on the Odisha coast site specifically:** Puri/Bhitarkanika area was chosen in
    `dataset-sites.md` for Cyclone Fani's landfall, but Puri itself is not a significant mangrove
    area (Bhitarkanika, the actual mangrove reserve, is a separate location further north/inland
    of the coast near Kendrapara). If the coastal human-activity story is meant to run on mangrove
    loss specifically (not just generic coastal NDBI growth), flag to the team whether the Odisha
    site coordinates should be Bhitarkanika instead of Puri — this wasn't caught in the original
    `dataset-sites.md` and is worth a deliberate decision, not a silent coordinate change.

---

## 11. Real rainfall pulled for all 8 coordinate-confirmed sites (2026-08-31)

- **Tool:** `ml/nasa_power.py` — direct wrapper around the NASA POWER REST API
  (power.larc.nasa.gov/api/temporal/daily/point). No auth needed, reachable from this
  environment (unlike Earth Engine), and coverage confirmed back to at least 1998
  (tested against the Malpa 1998 event date).
- **Method:** `rainfall_anomaly_pct` = % deviation of the mean daily rainfall in the
  90 days immediately before a site's `disaster_date` vs. the mean over the 5 years
  before that date (same real API, same site coordinates). For the 3 control sites
  with no disaster_date, anchored instead to a fixed reference date, **2023-01-01**
  (arbitrary but fixed, chosen so results are reproducible/comparable — not a real event).
  Requires ≥365 days of real data pulled before trusting the baseline; returns `None`
  otherwise rather than guessing.
- **Run via:** `ml/build_feature_table.py` now calls this automatically for every
  `TEMPLATE_SITES` entry with real lat/lon, and writes `ml/feature_table.csv`. Results
  (real, pulled 2026-08-31):

  | site_id | rainfall_anomaly_pct |
  |---|---|
  | joshimath | −17.6 |
  | raini | −78.3 |
  | kedarnath | +4.1 |
  | wazri | +179.5 |
  | dharali | +98.9 |
  | malpa | +52.3 |
  | auli_control | −58.2 |
  | sundarbans | −24.5 |
  | odisha_coast | −16.6 |
  | garhwal_control_tbd / sundarbans_control / coastal_control_tbd | not pulled — no coordinates yet |

- **IMPORTANT METHODOLOGICAL CAVEAT — read before using this feature in the model or
  the pitch:** the 90-day window is a *seasonal/moisture anomaly* indicator, not a
  *flash-trigger* indicator. It will systematically **understate** the signal for
  disasters caused by a short, intense rainfall burst, because a 2-3 day spike gets
  diluted across 90 days of averaging. This is visible in the numbers above: Kedarnath
  2013 — one of the most extreme, well-documented rainfall-triggered disasters in
  Indian record — comes back at only +4.1%, because the extreme rainfall was
  concentrated in ~2 days (June 16-17) right at the disaster date, not built up over
  three months. Compare this to the real, peer-reviewed Chamoli-Joshimath threshold
  already logged in §3 (Kanungo & Sharma 2014), which deliberately uses **10-day and
  20-day antecedent rainfall**, not 90-day — that's the more appropriate window for
  landslide/flash-flood triggers specifically. **Recommendation for the ML team:** keep
  `rainfall_anomaly_pct` (90-day) as the slow/seasonal-moisture feature it actually is,
  but consider adding a second, short-window feature (e.g. 10-day or 20-day cumulative
  rainfall immediately before the event) if the model needs to capture acute triggers
  like Kedarnath/Wazri/Dharali/Raini — don't let the 90-day number alone stand in for
  "how extreme was the trigger," it wasn't designed to answer that.
- Wazri (+179.5%) and Dharali (+98.9%) show a strong 90-day signal, consistent with
  monsoon-season antecedent saturation being part of their trigger story (not
  contradicted by the caveat above — just noting these two look more like the "slow
  buildup" pattern the 90-day window is suited to detect).

## 12. GEE pull script — written, NOT run (no Earth Engine access in this environment)

- `ml/gee_pull_site.py` — pulls NDVI, NDBI, DEM slope/elevation, and (coastal sites)
  GMW mangrove extent for one site, matching the Joshimath output file shape. Syntax-
  checked (`py_compile`) but **never executed** — this environment has no
  `earthengine-api` installed and no GEE credentials, confirmed by direct check
  (`import ee` fails; `which earthengine` finds nothing).
- Whoever runs it needs: `pip install earthengine-api`, then `earthengine authenticate`
  (one-time browser login) with an account that has GEE access, then possibly a
  `--project <cloud-project-id>` if their account requires one.
- **Unverified assumptions baked into the script — confirm before trusting output at
  scale:** buffer radius (1000m), Sentinel-2 cloud-filter threshold (20%), and the GMW
  asset paths (from gee-community-catalog.org, a community-maintained index, not the
  primary GMW/JAXA source — the path could have moved). None of these were confirmed
  against however the original Joshimath NDVI/NDBI pull was actually configured, because
  that original GEE script isn't in this repo — only its output CSVs are. If the team
  still has that original script, diff its parameters against this one before running
  it on new sites, so all sites are pulled the same way (methodological consistency
  matters more here than any single site's numbers being "optimal").

## 13. Control-site research (2026-08-31) — one resolved with real data, two still open

Attempted to resolve the 3 remaining TBD sites in `dataset-sites.md` via WebSearch, then
verified the coastal candidates against real cyclone-track data (not just search text).

- **Method for coastal candidates:** used the full raw IBTrACS North Indian Ocean track
  file (already downloaded this session, `ibtracs_NI.csv`, NOAA IBTrACS v04r01) — for a
  candidate point, computed the great-circle distance to every storm-track position with
  `NEWDELHI_WIND` (IMD agency) ≥ 48kt (IMD's Severe Cyclonic Storm threshold) in seasons
  2015-2023, and reported the closest such approach. This is a real, checkable filter, not
  a search-engine summary.
- **Result — coastal_control_tbd → RESOLVED, real coordinates added:** Coringa mangrove
  area, Kakinada, Andhra Pradesh (16.75°N, 82.28°E). Nearest severe-or-stronger cyclone
  2015-2023: Asani (2022, SCS, 50kt) at 157km — no close/direct hit. Chosen over other
  tested candidates specifically because it's also mangrove-coastal terrain (Coringa
  Wildlife Sanctuary), matching Sundarbans' terrain type. Now has real lat/lon and a real
  rainfall pull in `ml/feature_table.csv` (via `build_feature_table.py`).
  - Other candidates tested, for the record (all real IBTrACS-checked, 2015-2023 window):
    Visakhapatnam AP (164km to Titli 2018 VSCS 65kt), Nagapattinam TN (33km to Gaja 2018
    VSCS 70kt — too close, rejected), Chennai TN (13km to Vardah 2016 SCS 60kt — too
    close, rejected), Mangalore/Karnataka west coast (196km to Maha 2019 SCS 50kt — also
    clean, but not a mangrove site so weaker fit for the coastal narrative).
  - **Caveat to carry into the pitch if asked:** "no severe cyclone within 157km in
    2015-2023" is real evidence of lower exposure, not proof of zero risk ever — flag this
    the same way `ml-model-plan.md` already tells the team to flag control-site judgment
    calls generally.
- **Result — sundarbans_control → still UNRESOLVED, do not use a guessed coordinate:**
  the paper found on this (Bhargava et al. 2022, Frontiers in Marine Science, spatial
  cyclone-susceptibility study of the Sundarbans) confirms damage is spatially uneven
  (worse toward Bangladesh-side/west-central, better in taller/denser eastern stands) but
  does not publish coordinates or a named sub-region for the lower-damage zone in the
  fetched content — that level of detail is in supplementary data or would need contacting
  the author. **A guessed point (21.6°N, 89.05°E) was tested against real IBTrACS data and
  rejected** — Cyclone Bulbul (2019, SCS) passed within 23km, so it isn't actually a clean
  control. Do not substitute this guess into the feature table. Team needs either the
  paper's supplementary GIS data or a different source to resolve this one.
- **Result — garhwal_control_tbd (second hill control) → still UNRESOLVED:** WebSearch did
  not surface a specific second Garhwal town with citable no-event status, beyond what's
  already noted for Auli. Auli itself was upgraded from "TBD" to "weak evidence, not
  proof" — search found no news/GSI hits for a major event there, but I have no direct
  access to GSI's actual landslide inventory database to positively confirm a clean
  record, so treat this as suggestive, not settled. The Kanungo & Sharma (2014) paper
  (already cited in §3) mapped 128 landslides across the Chamoli-Joshimath region 2009-2012
  — if the team can get the underlying inventory (not just the paywalled abstract), it
  would be a more rigorous way to confirm which nearby villages had zero recorded events
  in that window, i.e. a real second control candidate, rather than relying on search
  absence-of-evidence.

## 14. MODEL TRAINED — real results, 2026-08-31 (the pitch centerpiece)

The team ran `gee_pull_site.py` for 8 of the 9 coordinate-confirmed sites (all except
already-done Joshimath), fixed two real bugs found along the way (see below), then ran
`build_feature_table.py` + `train_model.py`. **10/12 candidate sites now have real,
complete data** (7 hill, 3 coastal) — above the plan's own "≥8 sites" credibility bar.
Only `garhwal_control_tbd` and `sundarbans_control` remain unpulled (no confirmed
coordinates yet, per §13 — not urgent now that N=10 clears the bar).

**Actual model output — use these exact numbers in the pitch, do not round up or embellish:**
- LOOCV accuracy: **7/10 (70%)**
- Feature importance (logistic regression coefficients, standardized): `ndvi_trend_slope`
  **-1.032** (largest magnitude — declining NDVI predicts higher risk, consistent with
  the project's core hypothesis), `rainfall_anomaly_pct` +0.518, `mean_slope_degrees`
  +0.390, `ndbi_trend_slope` +0.303, `elevation_mean_m` +0.184, `terrain_hill` +0.142.
  Chart saved at `ml/feature_importance.png`.
- Cross-terrain validation: trained on the 7 hill sites only, tested on the 3 coastal
  sites — predicted [1,1,1], actual [1,1,0]. Got both real coastal disasters right
  (Sundarbans/Amphan, Odisha/Fani); false-positived on the one coastal control. **2/3,
  not 3/3** — state this exactly if asked, per `ml-model-plan.md`'s own instruction not to
  let a judge catch an inflated claim.
- Risk ranking: all 8 disaster sites scored 0.735-0.96; the 2 controls scored lower
  (auli_control 0.540, coastal_control_tbd 0.477) but auli_control in particular is not
  comfortably separated from the disaster cluster — worth a one-line acknowledgment in the
  pitch rather than pretending the separation is cleaner than it is.

**Suggested one-paragraph pitch summary (plain language, grounded in the numbers above —
edit tone but keep the numbers exact):** "Across 10 real, fully-instrumented sites — 7 in
the Himalayas, 3 on the coast — a simple logistic regression correctly classified 7 out of
10 under leave-one-out cross-validation. The model's own coefficients, not our assumption,
ranked declining vegetation cover as the single strongest predictor of disaster occurrence,
ahead of rainfall anomaly, slope, and construction growth. When trained only on hill sites
and tested on coastal sites it had never seen, it correctly flagged both real coastal
disasters as high-risk — a small but real cross-terrain generalization result, though it
also produced one false positive on our coastal control site, which we're upfront about."

**Two real bugs found and fixed while running this (both in `ml/gee_pull_site.py`, both
now fixed and verified):**
1. `mask_s2_clouds`'s `.divide(10000)` call was silently stripping image metadata
   (`system:time_start`), crashing every NDVI/NDBI pull with a cryptic
   "does not have a 'system:time_start' property" error. Fixed by copying properties back
   after the divide.
2. `pull_gmw_mangrove` guessed a `'year'` filter property on the `GMW_V3` ImageCollection
   that turned out not to exist, crashing with "Image.select: Parameter 'input' is
   required and may not be null" (an empty-filter-result error surfacing at compute time).
   Fixed by switching to the documented per-year vector assets
   (`gmw_v3_<year>_vec`) instead of guessing the raster collection's property schema.
   **This is still unverified end-to-end** — the fix hasn't been re-run yet since it was
   written after the last GEE session. Note also: GMW mangrove data was only ever meant as
   supplementary narrative context (see §10), not one of the model's actual input
   features (`ml-model-plan.md` §2 doesn't include it) — so this bug never blocked
   training, and re-running it is optional polish, not a blocker.

**Next real step, if the team wants to push further:** re-run the GMW pull for the 3
coastal sites to confirm the vector-asset fix works, and/or resolve the 2 remaining TBD
control sites if there's time — neither is required for the model to be presentable as-is.

**UPDATE 2026-08-31, same day: GMW re-run succeeded, fix confirmed working.** Real mangrove
extent (ha, within each site's 1km buffer) across all 11 GMW epochs:
- `sundarbans` (21.9497°N, 88.9468°E): 304.47 ha (1996) → 303.08 ha (2020), stable,
  slight non-monotonic decline. Real mangrove presence, consistent with siting.
- `odisha_coast` (19.7°N, 85.8°E, Puri): **0.00 ha in every single year, 1996-2020.**
  This is not a data-quality problem, it's a real confirmation of the site-choice concern
  already flagged in §10 — Puri itself has essentially no mangrove cover in this buffer.
  **This elevates that concern from "worth checking" to "confirmed": the current coastal
  disaster pair is Sundarbans (real mangrove decline, real cyclone) vs. Odisha (real
  cyclone, but ZERO measured mangrove to show any loss/amplifier trend for).** If the
  pitch leans on "mangrove loss amplifies cyclone damage" as the coastal-side story
  (mirroring the hill-side NDVI story), Odisha as currently sited can't carry that half of
  it — either (a) re-site to Bhitarkanika (the actual mangrove reserve, further
  north/inland of Puri) and re-pull, or (b) drop the mangrove-specific framing for the
  coastal side and lean on NDBI (built-up growth, which IS a model feature and already
  has real data for both coastal sites) as the human-activity signal there instead. This
  is a real decision for the team now, not a hypothetical one — model training itself is
  unaffected either way (GMW was never a model feature), but the pitch narrative should be
  consistent with what the data actually shows.
- `coastal_control_tbd` (16.75°N, 82.28°E, Coringa/Kakinada): 0.71-1.83 ha, fluctuating,
  no clear trend, small absolute numbers (likely near the edge of the sanctuary rather
  than its core — the 1km buffer may be undersized for this site specifically). Real data,
  but too small/noisy to support a strong trend claim on its own.

Raw per-year files: `datasourceSIH/sites/<site_id>/<site_id>_gmw_mangrove.csv` for all 3.

## 15. DECIDED, 2026-08-31: coastal narrative leans on cyclone intensity, not a human-activity land-use signal

Following up on the Odisha 0.00 ha finding in §14: the team's first instinct (mine
included, initially) was "swap the mangrove framing for NDBI as the coastal
human-activity signal" — but the actual per-site NDBI numbers don't support that either.
Checked before writing anything down (this is exactly what this file is for):

- `sundarbans` (disaster=1): ndbi_trend_slope = **-0.003** (near flat)
- `odisha_coast` (disaster=1): ndbi_trend_slope = **+0.0009** (near flat)
- `coastal_control_tbd` (disaster=0, control): ndbi_trend_slope = **-0.016** (more
  negative than either disaster site)

None of these separate disaster from control. NDBI does NOT carry a clean coastal
human-activity story the way NDVI does on the hill side (compare: Joshimath +0.011,
Raini +0.011, vs. the tiny/inconsistent coastal numbers above).

**DECISION: do not force a coastal human-activity narrative onto data that doesn't
support it.** The honest and more interesting framing for the pitch: hill-site disasters
in this dataset show a genuine slow human-activity amplifier (declining NDVI), while
coastal disasters are driven predominantly by acute cyclone intensity — a different
mechanism, not a weaker version of the same one. This is consistent with real-world
physics (storm-surge/wind damage vs. slope destabilization) and is more defensible than
stretching NDBI or mangrove loss into a role the numbers don't back up.

**This actually strengthens the cross-terrain validation talking point, not weakens it:**
the model trained ONLY on hill-derived human-activity features (NDVI/NDBI/slope/
elevation/rainfall) still correctly flagged both real coastal disasters (§14) — despite
coastal sites having no clean human-activity signal of their own to lean on. That's a more
impressive generalization result than if the coastal sites had their own matching
human-activity story to be "found."

`human_activity_notes` for all 3 real coastal rows in `ml/feature_table.csv` now state
this explicitly (updated via `ml/build_feature_table.py`, rebuilt 2026-08-31) — each notes
its own NDBI value, that mangrove is real supplementary data but not a model feature, and
that the disaster driver is the acute cyclone event, not a land-use trend. Model output
itself (LOOCV, feature importance, cross-terrain result — §14) is unchanged by this,
since GMW/mangrove was never a model input either way; only the pitch narrative and the
feature-table documentation changed.

**If asked "why doesn't the coastal side have its own human-activity evidence like the
hill side does":** answer with the above directly — say the mechanisms differ, don't
pretend the coastal NDBI/mangrove signal is stronger than 10 real data points show it to
be. Small sample honesty (already flagged as a required talking point in
`ml-model-plan.md` §6) applies here specifically, not just to overall N.

## 16. "If nothing changes" projection feature, 2026-08-31 -- user redirect + a real finding

User rejected the Operate-mode technical dashboard as unusable/unfeeling ("even I can't
understand what is happening") and asked for an awareness-focused interface instead:
interactive, image-driven, plain-language. Built `awareness/index.html` ("The Living
Land") -- a scroll-driven page, real India map (see below), before/after satellite
imagery slots (pending team's `gee_pull_thumbnail.py` runs), plain-language translation
of every technical finding with the real numbers still available on tap, and a new
"run the clock forward" projection control.

**How the projection works, and why it's built this way (read before touching it):**
`ml/build_projection_data.py` fits plain linear regression to each real site's actual
NDVI/NDBI time series (the raw satellite data, not the trend-slope summary feature) and
extrapolates to a chosen horizon (5/10/20/30 years). This is deliberately NOT the trained
classifier (`ml/train_model.py`) run further into the future -- the classifier's inputs
are already trend RATES, and a rate doesn't change just because more years pass; feeding
an artificially scaled-up "N years of slope" back into a model calibrated on ~5-year
rates would extrapolate it far outside anything ever validated, producing a confident-
looking number with no real grounding. Instead this reuses the exact illustrative-index
method already validated in `demo/app.js`'s Joshimath BAU/Intervention slider (NDVI
decline + NDBI growth, normalized against each site's own observed range), just
generalized across sites and made the time horizon a variable. Every card/disclaimer on
the page states this is illustrative, not the classifier, not a statistical forecast.

**Real finding surfaced while testing this, worth knowing before presenting it:** not
every site's real NDVI/NDBI trend points toward "things getting worse." Checked all 10
real sites at the 30-year horizon:
- **Trend worsening (BAU > Intervention), gap shown honestly:** joshimath (50%→40%),
  raini (50%→37%), kedarnath (100%→84%, clamped at the index's ceiling), auli_control
  (50%→43%).
- **Trend actually IMPROVING (BAU < Intervention) in this linear fit:** wazri, dharali,
  malpa, sundarbans, odisha_coast, coastal_control_tbd -- i.e. the majority of sites.

This is not a bug in the math -- it's a real property of fitting a straight line through
2019-2023 (or 2015-2023 for coastal) NDVI/NDBI values, which are heavily seasonal and
noisy; a positive slope over that window doesn't necessarily mean "the forest is healing,"
it can just as easily reflect where the sampled satellite passes happened to fall each
year. This is the same caveat that already applied to Joshimath's original single-site
slider (labeled illustrative for exactly this reason) -- it's just more visible now that
it's shown across 10 sites instead of 1. **Do not silently force a uniform "everything is
dying" narrative onto this feature** -- the app.js narrative text branches honestly on
whether the site's own real trend is worsening, improving, or flat, and that branching
must be preserved in any future edit. If asked about it: "the real data doesn't tell the
same story everywhere, and we're showing that honestly rather than picking the sites that
make the point for us."

**Also built, real data, not a stock asset:** `awareness/india-map.js` -- a simplified
India national outline derived from real district-boundary geometry (udit-001/india-maps-
data on GitHub, dissolved with `shapely.ops.unary_union` and simplified), with a linear
equirectangular projection reused identically in `app.js` to place site markers at their
true relative lat/lon position -- not eyeballed coordinates.

**Mode-shift disclosure (recorded in the artifact's own direction-contract comment too):**
`awareness/index.html` deliberately breaks from `DESIGN.md`'s Operate-mode restraint
(bigger scale, more motion, imagery) since this is now a Persuade/Experience surface, not
Operate. Same navy/teal/amber token identity kept for project-wide consistency; register
and composition are not the same as the technical dashboard.

**Still open:** before/after images depend on the team running
`ml/gee_pull_thumbnail.py` per site (commands already given to the user); the page
degrades gracefully to a labeled "pending" placeholder per site until that lands.

## 17. Restructure to a unified per-site explorer, 2026-08-31 -- user feedback the v1 layout was disconnected

User feedback on the first awareness build: no clear "why did this happen," too much
prose, unclear what "if nothing changes" was tracking, no tie to actual disaster risk,
unclear logic in the cross-terrain proof, an arbitrary-seeming single live-weather site,
and the core complaint -- "its a AIML project, it has to have some use." The root cause
across all of these: facts about ONE site were scattered across five separate full-page
sections (a generic causes section, the map, before/after, projection, live weather),
so nothing about any one place ever came together into something usable.

**Fix:** collapsed WHY + MAP + BEFORE/AFTER + PROJECTION + LIVE into one section,
`#explore-section` in `awareness/index.html` -- pick a site (map marker or pill), and
one profile panel renders, in order: what happened (real, sourced) -> why here
specifically (this exact site's real NDVI/NDBI trend direction, plus Joshimath's cited
government-committee cause where we actually have one) -> **the trained model's real
`predicted_risk_prob` for this site** (previously this number only lived in the
technical dashboard; the awareness page never showed the actual model output, just the
illustrative projection index -- now both are present and clearly distinguished) ->
before/after imagery -> the "if this continues" projection, now explicitly labeled what
it tracks ("Tracking this site's real vegetation-cover and construction trend") with
plainer card labels ("Trend continues" / "Activity halted today") -> live weather for
that same site (fixes "why just Dharali" -- it's whatever site is currently selected,
named explicitly in the live status line).

Reordered `#finding-section` (the global feature-importance finding) to come BEFORE the
per-site explorer, so the page establishes the general pattern first, then lets the user
dig into how it looks at any one place -- general claim, then a tool to verify it
yourself, rather than five disconnected facts in scroll order.

Also: the cross-terrain proof section's lede now states the actual logic, not just the
setup ("if it had just memorized mountains, it should fail completely somewhere this
different"). The risk-ranking list rows are now clickable -- clicking one selects that
site in the explorer and scrolls to it, so the whole page behaves as one connected tool
instead of independent widgets.

**On the redundancy question (why build a second "if nothing changes" slider when
`demo/index.html`'s Joshimath page already has one):** `demo/index.html`'s version is
Joshimath-only, fixed to a 2030 target, and includes the real rainfall-threshold
backtest against the two actual subsidence windows -- a capability nothing else on the
site has. `awareness/index.html`'s version covers all 10 real sites with a flexible
5/10/20/30-year horizon. The close section's CTA copy now says this explicitly
("Joshimath's rainfall-threshold backtest") instead of just "deep-dive," so the
distinction isn't left implicit. Neither page's version was deleted; if asked why both
exist, this is the honest answer.

**Not done, disclosed to the user rather than silently skipped:** the standalone
technical dashboard (`dashboard/index.html`) was also criticized ("looks like a ppt")
but was not rebuilt this round -- scope was the awareness page only. Revisit if asked.

## 18. Two more real gaps the user caught, same day: which trend, and where's the prediction

- "how do i know which trend you are talking about": the projection card said it was
  "tracking" a trend but never showed it. Fixed -- `renderProfileProjection` now renders
  a self-contained `#proj-trend-summary` block restating the site's actual NDVI/NDBI
  direction and real per-year numbers directly in that card, not just in the separate
  "Why here" card above.
- "y there is no disaster prediction": the real model output (`predicted_risk_prob`) WAS
  already on the page (added in sec 16/17's restructure) but was labeled "Our trained
  model's real risk read" -- not unmistakable. Renamed to **"Disaster risk prediction"**
  with an explicit line under it: "This is our trained model's actual output for this
  site -- not illustrative, the real prediction it makes."
- **Real problem underneath both:** the page had two DIFFERENT "risk" scales running at
  once -- the real model's `riskWord()` bands (Very High/High/Elevated/Lower @ 80/60/40%)
  and the projection's own `bandOf()` bands (Low/Moderate/Elevated/High @ 25/50/75%),
  different thresholds, different words, both called "risk" on the same page. Unified:
  the projection now uses the SAME `riskWord()`/`riskWordColor()` as the real prediction
  card. `bandOf()` deleted.
- Because unifying the vocabulary made the real score (e.g. Dharali 96%) and the
  illustrative trend-only projection (e.g. 33%) sit right next to each other using the
  same words, the gap between them became a new confusion risk on its own. Addressed
  directly in the disclaimer text, not glossed over: "The real risk score above also
  weighs slope, elevation, and rainfall, which is why the two numbers can land far
  apart." -- i.e. the real model uses 6 features, the illustrative index uses only 2
  (vegetation + construction trend), by design (see sec 16 for why it can't legitimately
  use more).

## 19. "How is 96% right if the trend is improving" -- real answer, not a guess

User pushback on Dharali specifically: vegetation there is recovering (real, positive raw
slope, +0.0029/yr), so why does "Disaster risk prediction" still read 96%? This deserved
an actual computed answer, not a plausible-sounding one, so before writing any UI copy I
checked the real numbers:

- Standardization compares each site to the OTHER sites in the sample, not to zero.
  Dharali's ndvi_trend_slope (+0.00295) is real and positive, but the sample mean across
  all 10 real sites is +0.00939 -- meaningfully higher. So relative to its peers,
  Dharali's vegetation recovery is still BELOW AVERAGE, which is what the standardized
  logistic regression actually sees. Checked directly: `python3` recomputation of the
  sample mean/site-by-site comparison confirmed this before any copy was written (not
  asserted from memory).
- `ml/train_model.py` now exports real per-site `feature_contributions` (coefficient x
  standardized value, every feature) and `top_drivers` (top 3 by absolute contribution)
  into `model_results.json` / `dashboard/data.js`. This is the actual math the trained
  model used for that site's score -- not a second illustrative index, not a guess.
  For Dharali the top 3 are (real, computed): ndvi_trend_slope +0.624 (raises risk --
  weaker-than-peers vegetation trend), rainfall_anomaly_pct +0.610 (raises risk --
  +98.9% anomaly, one of the most extreme in the sample), mean_slope_degrees +0.306
  (raises risk -- steeper than peers). Construction trend and elevation contribute much
  less here.
- `awareness/app.js`'s `renderProfileRisk()` now renders these as a real "what's
  actually driving this score" list under the Disaster risk prediction card, phrased
  relative to the sample ("weaker/healthier than most other sites we measured") using
  the ACTUAL contribution sign per site, not an assumption based on whether the site's
  raw trend looks superficially good or bad. Verified this generalizes correctly on a
  second site (Kedarnath): its vegetation trend is genuinely above the sample mean, and
  the driver list correctly shows it pulling risk DOWN there, with construction growth
  and elevation pulling it up instead -- confirms the logic isn't hardcoded to Dharali's
  case.
- **Do not hand-write a "why this site scored X" explanation again without checking the
  real per-site contribution numbers first** -- this file's own purpose is to prevent
  exactly the kind of plausible-but-unverified explanation that would have made this
  worse, not better, if guessed.

## 20. Land Surface Temperature (LST) added as a real, pipeline-ready third signal, 2026-08-31

User asked whether the project is relatable to SIH26206 and whether to add global-
warming/carbon/land-heating signals. Checked the actual official problem statement first
(not the team's own framing) -- scraped from the real SIH 2026 catalog
(github.com/NoBugNinja/Smart-India-Hackathon-SIH-2026-Problem-Statements): SIH26206 is an
open AICTE "Student Innovation" slot, theme Disaster Management, description "Disaster
management includes ideas related to risk mitigation, Planning and management before,
after or during a disaster." No narrow fixed brief -- the project fits comfortably.

**Decision on the three suggested additions:**
- Global warming / carbon emissions as a MODEL FEATURE: rejected. These are global
  numbers with zero variation across the 10 sites (same CO2 ppm value for Joshimath and
  Sundarbans alike) -- a feature with no within-sample variance can't help a small-N
  classifier distinguish anything. Fine as pitch narrative only, never as data.
- Land Surface Temperature (LST): accepted and built. Real, site-varying, satellite-
  measured (MODIS thermal bands, 1km resolution via Earth Engine), and mechanistically
  it's a direct, well-documented consequence of the exact same human activity (deforest-
  ation/construction) already being tracked -- deepens the existing story rather than
  adding a tangent.
- **Why NOT NASA POWER's "Earth Skin Temperature"** (which was already reachable without
  GEE, unlike everything else): its native grid is ~50km resolution (MERRA-2 reanalysis)
  -- far too coarse to distinguish one site's 1km buffer from the forested land next to
  it. Using it would not actually test "does local deforestation cause local heating,"
  it would just be a regional weather number dressed up as a land-cover signal. Rejected
  even though it would have been immediately pullable, because it wouldn't honestly
  measure what it claims to.

**What's built, ready for real data:**
- `ml/gee_pull_lst.py` -- new GEE pull script (MODIS/061/MOD11A2, same 1km buffer
  convention as the NDVI/NDBI pulls), not yet run (no GEE access in this environment).
  Outputs `<site_id>_lst_timeseries.csv` in the same per-site directories as the existing
  pulls.
- `ml/build_joshimath_features.py`: `lst_features()` computes trend slope (°C/yr) and
  mean temperature (°C) from that CSV, generically for any site; wired into both
  `compute()` (Joshimath) and `compute_gee_site()` (the other 9 sites). Returns nothing
  if the file doesn't exist yet -- fully optional, no site is blocked waiting on it.
- `ml/build_feature_table.py`: `lst_trend_slope`/`lst_mean_c` added to `COLUMNS`; citation
  line records the real observation count once present.
- `ml/train_model.py`: `choose_feature_cols()` only adds `lst_trend_slope` to the trained
  model's feature set once it's non-null for EVERY real site -- never partial-imputed,
  never silently drops rows to make it fit. Right now it prints exactly why it's excluded
  ("missing for 10/10 real sites") rather than staying silent. Confirmed the full
  pipeline (`build_feature_table.py` -> `train_model.py`) still reproduces the exact
  same LOOCV 7/10 and feature-importance numbers as before this change -- fully
  backward-compatible, nothing broke.
- `ml/model_results.json` / `dashboard/data.js`: `lst_trend_slope`/`lst_mean_c` now
  present on every real site's export, `null` until real data lands.
- `awareness/app.js`: `renderProfileWhy()` adds a third "the land itself has been
  warming/cooling" row automatically once `site.lst_trend_slope` is non-null, with the
  same real per-year number formatting as the NDVI/NDBI rows. `DRIVER_PHRASES`/
  `DRIVER_LABELS` already have an `lst_trend_slope` entry so the "what's actually
  driving this score" list (sec 19) will explain it correctly the moment it becomes a
  trained feature, without further code changes.

**Next step for whoever has GEE access:** run `gee_pull_lst.py` for each of the 9 non-
Joshimath real sites (same `--site-id/--lat/--lon` pattern as `gee_pull_site.py`,
`--outdir` pointing at the same per-site directory), plus once more for Joshimath itself
into `datasourceSIH/` directly (matching that site's non-standard file location), then
re-run `build_feature_table.py` and `train_model.py`. LST will light up automatically on
the awareness page and join the trained model with no further code changes needed.

## 21. Real GEE run results, 2026-08-31: one script bug fixed, one genuine coordinate error found

Team ran `gee_pull_lst.py` for real across 9 sites + Joshimath.

**Bug fixed (mine, in the handoff instructions, not the data):** the Joshimath LST
command I gave used `--outdir ../../datasourceSIH` from inside `ml/` -- one `..` too
many, landing the file at `/Users/kirthika_ck/Documents/datasourceSIH/` (outside the
project entirely) instead of `sih/datasourceSIH/`. File itself was real and fine (223
rows); just moved it to the correct path rather than re-running the pull.

**Real script bug fixed:** `gee_pull_lst.py` crashed on Raini with "Number.multiply:
Parameter left is required and may not be null" -- an 8-day MODIS composite was fully
cloud-masked within the 1km buffer for one date, and doing the Kelvin->Celsius
conversion as scalar `ee.Number` arithmetic AFTER `reduceRegion` doesn't handle a null
result gracefully (throws instead of propagating). Fixed by doing the conversion at the
Image level (`image.multiply().subtract()`, which is mask-aware) BEFORE `reduceRegion`,
so a fully-masked date now cleanly produces a `null` that the existing
`ee.Filter.notNull` step filters out, instead of crashing the whole pull.

**Real, more significant finding: `odisha_coast`'s coordinate (19.7°N, 85.8°E) is very
likely sitting in open water, not on land.** Evidence, not speculation:
- LST returned exactly 0 valid observations across the full 2019-2023 period (~230
  possible 8-day composites) -- not a sparse-data pattern, a total-exclusion pattern.
  MODIS LST products mask non-land pixels entirely.
- Cross-checked against data already in `feature_table.csv` from the ORIGINAL GEE pull
  at this same coordinate: `elevation_mean_m = 0.0` and `mean_slope_degrees = 0.0`,
  exactly -- the classic SRTM signature of a buffer sitting over open sea, not the "low
  but real" numbers a genuine low-lying coastal town would show.
- **This was flagging itself the whole time** -- `dataset-sites.md` already marked this
  coordinate "verify" and NDVI/NDBI/rainfall pulls succeeded there (optical/atmospheric
  data doesn't get masked the same way LST does), which is exactly why this went
  unnoticed until a land-only product hit it.
- **Corrected to Puri town center, 19.8106°N 85.8314°E** (19°48'38"N 85°49'53"E per
  Wikipedia, a well-documented on-land landmark, checked via WebSearch before using it
  -- not guessed). Updated directly in `ml/build_feature_table.py`'s `TEMPLATE_SITES`
  entry for `odisha_coast`, with the reasoning recorded in that row's
  `source_citation` field so it stays visible in the CSV itself, not just here.
- **Consequence: every GEE-derived value for `odisha_coast` (NDVI, NDBI, slope,
  elevation, LST) pulled at the OLD coordinate is now stale/unreliable** and needs
  re-pulling at the corrected point. Rainfall (NASA POWER, live-fetched every build) and
  the cyclone landfall data (IBTrACS nearest-track-point, ~15-20km from either
  coordinate, unaffected) do not need re-pulling.
- **Next step, real commands, not yet run:**
  ```
  python3 gee_pull_site.py --site-id odisha_coast --lat 19.8106 --lon 85.8314 --start 2015-01-01 --end 2023-12-31 --terrain coastal --outdir ../datasourceSIH/sites/odisha_coast --project stellar-polymer-470816-j9
  python3 gee_pull_lst.py --site-id odisha_coast --lat 19.8106 --lon 85.8314 --start 2015-01-01 --end 2023-12-31 --outdir ../datasourceSIH/sites/odisha_coast --project stellar-polymer-470816-j9
  ```
  Both overwrite the same filenames in the same directory, so no cleanup needed first.
  After that, `build_feature_table.py` + `train_model.py` should show LST included in
  the trained model for the first time (10/10 real sites), and `odisha_coast`'s
  slope/elevation will reflect real land values instead of 0.0/0.0.
- **This also means the ALREADY-TRAINED model's `odisha_coast` row has had
  slope=0/elevation=0 this whole time** -- worth knowing if anyone asks about that
  site's numbers before the re-pull lands. Low-importance features in this model
  (mean_slope_degrees, elevation_mean_m both mid-to-low in feature_importance), so the
  practical effect on `predicted_risk_prob` is likely small, but "likely small" isn't
  "verified" -- don't claim the impact was negligible until the corrected numbers are
  actually back.

## 22. odisha_coast re-pull landed real; LST now trained; live calculator built

**LST fully resolved:** team re-ran `gee_pull_site.py` + `gee_pull_lst.py` at the
corrected Puri coordinate (19.8106, 85.8314). Real result: `lst_trend_slope` now present
for all 10/10 real sites, and `train_model.py` printed "Including optional feature
'lst_trend_slope': present for all 10 real sites" -- it's a genuine trained-model input
now, not just a display number. New feature importance with 7 features: ndvi_trend_slope
-1.081 (still #1), rainfall_anomaly_pct +0.511, lst_trend_slope +0.418, mean_slope_degrees
+0.411, ndbi_trend_slope +0.128, terrain_hill +0.102, elevation_mean_m +0.074. LOOCV
unchanged at 7/10. Corrected odisha_coast's predicted_risk_prob moved from 0.788 to 0.838
(now using real slope/elevation instead of the old 0.0/0.0 water-pixel artifact).

**User's serious worry, addressed with a new capability, not just reassurance:** "it's
not looking like something anyone would understand... how am I supposed to prove the
model is learning... no other use is visible." Root cause: every existing view only
showed the model's PRECOMPUTED output for 10 fixed sites -- nothing let anyone watch it
actually compute something live, which is what actually distinguishes "a real trained
model" from "a lookup table with a story attached."

**Built: a live, client-side calculator** (`#calc-section` in `awareness/index.html`,
logic in `app.js`). Reproduces `ml/train_model.py`'s `predict_proba()` exactly in
JavaScript -- standardize each feature with the REAL fitted `scaler.mean_`/`scaler.scale_`,
dot with the REAL fitted `clf_full.coef_`, add the REAL `intercept_`, sigmoid. These
parameters are now exported in `model_results.json`'s new `model_params` field
(`ml/train_model.py`, added this session). **Verified exact match** before building any
UI on top: recomputed Dharali's score by hand in Python from the exported params and
compared to the stored `predicted_risk_prob` -- identical (0.955 = 0.955). Then verified
in-browser: loading the "Joshimath" preset reproduces 93%, matching the real stored
value exactly, confirming the live JS math and the real Python model agree.

**Reframed mid-build per user's own insight**, not mine originally: user connected "if
it's learning" directly to the actual SIH26206 problem statement wording ("mitigation,
Planning and management before, after or during a disaster") -- realized the calculator
isn't just a proof-of-learning demo, it's literally a planning/mitigation simulator: load
a real site, drag only the human-controllable inputs (vegetation trend, construction
trend -- explicitly separated into a "You can influence these" group, distinct from
"Fixed geography & weather"), and watch modeled risk respond. This IS simulating a
mitigation decision before making it. Section copy and framing built around this
directly ("This is also a planning tool"), not just "look, math."

**Also added:** per-site LOOCV results (`loocv.per_site` in `model_results.json`) --
for each real site, what the model predicted when trained on the other 9 only, not yet
surfaced in a dedicated UI table (the calculator was the higher-priority build this
round; this data is ready for a future "proof" table addition if wanted).

**Real bug caught and fixed during this build, not after:** `.risk-row .name` (the
risk-ranking list) had no `min-width: 0` on a flex item, so a long site name refused to
shrink and pushed the row wider than the mobile viewport -- genuine horizontal overflow,
caught by an explicit `scrollWidth > clientWidth` check, not a visual skim. Pre-existing
bug (not introduced by tonight's changes), fixed in the same pass.

## 23. "Jury has to understand it in under 90 seconds" -- measured, not guessed

User: technical breakdown is too much, "we don't need to tell everything we know, just
what they need to know." Asked which specific thing felt like too much (separate
dashboard vs. this page's own disclaimers vs. both); user delegated the call and gave
the real constraint instead: **90-second jury comprehension**.

Measured before cutting anything, per this file's own rule against guessing: full page
static text alone is ~460 words (~2.3 min), before counting the substantial dynamic
content app.js renders into the per-site explorer (site descriptions, why-here text,
risk drivers, projection narrative). Reading the WHOLE page was never going to fit 90
seconds, and trying to trim it down to fit would have gutted real, load-bearing content
(the per-site detail, the honesty checks, the full ranking).

**Decision: don't cut the deep content, draw an honest line instead.** Measured the
actual "top of page" path -- Hero -> Machine Noticed -> Calculator -- at 198 words
(~59 seconds reading), comfortably under 90s even with one calculator interaction on
top. That's already the real 90-second story: hook, what the model found, live proof
you can touch. Added a quiet `.scope-divider` right after the Calculator section,
before "Explore a site": *"That's the whole story. Everything below is optional depth:
real per-site detail, our honesty checks, the full ranking, and raw numbers."* This is
the literal implementation of "tell them what they need to know" -- not deleting the
rest, just being honest about which part is required and which is for someone with more
time or doing follow-up diligence (a judge in Q&A, e.g.).

Did NOT touch the separate technical dashboard (`dashboard/index.html`) this round --
the user's own framing ("whatever you prefer... I just want jury to understand it in
under 90sec") pointed at THIS page's structure as the actual lever, not the existence of
a secondary reviewer-facing page. If asked later whether the dashboard should also be
cut/simplified, that's still open -- don't assume it was covered by this fix.

## 24. Early warning check: real "before/during disaster" capability, built into the existing Live card

User pushed back on the PS-alignment claim: "mitigation is ok, but how is planning and
managing before and during disaster." Correct reading of the actual PS text first:
"before, after **or** during" is a menu, not a checklist -- doing "before" well is a
complete answer, not partial. Then found one real capability that already existed but
was disconnected: the real cited rainfall threshold (Kanungo & Sharma 2014, Chamoli-
Joshimath region specifically -- see sec 3) only lived on the old `demo/index.html`
Joshimath page, never connected to the live weather already running on the awareness
page.

**Built into the existing "Live right now" card** (`#ew-block` inside
`renderProfileLive`'s card, `awareness/app.js`'s new `renderEarlyWarning()`/`buildEwUI()`/
`updateEwDisplay()`) rather than as a new section -- user explicitly asked for "not
messy," and extending an existing card beats adding a sixth top-level section.

**What it does, all real:**
- Fetches real daily rainfall for the last 20 days live from Open-Meteo
  (`daily=precipitation_sum&past_days=20`), computes real rolling 10-day/20-day sums.
- Compares against the real cited threshold (55mm/10-day, 185mm/20-day) with a bar
  visualization, colored red/green by whether the real current sum is at/over it.
- **Interactive what-if slider** ("+ hypothetical rain, next few days", 0-150mm): drag
  it and both bars + the narrative recompute live, client-side, no refetch -- "if X more
  mm falls, does this cross the threshold" is a genuine before-disaster planning
  question, answerable with real math on real data.

**Honesty guard, the important part:** the threshold is only scientifically valid for
the Chamoli-Joshimath region it was derived for. `CHAMOLI_SITES = {joshimath, raini,
auli_control}` (the actual Chamoli-district sites) is the only set this renders the full
check for; every other site gets an explicit note instead: "hasn't been validated here
-- not shown for this site, to avoid implying it applies everywhere." Do not expand this
set without a real regional citation to back it -- this is exactly the kind of
scope-creep this file exists to prevent.

**Real bug caught by the detector, fixed properly, not just silenced:** animating the
bar fill via `width` triggers layout reflow (flagged as a real performance finding, not
noise) -- switched to `transform: scaleX()` with `transform-origin: left`, the standard
non-layout-triggering pattern for animated progress bars. Verified the fix actually
renders correctly in a FRESH tab (`scaleX(0.643636)` for a 35/55mm real ratio) after an
initial read on a stale-cached tab showed an empty transform -- same class of tab-cache
artifact noted earlier in this file, not a real regression; don't re-diagnose it as one
if it recurs, just open a fresh tab.

**"After":** not built (nothing to build -- it's already true). The model got smarter
this session by adding Dharali's real Aug 2025 event as training data. Worth stating in
the pitch; no code change needed.

## 25. Real Supabase backend: database + Edge Function, so there's an actual "skeleton" behind the page

User's pushback: "without backend.... its a ppt.... a body without skeleton.... while
explaining they will ask for backend and database." Correct call -- a static site with
data baked into JS files has no architecture story if a judge asks "where's your
backend." Built a real one rather than faking it.

**New Supabase project** `dercrxstnclfkcokcsdf` ("sih26206-ecorisk", region ap-south-1/
Mumbai) -- confirmed via MCP `get_cost` this is free ($0/month) before creating.
Deliberately a **separate** project from the team's pre-existing, unrelated
`tntlazyigoswiicivtlu` project (a real user-auth "visits" app -- confirmed via
investigation, not touched).

**Schema** (migration `create_core_schema`, 4 tables, RLS enabled, public-read-only
policies -- only service_role/migrations can write, anon can only `select`):
- `sites` -- the master feature table (same 12 rows as `ml/feature_table.csv`: 10 REAL,
  2 NOT_PULLED), now living in a real Postgres table instead of only a CSV.
- `model_runs` -- one row per trained model, with `feature_importance`, `cross_terrain`,
  `loocv_per_site`, and the full `model_params` (coefficients/intercept/scaler) as jsonb,
  sourced directly from `ml/model_results.json`. `is_current` flag for versioning future
  retrains.
- `risk_predictions` -- one row per site per model run: `predicted_risk_prob`,
  `feature_contributions`, `top_drivers`, FK'd to `model_runs`. All 10 real sites'
  predictions verified to match `model_results.json`'s `risk_ranking` exactly after
  insert (dharali 0.955 down to coastal_control_tbd 0.4207).
- `gdacs_snapshots` -- populated live by the Edge Function below, not seeded.

**Edge Function `fetch-gdacs`** (deployed, `verify_jwt: true`, called with the anon key
like any normal Supabase client call) is the actual point of the backend, not just
decoration. Real problem it solves: confirmed earlier this session via direct
`urllib.request` that `gdacs.org`'s API returns no `Access-Control-Allow-Origin` header
-- a static page's browser JS **cannot** call GDACS directly, full stop. The Edge
Function runs server-side (no CORS restriction applies), so it:
1. Reads the real `sites` table for lat/lon of all sites that have coordinates.
2. Fetches GDACS's live worldwide event list
   (`gdacsapi/api/events/geteventlist/SEARCH`).
3. Computes real haversine distance from each site to each event, keeps the nearest
   within 500km.
4. Writes one snapshot row per site to `gdacs_snapshots` (service-role client, bypasses
   RLS) and returns the same data as JSON.

**Verified live, twice:** once via direct `curl` (100 real GDACS events fetched, e.g. a
real Orange-level "Flood in India" event matched to Joshimath/Raini at ~295-310km), and
once through the actual UI in a browser -- see below.

**Frontend wiring:** added a new "Global disaster watch" card to the Explore-a-site
profile panel (`awareness/index.html`, `awareness/app.js`'s `checkGdacs()`/
`resetGdacsPanel()`), next to the existing Early Warning card. Deliberately a
manual "Check live now" button, not auto-fetch-on-site-select -- keeps GDACS calls
demo-controlled (a click judges can watch happen) instead of firing 10x automatically
every time someone browses sites. Panel resets on site switch. The card's own copy
states plainly *why* a backend was needed here (the CORS fact above), so it doubles as
the answer to "where's your backend" instead of just being a feature.

Browser-verified end to end: clicked "Check live now" for Dharali, got a real result
("Flood in India — 184.2km away, Orange alert, Type: FL") pulled live through the Edge
Function, written to the DB, rendered in under a few seconds. Confirmed panel resets to
idle on switching to Joshimath. Checked mobile viewport (375px) -- card lays out
correctly, no overflow. No new console errors (the only console 404s are pre-existing
missing before/after images, unrelated).

**Anon/publishable key is intentionally in client-side `app.js`** (`SUPABASE_URL`,
`SUPABASE_ANON_KEY`) -- this is the standard, safe way to call Supabase from a browser;
it only grants what RLS policies allow (public read on the 4 tables, nothing else). The
service-role key used inside the Edge Function to bypass RLS for writes is never sent to
the client -- it lives only in Supabase's server-side function environment.

**Not yet done / explicitly deferred:** the static `window.MODEL_DATA`/
`window.PROJECTION_DATA` that drive the rest of the page were NOT migrated to fetch from
the new REST API -- they're already real (sourced from the same `model_results.json`),
migrating them risked destabilizing a working, judge-ready page for marginal benefit
under time pressure. The backend's job here was to add one thing a static site
genuinely cannot do (the live GDACS call) and give the project a real, inspectable
database -- not to rebuild the whole page's data flow. If a judge asks "does the rest
of the page hit your database too," the honest answer is: the model numbers are baked
in from the same real training run that's also now in Postgres (`model_runs`/
`risk_predictions`), and the live disaster check is what actually round-trips through it.
(Section 26 below changed this for the risk card specifically -- see there.)

## 26. "It looks like an AIML subject model" -- two originality upgrades, kept honest

User feedback, twice: rated the project ~4/10 on originality and said plainly "thats
what the problem is" when told the algorithm itself (plain LogisticRegression on 7
features) is textbook, not novel. Also explicitly said: don't want it to look like a
classroom AIML assignment, it's a hackathon, the technical stack can be creative.

**Rejected approach, on purpose:** swapping in a "fancier" model (random forest,
XGBoost, a neural net) for its own sake. With only 10 real labeled sites, a more complex
model is LESS defensible, not more original -- it's overfitting bait on N=10 and any
judge who knows ML will say so immediately. The actual originality gap was never the
classifier; it was everything that should surround a small-N model and doesn't, in a
typical hackathon submission. Presented 4 options (Bayesian uncertainty, a
physics-informed feature, LLM text-evidence fusion, spatial risk propagation), user
delegated the choice ("u decide based on originality") -- picked the two that add real
methodological originality without weakening the "everything here is real" discipline
this whole project has held to:

**(a) Bootstrap confidence intervals (`ml/train_model.py`).** A single point probability
like "93% risk" overstates what a 10-site model can actually know -- genuine
overconfidence, and something a sharp judge would probe. Added non-parametric bootstrap:
resample the real sites with replacement (500 valid draws; draws with only one class
present can't fit logistic regression and are skipped -- 571 attempted for 500 valid in
the actual run), refit scaler+classifier on each resample, predict every real site from
that resampled model, take the 10th-90th percentile of the resulting distribution as an
honest per-site confidence interval. This is the statistically CORRECT thing to do given
N=10 -- not a novelty for its own sake -- and it produces a genuinely interesting result:
some sites are tight (dharali: 94-98%, malpa: 90-97%) and some are honestly very wide
(kedarnath: 17-99%!, auli_control: 19-94%, sundarbans/odisha_coast: mid-20s to mid-90s).
Exported as `bootstrap_uncertainty` (methodology + n_bootstrap) on the model run, and
`risk_ci_low`/`risk_ci_high`/`risk_std` per site in `risk_ranking`.

**(b) Independent evidence-confidence assessment (new, not derived from the trained
model).** For each of the 10 real sites, read the actual cited source text already
logged in `feature_table.csv`/`memory.md` (news outlets, government committee reports,
academic papers, IBTrACS-based checks, or this project's own verification notes) and
rated how well-corroborated the disaster label itself is -- High/Moderate-High/
Moderate/Low-Moderate/Low, each with a one-to-two sentence rationale grounded in what
the citation actually says (multiple independent sources vs. a single unverified
academic citation vs. an explicitly-flagged-as-unconfirmed control label, etc). This was
done by Claude directly reading the real citations already in the project -- NOT a live
third-party LLM API call from the browser, deliberately: shipping an external API key
client-side would be an actual security problem, and a live per-click call adds latency/
flakiness risk for a judge demo. What actually makes this a "second signal" rather than
decoration: it disagrees with the numeric confidence in genuinely interesting ways --
kedarnath has the WIDEST bootstrap CI (17-99%, the model itself is unsure) but HIGH
evidence confidence (2013 Uttarakhand floods are extremely well-documented public
record) -- two different systems catching two different kinds of uncertainty, not one
system pretending to be two.

**Schema:** new `evidence_assessments` table (site_id unique FK, evidence_confidence
check-constrained to the 5 levels, rationale, assessed_by defaulting to a string that
states plainly this was a manual Claude read of cited sources, not a live model call).
`risk_predictions` gained `risk_ci_low`/`risk_ci_high`/`risk_std` columns; `model_runs`
gained `bootstrap_uncertainty` jsonb. All public-read RLS, same pattern as sec 25.

**Frontend, and a real architectural choice:** unlike the rest of the page's data (still
static, per sec 25's deferral), these two new fields are deliberately NOT baked into a
static JS export -- `awareness/app.js` fetches both tables live from the Supabase REST
API on page load and merges them onto the existing site objects, re-rendering the open
profile once the fetch lands (`Promise.all` of two `supaGet()` calls near the top of the
file, using the same anon key already established for the GDACS feature -- moved the
`SUPABASE_URL`/`SUPABASE_ANON_KEY` consts to one shared location at the top of the file
instead of duplicating them, after a duplicate-`const` redeclaration bug briefly broke
the page). This means the page's core "Disaster risk prediction" card -- not a side
feature -- now genuinely reads from the live database. Rendered as two additions inside
the existing card (not a new top-level section, consistent with this project's repeated
"don't make it messy" steer): a `.risk-ci` line under the risk number, and an
`.evidence-check` block with a colored confidence badge + rationale, below the existing
drivers list.

**Verified in browser:** Dharali shows 96% (94-98% CI) with Moderate evidence confidence
(coordinates flagged unverified in project notes); Kedarnath shows 79% (17-99% CI, wide)
with High evidence confidence (major documented disaster) -- confirmed both signals
render correctly and independently, exactly the "two systems disagree usefully" story
intended. Checked mobile viewport (375px): both new blocks wrap and lay out cleanly, no
overflow. Detector run on both changed files afterward: zero new finding categories --
the only flags are the same pre-existing font-size/color/radius drift already pervasive
across this file before this session (confirmed by checking the flagged values already
appear on unrelated pre-existing lines), plus one pre-existing `.why-here-cited`
side-tab border already reviewed and accepted earlier in the project.

## 27. Human-attribution audit: the project's core narrative had a real hole, not just phrasing

User caught something real: "we are making a model which detects effect of humans in
disasters but all the ten places we choose are not real places where the humans are
actually making the problem. its senceable that way." Checked `feature_table.csv`
directly rather than trusting memory of earlier sessions -- confirmed exactly how far
this goes: of the 10 real sites, only **joshimath** has an actual cited human-causation
finding. `raini`, `kedarnath`, `wazri`, `dharali`, `malpa` have empty
`human_activity_notes` and natural triggers (rainfall, glacial/rock collapse) in their
`disaster_type`/citation. `sundarbans` and `odisha_coast` are cyclones, and this
project's OWN notes already said, before this session, "not a usable human-activity
signal" for both (sec 14/15). So the calculator's old copy -- "drag only the things
people can actually control: vegetation, construction" -- implied a human-causation
story the data backs at exactly 1 of 10 sites. A real gap, not a wording nitpick, and
the user was right to flag it before a judge did.

Presented three fixes: reword the overclaiming copy (fast), build an honest per-site
human-attribution audit reusing existing citations (fast, no new data), or go find and
pull real data for more genuinely human-caused disaster sites (slow, needs the team to
run the GEE pipeline again for new coordinates). User's answer -- "what ever you it
should show originality through ui ux" -- meant: do the fast honest fixes, AND make sure
the fix itself is visually original, not just another text disclaimer. Directly
continues the sec 26 originality thread: the ask was never "add a paragraph," it was
"show it well."

**What was built:**

1. **Copy fix** (`awareness/index.html` calculator lede): dropped "things people can
   actually control" framing; now says the model weighs vegetation/construction most
   heavily as predictors, and explicitly separates that from a causation claim, pointing
   to the audit below.

2. **Aggregate "human-attribution audit"** -- a dot-matrix visualization (`#attr-audit`
   in the Machine Noticed section, `renderAttributionAudit()` in `app.js`), deliberately
   placed in the REQUIRED 90-second story (not buried past the scope-divider) since it
   directly qualifies the page's headline finding. 10 dots, one per real site, four
   visually distinct treatments with zero reliance on color alone: solid fill
   (human-confirmed, 1), hollow outline (natural trigger, 5), diagonal-hatched (acute
   cyclone, 2), faint dashed (control, 2) -- a genuinely different visual motif from
   every other chart on this page (driver bars, rainfall bars, risk badges), chosen
   specifically because a proportional bar would have been less honest-feeling than "here
   are the actual 10 dots, judge for yourself." Big "1 of 10" stat, legend with real
   counts, and a caption stating plainly: "strongest predictor" and "human-caused" are
   different claims.

3. **Per-site "attribution spectrum"** -- a horizontal gradient-track bar with a
   positioned marker (`#attr-spectrum` inside the "Why here" card, `renderProfileWhy()`),
   replacing the old `CITED_CAUSES` object that only ever had a Joshimath entry and
   silently said nothing for the other 9 sites. Now every real disaster site gets an
   explicit marker position (natural-trigger end vs human-linked end) plus the same
   rationale text used in the aggregate audit -- so a reader drilling into any single
   site sees the same honest answer, not just the aggregate.

**Schema:** extended the existing `evidence_assessments` table (sec 26) rather than
creating a new one -- added `human_attribution` (check-constrained:
human_confirmed/natural_trigger/acute_natural/control) and `human_attribution_note`.
Same table now carries two independent AI-reasoned reads of the same citations: how
*reliable* the evidence is (sec 26's `evidence_confidence`), and what it actually
*attributes the disaster to* (this section's `human_attribution`) -- related but
distinct questions, both grounded in the same real source text, both fetched live in the
same `Promise.all` already wired in `app.js`.

**Real bug caught fixing this:** moving `SUPABASE_URL`/`SUPABASE_ANON_KEY` to a shared
top-of-file location (sec 26) had left a second, now-duplicate `const` declaration
further down from the original GDACS feature -- browser threw "Identifier already
declared," page fully broken. Fixed by deleting the duplicate and leaving a comment
pointing to the single declaration. Caught because a stale browser tab's console showed
the error persisting after the file was already fixed on disk -- same tab-cache artifact
noted earlier in this file (fetching the file via `javascript_tool` proved the on-disk
file was already correct); opening a fresh tab confirmed the real, fixed state. Don't
re-diagnose this pattern as a real regression if it recurs -- open a fresh tab first.

**Detector caught a real self-inflicted issue:** first draft used
`box-shadow: 0 0 12px rgba(...)` glow on the "human-confirmed" dot/marker to make it
stand out -- flagged as `[dark-glow]`, the exact "default cool AI-generated UI" tell the
detector exists to catch. Ironic given the whole point of this section was avoiding a
generic/derivative look. Fixed by dropping the glow entirely and relying on solid-fill
color contrast (plus a slightly larger marker for the spectrum-bar case) -- the
human/natural/acute/control distinction reads clearly without it. Zero new finding
categories after the fix.

**Verified in browser:** Kedarnath's spectrum marker sits at the natural-trigger end
with the correct rationale text: Joshimath's sits at the human-linked end with the glow
removed but still visually distinct via solid fill + size. Aggregate audit shows correct
counts (1+5+2+2=10) with working hover tooltips per dot (site name + category). Checked
mobile (375px): both new elements wrap cleanly, no overflow.

**Follow-up fix, same session:** user's next message, quoting the aggregate audit's own
copy back verbatim, was "this is showing negative impact of the system." Correct
read: not a request to remove the honesty (that would re-open the exact overclaiming
problem this section exists to fix), but a real problem with HOW it was presented. The
first version led with a giant colored "1" styled identically to the page's dramatic
reveal stats (`93%` risk score, `8.9 centimetres` hero number) -- so it read as a second,
competing headline stat undercutting the positive finding directly above it, a scoreboard
of failure rather than evidence of rigor. Fixed by changing the visual hierarchy, not the
substance: dropped the giant-number treatment entirely; now leads with a small kicker
("SELF-CHECK — WE AUDITED OUR OWN CLAIM") and a bold headline SENTENCE ("We only say
'human-caused' where we can cite it.") at the same weight/size as the finding-hero's
headline text, with "1 of 10" folded into supporting-paragraph prose instead of a
standalone stat. Same dot-matrix, same counts, same rationale -- only the framing
changed, from "look how limited we are" to "here's how we hold ourselves accountable."
General lesson for this project: when self-auditing content is true and belongs on the
page, the fix for it reading badly is almost never deletion -- it's whether the layout
makes it look like a confession or like a methodology. Detector re-run clean after the
change; mobile-checked again.

## 28. "How is this a planning tool" -- the calculator didn't recommend anything

User's next challenge, same session: "how is this a planning tool.... are you
mitigating the disaster, how is it helpful in disaster management before or after."
Answered honestly first, without changing anything, since the question deserved a real
answer before a fix: BEFORE is covered by the risk ranking (prioritization) and the
Chamoli-only early-warning threshold (sec 24); DURING by the live GDACS check (sec 25);
AFTER is not covered at all (the only "after" story is the model itself improving once
Dharali's real event became training data -- learning, not response/recovery support).
The live calculator's old copy -- "This is also a planning tool," "That's simulating a
mitigation decision" -- was the actual weak claim: dragging a slider and watching a
number move is exploration, not planning. A planning tool implies telling the user what
to prioritize; the calculator didn't recommend anything, it just displayed.

**Fix: made the calculator actually recommend something, from real model math it
already had client-side.** Added `renderCalcRecommendation()` in `awareness/app.js`,
called every time `updateCalcDisplay()` runs. For the two controllable levers
(vegetation trend, construction trend), computes the modeled risk-probability drop from
nudging EACH ONE by exactly one standard deviation (`MP.scaler_scale`, the real fitted
value from `ml/train_model.py` -- not an arbitrary guess) in its risk-reducing
direction, holding everything else at the current slider state. This is a fair,
model-native unit for comparing two differently-scaled features (matching why
standardization exists in the first place), not a cost or feasibility comparison -- the
UI says so explicitly. Renders as two horizontal bars (points of risk reduction) plus a
plain-language verdict naming which lever wins and by what ratio, recomputed live on
every drag.

**Real, checked finding, not asserted:** tested this at default (sample-mean) settings,
at the real Joshimath preset, and at an extreme hand-set scenario (vegetation maxed
healthy, construction maxed unhealthy) -- vegetation restoration won every time (ratios
7.8x-12.7x), because the real fitted coefficient magnitude for `ndvi_trend_slope`
(-1.081) is about 8x larger than `ndbi_trend_slope` (+0.128) even before the sigmoid's
nonlinearity amplifies it further. So this feature will not flip which lever "wins" in
practice across realistic inputs -- worth knowing so nobody claims live in front of
judges that it can. What DOES genuinely vary per scenario is the magnitude and ratio
(18.8pt/1.7pt at the default vs 10.9pt/0.9pt at Joshimath vs 15.6pt/3.2pt at the extreme
test) -- real, non-trivial information for prioritization even when the ranked order is
stable, not a lookup-table gimmick.

Also reworded the section's own copy to match what it actually does: h2 changed from
"This is also a planning tool" to "Not every fix helps equally, here"; lede now
describes the recommendation as "a real, per-site priority signal, not a full
mitigation plan with costs or timelines attached" -- earns the claim instead of
asserting it.

**Real mobile bug caught testing this, not a cosmetic one:** the recommendation bars'
fixed-width label (130px) left almost no room for the track at 375px width once the
longer labels ("Vegetation restoration") wrapped to two lines -- the bar fill was
present but visually imperceptible, a real functional regression, not just untidy
spacing. Fixed with a `@media (max-width: 640px)` rule (added to the file's one existing
mobile breakpoint) that stacks label above track+value instead of shrinking the track to
near-zero. Verified fixed with a real screenshot at 375px after the fix, not just
reasoning about the CSS.

## 29. GDACS panel: add direction/location, strip internal-facing narration

User feedback on the "Global disaster watch" card (sec 25): "you should say from which
direction near where... you don't need to add unnecessary content which we don't
require user to see... its between us... user is third party." Two distinct asks, both
acted on in `awareness/app.js` and `index.html`:

**1. Direction, computed, not guessed.** Added `compassDirection()` -- real bearing math
(atan2 on the site's and event's actual lat/lon, both already returned by the
`fetch-gdacs` Edge Function) converted to 8-point compass (N/NE/E/SE/S/SW/W/NW). Result
line changed from "184.2km away" to "184.2km W". Also surfaces the real GDACS `country`
field from the event's raw properties for "near where" -- deliberately did NOT add a
town/city-level lookup (would need a geocoding service GDACS doesn't provide; the
project's real API data only goes to country granularity, confirmed by inspecting the
raw event payload). Deduped: GDACS often names events "[Type] in [Country]" (e.g.
"Flood in India"), so the country suffix only appends when it isn't already in the event
name -- checked live for both cases (Dharali's "Flood in India" -> no repeat; Odisha
coast's "Tropical Cyclone ONE-25" -> ", India" correctly appended).

**2. Cut the internal narration.** The card previously explained, to the end viewer, WHY
the team built a backend (the CORS finding, "written to our database just now",
"calling our backend, which is calling GDACS, right now..."). That reasoning belongs in
the team's own head for defending the architecture in Q&A (already logged in sec 25),
not printed on a page a judge/third party reads -- it read as the team narrating its own
implementation choices instead of presenting information. Trimmed: the `.backend-note`
now states only what GDACS is and what the check does (one sentence, no CORS backstory);
loading state now says "Checking GDACS now…" instead of "Calling our backend, which is
calling GDACS, right now…"; the result meta line dropped "against N events worldwide,
written to our database just now" down to just the checked timestamp. General principle
for this project going forward: architecture justifications are for us to defend
verbally, not to print for the viewer -- the page should say what's true, not narrate
how it was built.

Verified live for both the "hit" case (Dharali, Odisha coast) and confirmed no dev-facing
text remains. Detector clean after the change.

## 31. Cut methodology/self-audit content out of the live tool entirely (not just reframed)

User's message: "we don't need to tell everyone that what, how, and why we are training
a model.... user just want to use it they don't want to know what it is training.......
thats y ppt exist." A materially different ask from every prior round this session
(secs 26-30 were all about reframing self-audit content to read better) -- this one
says the content doesn't belong in the live tool at all, full stop. That's a big,
hard-to-reverse cut across a lot of real work built earlier this session, so asked one
scoped clarifying question before touching anything (AskUserQuestion: remove entirely
vs. keep-but-demote to a secondary area) rather than guessing. User picked: remove
entirely.

**Removed completely from `awareness/index.html` / `app.js`:**
- "Machine Noticed" section in full -- the `finding-hero` feature-importance reveal
  (`finding-num`/`finding-label`/`finding-toggle`/`finding-detail`) AND the "Self-check"
  human-attribution dot-matrix audit (sec 27) that lived inside it.
- "Stress Test" / cross-terrain validation section in full (sec 30's proof-row cards).
- The per-site human-attribution spectrum bar (sec 27) inside "Why here".
- The bootstrap confidence interval and independent evidence-confidence check (sec 26)
  inside "Disaster risk prediction".
- The scope-divider ("That's the whole story. Everything below is optional depth...")
  -- its "required story vs. optional depth" framing stopped making sense once the
  content on both sides of the divide changed this much.
- The `risk-explain` reassurance line ("This is our trained model's actual output...
  not illustrative") -- a self-justifying aside, not functional info.
- The calculator's disclaimer explaining HOW the math works (standardize / coefficients
  / sigmoid) -- kept the calculator itself (it's a real decision-support feature, not
  methodology), cut the internals explanation.

**Also removed, as dead code once their UI was gone:** the `Promise.all`/`supaGet` live
fetch of `risk_predictions` (CI fields) and `evidence_assessments` (confidence +
attribution) that fed all of the above -- nothing on the page displays those fields
anymore, so the fetch was pure overhead. `renderAttributionAudit()`,
`ATTRIBUTION_SPECTRUM`, `ATTR_LABELS`, `ATTR_ORDER`, `FEATURE_LABELS_PLAIN`, and the
cross-terrain proof-row block all deleted outright, plus every now-orphaned CSS rule
(`.finding-*`, `.fi-*`, `.attr-*`, `.scope-divider*`, `.risk-ci*`, `.evidence-*`,
`.proof-*`, `.risk-explain`, the old `.calc-disclaimer`). Verified zero dangling
references afterward with a `grep` sweep across both files before testing -- clean.

**Reordered the page to match the actual product flow** the user described (site picker
-> risk score -> early warning -> live disaster watch -> calculator -> risk list): moved
the "Live Calculator" section (renamed kicker "Try a scenario") to after "Explore a
Site" instead of before it, so simulating a scenario comes after seeing a real site's
risk, not before.

**Rewrote the close section**, which had directly referenced the now-deleted
cross-terrain proof ("held up even on places the model had never seen") -- would have
been a dangling claim otherwise. New version is a plain closing CTA pointing to
`dashboard/index.html` and `demo/index.html` (the pre-existing separate technical pages)
for anyone who wants the methodology -- this is the natural home for what got cut here,
not a new page that needs building. The removed content itself was NOT deleted from the
codebase's history/memory -- it's fully described in secs 26/27/30 above and the
Supabase tables (`risk_predictions.risk_ci_*`, `evidence_assessments`) are untouched and
still live, so the team can rebuild a "how it works" page from real data later, or use
it directly in the PPT/Q&A defense, without redoing the underlying work.

**Verified in browser:** full page text dump confirms the lean flow end to end (hero ->
site picker/profile with why-here, risk score, before/after, projection, live weather +
early warning, GDACS -> calculator -> risk list -> close), no Machine Noticed/stress-test/
audit content anywhere. GDACS live check still works (confirmed "Flood in India --
184.2km W" for Dharali; took a few seconds longer than usual, an Edge Function cold
start, not a regression). Calculator recommendation still works unchanged. Mobile
(375px) checked. Detector clean, zero new findings.

## 30. Cross-terrain section: cut the quiz-show framing, kept the real proof

User, quoting the section verbatim: "Is this real, or did it get lucky... these are not
needed it makes it look more like ppt." Checked every kicker/headline on the page
(`grep` across `index.html`) before touching anything -- confirmed this was the one
outlier. Every other section header on the page ("What the model found, on its own,"
"Prove it yourself, and use it," "Now at any one place," "Right now," "We're not
fortune tellers") is already a plain, declarative statement; only this section's kicker
was phrased as a rhetorical quiz-show question aimed at an audience, which is exactly
the PPT-narrator tell the user has flagged multiple times before in this session.

Reworded, content unchanged: kicker "Is this real, or did it get lucky" ->
"Cross-terrain validation" (states what the section IS, not a rhetorical setup);
headline "We hid the coastal disasters from it." -> "Trained on mountains only. Tested
on the coast." (states what was actually done, same information, no reveal framing);
lede trimmed to drop the "if it had just memorized mountains, it should fail completely"
narrative aside, keeping only the factual setup. Did NOT touch the actual proof cards
below (`renderProofRow` in `app.js`) -- their per-site pass/fail copy was already plain
and factual, not part of what was flagged. Verified in browser: real cross-terrain
results (Sundarbans hit, Odisha coast hit, etc.) render unchanged under the new,
non-rhetorical header. Detector clean.

## 32. Dataset expansion to 15 real sites + fixed the terrain encoding, not just added data

Two connected pieces of work. First, added 5 new real, WebSearch-verified sites via the
established pipeline (WebSearch facts -> `gee_pull_site.py`/`gee_pull_lst.py`
(Earth Engine) -> `nasa_power.py` (rainfall anomaly, anchored on the real disaster date)
-> `compute_gee_site()` for the exact same trend-slope methodology as the original 10
-> append to `feature_table.csv`): `chennai` (Dec 2023 cyclone-induced flooding -- added
specifically because the jury is Chennai-based and can locally sanity-check the claim),
`wayanad` (July 2024 Chooralmala-Mundakkai landslide), `jakhau` (Cyclone Biparjoy 2023 --
landfall wind/pressure left blank, not in `cyclone_landfall_ibtracs.csv`), `guna` (2025
Kalora Dam breach flood, MP), `silchar` (2022 embankment-breach flood, Assam).

Guna and Silchar are genuinely inland plains/riverine, not coastal -- mislabeling them
coastal for schema convenience was rejected; added a real third `terrain_type` value,
`"plains"`, instead. That surfaced a real structural bug: the model's only terrain
signal was a single binary `terrain_hill` column, which cannot distinguish coastal from
plains (both were "not hill"). User chose, via AskUserQuestion, "fix the model first"
before adding any more new-terrain sites.

Fix: replaced `terrain_hill` with proper one-hot encoding (`terrain_is_coastal`,
`terrain_is_plains`; hill is the implicit baseline) in `ml/train_model.py` --
`CORE_FEATURE_COLS`, `prep()`, the preview-print column slicing, and the cross-terrain
ablation's `is_hill` mask all updated. Caught and fixed a real bug in this fix before
running it: the cross-terrain JSON-export block still referenced the pre-rename
`coastal` variable (renamed to `not_hill` earlier in the same edit) -- would have been a
`NameError` on the next run; fixed before executing, not after a crash.

Ran clean on 15 real sites. Honest before/after: LOOCV unchanged at 11/15 = 73%. The
cross-terrain holdout finding (secs on the "always predict disaster" ties-baseline
result) is now MORE robust, not less -- at N=7 non-hill sites (5 coastal + 2 plains) the
model predicts disaster for all 7, actual is 6/7 (misses `coastal_control_tbd`, the one
true negative), which still exactly ties a naive "always predict 1" baseline. This is
now a materially harder-to-dismiss version of the same finding (was N=3 originally, then
N=7) BECAUSE the terrain fix is real this time -- `terrain_is_coastal` and
`terrain_is_plains` now carry genuinely different, non-zero coefficients
(-0.088 and +0.146) instead of being unable to separate the two categories at all, so
the tie isn't an artifact of a broken feature -- the model can now tell coastal and
plains apart and still can't beat naive on this holdout. Jakhau stays low-confidence
(bootstrap CI [0.13, 0.94], spanning both sides of 0.5).

**Still pending, flagged but not yet actioned:** propagate these updated 15-site numbers
(was "10 sites / 70% LOOCV") to Supabase tables, `dashboard/data.js`, and the PPT deck's
slide content/speaker notes -- all four still reflect the old 10-site figures as of this
entry. Next step per the user's own sequencing is real sites from genuinely new terrain
types not yet represented (desert/arid Rajasthan; the 2023 South Lhonak Lake GLOF,
Sikkim, for glacial) -- deliberately deferred until after this fix, which is now done.

## 33. Reliability audit found 0% specificity; two attempted fixes, neither closed it

User pushed hard on "is it reliable" and "what if it tells every single one at risk."
Ran the real diagnostic on the (then) 15-site LOOCV output: confusion matrix was
TP=11 FN=2 FP=2 TN=0 -- the model has NEVER, across any real held-out test in this
project, correctly identified a genuinely safe site. Worse, the two known-safe sites
(`auli_control`, `coastal_control_tbd`) scored 0.96-0.97 -- the HIGHEST risk scores in
the entire dataset, higher than 11 of 13 real disasters. A naive "always predict
disaster" baseline beats the model on raw accuracy (87% vs 73% at N=15).

**Attempted fix #1 (rejected after testing): `class_weight='balanced'`.** Tested before
touching the real pipeline. Made things WORSE (67% vs 73% accuracy) and still didn't fix
specificity -- the two negatives still scored 0.88/0.90, still wrong. Confirmed this is a
data-scarcity problem, not a calibration problem: in LOOCV, holding out either negative
site leaves only 1 remaining negative in training, which no reweighting can fix.

**Attempted fix #2: added `jaisalmer`** (real site, Jaisalmer city, Rajasthan) as the
first desert/arid terrain example and a 3rd real negative control -- WebSearch-verified
no major disaster in the 2019-2023 window (checked town-level, not just district-level:
Jaisalmer district had +69%/+96% above-normal monsoon rainfall in 2021/2022 per Down To
Earth, but no recorded town disaster resulted). Real GEE + NASA POWER pull, added
`terrain_is_desert` as a 3rd one-hot terrain dummy in `train_model.py`.

**Result: looked fixed, wasn't.** The in-sample "risk ranking" table showed Jaisalmer
correctly low (0.13) -- but that's the model scoring data it was trained on. The honest
LOOCV number (Jaisalmer held OUT of its own training) was 0.72 -- still wrong. Mechanism:
with N=1 desert example, holding it out leaves `terrain_is_desert` constant-zero in the
remaining training data, so the model has zero signal to generalize from -- structurally
the same "mathematically inert" effect already documented for the cross-terrain
ablation, just showing up in ordinary LOOCV too. Overall accuracy at N=16 actually
DROPPED to 69% (naive baseline 81%). Caught and reported this gap between in-sample and
held-out numbers explicitly rather than reporting the flattering in-sample figure --
matches this project's standing rule of leading with the honest number even when it's
worse.

**User's next call: "make machine only learn hill and coastal only."** Scoped
`train_model.py` to `IN_SCOPE_TERRAIN_TYPES = ["hill", "coastal"]` -- `load_real_rows()`
now filters `real` to those two terrain types (plains/desert real sites stay in
`feature_table.csv`, just excluded from training); simplified back to a single
`terrain_is_coastal` dummy (N-1 for N=2 categories) since plains/desert are out of scope;
added an explicit in-scope/out-of-scope status breakdown to the printed report so
"16 real sites" doesn't silently mean "13 sites actually used." Re-ran clean at N=13
(8 hill + 5 coastal).

**Honest result: this did NOT fix specificity either.** TP=9 FN=2 FP=2 TN=0 -- still
0/2 on the two negatives, still both misclassified. Accuracy 69% (9/13), naive baseline
85% (11/13) -- basically the same relative gap as before scoping. This is the important
confirmation: the root cause was never "too many terrain categories diluting the
signal" -- it's "1 negative example per category is fundamentally unvalidatable by
LOOCV," and that's exactly as true within just hill+coastal as it was across all four
terrain types. Scoping down simplified the model (useful on its own) but is not, by
itself, the fix. The only fix that has any real chance: 2+ more negative-control sites
in hill and/or coastal specifically (not new terrain types) before this can be honestly
claimed to work.

## 34. Added 2 more real hill/coastal controls -- specificity STILL 0%; found the real reason

User said "fix it and test... right now." Added the two negative controls the sec-33
conclusion called for, both real, both WebSearch-verified against the 2019-2023 window
used everywhere else in this project:

- **`ranikhet`** (hill, Almora district) -- only documented recent-era event is a 2004
  cloudburst (1 casualty), outside the study window; same "no major event in window, not
  zero risk ever" standard as `auli_control`.
- **`kollam`** (coastal, Kerala) -- verified with an actual downloaded NOAA IBTrACS
  North Indian Ocean track file (`ibtracs.NI.list.v04r01.csv`, not just the 2-row extract
  already in the repo): nearest NEWDELHI-graded Severe-or-stronger (>=48kt) cyclone track
  point 2019-2023 was NIVAR (2020) at 509km -- 3x farther than `coastal_control_tbd`'s
  157km. Also confirmed via news search: Kollam was NOT among Kerala's worst-hit
  districts in 2018 (1,503 ha flooded vs Alappuzha's 21,799 ha) or 2019 (yellow alert,
  the lowest tier, vs red alerts up north).

Both got the full real pipeline (GEE NDVI/NDBI/DEM/LST + NASA POWER rainfall, anchored
2023-01-01 same as the other controls) and were appended to `feature_table.csv`.
Re-ran at N=15 (9 hill + 6 coastal, 4 total negatives now).

**Still 0/4 specificity.** TP=10 FN=1 FP=4 TN=0, accuracy 67% (10/15) vs naive baseline
73% (11/15). Even `ranikhet`, the most carefully-vetted control, scored 0.75 (wrong) when
honestly held out.

**This time, instead of just re-testing, diagnosed WHY with the raw feature values**
(printed the full `ndvi_trend_slope`/`ndbi_trend_slope`/`mean_slope_degrees`/
`rainfall_anomaly_pct` table for all 15 in-scope sites, sorted by label). Finding: the
4 negative controls' feature values sit INSIDE the range spanned by the disaster sites,
on every feature that matters -- e.g. rainfall_anomaly_pct ranges from -78% to +180%
across disaster sites (because Joshimath/Raini/Kedarnath are ice-avalanche/subsidence,
not rainfall-driven, while Wazri/Dharali/Wayanad are), so a control's rainfall value can
never fall clearly outside that range no matter which real safe site gets picked. This
is a real structural limit, not a data-volume problem: `disaster_occurred=1` currently
lumps landslide, cyclone, subsidence, ice-avalanche, and dam-breach into one label, and
asks 6 generic environmental features to separate all of them from "safe" at once.

**User's hypothesis: human pressure/activity is the confound** -- "places under high
human pressure are moderately[-to-never] affected." Tested it directly and honestly
rather than assuming it: computed real mean NDBI (built-up level, not just its trend --
this didn't exist as a feature before) for all 15 in-scope sites from the Sentinel-2
timeseries already on disk, no new pulls needed. Added `ndbi_mean` as a new column to
`feature_table.csv` (kept, real data) and tried it as a 7th model feature.

**Result: made things WORSE, not better** -- LOOCV dropped further, 67% -> 53%, and
specificity stayed exactly 0%. Reverted it as a training feature (comment in
`train_model.py` explains why, column stays in the CSV for later). The real pattern,
from the raw numbers: the hypothesis is TRUE for hill sites (`auli_control`/`ranikhet`,
the more built-up/managed hill towns, score lower than the remote disaster sites
`kedarnath`/`wayanad`/`raini`) but FALSE for coastal sites (`chennai` and `jakhau`, the
two most built-up coastal sites in the whole dataset, are both real disasters -- cyclone
risk didn't care how developed the site was). One linear coefficient can't hold opposite
signs for two terrain types simultaneously, so adding it as a single global feature just
added noise on top of a real, terrain-specific effect.

**Where this leaves the project, honestly:** four real fix attempts (class-weighting,
a desert control, hill+coastal scoping, two more real controls) plus one real hypothesis
test (human-pressure/NDBI) have ALL failed to get specificity above 0%, and the last one
now explains a plausible root cause -- the label conflates too many distinct disaster
mechanisms for one generic feature set to separate from "safe." Recall stays genuinely
strong (85-91% across every real config tested). Two honest paths from here, put to the
user and awaiting their call: (1) reframe the live claim as a disaster-precursor
detector, not a safe/unsafe classifier, since the data doesn't support the second claim
no matter how it's tuned; or (2) split the model by disaster mechanism (e.g. a
rainfall/slope model for landslides, separate from a cyclone-driven coastal model) since
mixing mechanisms may be the actual reason one feature set can't discriminate -- a real
redesign, not a quick patch.

## 35. First non-zero specificity all session -- mechanism-scoped rainfall-landslide model

User picked option (2) from sec 34's menu, framed as a quick test first ("ok do it")
before any commitment. Tested mechanism-narrowing as a standalone diagnostic (not yet
touching `train_model.py`): scope to ONLY rainfall/cloudburst-triggered hill landslide
sites -- `wazri`, `dharali`, `malpa`, `wayanad`, `kedarnath` -- dropping `joshimath`
(land_subsidence, wrong mechanism) and the coastal/cyclone sites (also wrong mechanism,
already covered live by GDACS elsewhere in the product) entirely from this claim. Plus
the 2 real hill negatives (`auli_control`, `ranikhet`).

**At N=7: LOOCV specificity = 1/2 = 50%.** First non-zero specificity in this entire
project, across every config tried in secs 32-34. `ranikhet` correctly classified safe
(0.43) when honestly held out -- the first time any real negative site has EVER been
correctly classified under genuine LOOCV in this project. `auli_control` still wrong
(0.67) -- reported honestly, not hidden. Accuracy still tied naive (5/7 both) at this N.

User's response, given the small N: "if you want and think more value of n can make or
give good result its always welcomed" -- explicit permission to grow this specific
scope, not carte blanche to keep guessing broadly. Found and added 2 more real,
WebSearch-verified rainfall-triggered landslide sites matching this exact mechanism:

- **`pettimudi`** (Idukki, Kerala, Western Ghats) -- 6 Aug 2020, 616mm rain in one day,
  66-70 killed, peer-reviewed in *Landslides* journal + NDRF records. Real geographic
  diversity (Western Ghats, not Himalaya) within the same physical mechanism.
- **`kinnaur`** (Nigulsari, Himachal Pradesh) -- 11 Aug 2021, rainfall-triggered
  rockslide hit a highway bus, 25+ killed, exact date cross-checked against 3 independent
  news sources (Tribune, Deccan Herald, Business Standard).

Full real pipeline for both (GEE NDVI/NDBI/DEM/LST, NASA POWER rainfall anchored on each
site's real disaster date -- both showed +91%/+93% rainfall anomaly, consistent with
their documented triggers). Re-ran at N=9.

**Result held and improved, not just noise from a lucky small draw:** specificity still
1/2 = 50% (same site, `ranikhet`, correct again against 2 more competing disaster
examples); recall improved 80%->85.7%; accuracy improved 71.4%->77.8% (still ties naive
exactly, 7/9 both). N=9 now clears the project's own stated floor (`MIN_SITES_TO_TRAIN
= 8`) for the first time with a config that also has non-zero specificity.

**User's call on scope: "keep it at least that much validated"** -- not a request to
make this the sole official model (that would mean narrowing the whole product's ML
claim from multi-hazard to rainfall-landslide-only, a real decision still open). Instead
formalized it as a proper second function in `train_model.py`,
`run_rainfall_landslide_mechanism_model()`, called from `main()` alongside the existing
broader hill+coastal model (unchanged) -- not a throwaway inline diagnostic script this
time, so the result is reproducible by anyone re-running `python3 ml/train_model.py`.
Exported under a new `mechanism_scoped_rainfall_landslide` key in `model_results.json`,
clearly separate from the main model's keys, with an honest `description` field stating
explicitly that this is "first validated signal, not solved" and still misses one of two
negatives. `MECHANISM_FEATURE_COLS`/`RAINFALL_LANDSLIDE_DISASTER_TYPES`/
`MIN_SITES_MECHANISM` added as module-level constants; the function guards on
`MIN_SITES_MECHANISM` the same way `main()` guards on `MIN_SITES_TO_TRAIN`, so it will
cleanly say "not enough sites" instead of training on too few if this scope ever loses
sites. Verified end-to-end: `python3 ml/train_model.py` runs both models back to back
without error, main model's own numbers unaffected by the new function's presence.

**Still open, not yet decided:** whether this narrower mechanism claim ever REPLACES the
broader multi-hazard claim as the product's primary pitch (PPT/dashboard), or stays a
secondary, more-defensible result sitting alongside the weaker broad one. Left as two
live, both-real numbers for the team to choose between, not resolved unilaterally.

## 36. Tried the same mechanism-scoping trick for coastal/cyclone -- it genuinely failed

User asked "what abt chennai?" after sec 35 -- Chennai is coastal/cyclone, so it isn't in
the new rainfall-landslide model at all, even though it was added specifically because
"jury would be able to analyse as we are in chennai" (a local-verification argument).
Offered two options: keep Chennai in the broader (weaker) story, or try the same
mechanism-narrowing trick for coastal/cyclone specifically. User picked "2".

**Cheap check first, before pulling any new data** (same discipline as every other test
this session): scoped to cyclone-only coastal sites already in the table --
`sundarbans`, `odisha_coast`, `chennai`, `jakhau` (all real cyclone/cyclone-induced-
flooding) + `coastal_control_tbd`, `kollam` (negatives). N=6.

**Catastrophic at N=6: LOOCV 1/6 = 17%, far WORSE than naive (67%).** Real disasters
predicted low, real negatives predicted high -- inverted from the usual failure mode.
Diagnosed why before concluding anything: 6 features vs 5 training points per LOO fold
is mathematically underdetermined (more parameters than data), so this result alone
doesn't prove the mechanism can't work -- it proves N=6 is too small to know yet, same
floor problem as the landslide case had at N=6-7.

**Added 2 more real, WebSearch-verified cyclone landfalls to test properly at N=8:**

- **`visakhapatnam`** -- Cyclone Hudhud, VSCS, landfall 2014-10-12 near Vizag, 170-180
  km/h winds, 950mb, confirmed via IMD RSMC New Delhi's own cyclone report + ReliefWeb.
  Predates Sentinel-2 (launched 2015) -- NDVI/NDBI/slope use the same 2019-2023
  current-baseline convention already established for `kedarnath` (2013) and `malpa`
  (1998); only rainfall is anchored on the real 2014 landfall date.
- **`nagapattinam`** -- Cyclone Gaja, VSCS, landfall 2018-11-16 between Nagapattinam and
  Vedaranyam, 33+ killed, 82,000 evacuated, confirmed via ReliefWeb/NASA hurricane
  blog/Deccan Herald. Initial coordinates (10.79, 79.88) returned 0 LST observations --
  same water-point failure mode already seen and fixed for `odisha_coast` -- corrected
  to the real town center (10.7672, 79.8449) and re-pulled clean (179 obs) before
  proceeding, not silently left broken.

**Result at N=8: improved but genuinely did NOT replicate the landslide finding.**
Accuracy 17%->50% (still well below naive's 75%), recall 25%->66.7%, but
**specificity stayed exactly 0%** -- neither negative control was ever correctly
cleared, at any N tried for this mechanism. `visakhapatnam` (Cyclone Hudhud, one of the
most severe, unambiguous cyclone disasters in the whole dataset) scored a confident
WRONG at probability 0.00.

**Conclusion, and why this is a different kind of result from the landslide one:**
growing N stabilized the wild N=6 result but did not produce real separation, unlike
landslide where specificity moved off 0% and held as N grew. Real, physically-grounded
reason: NDVI/slope/rainfall-trend features are causally linked to landslide risk, but
cyclone risk is driven by storm track and intensity -- none of which these 6 land-
surface features capture at all. More coastal sites of the same kind are unlikely to
fix this; the feature set itself is mismatched to this mechanism, not merely
under-sampled. **Did NOT add this as a secondary model in `train_model.py`** (unlike
sec 35's landslide model) -- committing a non-working result next to a working one
would misrepresent it. `visakhapatnam`/`nagapattinam` stay in `feature_table.csv` as
real data (they still contribute to the broader hill+coastal model), just not exported
as a validated "coastal risk model."

**Chennai's status, resolved:** stays in the broader multi-hazard model only (correctly
predicted there, 0.80 probability, real disaster caught under LOOCV) -- not part of any
validated specificity claim. This negative result is itself now real evidence (not just
prior intuition) for the product's existing design choice of live GDACS cyclone
monitoring over a static land-feature classifier for this specific mechanism.

## 37. Real before/after satellite imagery for all 22 sites -- and why CLOUDY_PIXEL_PERCENTAGE lied

`ml/gee_pull_thumbnail.py` existed but had never been run (no GEE credentials when it was
written). With real credentials confirmed working this session, pulled real Sentinel-2
before/after thumbnails for all 22 real sites (`dashboard/images/`), season-matched
where possible (before = same calendar month, 1yr before disaster; after = ~45 days
post) to avoid a seasonal-greenness confound flagged on the very first Dharali pull.
Sites whose disaster predates Sentinel-2 (kedarnath 2013, malpa 1998, visakhapatnam
2014) use a 2016-vs-2023 long-term comparison instead, since no real "before" imagery
exists for those events -- documented as `long_term_no_real_before` in each site's
`_thumbnail_meta.json`.

Also fixed two real, separate bugs surfaced by this: (1) the awareness page's before/
after slider component already existed and needed zero code changes, just the files
appearing at the expected path; (2) the calculator's terrain feature was still keyed on
the pre-one-hot-fix name `terrain_hill` throughout `app.js` (driver labels, the
calculator's Hill/Coastal toggle, preset-loading) -- the toggle silently did nothing
(always used the sample mean, never the clicked value) since `terrain_hill` isn't in
`MP.feature_cols` anymore, only `terrain_is_coastal` is. Fixed all references; verified
live the toggle now actually changes the prediction (78% hill vs 86% coastal for the
default site).

**User then reported real problems in specific images, one round at a time, and each
round found MORE real problems than the one they flagged** -- the recurring lesson:
`CLOUDY_PIXEL_PERCENTAGE` (the field used to pick "least cloudy in window") does NOT
reliably indicate a usable image. Three separate failure modes it misses entirely:
1. **Thin haze/cirrus** -- visually hazy across the whole frame despite a "low" cloud
   score (dharali before was 11.7% reported but visually almost unreadable).
2. **Seasonal snow cover at high altitude** -- bright washed-out white, not classified
   as "cloud" by the metric at all (kedarnath ~3678m, raini ~3419m; a "before/after" pair
   picked near the actual disaster date can land deep in winter even 9+ months later).
3. **Satellite swath gaps (no-data black bands)** -- the metric only measures cloud over
   pixels that HAVE data; it says nothing about whether the requested 1.8km region is
   even fully covered by the image tile. Hit `kinnaur_after`, then `odisha_coast_after`
   separately (this one WAS missed initially -- only checked `odisha_coast`'s `before`
   after the user's first report, not realizing `after` had the identical problem, then
   the user reported it again ("size difference") before it got caught).

**Fix, `pull_best_covering_image()`** (now in `fix_snow_haze_thumbnails.py` in the
scratchpad, not yet promoted into `ml/`): instead of accepting the single least-cloudy
image via `.first()`, pulls the top-N (8-15) least-cloudy candidates and checks each
one's actual footprint geometry with `.contains(region)` before accepting -- rejects
swath-gap images even at 0% reported cloud. For snow, shifted target months to
post-monsoon/pre-winter (Sept-Nov, and even that wasn't early enough for kedarnath's
elevation -- had to narrow to September specifically). For the "after" side, always
floored the search at the real disaster date (`ee.Date(floor_date)`, not a symmetric
window) after one real near-miss: an early wide-window retry for `sundarbans_after`
picked an image from 2020-04-06 -- BEFORE the actual 2020-05-20 cyclone -- which would
have mislabeled a pre-disaster image as "after." Caught and fixed before it reached the
live site, but it's the reason every subsequent "after" refetch uses a hard floor, not
just a wider symmetric window.

**Process lesson worth keeping**: after the user's first report (5 sites), proactively
re-checked visually similar sites (other high-altitude Himalayan disaster sites: wazri,
joshimath, malpa) rather than waiting for those to be reported too -- correctly clean.
But did NOT proactively check the *paired* image (the other half of before/after) on
sites already touched, which is exactly how the `odisha_coast_after` and `raini_after`
misses happened -- both were the untouched half of a pair where the OTHER half had
already been flagged and fixed. Next time: when fixing one half of a before/after pair
for a real visual defect, check the other half too before calling it done, not just the
half that was reported.

Every fix re-ran `dashboard/build_data.py` to keep `data.js` in sync (harmless/no-op for
images specifically, but avoids the same kind of staleness that hit sec on the 10-site
stale dashboard earlier in this project).

## 38. guna/silchar/jaisalmer were invisible on the live site; made them visible, honestly

User noticed these 3 real, out-of-scope (plains/desert) sites had no working calculator
and asked what to do. They had complete real data (GEE + NASA POWER pulls, satellite
images) but were entirely absent from the live page -- not in the site picker, no
profile, nothing -- because `allSites` was `D.risk_ranking` directly, which only
contains sites `train_model.py`'s `IN_SCOPE_TERRAIN_TYPES` (hill/coastal) actually
trains on.

**Decision: show them with their real data, but be explicit no risk score exists** --
not hide them (real data shouldn't disappear) and not fake a score by running them
through the hill/coastal model anyway (that model was never validated on plains/desert
terrain; scoring them would be exactly the overclaiming this project has spent this
whole session catching and fixing).

**Real changes across three files:**
- `ml/train_model.py`: new `out_of_scope_real_sites` export -- same real per-site fields
  (NDVI/NDBI/slope/rainfall/LST trends, human_activity_notes, source_citation) as
  `risk_ranking`, but NO `predicted_risk_prob`/`top_drivers`/CI fields at all (not even
  null ones) so the UI can't accidentally treat a missing score as a real one.
- `awareness/app.js`: `allSites` now merges `risk_ranking` (`hasModel: true`) with
  `out_of_scope_real_sites` (`hasModel: false`). `renderProfileRisk` shows an honest
  "No trained risk score for this terrain yet" card with the real reason, instead of
  computing `undefined * 100 = NaN%`. The calculator shows a matching
  "Calculator not available for X" note (new `showCalcUnavailable()`) instead of
  guessing, and leaves the last real site's values on screen rather than blanking or
  crashing. The bottom "risk list" (a RANKING) now explicitly filters to `hasModel`
  sites only -- unscored sites don't belong in a ranking. The default-site selection on
  load was also guarded the same way (`modeledSites`), so an out-of-scope site can never
  become the default and immediately show broken state.

**Follow-up bug caught by the user asking about the SAME projection card**: `awareness/
projection-data.js` (from `ml/build_projection_data.py`) was hardcoded to only the
original 10 sites -- none of the 12 sites added this session (chennai, wayanad, jakhau,
ranikhet, kollam, pettimudi, kinnaur, visakhapatnam, nagapattinam, guna, silchar,
jaisalmer) had projection data, so their "If today's trend continues" card silently said
"No satellite time series available" even for in-scope sites with real, already-pulled
NDVI/NDBI data. Generalized the script's site list (all real sites, real NDVI/NDBI
already on disk from this session's pulls -- `chennai`'s directory is `chennai_test`,
handled with an explicit override map) and re-ran it: 10 -> 22 sites with real
projection data.

**That fix then surfaced the SAME `NaN%` bug in a second place**: `renderProfileRisk`
had been fixed for `hasModel: false` sites, but `renderProfileProjection`'s narrative
text still unconditionally read `site.predicted_risk_prob * 100` -- harmless while these
sites had no projection data at all (function returned early), but as soon as real
projection data existed for them, this code path became reachable and produced literal
"today is NaN%" in the live narrative text for jaisalmer. Fixed by branching all of
`renderProfileProjection`'s narrative/disclaimer text on `site.hasModel`, verified live
for both jaisalmer (honest, no NaN, no real-score claim) and dharali (unchanged, still
shows the real score correctly).

**Pattern across secs 37-38**: fixing one visible symptom for a new/edge-case site
category keeps surfacing a NEXT latent bug in adjacent code that assumed every site
looks like the original 10 -- worth a real audit of anywhere else `predicted_risk_prob`,
`top_drivers`, `risk_ci_*`, or PROJ lookups are read without a `hasModel`/existence
check, rather than waiting for the user to find each one by clicking around.
