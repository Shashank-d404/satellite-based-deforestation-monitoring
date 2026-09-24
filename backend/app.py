import json
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory


# ==================================================
# PROJECT PATHS
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = BASE_DIR / "frontend"
NDVI_DIR = BASE_DIR / "data" / "ndvi"
VISUAL_DIR = NDVI_DIR / "visuals"


# ==================================================
# FLASK APPLICATION
# ==================================================

app = Flask(__name__)


# ==================================================
# FRONTEND ROUTES
# ==================================================

@app.route("/")
def home():
    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.route("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(
        FRONTEND_DIR,
        filename
    )


# ==================================================
# NDVI VISUALIZATION FILES
# ==================================================

@app.route("/visuals/<path:filename>")
def visualization_files(filename):
    return send_from_directory(
        VISUAL_DIR,
        filename
    )


# ==================================================
# HEALTH CHECK
# ==================================================

@app.route("/api/health", methods=["GET"])
def health_check():

    return jsonify({
        "status": "ok",
        "message": "Forest Monitor API is running"
    })


# ==================================================
# SATELLITE ANALYSIS
# ==================================================

@app.route("/api/analysis", methods=["GET"])
def analysis():

    return jsonify({

        "project":
            "Satellite-Based Deforestation Monitoring",

        "comparison": {
            "baseline_year": 2025,
            "current_year": 2026
        },

        "method":
            "Cloud-masked NDVI change detection",

        "threshold":
            -0.20,

        "statistics": {

            "mean_ndvi_change":
                -0.0052,

            "minimum_ndvi_change":
                -0.3792,

            "maximum_ndvi_change":
                0.1958,

            "potential_loss_pixels":
                23,

            "valid_pixels":
                192608,

            "potential_loss_share":
                0.01
        },

        "outputs": {

            "ndvi_2025":
                str(
                    NDVI_DIR /
                    "ndvi_2025_masked.tif"
                ),

            "ndvi_2026":
                str(
                    NDVI_DIR /
                    "ndvi_2026_masked.tif"
                ),

            "ndvi_change":
                str(
                    NDVI_DIR /
                    "ndvi_change_masked.tif"
                ),

            "deforestation_mask":
                str(
                    NDVI_DIR /
                    "deforestation_mask_masked.tif"
                )
        }
    })


# ==================================================
# POTENTIAL VEGETATION-LOSS GEOJSON
# ==================================================

@app.route("/api/deforestation", methods=["GET"])
def deforestation():

    geojson_path = (
        NDVI_DIR /
        "deforestation_masked.geojson"
    )

    if not geojson_path.exists():

        return jsonify({
            "error":
                "Cloud-masked deforestation GeoJSON not found"
        }), 404

    with open(
        geojson_path,
        "r"
    ) as f:

        data = json.load(f)

    return jsonify(data)


# ==================================================
# NDVI VISUALIZATION METADATA
# ==================================================

@app.route("/api/visuals", methods=["GET"])
def visuals():

    metadata_path = (
        VISUAL_DIR /
        "metadata.json"
    )

    if not metadata_path.exists():

        return jsonify({
            "error":
                "NDVI visualization metadata not found"
        }), 404

    with open(
        metadata_path,
        "r"
    ) as f:

        metadata = json.load(f)

    # Convert local file paths into browser URLs.
    for layer in metadata.values():

        filename = Path(
            layer["image"]
        ).name

        layer["url"] = (
            f"/visuals/{filename}"
        )

    return jsonify(metadata)


# ==================================================
# UNIVERSAL PLACE SEARCH
# ==================================================

@app.route("/api/geocode", methods=["GET"])
def geocode():

    query = request.args.get(
        "q",
        ""
    ).strip()

    if not query:

        return jsonify({
            "error":
                "Search query is required"
        }), 400

    url = (
        "https://nominatim.openstreetmap.org/search"
    )

    params = {

        "q":
            query,

        "format":
            "jsonv2",

        "limit":
            10,

        "addressdetails":
            1,

        "namedetails":
            1,

        "layer":
            "address,poi,railway,natural,manmade",

        "accept-language":
            "en"
    }

    headers = {

        "User-Agent":
            "ForestMonitorHackathon/1.0"
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        results = response.json()

        locations = []

        for result in results:

            address = result.get(
                "address",
                {}
            )

            locations.append({

                "name":
                    result.get(
                        "display_name",
                        "Unknown location"
                    ),

                "latitude":
                    float(
                        result["lat"]
                    ),

                "longitude":
                    float(
                        result["lon"]
                    ),

                "category":
                    result.get(
                        "category",
                        "unknown"
                    ),

                "type":
                    result.get(
                        "type",
                        "unknown"
                    ),

                "osm_type":
                    result.get(
                        "osm_type",
                        "unknown"
                    ),

                "osm_id":
                    result.get(
                        "osm_id"
                    ),

                "address":
                    address
            })

        return jsonify({

            "query":
                query,

            "count":
                len(locations),

            "results":
                locations
        })

    except requests.RequestException as error:

        return jsonify({

            "error":
                "Unable to contact location search service",

            "details":
                str(error)
        }), 502


# ==================================================
# RUN FLASK
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )