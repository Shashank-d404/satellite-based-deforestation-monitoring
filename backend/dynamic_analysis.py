import json
from pathlib import Path

import numpy as np
import planetary_computer
import pystac_client
import rasterio
from PIL import Image
from rasterio.features import shapes
from rasterio.warp import transform_bounds, transform_geom


# ==================================================
# CONFIGURATION
# ==================================================

CATALOG_URL = (
    "https://planetarycomputer.microsoft.com/api/stac/v1"
)

STUDY_TILE = "43PEP"

COMPARISON_MONTH = 1

IMAGE_SIZE = 512

DEFORESTATION_THRESHOLD = -0.20

OUTPUT_ROOT = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "dynamic_analysis"
)

OUTPUT_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


# ==================================================
# STAC CATALOG
# ==================================================

catalog = pystac_client.Client.open(
    CATALOG_URL,
    modifier=planetary_computer.sign_inplace
)


# ==================================================
# FIND BEST SCENE
# ==================================================

def find_scene(year):

    start_date = (
        f"{year}-{COMPARISON_MONTH:02d}-01T00:00:00Z"
    )

    if COMPARISON_MONTH == 12:

        next_year = year + 1
        next_month = 1

    else:

        next_year = year
        next_month = COMPARISON_MONTH + 1


    end_date = (
        f"{next_year}-{next_month:02d}-01T00:00:00Z"
    )


    search = catalog.search(
        collections=["sentinel-2-l2a"],
        datetime=f"{start_date}/{end_date}",
        query={
            "s2:mgrs_tile": {
                "eq": STUDY_TILE
            }
        },
        max_items=50
    )


    items = list(
        search.items()
    )


    if not items:

        raise RuntimeError(
            f"No Sentinel-2 L2A scene found "
            f"for {year} in tile {STUDY_TILE}."
        )


    items.sort(
        key=lambda item:
            item.properties.get(
                "eo:cloud_cover",
                100
            )
    )


    return items[0]


# ==================================================
# READ REMOTE BAND
# ==================================================

def read_band(
    url,
    size=IMAGE_SIZE,
    resampling=rasterio.enums.Resampling.bilinear
):

    with rasterio.open(url) as src:

        raw_data = src.read(
            1,
            out_shape=(1, size, size),
            masked=True,
            resampling=resampling
        )

        # IMPORTANT:
        # Convert to float32 BEFORE filling masked
        # pixels with NaN. This prevents the uint16
        # SCL raster from failing on NaN conversion.
        data = (
            raw_data
            .astype("float32")
            .filled(np.nan)
        )

        transform = (
            src.transform
            * rasterio.Affine.scale(
                src.width / size,
                src.height / size
            )
        )

        profile = src.profile.copy()

        crs = src.crs

        bounds = src.bounds


    return (
        data,
        transform,
        profile,
        crs,
        bounds
    )


# ==================================================
# PROCESS ONE YEAR
# ==================================================

