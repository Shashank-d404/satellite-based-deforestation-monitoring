from pathlib import Path

import numpy as np
import rasterio


NDVI_2025 = "data/ndvi/ndvi_2025_masked.tif"
NDVI_2026 = "data/ndvi/ndvi_2026_masked.tif"

CHANGE_OUTPUT = "data/ndvi/ndvi_change_masked.tif"
MASK_OUTPUT = "data/ndvi/deforestation_mask_masked.tif"

DEFORESTATION_THRESHOLD = -0.20


def main():
    Path("data/ndvi").mkdir(parents=True, exist_ok=True)

    with rasterio.open(NDVI_2025) as src_2025:
        ndvi_2025 = src_2025.read(1)
        profile = src_2025.profile.copy()

    with rasterio.open(NDVI_2026) as src_2026:
        ndvi_2026 = src_2026.read(1)

    if ndvi_2025.shape != ndvi_2026.shape:
        raise ValueError(
            f"Shape mismatch: 2025={ndvi_2025.shape}, "
            f"2026={ndvi_2026.shape}"
        )

    # Only compare pixels that are valid in BOTH years.
    valid = (
        np.isfinite(ndvi_2025)
        & np.isfinite(ndvi_2026)
    )

    change = np.full(
        ndvi_2025.shape,
        np.nan,
        dtype="float32",
    )

    change[valid] = (
        ndvi_2026[valid] - ndvi_2025[valid]
    )

    # 1 = potential vegetation loss
    # 0 = no significant detected loss
    loss_mask = np.zeros(
        ndvi_2025.shape,
        dtype="uint8",
    )

    loss_mask[
        valid & (change < DEFORESTATION_THRESHOLD)
    ] = 1

    # Save NDVI change raster
    change_profile = profile.copy()

    change_profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        compress="lzw",
        nodata=np.nan,
    )

    with rasterio.open(
        CHANGE_OUTPUT,
        "w",
        **change_profile,
    ) as dst:
        dst.write(change, 1)

    # Save potential-loss mask
    mask_profile = profile.copy()

    mask_profile.update(
        driver="GTiff",
        dtype="uint8",
        count=1,
        compress="lzw",
        nodata=0,
    )

    with rasterio.open(
        MASK_OUTPUT,
        "w",
        **mask_profile,
    ) as dst:
        dst.write(loss_mask, 1)

    valid_change = change[valid]

    valid_pixels = int(np.sum(valid))
    loss_pixels = int(np.sum(loss_mask == 1))

    loss_percentage = (
        loss_pixels / valid_pixels * 100
        if valid_pixels > 0
        else 0
    )

    print("\n=== CLOUD-MASKED CHANGE DETECTION ===")
    print(f"Threshold             : {DEFORESTATION_THRESHOLD}")
    print(f"Common valid pixels   : {valid_pixels}")
    print(f"Minimum NDVI change   : {valid_change.min():.4f}")
    print(f"Maximum NDVI change   : {valid_change.max():.4f}")
    print(f"Mean NDVI change      : {valid_change.mean():.4f}")
    print(f"Potential loss pixels : {loss_pixels}")
    print(f"Potential loss area   : {loss_percentage:.2f}%")

    print(f"\nSaved: {CHANGE_OUTPUT}")
    print(f"Saved: {MASK_OUTPUT}")


if __name__ == "__main__":
    main()
