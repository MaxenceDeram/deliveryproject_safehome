from __future__ import annotations

import csv
import io

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

from services.air_quality import build_computed, validate_sensor_payload
from services.health_guidelines import DISCLAIMER, GUIDELINES, SOURCE_REFERENCES, SUMMARY_GUIDELINES
from services import storage


app = Flask(__name__)


@app.context_processor
def inject_global_template_data():
    return {"global_disclaimer": DISCLAIMER}


@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", title="Dashboard", dashboard_shell=True)


@app.route("/history")
def history():
    return render_template("history.html", title="Historique")


@app.route("/recommendations")
def recommendations():
    return render_template("recommendations.html", title="Recommandations")


@app.route("/about")
def about():
    return render_template("about.html", title="A propos")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        return redirect(url_for("dashboard"))
    return render_template("login.html", title="Mon compte")


@app.get("/api/current-data")
def api_current_data():
    record = storage.get_latest()
    if record is None:
        return jsonify({"raw": {}, "computed": build_computed({}), "guidelines_used": []})
    return jsonify(record)


@app.get("/api/history")
def api_history():
    range_key = request.args.get("range", "24h")
    items = storage.history_rows(range_key)
    return jsonify(
        {
            "range": range_key,
            "count": len(items),
            "items": items,
            "summary": storage.daily_summary(),
        }
    )


@app.get("/api/recommendations")
def api_recommendations():
    record = storage.get_latest() or {"raw": {}, "computed": build_computed({})}
    computed = record["computed"]
    return jsonify(
        {
            "score": computed["global_score"],
            "status": computed["status"],
            "tone": computed["tone"],
            "label": computed["label"],
            "smiley": computed["smiley"],
            "items": computed.get("recommendations", []),
            "risks": computed["risks"],
            "disclaimer": DISCLAIMER,
        }
    )


@app.post("/api/sensor-data")
def api_sensor_data():
    payload = request.get_json(silent=True)
    data, errors, warnings = validate_sensor_payload(payload)
    if errors:
        return jsonify({"error": "Payload invalide", "details": errors, "warnings": warnings}), 400

    assert data is not None
    record = storage.make_record(data, simulated=False, source="esp32")
    storage.append_history(record)
    return jsonify({"message": "Données capteur reçues", **record, "warnings": warnings}), 201


@app.get("/api/guidelines")
def api_guidelines():
    return jsonify(
        {
            "disclaimer": DISCLAIMER,
            "summary_guidelines": SUMMARY_GUIDELINES,
            "guidelines": GUIDELINES,
            "sources": SOURCE_REFERENCES,
            "bme680_limits": {
                "does_measure": ["temperature", "humidity", "pressure", "gas_resistance"],
                "does_not_measure": ["co2", "pm25", "pm10", "co", "no2", "ozone", "so2"],
                "message": "Le BME680 ne mesure pas directement CO₂, PM2.5 ou PM10.",
            },
            "scd40_scd41": {
                "does_measure": ["co2"],
                "unit": "ppm",
                "message": "Le SCD40/SCD41 fournit le vrai CO₂ en ppm.",
            },
        }
    )


@app.get("/api/health")
def api_health():
    record = storage.get_latest()
    age = storage.latest_age_seconds()
    esp32_connected = bool(record and not record["raw"].get("simulated") and age is not None and age <= 30)
    return jsonify(
        {
            "api": "ok",
            "esp32_connected": esp32_connected,
            "device_connected": esp32_connected or bool(record and record["raw"].get("simulated")),
            "last_update_seconds_ago": age,
            "last_source": record["raw"].get("source") if record else None,
            "device_id": record["raw"].get("device_id") if record else None,
            "battery": record["raw"].get("battery") if record else None,
            "wifi": "simulation" if record and record["raw"].get("simulated") else "online" if esp32_connected else "waiting",
            "history_count": storage.get_history_count(),
        }
    )


@app.get("/api/simulate")
def api_simulate():
    record = storage.make_record(storage.simulate_measurement(), simulated=True, source="simulation")
    storage.append_history(record)
    return jsonify({"message": "Mesure simulée créée", **record}), 201


@app.get("/api/export.csv")
def api_export_csv():
    output = io.StringIO()
    fieldnames = [
        "timestamp",
        "device_id",
        "simulated",
        "source",
        "global_score",
        "status",
        "confidence_level",
        "temperature",
        "humidity",
        "pressure",
        "gas_resistance",
        "battery",
        "co2",
        "pm25",
        "pm10",
        "co",
        "no2",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in storage.history_store:
        raw = record["raw"]
        computed = record["computed"]
        writer.writerow(
            {
                "timestamp": raw.get("timestamp"),
                "device_id": raw.get("device_id"),
                "simulated": raw.get("simulated"),
                "source": raw.get("source"),
                "global_score": computed.get("global_score"),
                "status": computed.get("status"),
                "confidence_level": computed.get("confidence_level"),
                "temperature": raw.get("temperature"),
                "humidity": raw.get("humidity"),
                "pressure": raw.get("pressure"),
                "gas_resistance": raw.get("gas_resistance"),
                "battery": raw.get("battery"),
                "co2": raw.get("co2"),
                "pm25": raw.get("pm25"),
                "pm10": raw.get("pm10"),
                "co": raw.get("co"),
                "no2": raw.get("no2"),
            }
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=safehome-history.csv"},
    )


@app.errorhandler(404)
def not_found(_error):
    return (
        render_template(
            "error.html",
            title="Page introuvable",
            code=404,
            message="Cette page n'existe pas ou a été déplacée.",
        ),
        404,
    )


@app.errorhandler(500)
def server_error(_error):
    return (
        render_template(
            "error.html",
            title="Erreur",
            code=500,
            message="Un problème technique est survenu.",
        ),
        500,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
