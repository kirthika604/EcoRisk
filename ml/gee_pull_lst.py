#!/usr/bin/env python3
"""Pulls real Land Surface Temperature (LST) time series for one site -- the third real
signal alongside NDVI (vegetation) and NDBI (built-up): does the land itself measurably
run hotter as forest gives way to construction? Not tested in this dev environment (no
Earth Engine credentials here); written to be run by whoever has GEE access, same
pattern as gee_pull_site.py.

WHY THIS NEEDS GEE, NOT A SIMPLER SOURCE: reanalysis products like NASA POWER's "Earth
Skin Temperature" (already used elsewhere in this project for rainfall) are gridded at
roughly 50km resolution -- far too coarse to tell a 1km deforested patch from the
forested land next to it. The whole point of this feature is testing whether LOCAL land-
cover change shows up as LOCAL heating, so it has to come from actual thermal satellite
imagery (MODIS, 1km resolution) via Earth Engine, same as the NDVI/NDBI pulls.

Usage:
    python3 gee_pull_lst.py --site-id joshimath --lat 30.5551 --lon 79.5641 \
        --start 2019-01-01 --end 2023-12-31 --outdir ../datasourceSIH/sites/joshimath \
        --project stellar-polymer-470816-j9

Output (matching the NDVI/NDBI file shape, same directory as the other per-site pulls):
    <site_id>_lst_timeseries.csv   date, lst_celsius
"""
import argparse
import csv
import os

try:
    import ee
except ImportError:
    ee = None

BUFFER_METERS = 1000  # matches gee_pull_site.py's NDVI/NDBI stats buffer, for consistency
LST_COLLECTION = "MODIS/061/MOD11A2"  # Terra 8-day LST composite, 1km resolution, real satellite thermal data
LST_BAND = "LST_Day_1km"
LST_SCALE_FACTOR = 0.02  # per MODIS product spec: stored value * 0.02 = Kelvin


def pull_lst_timeseries(region, start, end, out_csv):
    coll = (
        ee.ImageCollection(LST_COLLECTION)
        .filterBounds(region)
        .filterDate(start, end)
        .select(LST_BAND)
    )

    def reduce_one(image):
        # Convert to Celsius at the IMAGE level (mask-aware) before reducing, not on the
        # scalar reduceRegion result after -- an 8-day MODIS composite can be fully
        # cloud-masked within a 1km mountain buffer, and ee.Number(null).multiply()
        # throws instead of propagating the mask, crashing the whole pull on one bad
        # date. Image.multiply()/.subtract() handle masked pixels correctly; the
        # reduceRegion result is then either a real number or a clean null we can filter.
        celsius_img = image.multiply(LST_SCALE_FACTOR).subtract(273.15)
        stat = celsius_img.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=1000, maxPixels=1e9)
        return ee.Feature(None, {"date": image.date().format("YYYY-MM-dd"), "lst_celsius": stat.get(LST_BAND)})

    feats = coll.map(reduce_one).filter(ee.Filter.notNull(["lst_celsius"]))
    rows = feats.getInfo()["features"]
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "lst_celsius"])
        for r in sorted(rows, key=lambda x: x["properties"]["date"]):
            w.writerow([r["properties"]["date"], round(r["properties"]["lst_celsius"], 2)])
    print(f"  wrote {out_csv} ({len(rows)} rows)")
    return len(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--site-id", required=True)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--start", default="2019-01-01")
    p.add_argument("--end", default="2023-12-31")
    p.add_argument("--outdir", required=True)
    p.add_argument("--project", default=None)
    args = p.parse_args()

    if ee is None:
        raise SystemExit("earthengine-api not installed. Run: pip install earthengine-api, then: earthengine authenticate")
    ee.Initialize(project=args.project) if args.project else ee.Initialize()

    os.makedirs(args.outdir, exist_ok=True)
    region = ee.Geometry.Point([args.lon, args.lat]).buffer(BUFFER_METERS)

    print(f"Pulling LST for {args.site_id}...")
    n = pull_lst_timeseries(region, args.start, args.end, os.path.join(args.outdir, f"{args.site_id}_lst_timeseries.csv"))
    if n < 10:
        print(f"  WARNING: only {n} observations -- widen --start/--end if this looks too sparse to trend.")


if __name__ == "__main__":
    main()
