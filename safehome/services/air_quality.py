from __future__ import annotations

import math
from typing import Any

from .health_guidelines import DISCLAIMER, GUIDELINES, SENSITIVE_PEOPLE


CURRENT_SENSOR_FIELDS = {"temperature", "humidity", "pressure", "gas_resistance", "battery", "score"}
FUTURE_SENSOR_FIELDS = {"co2"}
NUMERIC_FIELDS = CURRENT_SENSOR_FIELDS | FUTURE_SENSOR_FIELDS

FIELD_RANGES: dict[str, tuple[float | None, float | None]] = {
    "temperature": (-40, 85),
    "humidity": (0, 100),
    "pressure": (300, 1200),
    "gas_resistance": (0, None),
    "battery": (0, 100),
    "co2": (0, 10000),
    "score": (0, 100),
}

METRIC_ORDER = [
    "co2",
    "temperature",
    "humidity",
    "gas_resistance",
    "pressure",
    "battery",
]

STATUS_LEVELS = [
    {
        "status": "excellent",
        "tone": "good",
        "label": "Excellente",
        "color": "#22c55e",
        "smiley": "😊",
        "risk_level": "low",
        "min": 85,
    },
    {
        "status": "good",
        "tone": "good",
        "label": "Bonne",
        "color": "#06b6d4",
        "smiley": "🙂",
        "risk_level": "low",
        "min": 70,
    },
    {
        "status": "medium",
        "tone": "medium",
        "label": "Vigilance",
        "color": "#f59e0b",
        "smiley": "😐",
        "risk_level": "medium",
        "min": 50,
    },
    {
        "status": "bad",
        "tone": "bad",
        "label": "Dégradée",
        "color": "#ef4444",
        "smiley": "😟",
        "risk_level": "high",
        "min": 0,
    },
]

UNKNOWN_STATUS = {
    "status": "unknown",
    "tone": "unknown",
    "label": "En attente",
    "color": "#3b82f6",
    "smiley": "○",
    "risk_level": "unknown",
}


def round_value(value: float, digits: int = 1) -> float | int:
    rounded = round(float(value), digits)
    if float(rounded).is_integer():
        return int(rounded)
    return rounded


def compute_status(score: int | None) -> dict[str, Any]:
    if score is None:
        return UNKNOWN_STATUS.copy()
    for level in STATUS_LEVELS:
        if score >= level["min"]:
            return {key: value for key, value in level.items() if key != "min"}
    return UNKNOWN_STATUS.copy()


def _score_co2(value: float) -> int:
    if value < 800:
        return 100
    if value < 1000:
        return 86
    if value < 1500:
        return 58
    if value < 2000:
        return 38
    return 20


def _score_humidity(value: float) -> int:
    if 40 <= value <= 60:
        return 100
    if 35 <= value < 40 or 60 < value <= 65:
        return 78
    if 30 <= value < 35 or 65 < value <= 70:
        return 58
    return 35


def _score_temperature(value: float) -> int:
    if 19 <= value <= 22:
        return 100
    if 17 <= value < 19 or 22 < value <= 25:
        return 76
    if 15 <= value < 17 or 25 < value <= 28:
        return 55
    return 34


def _score_gas_resistance(value: float) -> int:
    if value >= 150000:
        return 100
    if value >= 100000:
        return 88
    if value >= 50000:
        return 62
    if value >= 25000:
        return 40
    return 25


def _metric_status(score: int | None, measured: bool = True) -> tuple[str, str]:
    if not measured or score is None:
        return "unknown", "Non mesuré"
    if score >= 85:
        return "good", "Excellent"
    if score >= 70:
        return "good", "Correct"
    if score >= 50:
        return "medium", "À surveiller"
    return "bad", "Élevé"


def metric_missing(key: str) -> dict[str, Any]:
    guideline = GUIDELINES[key]
    value_label = "CO₂ non mesuré" if key == "co2" else "Non mesuré"
    return {
        "key": key,
        "label": guideline["label"],
        "value": None,
        "value_label": value_label,
        "unit": guideline["api_unit"],
        "tone": "unknown",
        "status": "unknown",
        "status_label": "Non mesuré",
        "measured": False,
        "interpretation": "Donnée absente du payload. SafeHome ne l'invente pas.",
        "source": guideline["source"],
        "source_url": guideline["source_url"],
        "recommendation": f"{guideline['requires_sensor']} nécessaire pour afficher cette donnée.",
        "confidence": "not_measured",
        "score_component": None,
    }


