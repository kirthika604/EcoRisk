#!/usr/bin/env python3
"""Pulls real Sentinel-2 true-color before/after thumbnail images for one site -- the
visual proof for the awareness dashboard's "before/after, made visible" section. Not
tested in this dev environment (no Earth Engine credentials here); written to be run by
whoever has GEE access, same pattern as gee_pull_site.py.

For each of a "before" and "after" target date, searches a window around it for the
least-cloudy available Sentinel-2 scene (exact-date imagery is often cloud-covered,
especially near monsoon-adjacent disaster dates), downloads a true-color JPEG thumbnail,
and records the ACTUAL image date used (which may differ from the target) plus its cloud
cover in a sidecar JSON -- caption the image with the real date, never the target date.

Usage:
    python3 gee_pull_thumbnail.py --site-id joshimath --lat 30.5551 --lon 79.5641 \
        --before 2019-03-01 --after 2023-04-01 --outdir ../dashboard/images \
        --project stellar-polymer-470816-j9

Outputs (into --outdir):
    <site_id>_before.jpg
    <site_id>_after.jpg
    <site_id>_thumbnail_meta.json   {"before": {"date": "...", "cloud_pct": ...}, "after": {...}}
"""
import argparse
import json
import os

try:
    import ee
except ImportError:
    ee = None

IMAGE_BUFFER_METERS = 1800  # wider than the 1km stats buffer -- a thumbnail needs
                             # recognizable landscape context, not just the exact pixel
WINDOW_DAYS = 45            # search +/- this many days around the target date
THUMB_DIM = 640             # output image width in px (height set by aspect via region)


def least_cloudy_image(point, target_date, window_days):
    start = ee.Date(target_date).advance(-window_days, "day")
    end = ee.Date(target_date).advance(window_days, "day")
    coll = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(point)
        .filterDate(start, end)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    img = coll.first()
    return img


def download_thumbnail(img, region, out_path):
    import urllib.request
    url = img.getThumbURL({
        "region": region,
        "dimensions": THUMB_DIM,
        "format": "jpg",
        "bands": ["B4", "B3", "B2"],
        "min": 0,
        "max": 2500,  # typical S2 SR true-color stretch; adjust if images look too dark/bright
        "gamma": 1.3,
    })
    urllib.request.urlretrieve(url, out_path)


def pull_one(label, point, region, target_date, outdir, site_id):
    img = least_cloudy_image(point, target_date, WINDOW_DAYS)
    info = img.getInfo()
    if info is None:
        print(f"  {label}: NO IMAGE FOUND within {WINDOW_DAYS} days of {target_date} -- try a wider window or different date")
        return None
    actual_date = img.date().format("YYYY-MM-dd").getInfo()
    cloud_pct = img.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()
    out_path = os.path.join(outdir, f"{site_id}_{label}.jpg")
    download_thumbnail(img, region, out_path)
    print(f"  {label}: wrote {out_path} (actual date {actual_date}, {cloud_pct:.1f}% cloud)")
    return {"date": actual_date, "cloud_pct": round(cloud_pct, 1), "requested_date": target_date}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--site-id", required=True)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--before", required=True, help="target date for the 'before' image, YYYY-MM-DD")
    p.add_argument("--after", required=True, help="target date for the 'after' image, YYYY-MM-DD")
    p.add_argument("--outdir", required=True)
    p.add_argument("--project", default=None)
    args = p.parse_args()

    if ee is None:
        raise SystemExit("earthengine-api not installed. Run: pip install earthengine-api, then: earthengine authenticate")
    ee.Initialize(project=args.project) if args.project else ee.Initialize()

    os.makedirs(args.outdir, exist_ok=True)
    point = ee.Geometry.Point([args.lon, args.lat])
    region = point.buffer(IMAGE_BUFFER_METERS).bounds()

    print(f"Pulling before/after thumbnails for {args.site_id}...")
    meta = {}
    meta["before"] = pull_one("before", point, region, args.before, args.outdir, args.site_id)
    meta["after"] = pull_one("after", point, region, args.after, args.outdir, args.site_id)

    meta_path = os.path.join(args.outdir, f"{args.site_id}_thumbnail_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  wrote {meta_path}")

    if meta["before"] is None or meta["after"] is None:
        print("WARNING: one or both images failed -- widen --before/--after window or pick different dates and re-run.")


if __name__ == "__main__":
    main()
