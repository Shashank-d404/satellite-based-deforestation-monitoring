from pathlib import Path
import json

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from PIL import Image


# ==================================================
# Paths
# ==================================================

NDVI_DIR = Path("data/ndvi")
VISUAL_DIR = NDVI_DIR / "visuals"

VISUAL_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# Color helpers
# ==================================================

def ndvi_to_rgba(data):
    """
    Convert NDVI values (-1 to 1) into an RGBA image.

    Low NDVI  -> brown/orange
    Mid NDVI  -> yellow
    High NDVI -> green
    """

    normalized = np.clip(
        (data + 1.0) / 2.0,
        0.0,
        1.0
    )

    # Brown -> yellow -> green
    stops = np.array([
        [165, 42, 42],
        [240, 200, 60],
        [34, 139, 34]
    ], dtype=np.float32)

    rgba = np.zeros(
        (*data.shape, 4),
        dtype=np.uint8
    )

    low = normalized < 0.5
    high = ~low

    # Lower half: brown -> yellow
    t_low = normalized[low] * 2.0

    low_rgb = (
        stops[0]
        + (stops[1] - stops[0]) * t_low[:, None]
    )

    # Upper half: yellow -> green
    t_high = (normalized[high] - 0.5) * 2.0

    high_rgb = (
        stops[1]
        + (stops[2] - stops[1]) * t_high[:, None]
    )

    rgba[low, :3] = np.clip(
        low_rgb,
        0,
        255
    ).astype(np.uint8)

    rgba[high, :3] = np.clip(
        high_rgb,
        0,
        255
    ).astype(np.uint8)

    rgba[:, :, 3] = np.where(
        np.isfinite(data),
        210,
        0
    ).astype(np.uint8)

    return rgba


def change_to_rgba(data):
    """
    Convert NDVI change into an RGBA image.

    Negative change -> red
    Near zero        -> white
    Positive change  -> green
    """

    # Keep the visualization range stable.
    clipped = np.clip(
        data,
        -0.4,
        0.4
    )

    normalized = (
        clipped + 0.4
    ) / 0.8

    rgba = np.zeros(
        (*data.shape, 4),
        dtype=np.uint8
    )

    # Red -> white -> green
    red = np.zeros_like(normalized)
    green = np.zeros_like(normalized)
    blue = np.zeros_like(normalized)

    negative = normalized < 0.5
    positive = ~negative

    # Negative: red -> white
    t_negative = normalized[negative] * 2.0

    red[negative] = 220
    green[negative] = (
        80
        + 175 * t_negative
    )
    blue[negative] = (
        80
        + 175 * t_negative
    )

    # Positive: white -> green
    t_positive = (
        normalized[positive] - 0.5
    ) * 2.0

    red[positive] = (
        255
        - 175 * t_positive
    )

    green[positive] = 255

    blue[positive] = (
        255
        - 175 * t_positive
    )

    rgba[:, :, 0] = np.clip(
        red,
        0,
        255
    ).astype(np.uint8)

    rgba[:, :, 1] = np.clip(
        green,
        0,
        255
    ).astype(np.uint8)

    rgba[:, :, 2] = np.clip(
        blue,
        0,
        255
    ).astype(np.uint8)

    rgba[:, :, 3] = np.where(
        np.isfinite(data),
        190,
        0
    ).astype(np.uint8)

    return rgba


# ==================================================
# Create visualization
# ==================================================

def create_visual(
    input_path,
    output_path,
    mode
):

    print(f"\nReading: {input_path}")

    with rasterio.open(input_path) as src:

        data = src.read(1).astype(
            "float32"
        )

        bounds = src.bounds

        crs = src.crs

        width = src.width
        height = src.height


    if mode == "ndvi":

        rgba = ndvi_to_rgba(data)

    elif mode == "change":

        rgba = change_to_rgba(data)

    else:

        raise ValueError(
            f"Unknown visualization mode: {mode}"
        )


    image = Image.fromarray(
        rgba,
        mode="RGBA"
    )

    image.save(
        output_path,
        optimize=True
    )


    # Convert raster bounds to WGS84
    west, south, east, north = transform_bounds(
        crs,
        "EPSG:4326",
        bounds.left,
        bounds.bottom,
        bounds.right,
        bounds.top
    )


    return {
        "image": str(output_path),
        "bounds": [
            [south, west],
            [north, east]
        ],
        "width": width,
        "height": height,
        "crs": str(crs)
    }


# ==================================================
# Generate all visualizations
# ==================================================

def main():

    outputs = {}


    # ------------------------------------------------
    # NDVI 2025
    # ------------------------------------------------

    outputs["ndvi_2025"] = create_visual(
        NDVI_DIR / "ndvi_2025_masked.tif",
        VISUAL_DIR / "ndvi_2025.png",
        "ndvi"
    )


    # ------------------------------------------------
    # NDVI 2026
    # ------------------------------------------------

    outputs["ndvi_2026"] = create_visual(
        NDVI_DIR / "ndvi_2026_masked.tif",
        VISUAL_DIR / "ndvi_2026.png",
        "ndvi"
    )


    # ------------------------------------------------
    # NDVI Change
    # ------------------------------------------------

    outputs["ndvi_change"] = create_visual(
        NDVI_DIR / "ndvi_change_masked.tif",
        VISUAL_DIR / "ndvi_change.png",
        "change"
    )


    # ------------------------------------------------
    # Save metadata
    # ------------------------------------------------

    metadata_path = (
        VISUAL_DIR / "metadata.json"
    )

    with open(
        metadata_path,
        "w"
    ) as f:

        json.dump(
            outputs,
            f,
            indent=2
        )


    print("\n====================================")
    print("NDVI visualizations created")
    print("====================================")

    for name, info in outputs.items():

        print(
            f"{name}: "
            f"{info['image']}"
        )

    print(
        f"\nMetadata: {metadata_path}"
    )


if __name__ == "__main__":
    main()
