import json
from pathlib import Path

from flask import Flask, jsonify, send_from_directory


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
NDVI_DIR = BASE_DIR / "data" / "ndvi"

app = Flask(__name__)


@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Forest Monitor API is running"
    })


@app.route("/api/analysis", methods=["GET"])
def analysis():
    return jsonify({
        "project": "Satellite-Based Deforestation Monitoring",
        "comparison": {
            "baseline_year": 2025,
            "current_year": 2026
        },
        "method": "NDVI change detection",
        "threshold": -0.20,
        "statistics": {
            "mean_ndvi_change": -0.0107,
            "minimum_ndvi_change": -0.3792,
            "maximum_ndvi_change": 0.2544,
            "potential_loss_pixels": 68,
            "valid_pixels": 262144,
            "potential_loss_percentage": 0.03
        },
        "outputs": {
            "ndvi_2025": str(NDVI_DIR / "ndvi_2025.tif"),
            "ndvi_2026": str(NDVI_DIR / "ndvi_2026.tif"),
            "ndvi_change": str(
                NDVI_DIR / "ndvi_change_2026_minus_2025.tif"
            ),
            "deforestation_mask": str(
                NDVI_DIR / "deforestation_mask.tif"
            )
        }
    })


@app.route("/api/deforestation", methods=["GET"])
def deforestation():
    geojson_path = NDVI_DIR / "deforestation.geojson"

    if not geojson_path.exists():
        return jsonify({
            "error": "Deforestation GeoJSON not found"
        }), 404

    with open(geojson_path, "r") as f:
        data = json.load(f)

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
