#!/usr/bin/env python3
"""Earth Engine pull script for one site: NDVI, NDBI, DEM slope/elevation, and (for
coastal sites) Global Mangrove Watch extent.

WHY THIS SCRIPT EXISTS AS A SEPARATE HANDOFF: this dev environment has no Earth Engine
credentials, so none of this has been run or tested here -- it's written to match the
existing Joshimath data shape (see datasourceSIH/joshimath_ndvi_timeseries.csv etc.) as
closely as inferable from those output files, since the original GEE script that produced
them isn't in this repo. CONFIRM the buffer radius / cloud-filter threshold below against
however Joshimath was actually pulled before running this at scale -- consistency across
sites matters more than any single site being "optimal" (see ml-model-plan.md: same
features, pulled the same way).

Usage (run by someone with Earth Engine access, `earthengine authenticate` already done):
    python3 gee_pull_site.py --site-id raini --lat 30.5642 --lon 79.7369 \
        --start 2019-01-01 --end 2023-12-31 --terrain hill \
        --outdir ../datasourceSIH/sites/raini

Outputs (matching the Joshimath file shape, one directory per site):
    <site_id>_ndvi_timeseries.csv   date, ndvi_avg
    <site_id>_ndbi_timeseries.csv   date, ndbi_avg
    <site_id>_dem_slope.csv         elev_max/mean/min, slope_max/mean/min
    <site_id>_gmw_mangrove.csv      (coastal sites only) year, mangrove_area_ha

Then feed these into ml/build_feature_table.py's per-site feature computation (extend
build_joshimath_features.py's compute() to take a site directory instead of being
hardcoded to Joshimath's paths -- it already does the linear-trend-slope math you need,
just generalize the file paths).
"""
import argparse
import csv
import os

try:
    import ee
except ImportError:
    ee = None

BUFFER_METERS = 1000  # CONFIRM this matches whatever radius Joshimath was pulled with
CLOUD_FILTER_PCT = 20  # Sentinel-2 max cloud cover, matches common GEE tutorial defaults

# Public Earth Engine assets for Global Mangrove Watch v3
# (source: gee-community-catalog.org, checked 2026-08-31 -- verify the path still
# resolves before relying on it; asset paths on community catalogs can move)
GMW_RASTER_COLLECTION = "projects/sat-io/open-datasets/GMW/extent/GMW_V3"
GMW_YEARS = [1996, 2007, 2008, 2009, 2010, 2015, 2016, 2017, 2018, 2019, 2020]


def mask_s2_clouds(image):
    qa = image.select("QA60")
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    masked = image.updateMask(mask).divide(10000)
    # .divide() drops image metadata (system:time_start etc) as a side effect -- copy it
    # back explicitly, otherwise image.date() downstream fails on every image.
    return masked.copyProperties(image, image.propertyNames())


def pull_index_timeseries(region, start, end, band_formula, out_csv):
    """band_formula: function(image) -> single-band ee.Image of the index (NDVI or NDBI)."""
    coll = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_FILTER_PCT))
        .map(mask_s2_clouds)
    )

    def reduce_one(image):
        idx = band_formula(image)
        stat = idx.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=10, maxPixels=1e9)
        return ee.Feature(None, {"date": image.date().format("YYYY-MM-dd"), "value": stat.values().get(0)})

    feats = coll.map(reduce_one).filter(ee.Filter.notNull(["value"]))
    rows = feats.getInfo()["features"]
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", os.path.basename(out_csv).split("_")[-2] + "_avg"])
        for r in sorted(rows, key=lambda x: x["properties"]["date"]):
            w.writerow([r["properties"]["date"], r["properties"]["value"]])
    print(f"  wrote {out_csv} ({len(rows)} rows)")


def ndvi_formula(image):
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def ndbi_formula(image):
    return image.normalizedDifference(["B11", "B8"]).rename("NDBI")


