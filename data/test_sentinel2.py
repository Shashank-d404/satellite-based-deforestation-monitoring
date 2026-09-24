"""
Proof-of-concept: search the official Copernicus Data Space Ecosystem (CDSE)
STAC API for Sentinel-2 Level-2A scenes over Kodagu, Karnataka, India.

Endpoint being tested:
    POST https://stac.dataspace.copernicus.eu/v1/search

This is CDSE's STAC (SpatioTemporal Asset Catalog) search endpoint. We send
it a small JSON body describing WHERE (a bounding box), WHEN (a date range),
and WHAT (the "sentinel-2-l2a" collection = atmospherically corrected,
surface-reflectance Sentinel-2 imagery), and it returns a list of matching
scenes ("items") as GeoJSON-like features, each with metadata (acquisition
date, cloud cover, etc.) and links to the actual image bands ("assets").

We query TWO separate time windows -- January 2025 and January 2026 -- so
we can compare the same month a year apart over Kodagu, useful for picking
a good before/after pair for disturbance detection later. Results are
filtered server-side to scenes with less than MAX_CLOUD_COVER% cloud cover,
so only usable, mostly-clear imagery comes back.

This script only SEARCHES the catalog and prints metadata. It does not
download any imagery.
"""

import requests

STAC_SEARCH_URL = "https://stac.dataspace.copernicus.eu/v1/search"
COLLECTION = "sentinel-2-l2a"

# Small bounding box around Madikeri / central Kodagu, Karnataka, India.
# Format: [min_lon, min_lat, max_lon, max_lat]
KODAGU_BBOX = [75.65, 12.30, 75.85, 12.50]

# Two time periods to compare: the same month, one year apart. CDSE STAC
# caps sentinel-2-l2a results at 200 per request, but we only need a
# handful, so a small "limit" is fine.
TIME_PERIODS = [
    ("Period 1 (Jan 2025)", "2025-01-01T00:00:00Z/2025-01-31T23:59:59Z"),
    ("Period 2 (Jan 2026)", "2026-01-01T00:00:00Z/2026-01-31T23:59:59Z"),
]

RESULTS_PER_PERIOD = 5

# Only return scenes with cloud cover below this percentage.
MAX_CLOUD_COVER = 10


def search_sentinel2(datetime_range, limit=RESULTS_PER_PERIOD):
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
        # STAC query extension: only return scenes below our cloud-cover
        # threshold, so we don't waste time/output on unusably cloudy scenes.
        "query": {"eo:cloud_cover": {"lt": MAX_CLOUD_COVER}},
    }

    response = requests.post(STAC_SEARCH_URL, json=request_body, timeout=30)
    response.raise_for_status()

    return response.json().get("features", [])


def print_scenes(label, items):
    print(f"\n=== {label} ===")

    if not items:
        print(f"No scenes found under {MAX_CLOUD_COVER}% cloud cover for this period/region.")
        return

    # Re-sort client-side by cloud cover, ascending, as a safety net.
    items = sorted(
        items,
        key=lambda item: item.get("properties", {}).get("eo:cloud_cover", 999),
    )

    for item in items:
        props = item.get("properties", {})
        assets = item.get("assets", {})

        print(f"Item ID       : {item.get('id')}")
        print(f"Acquired      : {props.get('datetime')}")
        print(f"Cloud cover   : {props.get('eo:cloud_cover')}%")
        print(f"Assets/bands  : {', '.join(sorted(assets.keys()))}")
        print("-" * 50)


if __name__ == "__main__":
    for label, date_range in TIME_PERIODS:
        try:
            scenes = search_sentinel2(date_range)
            print_scenes(label, scenes)
        except requests.exceptions.RequestException as exc:
            print(f"\n=== {label} ===")
            print(f"Request failed: {exc}")