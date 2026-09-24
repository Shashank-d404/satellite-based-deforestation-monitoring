import json
from pathlib import Path

import requests
from flask import (
    Flask,
    Response,
    jsonify,
    request,
    send_file,
    send_from_directory,
)

from dynamic_analysis import run_comparison


# ==================================================
# PROJECT PATHS
# ==================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

FRONTEND_DIR = (
    BASE_DIR / "frontend"
)

NDVI_DIR = (
    BASE_DIR / "data" / "ndvi"
)

VISUAL_DIR = (
    NDVI_DIR / "visuals"
)

DYNAMIC_DIR = (
    BASE_DIR / "data" / "dynamic_analysis"
)


# ==================================================
# FLASK APPLICATION
# ==================================================

app = Flask(__name__)


# ==================================================
# FRONTEND
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
# STATIC NDVI VISUALS
# ==================================================

@app.route(
    "/visuals/<path:filename>"
)
def visualization_files(filename):

    return send_from_directory(
        VISUAL_DIR,
        filename
    )


# ==================================================
# DYNAMIC ANALYSIS FILES
# ==================================================

@app.route(
    "/dynamic/<pair>/<path:filename>"
)
def dynamic_files(
    pair,
    filename
):

    directory = (
        DYNAMIC_DIR / pair
    )

    return send_from_directory(
        directory,
        filename
    )


# ==================================================
# HEALTH CHECK
# ==================================================

@app.route(
    "/api/health",
    methods=["GET"]
)
def health_check():

    return jsonify({

        "status":
            "ok",

        "message":
            "Forest Monitor API is running"

    })


# ==================================================
# ORIGINAL VERIFIED ANALYSIS
# ==================================================

@app.route(
    "/api/analysis",
    methods=["GET"]
)
def analysis():

    return jsonify({

        "project":
            "Satellite-Based Deforestation Monitoring",

        "comparison": {

            "baseline_year":
                2025,

            "current_year":
                2026

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

        }

    })


# ==================================================
# ORIGINAL VERIFIED GEOJSON
# ==================================================

@app.route(
    "/api/deforestation",
    methods=["GET"]
)
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
# ORIGINAL STATIC VISUAL METADATA
# ==================================================

@app.route(
    "/api/visuals",
    methods=["GET"]
)
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


    for layer in metadata.values():

        filename = Path(
            layer["image"]
        ).name

        layer["url"] = (
            f"/visuals/{filename}"
        )


    return jsonify(metadata)


# ==================================================
# DYNAMIC YEAR ANALYSIS
# ==================================================

