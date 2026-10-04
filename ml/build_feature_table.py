#!/usr/bin/env python3
"""Builds ml/feature_table.csv: one row per candidate site from sihPlan/dataset-sites.md.

Joshimath is filled in with REAL computed values (via build_joshimath_features.py).
Every other site is a template row with status=NOT_PULLED and blank NDVI/NDBI/slope/
rainfall columns -- these require an actual Earth Engine + NASA POWER pull per site,
which this environment cannot do (no earthengine-api credentials here). Fill them in
by running the same GEE scripts used for Joshimath against each site's coordinates,
then updating this CSV -- do NOT hand-fill numbers without a real pull.

Coordinates/dates below are transcribed from sihPlan/dataset-sites.md as of the multi-
site plan pivot (2026-08-31) -- that file itself says "verify every citation yourself,"
so treat these as leads, not confirmed facts, until the team checks them."""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_joshimath_features import compute as compute_joshimath, compute_gee_site
from nasa_power import rainfall_anomaly_pct
import datetime as dt

# Reference date for control sites (no disaster_date to anchor the rainfall window to).
# Arbitrary but fixed so results are reproducible/comparable -- chosen as a recent date
# after all listed disaster events.
DEFAULT_CONTROL_ANCHOR = dt.date(2023, 1, 1)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES_DIR = os.path.join(BASE, "datasourceSIH", "sites")  # per-site GEE pull output, see gee_pull_site.py

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feature_table.csv")

COLUMNS = [
    "site_id", "site_name", "terrain_type", "latitude", "longitude",
    "ndvi_trend_slope", "ndbi_trend_slope", "mean_slope_degrees", "elevation_mean_m",
    "rainfall_anomaly_pct", "lst_trend_slope", "lst_mean_c",
    "human_activity_notes", "disaster_occurred", "disaster_type",
    "disaster_date", "source_citation", "status",
    # Cyclone intensity at landfall (coastal sites only) -- real, from NOAA IBTrACS.
    # Kept as separate evidence/backtest columns, NOT folded into the core terrain-agnostic
    # ML feature vector (ndvi/ndbi/slope/elevation/rainfall) used by train_model.py -- see
    # sihPlan/memory.md sec 10 for why, and for the open design question this raises.
    "cyclone_name", "cyclone_landfall_wind_kmh_imd", "cyclone_landfall_pressure_mb_imd",
    "cyclone_grade_imd", "cyclone_source",
]

CYCLONE_DATA = {
    "sundarbans": dict(cyclone_name="AMPHAN", cyclone_landfall_wind_kmh_imd=166.7,
                        cyclone_landfall_pressure_mb_imd=960, cyclone_grade_imd="ESCS (Extremely Severe Cyclonic Storm)",
                        cyclone_source="NOAA IBTrACS v04r01, IMD/NEWDELHI agency track, landfall 2020-05-20 09:00 UTC near 21.4N 88.1E; see datasourceSIH/cyclone_landfall_ibtracs.csv"),
    "odisha_coast": dict(cyclone_name="FANI", cyclone_landfall_wind_kmh_imd=185.2,
                          cyclone_landfall_pressure_mb_imd=952, cyclone_grade_imd="ESCS (Extremely Severe Cyclonic Storm)",
                          cyclone_source="NOAA IBTrACS v04r01, IMD/NEWDELHI agency track, landfall 2019-05-03 03:00 UTC near 19.6N 85.7E; see datasourceSIH/cyclone_landfall_ibtracs.csv"),
}

