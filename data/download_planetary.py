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

Path("data/ndvi").mkdir(parents=True, exist_ok=True)


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


def calculate_ndvi(date_str, output_path):
    item = get_scene(date_str)

    print(f"\n=== {date_str} ===")
    print("Item ID     :", item.id)
    print("Cloud cover :", item.properties.get("eo:cloud_cover"))
    print("Acquired    :", item.properties.get("datetime"))

    # Sign the asset URLs for temporary read access
    red_url = item.assets["B04"].href
    nir_url = item.assets["B08"].href

    print("Reading B04 and B08 remotely...")

    # Read a low-resolution version of the complete tile.
    # This avoids downloading the massive original files.
    with rasterio.open(red_url) as red_src:
        red = red_src.read(
            1,
            out_shape=(1, 512, 512),
            masked=True,
            resampling=rasterio.enums.Resampling.bilinear,
        )

        profile = red_src.profile.copy()
        transform = red_src.transform

        # Adjust transform for the resized raster.
        scale_x = red_src.width / 512
        scale_y = red_src.height / 512

        transform = transform * rasterio.Affine.scale(
            scale_x,
            scale_y,
        )

    with rasterio.open(nir_url) as nir_src:
        nir = nir_src.read(
            1,
            out_shape=(1, 512, 512),
            masked=True,
            resampling=rasterio.enums.Resampling.bilinear,
        )

    red = red.astype("float32")
    nir = nir.astype("float32")

    denominator = nir + red

    ndvi = np.ma.divide(
        nir - red,
        denominator,
    )

    ndvi = np.ma.filled(ndvi, np.nan).astype("float32")

    profile.update(
        driver="GTiff",
        height=512,
        width=512,
        count=1,
        dtype="float32",
        transform=transform,
        compress="lzw",
        nodata=np.nan,
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(ndvi, 1)

    valid = ndvi[~np.isnan(ndvi)]

    print(f"NDVI saved to: {output_path}")
    print(f"Minimum NDVI: {valid.min():.4f}")
    print(f"Maximum NDVI: {valid.max():.4f}")
    print(f"Mean NDVI:    {valid.mean():.4f}")


calculate_ndvi(
    "2025-01-05",
    "data/ndvi/ndvi_2025.tif",
)

calculate_ndvi(
    "2026-01-05",
    "data/ndvi/ndvi_2026.tif",
)

print("\nNDVI processing completed.")