@app.route(
    "/api/run-analysis",
    methods=["POST"]
)
def run_analysis():

    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({

            "error":
                "JSON request body is required"

        }), 400


    try:

        baseline_year = int(
            data.get(
                "baseline_year"
            )
        )

        current_year = int(
            data.get(
                "current_year"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({

            "error":
                "Years must be integers"

        }), 400


    if baseline_year >= current_year:

        return jsonify({

            "error":
                "Baseline year must be earlier than current year"

        }), 400


    if (
        baseline_year < 2016
        or current_year < 2016
    ):

        return jsonify({

            "error":
                "The selectable Sentinel-2 comparison range starts at 2016"

        }), 400


    if (
        baseline_year > 2026
        or current_year > 2026
    ):

        return jsonify({

            "error":
                "Year cannot be later than 2026"

        }), 400


    try:

        result = run_comparison(

            baseline_year,

            current_year

        )

        return jsonify(result)


    except Exception as error:

        return jsonify({

            "error":
                str(error)

        }), 500


# ==================================================
# EXPORT HELPER
# ==================================================

def get_export_years():

    try:

        baseline_year = int(
            request.args.get(
                "baseline_year"
            )
        )

        current_year = int(
            request.args.get(
                "current_year"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        raise ValueError(
            "baseline_year and current_year "
            "must be integers"
        )


    if baseline_year >= current_year:

        raise ValueError(
            "Baseline year must be earlier "
            "than current year"
        )


    if (
        baseline_year < 2016
        or current_year < 2016
    ):

        raise ValueError(
            "Year must be between 2016 and 2026"
        )


    if (
        baseline_year > 2026
        or current_year > 2026
    ):

        raise ValueError(
            "Year must be between 2016 and 2026"
        )


    return (
        baseline_year,
        current_year
    )


# ==================================================
# EXPORT TEXT REPORT
# ==================================================

@app.route(
    "/api/export/report",
    methods=["GET"]
)
def export_report():

    try:

        baseline_year, current_year = (
            get_export_years()
        )

        result = run_comparison(
            baseline_year,
            current_year
        )


        stats = result["statistics"]

        baseline_scene = (
            result["baseline_scene"]
        )

        current_scene = (
            result["current_scene"]
        )

        comparison = (
            result["comparison"]
        )


        report = f"""
FOREST MONITOR
Satellite-Based Deforestation Monitoring
==========================================

ANALYSIS REPORT

Comparison
----------
Baseline Year     : {comparison["baseline_year"]}
Current Year      : {comparison["current_year"]}
Comparison Month  : {comparison["month"]}
Study Tile        : {comparison["study_tile"]}

Method
------
{result["method"]}

Detection Threshold
-------------------
NDVI change < {result["threshold"]:.2f}

BASELINE SCENE
--------------
Scene ID          : {baseline_scene["item_id"]}
Acquired          : {baseline_scene["acquired"]}
Cloud Cover      : {float(baseline_scene["cloud_cover"]):.2f}%

CURRENT SCENE
-------------
Scene ID          : {current_scene["item_id"]}
Acquired          : {current_scene["acquired"]}
Cloud Cover      : {float(current_scene["cloud_cover"]):.2f}%

RESULTS
-------
Mean NDVI Change       : {stats["mean_ndvi_change"]:.4f}
Minimum NDVI Change    : {stats["minimum_ndvi_change"]:.4f}
Maximum NDVI Change    : {stats["maximum_ndvi_change"]:.4f}
Valid Comparison Pixels: {stats["valid_pixels"]:,}
Potential-Loss Pixels  : {stats["potential_loss_pixels"]:,}
Potential-Loss Share   : {stats["potential_loss_share"]:.2f}%
Detected Regions       : {stats["detected_regions"]}

INTERPRETATION
--------------
Pixels with an NDVI decrease below the configured threshold
were flagged as potential vegetation loss after cloud/shadow
filtering.

This output is an initial screening result and should not be
interpreted as confirmed deforestation without additional
validation.

Generated by Forest Monitor.
"""


        filename = (
            f"forest_monitor_"
            f"{baseline_year}_"
            f"{current_year}.txt"
        )


        return Response(

            report.strip() + "\n",

            mimetype="text/plain",

            headers={

                "Content-Disposition":
                    f'attachment; filename="{filename}"'

            }

        )


    except ValueError as error:

        return jsonify({

            "error":
                str(error)

        }), 400


    except Exception as error:

        return jsonify({

            "error":
                str(error)

        }), 500


# ==================================================
# EXPORT GEOJSON
# ==================================================

@app.route(
    "/api/export/geojson",
    methods=["GET"]
)
def export_geojson():

    try:

        baseline_year, current_year = (
            get_export_years()
        )


        run_comparison(
            baseline_year,
            current_year
        )


        pair_name = (
            f"{baseline_year}_{current_year}"
        )


        geojson_path = (
            DYNAMIC_DIR
            / pair_name
            / "potential_loss.geojson"
        )


        if not geojson_path.exists():

            return jsonify({

                "error":
                    "Potential-loss GeoJSON was not generated"

            }), 404


        filename = (
            f"potential_loss_"
            f"{baseline_year}_"
            f"{current_year}.geojson"
        )


        return send_file(

            geojson_path,

            as_attachment=True,

            download_name=filename,

            mimetype="application/geo+json"

        )


    except ValueError as error:

        return jsonify({

            "error":
                str(error)

        }), 400


    except Exception as error:

        return jsonify({

            "error":
                str(error)

        }), 500


# ==================================================
# UNIVERSAL PLACE SEARCH
# ==================================================

@app.route(
    "/api/geocode",
    methods=["GET"]
)
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