# Data Structure & Sources — SIH26206 (Multi-Site ML Version)

---

## 1. What Changed From Single-Site to Multi-Site

Previously, all data was pulled for one location (Joshimath). Now, the SAME pulls need
to run for every site in `dataset-sites.md`. The tools and scripts don't change — only
the coordinates and date ranges per site, and the fact that outputs get compiled into
ONE combined feature table instead of separate per-site files.

---

## 2. Per-Site Feature Table (the end goal)

Every site should end up as one row in a master table shaped like this:

```
{
  "site_id": string,
  "site_name": string,
  "terrain_type": "hill" | "coastal",
  "latitude": float,
  "longitude": float,
  "ndvi_trend_slope": float,        // linear trend of NDVI over available years
  "ndbi_trend_slope": float,        // linear trend of NDBI over available years
  "mean_slope_degrees": float,      // hill sites: DEM slope; coastal sites: use 0 or terrain-specific proxy
  "elevation_mean_m": float,
  "rainfall_anomaly_pct": float,    // deviation from long-term average in the relevant window
  "human_activity_notes": string,   // brief text: what human activity is documented here
  "disaster_occurred": 0 | 1,       // label
  "disaster_type": string,
  "disaster_date": "YYYY-MM-DD",
  "source_citation": string
}
```

---

## 3. Satellite / Land-Cover Data (NDVI + NDBI) — per site

- **Tool:** Google Earth Engine (code.earthengine.google.com) — reuse the exact scripts
  already built for Joshimath (NDVI script and NDBI script). Only change:
  the `ee.Geometry.Point([lon, lat])` coordinates and the date range if needed.
- **What to pull per site:** NDVI and NDBI time series across as many years as available
  (aim for at least 3-4 years per site to compute a trend, not just a snapshot)
- **Processing:** compute a simple linear trend (slope) from each site's time series —
  this becomes the `ndvi_trend_slope` / `ndbi_trend_slope` feature. A single number per
  site, not a full time series, is what goes into the ML feature table.

---

## 4. Terrain Data (slope/elevation) — per site

- **Tool:** Google Earth Engine (reuse the DEM/slope script already built)
- **For hill sites:** pull mean slope (degrees) and mean elevation, same as Joshimath
- **For coastal sites:** slope is less meaningful — consider using elevation (low-lying
  = higher exposure) and/or distance-to-coastline as the terrain-risk proxy instead

---

## 5. Rainfall Data — per site

- **Tool:** NASA POWER Data Access Viewer (power.larc.nasa.gov/data-access-viewer)
- **What to pull:** daily precipitation for each site's coordinates, covering the relevant
  historical window (a few years back, plus the specific window around any known event)
- **Processing:** compute a rainfall anomaly (e.g., % deviation from the multi-year
  average for that site) rather than storing full daily series in the feature table

---

## 6. Human-Activity Intensity Proxy — per site

- **For hill sites:** construction/tunnelling growth — use the NDBI trend itself as the
  primary proxy (already captured above); supplement with a short text note on any
  documented construction/mining/tunnelling activity found via news search
- **For coastal sites:** aquaculture/shrimp-farming expansion or coastal development —
  search news/state coastal-zone-management reports; NDBI trend can also capture general
  coastal development growth

---

## 7. Disaster Event Labels — per site

- **Sources:**
  - GSI (Geological Survey of India) landslide records and susceptibility reports
  - NDMA disaster database
  - State disaster management authority reports (Uttarakhand USDMA; Odisha/West Bengal
    state disaster authorities for coastal sites)
  - Credible news archives — search `[site name] + landslide/subsidence/cyclone + year`
- **For "no disaster" control sites:** choose sites of similar terrain type in the same
  general region that do NOT have a documented major event in the same period — note
  this is a judgment call; document why each control site was chosen (e.g., "similar
  elevation and slope range, no GSI-recorded event in this period")

---

## 8. Threshold / Reference Citations (kept from single-site version)

Still useful as supporting evidence, not as ML features directly:
- Slope-risk range citation (17°-47°, Joshimath study) — already collected
- Any equivalent published threshold for coastal mangrove-loss vs. cyclone damage
  severity — search Google Scholar: `mangrove cover cyclone damage severity India`

---

## 9. Data Collection Checklist (per site, repeat for each)

- [ ] NDVI time series pulled (Earth Engine)
- [ ] NDBI time series pulled (Earth Engine)
- [ ] Slope/elevation pulled (Earth Engine)
- [ ] Rainfall pulled (NASA POWER)
- [ ] Disaster label confirmed with source (or confirmed as a valid control site)
- [ ] Row added to master feature table

**Do this fully for 2-3 sites first to confirm the pipeline works end-to-end before
running it across the full site list — this catches format/API issues early.**

---

## 10. Open / Not Yet Decided

- Final list of sites and their terrain_type split — see `dataset-sites.md`
- Exact definition of "rainfall anomaly" window per site (may vary hill vs. coastal)
- Coastal terrain-risk proxy: elevation alone, or elevation + distance-to-coast
