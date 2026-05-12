from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import choice, uniform
from typing import Any

from .air_quality import METRIC_ORDER, build_computed
from .recommendations import generate_recommendations


MAX_HISTORY = 500
SOURCE_MODES = {"api", "simulation"}

latest_record: dict[str, Any] | None = None
latest_api_record: dict[str, Any] | None = None
latest_simulated_record: dict[str, Any] | None = None
history_store: list[dict[str, Any]] = []
source_mode = "api"
current_streak = 3  # On commence à 3 cœurs pour la démonstration
last_streak_update_date = None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat(timespec="seconds")


def normalize_timestamp(value: str | None) -> str:
    return value or iso_now()


def make_record(data: dict[str, Any], *, simulated: bool = False, source: str = "esp32") -> dict[str, Any]:
    global current_streak, last_streak_update_date
    
    raw = data.copy()
    raw["timestamp"] = normalize_timestamp(raw.get("timestamp"))
    raw["simulated"] = simulated
    raw["source"] = "simulation" if simulated else source
    raw.setdefault("device_id", "safehome_demo" if simulated else "unknown_device")

    computed = build_computed(raw)
    
    # --- LOGIQUE DE SÉRIE (STREAK) ---
    score = computed.get("global_score")
    at_risk = False
    today = now_utc().date()
    
    if score is not None:
        # Nouveau jour = +1 coeur (si on n'a pas perdu la série)
        if last_streak_update_date is not None and last_streak_update_date < today and current_streak > 0:
            current_streak += 1
        last_streak_update_date = today

        # Pénalités et alertes
        if score < 50:
            current_streak = 0
        elif score < 70:
            at_risk = True
            
    computed["streak"] = {
        "hearts": current_streak,
        "at_risk": at_risk,
    }
    # ---------------------------------
    
    computed["recommendations"] = generate_recommendations(raw, computed["risks"], computed["streak"])
    return {
        "raw": raw,
        "computed": computed,
        "guidelines_used": [],
    }


def append_history(record: dict[str, Any]) -> None:
    global latest_record, latest_api_record, latest_simulated_record
    latest_record = record
    if record["raw"].get("simulated"):
        latest_simulated_record = record
    else:
        latest_api_record = record
    history_store.append(record)
    del history_store[:-MAX_HISTORY]


def get_latest() -> dict[str, Any] | None:
    return get_latest_for_mode(source_mode)


def get_latest_for_mode(mode: str) -> dict[str, Any] | None:
    if mode == "simulation":
        return latest_simulated_record
    return latest_api_record


def get_source_mode() -> str:
    return source_mode


def set_source_mode(mode: str) -> str:
    global source_mode
    if mode not in SOURCE_MODES:
        raise ValueError(f"Mode source invalide: {mode}")
    source_mode = mode
    return source_mode


def get_history_count() -> int:
    return len(history_store)


def latest_age_seconds() -> int | None:
    return record_age_seconds(get_latest())


def record_age_seconds(record: dict[str, Any] | None) -> int | None:
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


def sim_score(co2: float) -> int:
    if co2 <= 400: return 100
    elif co2 <= 800: return int((co2 - 400) * (81 - 100) / (800 - 400) + 100)
    elif co2 <= 1500: return int((co2 - 800) * (50 - 80) / (1500 - 800) + 80)
    else: return max(0, min(100, int((co2 - 1500) * (0 - 49) / (3000 - 1500) + 49)))


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
    base["score"] = sim_score(base["co2"])
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


def history_rows(range_key: str | None = None, mode: str | None = None) -> list[dict[str, Any]]:
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
        if mode == "api" and raw.get("simulated"):
            continue
        if mode == "simulation" and not raw.get("simulated"):
            continue
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
            "voc_index": round(raw.get("gas_resistance", 0) / 1000.0, 1) if raw.get("gas_resistance") is not None else None,
        }
        for key in METRIC_ORDER:
            row[key] = raw.get(key)
        rows.append(row)
    return rows


def daily_summary(mode: str | None = None) -> dict[str, Any]:
    rows = history_rows("24h", mode=mode)
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
