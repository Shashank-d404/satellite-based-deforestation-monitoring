import json
from pathlib import Path

import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom


MASK_PATH = "data/ndvi/deforestation_mask_masked.tif"
OUTPUT_PATH = "data/ndvi/deforestation_masked.geojson"


def main():
    with rasterio.open(MASK_PATH) as src:
        mask = src.read(1)

        features = []

        for geometry, value in shapes(
            mask,
            mask=(mask == 1),
            transform=src.transform,
        ):
            if value != 1:
                continue

            geometry_wgs84 = transform_geom(
                src.crs,
                "EPSG:4326",
                geometry,
                precision=6,
            )

            features.append({
                "type": "Feature",
                "properties": {
                    "type": "potential_vegetation_loss",
                    "method": "cloud_masked_ndvi_change",
                    "threshold": -0.20
                },
                "geometry": geometry_wgs84,
            })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(geojson, f)

    print(f"GeoJSON saved to: {OUTPUT_PATH}")
    print(f"Detected regions: {len(features)}")


if __name__ == "__main__":
    main()
