from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import choice, uniform
from typing import Any

from .air_quality import METRIC_ORDER, build_computed, gas_resistance_to_voc_index
from .recommendations import generate_recommendations


MAX_HISTORY = 500

latest_record: dict[str, Any] | None = None
history_store: list[dict[str, Any]] = []


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat(timespec="seconds")


def normalize_timestamp(value: str | None) -> str:
    return value or iso_now()


def make_record(data: dict[str, Any], *, simulated: bool = False, source: str = "esp32") -> dict[str, Any]:
    raw = data.copy()
    raw["timestamp"] = normalize_timestamp(raw.get("timestamp"))
    raw["simulated"] = simulated
    raw["source"] = "simulation" if simulated else source
    raw.setdefault("device_id", "safehome_demo" if simulated else "unknown_device")

    computed = build_computed(raw)
    computed["recommendations"] = generate_recommendations(raw, computed["risks"])
    return {
        "raw": raw,
        "computed": computed,
        "guidelines_used": [],
    }


def append_history(record: dict[str, Any]) -> None:
    global latest_record
    latest_record = record
    history_store.append(record)
    del history_store[:-MAX_HISTORY]


def get_latest() -> dict[str, Any] | None:
    return latest_record


def get_history_count() -> int:
    return len(history_store)


def latest_age_seconds() -> int | None:
    record = get_latest()
    if not record:
        return None
    timestamp = record["raw"].get("timestamp")
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0, int((now_utc() - parsed).total_seconds()))


def simulate_measurement(*, timestamp: str | None = None) -> dict[str, Any]:
    scenario = choice(["excellent", "good", "co2", "humid", "voc", "warm"])
    base = {
        "device_id": "safehome_demo",
        "temperature": round(uniform(20.0, 22.3), 1),
        "humidity": round(uniform(43, 56), 1),
        "pressure": round(uniform(1008, 1021), 1),
        "gas_resistance": int(uniform(115000, 185000)),
        "co2": int(uniform(405, 760)),
        "battery": int(uniform(74, 96)),
    }
    if scenario == "good":
        base["co2"] = int(uniform(760, 960))
        base["gas_resistance"] = int(uniform(95000, 150000))
    elif scenario == "co2":
        base["co2"] = int(uniform(1020, 1440))
        base["humidity"] = round(uniform(44, 59), 1)
    elif scenario == "humid":
        base["humidity"] = round(uniform(62, 72), 1)
        base["gas_resistance"] = int(uniform(65000, 115000))
    elif scenario == "voc":
        base["gas_resistance"] = int(uniform(28000, 68000))
        base["co2"] = int(uniform(620, 940))
    elif scenario == "warm":
        base["temperature"] = round(uniform(25.2, 27.4), 1)
        base["co2"] = int(uniform(720, 1060))
    if timestamp:
        base["timestamp"] = timestamp
    return base


def seed_demo_history(points: int = 48) -> None:
    if history_store:
        return

    start = now_utc() - timedelta(hours=6)
    for index in range(points):
        timestamp = (start + timedelta(minutes=index * 8)).isoformat(timespec="seconds")
        data = simulate_measurement(timestamp=timestamp)

        # Smooth the generated demo so charts look like a real sensor stream.
        phase = index / max(1, points - 1)
        data["co2"] = int(430 + 210 * phase + uniform(-45, 75))
        data["temperature"] = round(21.2 + 1.4 * phase + uniform(-0.5, 0.45), 1)
        data["humidity"] = round(47 + 6 * phase + uniform(-4, 4), 1)
        data["gas_resistance"] = int(150000 - 42000 * phase + uniform(-16000, 14000))
        append_history(make_record(data, simulated=True, source="simulation"))


def parse_timestamp(timestamp: str | None) -> datetime:
    if not timestamp:
        return now_utc()
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return now_utc()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def history_rows(range_key: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cutoff: datetime | None = None
    if range_key == "6h":
        cutoff = now_utc() - timedelta(hours=6)
    elif range_key == "24h":
        cutoff = now_utc() - timedelta(hours=24)
    elif range_key == "7d":
        cutoff = now_utc() - timedelta(days=7)
    elif range_key == "30d":
        cutoff = now_utc() - timedelta(days=30)

    for record in history_store:
        raw = record["raw"]
        parsed = parse_timestamp(raw.get("timestamp"))
        if cutoff and parsed < cutoff:
            continue
        computed = record["computed"]
        row = {
            "timestamp": raw.get("timestamp"),
            "label": parsed.astimezone().strftime("%H:%M") if range_key in {"6h", "24h"} else parsed.astimezone().strftime("%d/%m"),
            "score": computed.get("global_score"),
            "status": computed.get("status"),
            "tone": computed.get("tone"),
            "status_label": computed.get("label"),
            "confidence_level": computed.get("confidence_level"),
            "simulated": raw.get("simulated", False),
            "source": raw.get("source"),
            "voc_index": gas_resistance_to_voc_index(raw.get("gas_resistance")),
        }
        for key in METRIC_ORDER:
            row[key] = raw.get(key)
        rows.append(row)
    return rows


def daily_summary() -> dict[str, Any]:
    rows = history_rows("24h")
    if not rows:
        return {"count": 0}

    def avg(key: str) -> float | None:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        return round(sum(values) / len(values), 1) if values else None

    scores = [row["score"] for row in rows if row.get("score") is not None]
    return {
        "count": len(rows),
        "score_avg": round(sum(scores) / len(scores)) if scores else None,
        "co2_avg": avg("co2"),
        "temperature_avg": avg("temperature"),
        "humidity_avg": avg("humidity"),
        "voc_peak": max((row.get("voc_index") or 0 for row in rows), default=None),
    }

