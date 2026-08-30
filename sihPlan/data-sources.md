# Data Structure & Sources — SIH26206 Project

---

## 1. Data Layers Overview

| Layer | Purpose | Update cadence | Real or Mocked |
|---|---|---|---|
| Satellite imagery (land cover / NDVI) | Human-activity trend detection | Historical, ~5-day revisit | Real |
| Historical rainfall | Trigger correlation, backtesting | Daily (historical) | Real |
| Live rainfall (current) | "Live" demo element | Real-time | Real (single call) |
| Land records / survey boundaries | Locate exact plot/slope | Static | Real (if accessible) |
| Published risk thresholds | Convert trend → risk band | Static, cited | Real, hardcoded |
| Past disaster event record | Ground-truth for backtesting | Static, one-time lookup | Real |

---

## 2. Satellite / Land-Cover Data

**Purpose:** detect deforestation, construction growth, drainage loss over time (the "slow trend" layer).

- **Source:** Sentinel-2 (via Copernicus Open Access Hub or Sentinel Hub EO Browser) or Landsat (via USGS EarthExplorer)
- **Access tools:** Google Earth Engine (recommended — free, browser-based, has NDVI functions built in), or QGIS with plugins
- **What to pull:**
  - Imagery for chosen location, several timestamps across ~5 years (yearly or seasonal snapshots are enough — daily granularity not needed for this layer)
  - Imagery immediately before and immediately after the locked historical disaster event
- **Processing:** compute NDVI (Normalized Difference Vegetation Index) from red + near-infrared bands; track % forest cover change and/or built-up area change over time
- **Structure to store:**
  ```
  {
    "location_id": string,
    "date": "YYYY-MM-DD",
    "ndvi_avg": float,
    "forest_cover_pct": float,
    "built_up_area_pct": float,
    "source_image_id": string
  }
  ```

---

## 3. Historical Rainfall Data

**Purpose:** identify the trigger conditions (short-timescale spike) that preceded the past disaster event; used for backtesting the threshold logic.

- **Source:** India Meteorological Department (IMD) historical daily gridded rainfall data; also check state disaster management department archives
- **What to pull:** daily rainfall for the chosen district, spanning at least the period around the locked historical event (a window of a few weeks before/after is enough)
- **Structure to store:**
  ```
  {
    "district": string,
    "date": "YYYY-MM-DD",
    "rainfall_mm": float
  }
  ```

---

## 4. Live Rainfall Data (the one real live element)

**Purpose:** demo credibility — show the dashboard pulling a genuine current value, not everything static.

- **Source options (pick one, whichever has simplest free API access):**
  - OpenWeather API
  - NASA POWER API
  - IMD's public data endpoints (if accessible without heavy registration)
- **What to pull:** today's rainfall / current weather for the chosen district
- **Structure to store:** same shape as historical rainfall, tagged `"live": true`

---

## 5. Land Records / Location Boundaries

**Purpose:** precisely locate the slope/plot for satellite comparison (needed to line up "before" and "after" imagery on the exact same area).

- **Source:** Bhuvan (ISRO's geoportal) for boundary/terrain reference; state land record portals if survey numbers are needed; OpenStreetMap as a fallback for road/village reference points
- **Fallback approach if precise land records aren't accessible in time:** manually pin coordinates using news photos, known landmarks, or road names near the reported event location — document this as a known limitation in the pitch, not hidden

---

## 6. Published Risk Thresholds

**Purpose:** convert the human-activity trend into a risk band, using real (not invented) numbers.

- **Source:** Geological Survey of India (GSI) landslide susceptibility reports; NDMA guidelines/reports; peer-reviewed studies on deforestation-landslide or land-use-flood correlation for similar terrain
- **Important:** these will likely be *ranges*, not a single precise number — cite the range and the source, don't invent false precision
- **Structure to store:**
  ```
  {
    "hazard_type": "landslide" | "flood",
    "risk_factor": "deforestation_pct" | "rainfall_3day_cumulative_mm" | etc,
    "threshold_low": float,
    "threshold_high": float,
    "source_citation": string
  }
  ```

---

## 7. Past Disaster Event Record (ground truth)

**Purpose:** the one confirmed real event used to validate that your model's risk band logic would have flagged it.

- **Source:** NDMA disaster database, state disaster management authority reports, credible news archives (search by district + year + "landslide"/"flood")
- **What to record:**
  ```
  {
    "event_date": "YYYY-MM-DD",
    "location": string,
    "hazard_type": string,
    "description": string,
    "source_url_or_citation": string
  }
  ```

---

## 8. Data Access Checklist (do this in Hour 0–3 of the hackathon)

- [ ] Test-pull Sentinel-2 imagery for chosen location in Google Earth Engine — confirm it works
- [ ] Test-pull historical rainfall for chosen district — confirm format/availability
- [ ] Test-call live weather API — confirm key/access works, note rate limits
- [ ] Find and screenshot/save the one published threshold figure you'll cite
- [ ] Find and save the one credible source for the historical disaster event (date + location)

**If any of these fail, do not keep debugging past 30 minutes — switch to a backup district/event immediately.**

---

## 9. Open / Not Yet Decided

- Final chosen district and event
- Which live weather API to standardize on
- Whether precise land records are accessible, or manual pinning is needed