def _metric(
    key: str,
    value: float,
    score: int | None,
    status_label: str,
    interpretation: str,
    recommendation: str,
    *,
    confidence: str = "measured",
    value_label: str | None = None,
    tone: str | None = None,
    unit: str | None = None,
) -> dict[str, Any]:
    guideline = GUIDELINES[key]
    resolved_tone, fallback_status_label = _metric_status(score)
    return {
        "key": key,
        "label": guideline["label"],
        "value": round_value(value, 1),
        "value_label": value_label or str(round_value(value, 1)),
        "unit": unit or guideline["api_unit"],
        "tone": tone or resolved_tone,
        "status": tone or resolved_tone,
        "status_label": status_label or fallback_status_label,
        "measured": True,
        "interpretation": interpretation,
        "source": guideline["source"],
        "source_url": guideline["source_url"],
        "recommendation": recommendation,
        "confidence": confidence,
        "score_component": score,
    }


def evaluate_metric(key: str, data: dict[str, Any]) -> dict[str, Any]:
    if key not in data or data[key] is None:
        return metric_missing(key)

    value = float(data[key])

    if key == "co2":
        score = _score_co2(value)
        if value < 800:
            status_label = "Excellent"
            interpretation = "CO₂ bas, air bien renouvelé."
        elif value < 1000:
            status_label = "Correct"
            interpretation = "CO₂ sous 1000 ppm, bon indicateur de ventilation."
        elif value < 1500:
            status_label = "À surveiller"
            interpretation = "Le CO₂ commence à indiquer un air confiné."
        else:
            status_label = "Élevé"
            interpretation = "CO₂ élevé mesuré par SCD40/SCD41, ventilation recommandée."
        return _metric(
            key,
            value,
            score,
            status_label,
            interpretation,
            "Aérez la pièce si le CO₂ dépasse 1000 ppm ou continue à monter.",
        )

    if key == "temperature":
        score = _score_temperature(value)
        if 19 <= value <= 22:
            status_label = "Confortable"
            interpretation = "Température dans la zone de confort 19-22 °C."
        elif value > 25:
            status_label = "Élevée"
            interpretation = "La pièce peut devenir inconfortable."
        elif value < 17:
            status_label = "Fraîche"
            interpretation = "Température basse pour un confort durable."
        else:
            status_label = "Correcte"
            interpretation = "Température proche de la zone de confort."
        return _metric(
            key,
            value,
            score,
            status_label,
            interpretation,
            "Visez un confort autour de 19-22 °C selon l'usage de la pièce.",
        )

    if key == "humidity":
        score = _score_humidity(value)
        if 40 <= value <= 60:
            status_label = "Optimal"
            interpretation = "Humidité dans la zone de confort 40-60 %."
        elif value < 40:
            status_label = "Trop sec"
            interpretation = "L'air est plus sec que la zone de confort."
        else:
            status_label = "Trop humide"
            interpretation = "Humidité au-dessus de la zone de confort."
        return _metric(
            key,
            value,
            score,
            status_label,
            interpretation,
            "Gardez l'humidité entre 40 et 60 % si possible.",
        )

    if key == "gas_resistance":
        score = _score_gas_resistance(value)
        if value >= 100000:
            status_label = "Faible"
            interpretation = "Signal BME680 favorable, COV estimés faibles."
        elif value >= 50000:
            status_label = "Moyen"
            interpretation = "Signal COV/gaz estimé à surveiller."
        else:
            status_label = "Élevé"
            interpretation = "Signal BME680 défavorable, possible présence de COV/gaz."
        val_kohm = round_value(value / 1000.0, 1)
        metric = _metric(
            key,
            value,
            score,
            status_label,
            interpretation,
            "Évitez sprays, bougies et produits odorants si le signal se dégrade.",
            confidence="estimated",
            value_label=str(val_kohm),
            unit="kΩ",
        )
        metric["raw_value"] = round_value(value)
        metric["raw_unit"] = "Ω"
        return metric

    if key == "pressure":
        return _metric(
            key,
            value,
            None,
            "Information",
            "Contexte environnemental, non utilisé dans le score santé.",
            "Suivez surtout CO₂, humidité, température et COV estimés.",
            tone="info",
            unit=GUIDELINES[key]["api_unit"],
        )

    if key == "battery":
        score = 100 if value >= 40 else 65 if value >= 20 else 30
        tone, status_label = _metric_status(score)
        return _metric(
            key,
            value,
            None,
            "Batterie OK" if value >= 40 else "À recharger" if value >= 20 else "Faible",
            "Télémétrie technique du boîtier.",
            "Rechargez le boîtier si la batterie descend sous 20 %.",
            tone=tone,
            unit=GUIDELINES[key]["api_unit"],
        )

    return metric_missing(key)


