"""
Proof-of-concept: remotely read a small window (just our Kodagu test
region) out of the B04 (red) and B08 (NIR) Sentinel-2 Cloud-Optimized
GeoTIFFs, for the two scenes we already located via Earth Search STAC
(test_earth_search.py), WITHOUT downloading the full ~100km x 100km tile.

How remote windowed reading works:
    A Cloud-Optimized GeoTIFF (COG) is a regular GeoTIFF whose internal
    data is organized as a grid of independently-compressed tiles, with
    an index of "which byte range holds which tile" stored up front in
    the file. Because of that layout, a client doesn't need the whole
    file to read one small area -- it only needs to:
        1. Fetch the file's header/index (a tiny HTTP range request).
        2. Work out which tiles overlap the area we care about.
        3. Fetch just those tiles (a handful more small HTTP range
           requests), instead of the entire multi-hundred-MB file.
    GDAL (which rasterio wraps) does this automatically via its "/vsicurl/"
    virtual filesystem: when you open a path prefixed with /vsicurl/, GDAL
    talks to the URL using HTTP Range headers instead of downloading it,
    and rasterio.windows.from_bounds() tells GDAL exactly which pixel
    region to fetch. So opening the dataset is cheap (metadata only), and
    src.read(window=...) is what triggers the small number of targeted
    byte-range fetches for just our window -- the rest of the ~100km tile
    is never transferred.

This script:
    1. Re-runs the same STAC search as test_earth_search.py to get the
       best (lowest-cloud) scene's red/NIR COG URLs for 2025-01-05 and
       2026-01-05, over the same Kodagu bounding box.
    2. Opens each COG remotely with rasterio and reads only the small
       window covering KODAGU_BBOX.
    3. Applies the raster's scale/offset metadata (if the asset defines
       any) to convert raw digital numbers to physical reflectance
       values, and prints basic stats for that window.

No NDVI, no downloading of full scenes, no Flask/AI/ML/database/frontend
code -- just remote windowed reads and their stats.
"""

from datetime import datetime, timedelta

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds

import requests

# --- STAC search setup (same as test_earth_search.py) ----------------------

STAC_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"

# Same test area as our other Sentinel-2 scripts: small bounding box around
# Madikeri / central Kodagu, Karnataka, India, in EPSG:4326 (lon/lat).
KODAGU_BBOX = [75.65, 12.30, 75.85, 12.50]

TARGET_DATES = [
    "2025-01-05",
    "2026-01-05",
]

WINDOW_DAYS = 5

RED_ASSET_CANDIDATES = ["red", "B04"]
NIR_ASSET_CANDIDATES = ["nir", "B08"]
COG_TYPE_HINTS = ["geotiff", "cog", "cloud-optimized"]


def date_window(target_date_str, days=WINDOW_DAYS):
    target = datetime.strptime(target_date_str, "%Y-%m-%d")
    start = target - timedelta(days=days)
    end = target + timedelta(days=days)
    return f"{start:%Y-%m-%d}T00:00:00Z/{end:%Y-%m-%d}T23:59:59Z"


def search_sentinel2(datetime_range, limit=20):
    request_body = {
        "collections": [COLLECTION],
        "bbox": KODAGU_BBOX,
        "datetime": datetime_range,
        "limit": limit,
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
    }
    response = requests.post(STAC_SEARCH_URL, json=request_body, timeout=30)
    response.raise_for_status()
    return response.json().get("features", [])


def pick_best_scene(items):
    if not items:
        return None
    return min(
        items,
        key=lambda item: item.get("properties", {}).get("eo:cloud_cover", 999),
    )


def find_cog_href(assets, candidate_keys):
    for key in candidate_keys:
        asset = assets.get(key)
        if asset is None:
            continue
        asset_type = asset.get("type", "").lower()
        if any(hint in asset_type for hint in COG_TYPE_HINTS):
            return asset.get("href")
    return None


def get_best_scene_bands(target_date_str):
    """Search near target_date_str and return (item_id, red_href, nir_href)
    for the lowest-cloud scene, or (None, None, None) if nothing found."""

    scenes = search_sentinel2(date_window(target_date_str))
    best = pick_best_scene(scenes)

    if best is None:
        return None, None, None

    assets = best.get("assets", {})
    red_href = find_cog_href(assets, RED_ASSET_CANDIDATES)
    nir_href = find_cog_href(assets, NIR_ASSET_CANDIDATES)

    return best.get("id"), red_href, nir_href


# --- Remote windowed COG reading --------------------------------------------


def read_window_stats(href, band_label):
    """Open a COG remotely (no full download) and read only the small
    window covering KODAGU_BBOX, applying scale/offset if present."""

    # /vsicurl/ tells GDAL to treat this as a remote file accessed via
    # HTTP range requests, rather than something to download first.
    vsi_path = f"/vsicurl/{href}"

    # These GDAL settings keep remote reads lean: don't try to list a
    # directory of sibling files, and only fetch .tif-like URLs.
    gdal_env = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
    }

    with rasterio.Env(**gdal_env):
        with rasterio.open(vsi_path) as src:
            # KODAGU_BBOX is in EPSG:4326; the COG is usually in a UTM CRS,
            # so reproject our bbox into the raster's own CRS first.
            window_bounds = transform_bounds(
                "EPSG:4326", src.crs, *KODAGU_BBOX
            )

            # Convert those ground-coordinate bounds into a pixel window
            # (row/col offsets + size) using the dataset's affine transform.
            window = from_bounds(*window_bounds, transform=src.transform)

            # This is the actual network I/O: GDAL fetches only the tiles
            # that overlap this pixel window, via HTTP range requests.
            data = src.read(1, window=window)

            # Apply the band's scale/offset metadata, if the COG defines
            # any, to convert raw digital numbers to physical values.
            # rasterio exposes these as per-band tuples; default to
            # scale=1.0, offset=0.0 (i.e. a no-op) when absent.
            scale = src.scales[0] if src.scales and src.scales[0] else 1.0
            offset = src.offsets[0] if src.offsets and src.offsets[0] else 0.0
            data = data.astype("float64") * scale + offset

            print(f"\n--- {band_label} ---")
            print(f"CRS           : {src.crs}")
            print(f"Width/Height  : {src.width} x {src.height} (full dataset)")
            print(f"Bounds        : {src.bounds} (full dataset)")
            print(f"Window shape  : {data.shape}")
            print(f"Scale/Offset  : {scale} / {offset}")
            print(f"Min value     : {np.nanmin(data)}")
            print(f"Max value     : {np.nanmax(data)}")
            print(f"Mean value    : {np.nanmean(data)}")


if __name__ == "__main__":
    for target_date in TARGET_DATES:
        print(f"\n=== Scene near {target_date} ===")

        try:
            item_id, red_href, nir_href = get_best_scene_bands(target_date)
        except requests.exceptions.RequestException as exc:
            print(f"STAC search failed: {exc}")
            continue

        if item_id is None:
            print(f"No scenes found within {WINDOW_DAYS} days of this date.")
            continue

        print(f"Item ID: {item_id}")

        if red_href:
            read_window_stats(red_href, "B04 (red)")
        else:
            print("Red band COG not available for this scene.")

        if nir_href:
            read_window_stats(nir_href, "B08 (NIR)")
        else:
            print("NIR band COG not available for this scene.")