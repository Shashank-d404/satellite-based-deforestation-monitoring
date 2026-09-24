from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Forest Monitor API is running"
    })


@app.route("/api/geocode", methods=["GET"])
def geocode():
    region = request.args.get("region", "").strip()

    if not region:
        return jsonify({
            "error": "Region is required"
        }), 400

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": region,
        "format": "jsonv2",
        "limit": 1
    }

    headers = {
        "User-Agent": "ForestMonitorAI/1.0"
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

        if not results:
            return jsonify({
                "error": "Region not found"
            }), 404

        result = results[0]

        return jsonify({
            "display_name": result.get("display_name"),
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"])
        })

    except requests.RequestException as error:
        return jsonify({
            "error": "Geocoding service request failed",
            "details": str(error)
        }), 502


if __name__ == "__main__":
    app.run(debug=True)