def build_metrics(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metrics = {key: evaluate_metric(key, data) for key in METRIC_ORDER if key in GUIDELINES}
    return metrics


def compute_confidence_level(data: dict[str, Any]) -> dict[str, str]:
    measured = {key for key in NUMERIC_FIELDS if key in data and data[key] is not None}
    has_bme680 = {"temperature", "humidity", "pressure", "gas_resistance"}.issubset(measured)
    has_co2 = "co2" in measured

    if has_bme680 and has_co2:
        return {
            "level": "good",
            "label": "Confiance élevée",
            "explanation": "BME680 + SCD40/SCD41 sont disponibles.",
        }
    if {"temperature", "humidity", "gas_resistance"}.issubset(measured):
        return {
            "level": "medium",
            "label": "Confiance moyenne",
            "explanation": "BME680 disponible. CO₂ et particules demandent des capteurs dédiés.",
        }
    if len(measured & {"temperature", "humidity", "gas_resistance", "co2"}) >= 2:
        return {
            "level": "medium",
            "label": "Confiance moyenne",
            "explanation": "Quelques indicateurs sont présents, mais la mesure reste incomplète.",
        }
    return {
        "level": "low",
        "label": "Confiance faible",
        "explanation": "Peu de mesures sont disponibles pour interpréter l'air intérieur.",
    }


def generate_risks(data: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []

    co2 = data.get("co2")
    if co2 is not None:
        co2_value = float(co2)
        if co2_value > 1500:
            risks.append(
                {
                    "level": "high",
                    "title": "CO₂ élevé",
                    "description": "Le SCD40/SCD41 mesure un air très confiné.",
                    "source": GUIDELINES["co2"]["source"],
                    "affected_people": ["personnes âgées", "nourrissons", "patients hospitalisés"],
                    "confidence": "measured",
                }
            )
        elif co2_value > 1000:
            risks.append(
                {
                    "level": "medium",
                    "title": "Ventilation à surveiller",
                    "description": "Le CO₂ dépasse 1000 ppm, indicateur courant d'un renouvellement d'air à améliorer.",
                    "source": GUIDELINES["co2"]["source"],
                    "affected_people": ["personnes sensibles", "personnes fatiguées"],
                    "confidence": "measured",
                }
            )

    humidity = data.get("humidity")
    if humidity is not None:
        humidity_value = float(humidity)
        if humidity_value > 60:
            risks.append(
                {
                    "level": "high" if humidity_value > 70 else "medium",
                    "title": "Humidité élevée",
                    "description": "Une humidité durable au-dessus de 60 % favorise condensation, inconfort et moisissures.",
                    "source": GUIDELINES["humidity"]["source"],
                    "affected_people": ["personnes asthmatiques", "nourrissons", "personnes âgées"],
                    "confidence": "measured",
                }
            )
        elif humidity_value < 40:
            risks.append(
                {
                    "level": "medium",
                    "title": "Air trop sec",
                    "description": "Une humidité sous 40 % peut créer une sensation d'air sec.",
                    "source": GUIDELINES["humidity"]["source"],
                    "affected_people": ["personnes asthmatiques", "nourrissons", "personnes âgées"],
                    "confidence": "measured",
                }
            )

    temperature = data.get("temperature")
    if temperature is not None:
        temperature_value = float(temperature)
        if temperature_value > 25:
            risks.append(
                {
                    "level": "medium" if temperature_value <= 28 else "high",
                    "title": "Température élevée",
                    "description": "La pièce dépasse la zone de confort du prototype.",
                    "source": GUIDELINES["temperature"]["source"],
                    "affected_people": ["personnes âgées", "nourrissons"],
                    "confidence": "measured",
                }
            )

    gas_resistance = data.get("gas_resistance")
    if gas_resistance is not None:
        gas_value = float(gas_resistance)
        if gas_value < 50000:
            risks.append(
                {
                    "level": "medium",
                    "title": "COV détectés",
                    "description": "La résistance gaz BME680 est basse; cela suggère une possible variation de COV/gaz.",
                    "source": GUIDELINES["gas_resistance"]["source"],
                    "affected_people": ["personnes asthmatiques", "personnes sensibles aux odeurs"],
                    "confidence": "estimated",
                }
            )


    return risks


def validate_sensor_payload(payload: Any) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(payload, dict):
        return None, ["Le corps JSON doit être un objet."], warnings

    normalized: dict[str, Any] = {}
    device_id = payload.get("device_id", "unknown_device")
    if device_id is not None:
        if not isinstance(device_id, str):
            errors.append("device_id doit être une chaîne de caractères.")
        else:
            normalized["device_id"] = device_id.strip()[:80] or "unknown_device"

    if "gas" in payload and "gas_resistance" not in payload:
        payload = payload.copy()
        payload["gas_resistance"] = payload["gas"]
        warnings.append("Le champ legacy 'gas' a été interprété comme 'gas_resistance'.")

    for key in NUMERIC_FIELDS:
        if key not in payload or payload[key] is None:
            continue
        value = payload[key]
        if isinstance(value, bool):
            errors.append(f"{key} doit être numérique, pas booléen.")
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors.append(f"{key} doit être numérique.")
            continue
        if not math.isfinite(number):
            errors.append(f"{key} doit être une valeur finie.")
            continue
        minimum, maximum = FIELD_RANGES[key]
        if minimum is not None and number < minimum:
            errors.append(f"{key} doit être >= {minimum}.")
        if maximum is not None and number > maximum:
            errors.append(f"{key} doit être <= {maximum}.")
        normalized[key] = round_value(number, 3)

    timestamp = payload.get("timestamp")
    if timestamp is not None:
        if isinstance(timestamp, str):
            normalized["timestamp"] = timestamp
        else:
            warnings.append("timestamp ignoré car il n'est pas une chaîne ISO.")

    if not any(key in normalized for key in NUMERIC_FIELDS):
        errors.append("Au moins une mesure numérique doit être fournie.")

    unknown = sorted(set(payload) - NUMERIC_FIELDS - {"device_id", "timestamp", "gas"})
    if unknown:
        warnings.append(f"Champs ignorés: {', '.join(unknown)}.")

    return (None if errors else normalized), errors, warnings


def build_computed(data: dict[str, Any]) -> dict[str, Any]:
    score = int(data["score"]) if data.get("score") is not None else None
    status = compute_status(score)
    metrics = build_metrics(data)
    confidence = compute_confidence_level(data)
    risks = generate_risks(data)

    if score is None:
        interpretation = "Aucune mesure de CO₂ récente. Connectez l'ESP32 ou lancez une simulation."
    else:
        interpretation = "Score calculé uniquement sur la base du CO₂ (SCD41) suite au dysfonctionnement du capteur BME680."

    return {
        "global_score": score,
        "score": score,
        **status,
        "metrics": metrics,
        "confidence": confidence,
        "confidence_level": confidence["level"],
        "confidence_label": confidence["label"],
        "confidence_explanation": confidence["explanation"],
        "risks": risks,
        "human_interpretation": interpretation,
        "measured_fields": sorted(key for key in NUMERIC_FIELDS if key in data and data[key] is not None),
        "missing_fields": ["co2"] if "co2" not in data else [],
        "is_estimated": "gas_resistance" in data,
        "disclaimer": DISCLAIMER,
    }