"""
Proof-of-concept: for two target dates, find the best (lowest-cloud)
Sentinel-2 Level-2A scene near each date over Kodagu, Karnataka, India,
using the public Earth Search STAC API (run by Element 84), and print
the HTTPS asset URLs for the red and NIR bands.

STAC endpoint:
    Search: https://earth-search.aws.element84.com/v1/search

This mirrors the search logic from our existing CDSE script
(test_sentinel2_assets.py) -- same bbox, same "search a window around a
target date, then pick the lowest cloud-cover scene" approach -- just
pointed at a different (also public, no-auth) STAC provider.

Which asset keys are red and NIR?
    Earth Search's sentinel-2-l2a collection already stores every band as
    a Cloud-Optimized GeoTIFF (COG), and names assets by their common band
    name rather than by raw band code:
        "red" -> Sentinel-2 Band 4 (B04), the red band
        "nir" -> Sentinel-2 Band 8 (B08), the near-infrared band
    Some Earth Search items also carry a legacy "visual"/JP2-era style
    asset for compatibility. To be safe and explicit, this script checks
    each candidate asset's declared "type" and only accepts it if that
    type says GeoTIFF/cloud-optimized, skipping anything that looks like
    a JP2 asset.

An asset's "href" is just the direct URL to that one file -- a pointer to
the data, not the data itself. Fetching that URL is the download step,
which we deliberately are NOT doing here.

This script only SEARCHES the catalog and prints metadata + URLs. It does
no downloading, and no NDVI/AI/ML/mapping work.
"""

from datetime import datetime, timedelta

import requests

STAC_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"

# Same test area as our other Sentinel-2 scripts: small bounding box around
# Madikeri / central Kodagu, Karnataka, India.
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

# Asset keys to look for, in priority order, for each band. Earth Search
# uses common band names ("red"/"nir"); B04/B08 are kept as a fallback in
# case a given item only exposes raw band codes.
RED_ASSET_CANDIDATES = ["red", "B04"]
NIR_ASSET_CANDIDATES = ["nir", "B08"]

# Only accept an asset as our "COG" pick if its declared media type
# mentions geotiff/cloud-optimized -- this is how we skip JP2 assets.
COG_TYPE_HINTS = ["geotiff", "cog", "cloud-optimized"]


def date_window(target_date_str, days=WINDOW_DAYS):
    """Turn a 'YYYY-MM-DD' target date into a STAC datetime range string
    covering `days` before and after it."""

    target = datetime.strptime(target_date_str, "%Y-%m-%d")
    start = target - timedelta(days=days)
    end = target + timedelta(days=days)
    return f"{start:%Y-%m-%d}T00:00:00Z/{end:%Y-%m-%d}T23:59:59Z"


def search_sentinel2(datetime_range, limit=20):
    """Query the Earth Search STAC API for sentinel-2-l2a scenes over
    KODAGU_BBOX within the given datetime range. Returns the raw list of
    STAC items."""

    request_body = {
        "collections": [COLLECTION],
        "bbox": KODAGU_BBOX,
        "datetime": datetime_range,
        "limit": limit,
        # Ask the API to sort by cloud cover (ascending) so the clearest
        # scenes come first. We also re-pick client-side below in case
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


def find_cog_href(assets, candidate_keys):
    """Look through candidate_keys in order and return the href of the
    first one that is present AND whose type looks like a COG (not JP2).
    Returns None if no matching COG asset is found."""

    for key in candidate_keys:
        asset = assets.get(key)
        if asset is None:
            continue

        asset_type = asset.get("type", "").lower()
        if any(hint in asset_type for hint in COG_TYPE_HINTS):
            return asset.get("href")

    return None


def print_best_scene(target_date_str, item):
    print(f"\n=== Best scene near {target_date_str} ===")

    if item is None:
        print(f"No scenes found within {WINDOW_DAYS} days of this date.")
        return

    props = item.get("properties", {})
    assets = item.get("assets", {})

    red_href = find_cog_href(assets, RED_ASSET_CANDIDATES)
    nir_href = find_cog_href(assets, NIR_ASSET_CANDIDATES)

    print(f"Item ID       : {item.get('id')}")
    print(f"Acquired      : {props.get('datetime')}")
    print(f"Cloud cover   : {props.get('eo:cloud_cover')}%")
    print(f"Red band (COG): {red_href or 'not available'}")
    print(f"NIR band (COG): {nir_href or 'not available'}")


if __name__ == "__main__":
    for target_date in TARGET_DATES:
        try:
            scenes = search_sentinel2(date_window(target_date))
            best = pick_best_scene(scenes)
            print_best_scene(target_date, best)
        except requests.exceptions.RequestException as exc:
            print(f"\n=== Best scene near {target_date} ===")
            print(f"Request failed: {exc}")