# Template rows transcribed from sihPlan/dataset-sites.md. lat/lon marked "verify" in that
# file are kept as-is here -- confirm before running Earth Engine pulls against them.
TEMPLATE_SITES = [
    dict(site_id="raini", site_name="Raini village, Chamoli", terrain_type="hill",
         latitude=30.5642, longitude=79.7369, disaster_occurred=1,
         disaster_type="flash_flood_rock_ice_avalanche", disaster_date="2021-02-07",
         source_citation="News archives / academic papers on Rishiganga debris flow (unverified, per dataset-sites.md)"),
    dict(site_id="kedarnath", site_name="Kedarnath area, Rudraprayag", terrain_type="hill",
         latitude=30.7346, longitude=79.0669, disaster_occurred=1,
         disaster_type="rainfall_triggered_landslide_flood", disaster_date="2013-06-16",
         source_citation="Martha et al. 2015 (cited in ResearchGate search, per dataset-sites.md; not independently verified)"),
    dict(site_id="wazri", site_name="Wazri, near Yamunotri, Uttarkashi", terrain_type="hill",
         latitude=30.9064, longitude=78.3464, disaster_occurred=1,
         disaster_type="landslide", disaster_date="2017-09-12",
         source_citation="'Landslides Over Two Places of Uttarakhand: An Observation' (per dataset-sites.md; not independently verified)"),
    dict(site_id="dharali", site_name="Dharali, Uttarkashi", terrain_type="hill",
         latitude=30.83, longitude=78.45, disaster_occurred=1,
         disaster_type="cloudburst_landslide_flash_flood", disaster_date="2025-08-01",
         source_citation="Recent news coverage, e.g. ETV Bharat, Aug 2025 (per dataset-sites.md; coordinates marked 'verify' in source doc)"),
    dict(site_id="malpa", site_name="Malpa village, Pithoragarh", terrain_type="hill",
         latitude=29.85, longitude=80.35, disaster_occurred=1,
         disaster_type="landslide", disaster_date="1998-08-18",
         source_citation="Rautela & Pande, 2005 (per dataset-sites.md; coordinates marked 'verify', pre-Sentinel-2 era so NDVI trend may not be pullable)"),
    dict(site_id="auli_control", site_name="Auli, Chamoli (control)", terrain_type="hill",
         latitude=30.5271, longitude=79.5665, disaster_occurred=0,
         disaster_type="", disaster_date="",
         source_citation="Control candidate -- no major documented event in window, per dataset-sites.md; needs GSI/news search confirmation"),
    dict(site_id="garhwal_control_tbd", site_name="TBD second Garhwal control site", terrain_type="hill",
         latitude="", longitude="", disaster_occurred=0,
         disaster_type="", disaster_date="",
         source_citation="Not yet identified -- team to confirm per dataset-sites.md"),
    dict(site_id="sundarbans", site_name="Sundarbans (West Bengal side)", terrain_type="coastal",
         latitude=21.9497, longitude=88.9468, disaster_occurred=1,
         disaster_type="cyclone", disaster_date="2020-05-20",
         source_citation="Cyclone Amphan, state disaster reports / mangrove-cyclone damage studies (per dataset-sites.md; exact sub-area needs verification)",
         human_activity_notes="NDBI trend +/-0.003 (near flat) in this 1km buffer -- not a strong standalone "
                               "human-activity signal on its own. Real GMW mangrove data confirms mild decline "
                               "(304.5->303.1 ha, 1996-2020) but mangrove is not a model feature. This site's "
                               "disaster driver is primarily the acute cyclone event, not a slow land-use trend -- "
                               "see sihPlan/memory.md sec 15 for why the coastal narrative leans on cyclone "
                               "intensity rather than forcing a human-activity story the data doesn't support."),
    dict(site_id="odisha_coast", site_name="Odisha coast (Puri/Bhitarkanika area)", terrain_type="coastal",
         latitude=19.8106, longitude=85.8314, disaster_occurred=1,
         disaster_type="cyclone", disaster_date="2019-05-03",
         source_citation="Cyclone Fani, Odisha SDMA reports. COORDINATE CORRECTED 2026-08-31: original "
                          "19.7,85.8 (per dataset-sites.md, marked 'verify') returned elevation_mean_m=0.0 and "
                          "mean_slope_degrees=0.0 from the real SRTM DEM pull -- the signature of a point sitting "
                          "in open water, not land, which also produced 0 valid Land Surface Temperature "
                          "observations across the full 2019-2023 period (MODIS LST is land-only, masks water). "
                          "Replaced with Puri town center, 19.8106N 85.8314E (19 48'38\"N 85 49'53\"E), a "
                          "well-documented landmark confirmed on land. NDVI/NDBI/slope/elevation/LST all need "
                          "re-pulling at this corrected point -- the old values at 19.7,85.8 are unreliable.",
         human_activity_notes="NDBI trend +0.0009 (essentially flat). Real GMW data confirms 0.00 ha mangrove "
                               "in this buffer across all 11 years -- Puri itself is not a mangrove area (see "
                               "sihPlan/memory.md sec 14). Neither mangrove-loss nor NDBI growth is a usable "
                               "human-activity signal at this site; disaster driver is the acute cyclone event."),
    dict(site_id="sundarbans_control", site_name="Sundarbans denser-mangrove sub-area (control)", terrain_type="coastal",
         latitude="", longitude="", disaster_occurred=0,
         disaster_type="", disaster_date="",
         source_citation="Not yet identified -- same cyclone exposure, lower damage, per dataset-sites.md"),
    dict(site_id="coastal_control_tbd", site_name="Coringa mangrove area, Kakinada, Andhra Pradesh (control candidate)", terrain_type="coastal",
         latitude=16.75, longitude=82.28, disaster_occurred=0,
         disaster_type="", disaster_date="",
         source_citation="Candidate control site, checked against real IBTrACS track data 2026-08-31: nearest IMD-graded "
                          "Severe-or-stronger cyclone (>=48kt) in 2015-2023 was ASANI (2022, SCS, 50kt) at 157km distance -- "
                          "no direct/close severe cyclone hit in this window. Same coastal-mangrove terrain type as the "
                          "Sundarbans site (Coringa Wildlife Sanctuary mangroves), unlike a non-mangrove coastal control. "
                          "STILL NEEDS: team confirmation this is an acceptable control (157km is 'no severe hit nearby', "
                          "not 'zero cyclone exposure ever') -- see ml-model-plan.md's own caveat that control-site "
                          "selection is a judgment call to be ready to defend.",
         human_activity_notes="NDBI trend -0.016 (mildly declining) -- if anything more negative than either "
                               "real coastal disaster site, so NDBI alone would not distinguish this control "
                               "either. Real GMW mangrove data is small and noisy (0.71-1.83 ha, no clear trend) "
                               "-- likely near the sanctuary's edge rather than its core within this 1km buffer."),
]