def process_year(year):

    print(
        f"\nProcessing {year}..."
    )


    item = find_scene(
        year
    )


    print(
        "Scene:",
        item.id
    )


    print(
        "Cloud cover:",
        item.properties.get(
            "eo:cloud_cover"
        )
    )


    print(
        "Acquired:",
        item.properties.get(
            "datetime"
        )
    )


    red_url = item.assets["B04"].href

    nir_url = item.assets["B08"].href

    scl_url = item.assets["SCL"].href


    print(
        "Reading B04..."
    )


    (
        red,
        transform,
        profile,
        crs,
        bounds
    ) = read_band(
        red_url
    )


    print(
        "Reading B08..."
    )


    nir, _, _, _, _ = read_band(
        nir_url
    )


    print(
        "Reading SCL..."
    )


    scl, _, _, _, _ = read_band(
        scl_url,
        resampling=
            rasterio.enums.Resampling.nearest
    )


    # SCL is integer classification data.
    # We now convert it safely from float32.
    scl = np.rint(
        scl
    ).astype("uint8")


    # ------------------------------------------------
    # Keep vegetation and bare-soil pixels.
    #
    # SCL 4 = vegetation
    # SCL 5 = bare soil
    # ------------------------------------------------

    valid_scl = (
        (scl == 4)
        | (scl == 5)
    )


    denominator = (
        nir + red
    )


    ndvi = np.full(
        red.shape,
        np.nan,
        dtype="float32"
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


    valid_values = ndvi[
        np.isfinite(ndvi)
    ]


    if len(valid_values) == 0:

        raise RuntimeError(
            f"No valid NDVI pixels found for {year}."
        )


    return {

        "year":
            year,

        "item_id":
            item.id,

        "acquired":
            item.properties.get(
                "datetime"
            ),

        "cloud_cover":
            item.properties.get(
                "eo:cloud_cover"
            ),

        "ndvi":
            ndvi,

        "transform":
            transform,

        "profile":
            profile,

        "crs":
            crs,

        "bounds":
            bounds

    }


# ==================================================
# NDVI VISUALIZATION
# ==================================================

def ndvi_to_rgba(data):

    normalized = np.clip(
        (data + 1.0) / 2.0,
        0.0,
        1.0
    )


    rgba = np.zeros(
        (*data.shape, 4),
        dtype=np.uint8
    )


    low = (
        normalized < 0.5
    )


    high = ~low


    # ------------------------------------------------
    # Brown -> Yellow
    # ------------------------------------------------

    t_low = (
        normalized[low] * 2.0
    )


    low_red = (
        165
        + (240 - 165) * t_low
    )


    low_green = (
        42
        + (200 - 42) * t_low
    )


    low_blue = (
        42
        + (60 - 42) * t_low
    )


    rgba[low, 0] = np.clip(
        low_red,
        0,
        255
    ).astype(np.uint8)


    rgba[low, 1] = np.clip(
        low_green,
        0,
        255
    ).astype(np.uint8)


    rgba[low, 2] = np.clip(
        low_blue,
        0,
        255
    ).astype(np.uint8)


    # ------------------------------------------------
    # Yellow -> Green
    # ------------------------------------------------

    t_high = (
        normalized[high] - 0.5
    ) * 2.0


    high_red = (
        240
        + (34 - 240) * t_high
    )


    high_green = (
        200
        + (139 - 200) * t_high
    )


    high_blue = (
        60
        + (34 - 60) * t_high
    )


    rgba[high, 0] = np.clip(
        high_red,
        0,
        255
    ).astype(np.uint8)


    rgba[high, 1] = np.clip(
        high_green,
        0,
        255
    ).astype(np.uint8)


    rgba[high, 2] = np.clip(
        high_blue,
        0,
        255
    ).astype(np.uint8)


    rgba[:, :, 3] = np.where(
        np.isfinite(data),
        210,
        0
    ).astype(np.uint8)


    return rgba


# ==================================================
# NDVI CHANGE VISUALIZATION
# ==================================================

def change_to_rgba(data):

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


    negative = (
        normalized < 0.5
    )


    positive = ~negative


    # ------------------------------------------------
    # Red -> White
    # ------------------------------------------------

    t_negative = (
        normalized[negative] * 2.0
    )


    rgba[negative, 0] = 220


    rgba[negative, 1] = (
        80
        + 175 * t_negative
    ).astype(np.uint8)


    rgba[negative, 2] = (
        80
        + 175 * t_negative
    ).astype(np.uint8)


    # ------------------------------------------------
    # White -> Green
    # ------------------------------------------------

    t_positive = (
        normalized[positive] - 0.5
    ) * 2.0


    rgba[positive, 0] = (
        255
        - 175 * t_positive
    ).astype(np.uint8)


    rgba[positive, 1] = 255


    rgba[positive, 2] = (
        255
        - 175 * t_positive
    ).astype(np.uint8)


    rgba[:, :, 3] = np.where(
        np.isfinite(data),
        190,
        0
    ).astype(np.uint8)


    return rgba


# ==================================================
# SAVE PNG
# ==================================================

def save_png(
    data,
    output_path,
    mode
):

    if mode == "ndvi":

        rgba = ndvi_to_rgba(
            data
        )

    elif mode == "change":

        rgba = change_to_rgba(
            data
        )

    else:

        raise ValueError(
            f"Unknown mode: {mode}"
        )


    image = Image.fromarray(
        rgba,
        "RGBA"
    )


    image.save(
        output_path,
        optimize=True
    )


# ==================================================
# CREATE GEOJSON
# ==================================================

def create_geojson(
    loss_mask,
    transform,
    crs,
    output_path
):

    features = []


    for geometry, value in shapes(
        loss_mask,
        mask=(loss_mask == 1),
        transform=transform
    ):

        if value != 1:
            continue


        geometry_wgs84 = transform_geom(
            crs,
            "EPSG:4326",
            geometry,
            precision=6
        )


        features.append({

            "type":
                "Feature",

            "properties": {

                "type":
                    "potential_vegetation_loss",

                "method":
                    "cloud_masked_ndvi_change",

                "threshold":
                    DEFORESTATION_THRESHOLD

            },

            "geometry":
                geometry_wgs84

        })


    geojson = {

        "type":
            "FeatureCollection",

        "features":
            features

    }


    with open(
        output_path,
        "w"
    ) as f:

        json.dump(
            geojson,
            f
        )


    return len(features)


# ==================================================
# RUN YEAR COMPARISON
# ==================================================

def run_comparison(
    baseline_year,
    current_year
):

    if baseline_year >= current_year:

        raise ValueError(
            "Baseline year must be earlier "
            "than current year."
        )


    pair_name = (
        f"{baseline_year}_{current_year}"
    )


    output_dir = (
        OUTPUT_ROOT / pair_name
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    metadata_path = (
        output_dir / "metadata.json"
    )


    expected_files = [

        output_dir /
        "ndvi_baseline.png",

        output_dir /
        "ndvi_current.png",

        output_dir /
        "ndvi_change.png",

        output_dir /
        "potential_loss.geojson"

    ]


    # ------------------------------------------------
    # Use cache when available.
    # ------------------------------------------------

    if (
        metadata_path.exists()
        and all(
            path.exists()
            for path in expected_files
        )
    ):

        print(
            f"\nUsing cached analysis: "
            f"{pair_name}"
        )


        with open(
            metadata_path,
            "r"
        ) as f:

            return json.load(f)


    # ------------------------------------------------
    # Process selected years.
    # ------------------------------------------------

    baseline = process_year(
        baseline_year
    )


    current = process_year(
        current_year
    )


    baseline_ndvi = (
        baseline["ndvi"]
    )


    current_ndvi = (
        current["ndvi"]
    )


    if (
        baseline_ndvi.shape
        != current_ndvi.shape
    ):

        raise RuntimeError(
            "The selected scenes have "
            "different raster dimensions."
        )


    # ------------------------------------------------
    # Calculate NDVI difference.
    # ------------------------------------------------

    valid = (
        np.isfinite(
            baseline_ndvi
        )
        &
        np.isfinite(
            current_ndvi
        )
    )


    change = np.full(
        baseline_ndvi.shape,
        np.nan,
        dtype="float32"
    )


    change[valid] = (
        current_ndvi[valid]
        -
        baseline_ndvi[valid]
    )


    # ------------------------------------------------
    # Detect potential vegetation loss.
    # ------------------------------------------------

    loss_mask = np.zeros(
        baseline_ndvi.shape,
        dtype="uint8"
    )


    loss_mask[
        valid
        &
        (
            change
            < DEFORESTATION_THRESHOLD
        )
    ] = 1


    valid_change = change[
        np.isfinite(change)
    ]


    common_valid_pixels = int(
        np.sum(valid)
    )


    potential_loss_pixels = int(
        np.sum(
            loss_mask == 1
        )
    )


    potential_loss_share = (

        potential_loss_pixels
        / common_valid_pixels
        * 100

        if common_valid_pixels
        else 0

    )


    # ------------------------------------------------
    # Save visualizations.
    # ------------------------------------------------

    save_png(
        baseline_ndvi,
        output_dir /
        "ndvi_baseline.png",
        "ndvi"
    )


    save_png(
        current_ndvi,
        output_dir /
        "ndvi_current.png",
        "ndvi"
    )


    save_png(
        change,
        output_dir /
        "ndvi_change.png",
        "change"
    )


    # ------------------------------------------------
    # Create GeoJSON.
    # ------------------------------------------------

    region_count = create_geojson(

        loss_mask,

        baseline["transform"],

        baseline["crs"],

        output_dir /
        "potential_loss.geojson"

    )


    # ------------------------------------------------
    # Geographic bounds.
    # ------------------------------------------------

    baseline_bounds = (
        baseline["bounds"]
    )


    west, south, east, north = (
        transform_bounds(

            baseline["crs"],

            "EPSG:4326",

            baseline_bounds.left,

            baseline_bounds.bottom,

            baseline_bounds.right,

            baseline_bounds.top

        )
    )


    map_bounds = [

        [south, west],

        [north, east]

    ]


    # ------------------------------------------------
    # Metadata.
    # ------------------------------------------------

    metadata = {

        "comparison": {

            "baseline_year":
                baseline_year,

            "current_year":
                current_year,

            "month":
                "January",

            "study_tile":
                STUDY_TILE

        },


        "method":
            "Cloud-masked NDVI change detection",


        "threshold":
            DEFORESTATION_THRESHOLD,


        "statistics": {

            "mean_ndvi_change":
                float(
                    valid_change.mean()
                ),

            "minimum_ndvi_change":
                float(
                    valid_change.min()
                ),

            "maximum_ndvi_change":
                float(
                    valid_change.max()
                ),

            "potential_loss_pixels":
                potential_loss_pixels,

            "valid_pixels":
                common_valid_pixels,

            "potential_loss_share":
                float(
                    potential_loss_share
                ),

            "detected_regions":
                region_count

        },


        "baseline_scene": {

            "item_id":
                baseline["item_id"],

            "acquired":
                baseline["acquired"],

            "cloud_cover":
                baseline["cloud_cover"]

        },


        "current_scene": {

            "item_id":
                current["item_id"],

            "acquired":
                current["acquired"],

            "cloud_cover":
                current["cloud_cover"]

        },


        "bounds":
            map_bounds,


        "layers": {

            "ndvi_baseline": {

                "label":
                    f"NDVI {baseline_year}",

                "url":
                    f"/dynamic/{pair_name}/"
                    f"ndvi_baseline.png",

                "bounds":
                    map_bounds

            },


            "ndvi_current": {

                "label":
                    f"NDVI {current_year}",

                "url":
                    f"/dynamic/{pair_name}/"
                    f"ndvi_current.png",

                "bounds":
                    map_bounds

            },


            "ndvi_change": {

                "label":
                    f"NDVI Change "
                    f"{baseline_year} → "
                    f"{current_year}",

                "url":
                    f"/dynamic/{pair_name}/"
                    f"ndvi_change.png",

                "bounds":
                    map_bounds

            },


            "potential_loss": {

                "label":
                    "Potential vegetation loss",

                "url":
                    f"/dynamic/{pair_name}/"
                    f"potential_loss.geojson"

            }

        }

    }


    with open(
        metadata_path,
        "w"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2
        )


    print(
        f"\nCompleted comparison: "
        f"{baseline_year} → "
        f"{current_year}"
    )


    print(
        "Mean NDVI change:",
        f"{metadata['statistics']['mean_ndvi_change']:.4f}"
    )


    print(
        "Potential loss pixels:",
        potential_loss_pixels
    )


    print(
        "Potential loss share:",
        f"{potential_loss_share:.2f}%"
    )


    print(
        "Detected regions:",
        region_count
    )


    return metadata