def pull_dem_slope(region, out_csv):
    dem = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(dem)
    stats = dem.rename("elev").addBands(slope.rename("slope")).reduceRegion(
        reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
        geometry=region, scale=30, maxPixels=1e9,
    ).getInfo()
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elev_max", "elev_mean", "elev_min", "slope_max", "slope_mean", "slope_min"])
        w.writerow([
            stats.get("elev_max"), stats.get("elev_mean"), stats.get("elev_min"),
            stats.get("slope_max"), stats.get("slope_mean"), stats.get("slope_min"),
        ])
    print(f"  wrote {out_csv}")


def pull_gmw_mangrove(region, out_csv):
    """Coastal sites only. Sums mangrove polygon area (ha) within the buffer, per available
    GMW epoch. Uses the per-year VECTOR assets (gmw_v3_<year>_vec) since those paths are
    the ones actually documented (source: gee-community-catalog.org) -- the single
    ImageCollection path (GMW_V3) filtered by a guessed 'year' property failed in testing
    (2026-08-31: "Image.select: Parameter 'input' is required and may not be null", i.e.
    the filter matched nothing -- the property name was a guess and it was wrong. Rather
    than guess again blind, switched to the documented per-year vector paths, which don't
    need any filter property at all -- each year is its own asset."""
    rows = []
    for year in GMW_YEARS:
        asset = f"projects/sat-io/open-datasets/GMW/extent/gmw_v3_{year}_vec"
        try:
            fc = ee.FeatureCollection(asset).filterBounds(region)
            area_m2 = fc.geometry().intersection(region, 1).area(1).getInfo()
        except Exception as e:
            print(f"  GMW {year}: FAILED ({e}) -- asset path may not exist for this year/version, skipping")
            continue
        area_ha = area_m2 / 10000
        rows.append((year, area_ha))
        print(f"  GMW {year}: {area_ha:.2f} ha")
    if not rows:
        print("  WARNING: no GMW years succeeded -- writing empty file. This is a supplementary "
              "layer (mangrove context), NOT one of the model's actual features (see "
              "ml-model-plan.md's feature list), so this does not block training.")
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "mangrove_area_ha"])
        w.writerows(rows)
    print(f"  wrote {out_csv}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--site-id", required=True)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--start", default="2019-01-01")
    p.add_argument("--end", default="2023-12-31")
    p.add_argument("--terrain", choices=["hill", "coastal"], required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--project", default=None, help="GEE cloud project id, if required by your account")
    args = p.parse_args()

    if ee is None:
        raise SystemExit(
            "earthengine-api not installed. Run: pip install earthengine-api\n"
            "Then: earthengine authenticate  (one-time, opens a browser login)"
        )
    ee.Initialize(project=args.project) if args.project else ee.Initialize()

    os.makedirs(args.outdir, exist_ok=True)
    region = ee.Geometry.Point([args.lon, args.lat]).buffer(BUFFER_METERS)

    print(f"Pulling NDVI for {args.site_id}...")
    pull_index_timeseries(region, args.start, args.end, ndvi_formula,
                           os.path.join(args.outdir, f"{args.site_id}_ndvi_timeseries.csv"))

    print(f"Pulling NDBI for {args.site_id}...")
    pull_index_timeseries(region, args.start, args.end, ndbi_formula,
                           os.path.join(args.outdir, f"{args.site_id}_ndbi_timeseries.csv"))

    print(f"Pulling DEM/slope for {args.site_id}...")
    pull_dem_slope(region, os.path.join(args.outdir, f"{args.site_id}_dem_slope.csv"))

    if args.terrain == "coastal":
        print(f"Pulling GMW mangrove extent for {args.site_id}...")
        pull_gmw_mangrove(region, os.path.join(args.outdir, f"{args.site_id}_gmw_mangrove.csv"))

    print(f"Done. Now extend build_joshimath_features.py to read {args.outdir} and add a row to ml/feature_table.csv.")


if __name__ == "__main__":
    main()