def pull_rainfall(site):
    """Real NASA POWER pull -- no GEE needed, reachable from this environment. Returns
    (anomaly_pct, n_days) or (None, 0) if coordinates are missing/blank."""
    lat, lon = site.get("latitude"), site.get("longitude")
    if lat in ("", None) or lon in ("", None):
        return None, 0
    anchor = dt.date.fromisoformat(site["disaster_date"]) if site.get("disaster_date") else DEFAULT_CONTROL_ANCHOR
    try:
        return rainfall_anomaly_pct(float(lat), float(lon), anchor)
    except Exception as e:
        print(f"  WARNING: rainfall pull failed for {site['site_id']}: {e}")
        return None, 0


def main():
    joshimath = compute_joshimath()
    all_rows = [joshimath]
    for s in TEMPLATE_SITES:
        row = {c: "" for c in COLUMNS}
        row.update(s)
        row["human_activity_notes"] = row.get("human_activity_notes", "")
        has_cyclone = s["site_id"] in CYCLONE_DATA
        if has_cyclone:
            row.update(CYCLONE_DATA[s["site_id"]])

        print(f"Pulling rainfall for {s['site_id']} ({s.get('latitude')},{s.get('longitude')})...")
        anomaly, n_days = pull_rainfall(s)
        got_rainfall = anomaly is not None
        if got_rainfall:
            row["rainfall_anomaly_pct"] = round(anomaly, 2)
            row["source_citation"] = row["source_citation"] + f" | Rainfall: NASA POWER API, real pull, {n_days} days baseline (2026-08-31)."

        gee = compute_gee_site(s["site_id"], os.path.join(SITES_DIR, s["site_id"]))
        got_gee = gee is not None
        if got_gee:
            row.update(gee)
            row["source_citation"] = row["source_citation"] + " | NDVI/NDBI: Sentinel-2 via Earth Engine (gee_pull_site.py); slope/elevation: SRTM DEM via Earth Engine."
            if "lst_trend_slope" in gee:
                row["source_citation"] = row["source_citation"] + f" | LST: MODIS MOD11A2 via Earth Engine ({gee.get('_lst_n_obs', '?')} obs)."

        parts_real = (
            (["cyclone landfall (IBTrACS)"] if has_cyclone else [])
            + (["rainfall anomaly (NASA POWER)"] if got_rainfall else [])
            + (["NDVI/NDBI/slope (Earth Engine)"] if got_gee else [])
        )
        missing = [] if got_gee else ["NDVI/NDBI/slope (needs Earth Engine)"]
        if got_gee and (has_cyclone or got_rainfall or s["site_id"] == "joshimath"):
            row["status"] = "REAL - complete (rainfall + NDVI/NDBI/slope pulled; cyclone landfall too)" if has_cyclone else "REAL - complete (rainfall + NDVI/NDBI/slope pulled)"
        elif parts_real:
            row["status"] = f"PARTIAL - REAL: {', '.join(parts_real)}. Still NOT_PULLED: {', '.join(missing)}."
        else:
            row["status"] = "NOT_PULLED - needs Earth Engine (NDVI/NDBI/slope) + coordinates confirmed" if (row.get("latitude") in ("", None)) else "NOT_PULLED - needs Earth Engine (NDVI/NDBI/slope) pull"
        all_rows.append(row)

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in all_rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})

    real_count = sum(1 for r in all_rows if r.get("status", "").startswith("REAL"))
    partial_count = sum(1 for r in all_rows if r.get("status", "").startswith("PARTIAL"))
    print(f"Wrote {OUT}")
    print(f"  {len(all_rows)} total site rows, {real_count} with real complete data, "
          f"{partial_count} partial (some real data, e.g. cyclone landfall), "
          f"{len(all_rows) - real_count - partial_count} fully pending data pulls.")


if __name__ == "__main__":
    main()
