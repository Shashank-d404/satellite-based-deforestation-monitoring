import numpy as np
import rasterio


def calculate_ndvi(red_path, nir_path, output_path):
    with rasterio.open(red_path) as red_src:
        red = red_src.read(1).astype("float32")
        profile = red_src.profile.copy()

    with rasterio.open(nir_path) as nir_src:
        nir = nir_src.read(1).astype("float32")

    # Avoid division by zero
    denominator = nir + red

    ndvi = np.divide(
        nir - red,
        denominator,
        out=np.zeros_like(red, dtype="float32"),
        where=denominator != 0
    )

    profile.update(
        dtype="float32",
        count=1,
        compress="lzw"
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(ndvi, 1)

    print(f"NDVI saved to: {output_path}")
    print(f"Minimum NDVI: {np.nanmin(ndvi):.4f}")
    print(f"Maximum NDVI: {np.nanmax(ndvi):.4f}")
    print(f"Mean NDVI:    {np.nanmean(ndvi):.4f}")


if __name__ == "__main__":
    calculate_ndvi(
        "data/B04_2025.jp2",
        "data/B08_2025.jp2",
        "data/ndvi_2025.tif"
    )
