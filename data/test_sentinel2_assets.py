"""
Proof-of-concept: for two target dates, find the best (lowest-cloud)
Sentinel-2 Level-2A scene near each date over Kodagu, Karnataka, India,
using the official Copernicus Data Space Ecosystem (CDSE) STAC API, and
print the asset hrefs we'd need later to actually work with the imagery.

STAC endpoint (unchanged from test_sentinel2.py):
    Base: https://stac.dataspace.copernicus.eu/v1/
    Search: https://stac.dataspace.copernicus.eu/v1/search

What's an "asset href"?
    Each STAC item (scene) has an "assets" dict. Each asset is one file
    belonging to that scene -- usually a single spectral band, at a
    specific resolution. The asset's "href" is simply the direct URL to
    that file (typically a Cloud-Optimized GeoTIFF). It's a pointer to
    the data, not the data itself -- fetching that URL is the download
    step, which we deliberately are NOT doing here.

Bands we care about for later NDVI-style forest disturbance work
(not computed in this script -- just locating the files):
    B04_10m -- Red band, 10m resolution
    B08_10m -- Near-Infrared (NIR) band, 10m resolution
    SCL_20m -- Scene Classification Layer, 20m resolution (land cover /
               cloud / shadow / vegetation classes per pixel, useful for
               masking out clouds and non-forest pixels)

This script only SEARCHES the catalog and prints metadata + hrefs. It
does not download any imagery, and does no NDVI/AI/ML/mapping work.
"""

from datetime import datetime, timedelta

import requests

STAC_SEARCH_URL = "https://stac.dataspace.copernicus.eu/v1/search"
COLLECTION = "sentinel-2-l2a"

# Small bounding box around Madikeri / central Kodagu, Karnataka, India.
# Format: [min_lon, min_lat, max_lon, max_lat]
KODAGU_BBOX = [75.65, 12.30, 75.85, 12.50]

# Target dates we want the best available scene for.
TARGET_DATES = [
    "2025-01-05",
    "2026-01-05",
]

# Sentinel-2 revisits the same spot roughly every 5 days, so we search a
# window around each target date to make sure we actually find a scene,
# rather than requiring an exact same-day match.
WINDOW_DAYS = 5

# Assets (bands) we want the href for, per scene.
WANTED_ASSETS = ["B04_10m", "B08_10m", "SCL_20m"]


def date_window(target_date_str, days=WINDOW_DAYS):
    """Turn a 'YYYY-MM-DD' target date into a STAC datetime range string
    covering `days` before and after it."""

    target = datetime.strptime(target_date_str, "%Y-%m-%d")
    start = target - timedelta(days=days)
    end = target + timedelta(days=days)
    return f"{start:%Y-%m-%d}T00:00:00Z/{end:%Y-%m-%d}T23:59:59Z"


def search_sentinel2(datetime_range, limit=20):
    """Query the CDSE STAC API for sentinel-2-l2a scenes over KODAGU_BBOX
    within the given datetime range. Returns the raw list of STAC items."""

    request_body = {
        "collections": [COLLECTION],
        "bbox": KODAGU_BBOX,
        "datetime": datetime_range,
        "limit": limit,
        # Ask the API to sort by cloud cover (ascending) so the clearest
        # scenes come first. We also re-sort client-side below in case
        # this sort extension isn't honored.
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
    }

    response = requests.post(STAC_SEARCH_URL, json=request_body, timeout=30)
    response.raise_for_status()

    return response.json().get("features", [])


def pick_best_scene(items):
    """Pick the lowest-cloud-cover scene from a list of STAC items.
    Returns None if the list is empty."""

    if not items:
        return None

    return min(
        items,
        key=lambda item: item.get("properties", {}).get("eo:cloud_cover", 999),
    )


def print_best_scene(target_date_str, item):
    print(f"\n=== Best scene near {target_date_str} ===")

    if item is None:
        print(f"No scenes found within {WINDOW_DAYS} days of this date.")
        return

    props = item.get("properties", {})
    assets = item.get("assets", {})

    print(f"Item ID       : {item.get('id')}")
    print(f"Acquired      : {props.get('datetime')}")
    print(f"Cloud cover   : {props.get('eo:cloud_cover')}%")

    for asset_name in WANTED_ASSETS:
        asset = assets.get(asset_name)
        if asset is None:
            print(f"{asset_name:<14}: not available for this scene")
        else:
            print(f"{asset_name:<14}: {asset.get('href')}")


if __name__ == "__main__":
    for target_date in TARGET_DATES:
        try:
            scenes = search_sentinel2(date_window(target_date))
            best = pick_best_scene(scenes)
            print_best_scene(target_date, best)
        except requests.exceptions.RequestException as exc:
            print(f"\n=== Best scene near {target_date} ===")
            print(f"Request failed: {exc}")