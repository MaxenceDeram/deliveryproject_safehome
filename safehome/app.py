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
    return render_template("dashboard.html", title="Dashboard", dashboard_shell=True, active_page="dashboard")


@app.route("/history")
def history():
    return render_template("history.html", title="Historique", dashboard_shell=True, active_page="history")


@app.route("/recommendations")
def recommendations():
    return render_template("recommendations.html", title="Recommandations", dashboard_shell=True, active_page="recommendations")


@app.route("/about")
def about():
    return render_template("about.html", title="A propos", dashboard_shell=True, active_page="about")


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
    source = request.args.get("source")
    source_mode = storage.get_source_mode() if source == "active" else source
    if source_mode not in {"api", "simulation"}:
        source_mode = None
    items = storage.history_rows(range_key, mode=source_mode)
    return jsonify(
        {
            "range": range_key,
            "source_mode": source_mode or "all",
            "count": len(items),
            "items": items,
            "summary": storage.daily_summary(mode=source_mode),
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
    source_mode = storage.get_source_mode()
    record = storage.get_latest()
    api_record = storage.get_latest_for_mode("api")
    simulation_record = storage.get_latest_for_mode("simulation")
    age = storage.record_age_seconds(record)
    api_age = storage.record_age_seconds(api_record)
    esp32_connected = bool(api_record and api_age is not None and api_age <= 30)
    selected_raw = record["raw"] if record else {}
    return jsonify(
        {
            "api": "ok",
            "source_mode": source_mode,
            "esp32_connected": esp32_connected,
            "device_connected": esp32_connected if source_mode == "api" else bool(simulation_record),
            "last_update_seconds_ago": age,
            "api_last_update_seconds_ago": api_age,
            "last_source": selected_raw.get("source") if selected_raw else None,
            "device_id": selected_raw.get("device_id") if selected_raw else None,
            "battery": selected_raw.get("battery") if selected_raw else None,
            "wifi": "simulation" if source_mode == "simulation" and simulation_record else "online" if esp32_connected else "waiting",
            "history_count": storage.get_history_count(),
            "has_api_data": bool(api_record),
            "has_simulation_data": bool(simulation_record),
        }
    )


@app.get("/api/simulate")
def api_simulate():
    record = storage.make_record(storage.simulate_measurement(), simulated=True, source="simulation")
    storage.append_history(record)
    storage.set_source_mode("simulation")
    return jsonify({"message": "Mesure simulée créée", **record}), 201


@app.route("/api/source-mode", methods=["GET", "POST"])
def api_source_mode():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        mode = payload.get("mode")
        if mode not in storage.SOURCE_MODES:
            return jsonify({"error": "Mode invalide", "allowed": sorted(storage.SOURCE_MODES)}), 400
        storage.set_source_mode(mode)

    return jsonify(
        {
            "source_mode": storage.get_source_mode(),
            "has_api_data": bool(storage.get_latest_for_mode("api")),
            "has_simulation_data": bool(storage.get_latest_for_mode("simulation")),
        }
    )


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
