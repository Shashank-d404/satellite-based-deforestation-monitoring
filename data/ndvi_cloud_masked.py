from pathlib import Path

import numpy as np
import planetary_computer
import pystac_client
import rasterio


CATALOG_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

catalog = pystac_client.Client.open(
    CATALOG_URL,
    modifier=planetary_computer.sign_inplace,
)

OUTPUT_DIR = Path("data/ndvi")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_scene(date_str):
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        datetime=f"{date_str}T00:00:00Z/{date_str}T23:59:59Z",
        query={"s2:mgrs_tile": {"eq": "43PEP"}},
        max_items=10,
    )

    items = list(search.items())

    if not items:
        raise RuntimeError(f"No Sentinel-2 scene found for {date_str}")

    items.sort(
        key=lambda item: item.properties.get("eo:cloud_cover", 100)
    )

    return items[0]


def read_band(url, size=512, resampling=rasterio.enums.Resampling.bilinear):
    with rasterio.open(url) as src:
        data = src.read(
            1,
            out_shape=(1, size, size),
            resampling=resampling,
            masked=True,
        )

        transform = src.transform * rasterio.Affine.scale(
            src.width / size,
            src.height / size,
        )

        profile = src.profile.copy()

    return data, transform, profile


def calculate_masked_ndvi(date_str, output_path):
    item = get_scene(date_str)

    print(f"\n=== {date_str} ===")
    print("Item ID     :", item.id)
    print("Cloud cover :", item.properties.get("eo:cloud_cover"))
    print("Acquired    :", item.properties.get("datetime"))

    red_url = item.assets["B04"].href
    nir_url = item.assets["B08"].href
    scl_url = item.assets["SCL"].href

    print("Reading B04...")
    red, transform, profile = read_band(red_url)

    print("Reading B08...")
    nir, _, _ = read_band(nir_url)

    print("Reading SCL...")
    scl, _, _ = read_band(
        scl_url,
        resampling=rasterio.enums.Resampling.nearest,
    )

    red = red.astype("float32")
    nir = nir.astype("float32")
    scl = scl.astype("uint8")

    # Keep vegetation and bare-soil pixels.
    # These are the useful land classes for our initial
    # vegetation-change analysis.
    valid_scl = (scl == 4) | (scl == 5)

    denominator = nir + red

    ndvi = np.full(
        red.shape,
        np.nan,
        dtype="float32",
    )

    valid = (
        valid_scl
        & np.isfinite(red)
        & np.isfinite(nir)
        & (denominator != 0)
    )

    ndvi[valid] = (
        (nir[valid] - red[valid])
        / denominator[valid]
    )

    profile.update(
        driver="GTiff",
        height=ndvi.shape[0],
        width=ndvi.shape[1],
        count=1,
        dtype="float32",
        transform=transform,
        compress="lzw",
        nodata=np.nan,
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(ndvi, 1)

    valid_values = ndvi[np.isfinite(ndvi)]

    print(f"Saved: {output_path}")
    print(f"Valid pixels: {len(valid_values)}")
    print(f"Minimum NDVI: {valid_values.min():.4f}")
    print(f"Maximum NDVI: {valid_values.max():.4f}")
    print(f"Mean NDVI:    {valid_values.mean():.4f}")


calculate_masked_ndvi(
    "2025-01-05",
    OUTPUT_DIR / "ndvi_2025_masked.tif",
)

calculate_masked_ndvi(
    "2026-01-05",
    OUTPUT_DIR / "ndvi_2026_masked.tif",
)

print("\nCloud-masked NDVI processing completed.")
