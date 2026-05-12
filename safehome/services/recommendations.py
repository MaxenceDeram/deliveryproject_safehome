from __future__ import annotations

from typing import Any

from .health_guidelines import GUIDELINES


def _recommendation(
    items: list[dict[str, Any]],
    seen: set[str],
    *,
    priority: str,
    title: str,
    message: str,
    action: str,
    icon: str,
    source: str,
    why: str,
) -> None:
    if title in seen:
        return
    seen.add(title)
    items.append(
        {
            "priority": priority,
            "title": title,
            "message": message,
            "action": action,
            "icon": icon,
            "source": source,
            "why": why,
        }
    )


def generate_recommendations(
    data: dict[str, Any], 
    risks: list[dict[str, Any]] | None = None,
    streak: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    seen: set[str] = set()

    # --- RECOMMANDATIONS LIÉES À LA SÉRIE (GAMIFICATION) ---
    if streak:
        if streak.get("hearts") == 0:
            _recommendation(
                recommendations,
                seen,
                priority="moyenne",
                title="Série perdue 💔",
                message="La qualité de l'air a chuté en dessous de 50.",
                action="Aérez bien aujourd'hui pour redémarrer une série de cœurs demain !",
                icon="wind",
                source="SafeHome Gamification",
                why="Le système de série se réinitialise si l'air devient toxique/confiné.",
            )
        elif streak.get("at_risk"):
            _recommendation(
                recommendations,
                seen,
                priority="élevée",
                title="Sauve ta série ! ❤️",
                message="La qualité de l'air se dégrade, tes cœurs sont en danger.",
                action="Pense à aérer pour garder ta série.",
                icon="window",
                source="SafeHome Gamification",
                why="La série est réinitialisée si le score global tombe dans le rouge.",
            )

    co2 = data.get("co2")
    if co2 is not None and float(co2) > 1500:
        _recommendation(
            recommendations,
            seen,
            priority="critique",
            title="Aérer la pièce",
            message="Le taux de CO₂ est élevé.",
            action="Aérez immédiatement et vérifiez la ventilation.",
            icon="window",
            source=GUIDELINES["co2"]["source"],
            why="Le CO₂ mesuré par SCD40/SCD41 indique le confinement et le renouvellement d'air.",
        )
    elif co2 is not None and float(co2) > 1000:
        _recommendation(
            recommendations,
            seen,
            priority="élevée",
            title="Aérer la pièce",
            message="Le taux de CO₂ commence à augmenter.",
            action="Ouvrez une fenêtre pendant 10 minutes.",
            icon="window",
            source=GUIDELINES["co2"]["source"],
            why="CO₂ > 1000 ppm: bon signal pour améliorer la ventilation.",
        )

    humidity = data.get("humidity")
    if humidity is not None and float(humidity) < 40:
        _recommendation(
            recommendations,
            seen,
            priority="moyenne",
            title="Air trop sec",
            message="L'humidité est sous la zone de confort.",
            action="Essayez d'humidifier légèrement l'air.",
            icon="drop",
            source=GUIDELINES["humidity"]["source"],
            why="La zone de confort SafeHome vise 40-60 % d'humidité relative.",
        )
    elif humidity is not None and float(humidity) > 60:
        _recommendation(
            recommendations,
            seen,
            priority="moyenne",
            title="Humidité élevée",
            message="L'humidité dépasse la zone de confort.",
            action="Aérez et vérifiez les sources d'humidité.",
            icon="drop",
            source=GUIDELINES["humidity"]["source"],
            why="Une humidité durable au-dessus de 60 % peut favoriser condensation et moisissures.",
        )
    elif humidity is not None:
        _recommendation(
            recommendations,
            seen,
            priority="préventive",
            title="Humidité parfaite",
            message="Le taux d'humidité est optimal.",
            action="Gardez ce niveau de confort.",
            icon="drop",
            source=GUIDELINES["humidity"]["source"],
            why="La mesure se situe dans la plage 40-60 %.",
        )

    temperature = data.get("temperature")
    if temperature is not None and float(temperature) > 25:
        _recommendation(
            recommendations,
            seen,
            priority="moyenne",
            title="Température élevée",
            message="La pièce dépasse la zone de confort.",
            action="Rafraîchissez la pièce si possible.",
            icon="thermo",
            source=GUIDELINES["temperature"]["source"],
            why="SafeHome utilise 19-22 °C comme zone de confort du prototype.",
        )

    gas_resistance = data.get("gas_resistance")
    if gas_resistance is not None and float(gas_resistance) < 50000:
        _recommendation(
            recommendations,
            seen,
            priority="élevée",
            title="COV détectés",
            message="Le signal gaz du BME680 se dégrade.",
            action="Évitez sprays, bougies, produits odorants et aérez la pièce.",
            icon="wind",
            source=GUIDELINES["gas_resistance"]["source"],
            why="Le BME680 donne une estimation indirecte des COV/gaz, pas un diagnostic médical.",
        )
    elif gas_resistance is not None:
        _recommendation(
            recommendations,
            seen,
            priority="préventive",
            title="Qualité de l'air saine",
            message="Peu de composés organiques volatils détectés.",
            action="Continuez à limiter les sources odorantes inutiles.",
            icon="sun",
            source=GUIDELINES["gas_resistance"]["source"],
            why="La résistance gaz du BME680 est favorable.",
        )

    if "co2" not in data:
        _recommendation(
            recommendations,
            seen,
            priority="préventive",
            title="CO₂ non mesuré",
            message="Le BME680 ne mesure pas le CO₂.",
            action="Ajoutez le SCD40/SCD41 pour un vrai CO₂ en ppm.",
            icon="sensor",
            source=GUIDELINES["co2"]["source"],
            why="Le CO₂ doit venir d'un capteur NDIR dédié.",
        )

    _recommendation(
        recommendations,
        seen,
        priority="préventive",
        title="Gardez votre air sain !",
        message="Continuez ainsi pour un environnement sain.",
        action="Ventilez régulièrement selon le contexte.",
        icon="leaf",
        source="SafeHome preventive guidance",
        why="Les gestes simples gardent une marge de confort sans alarme inutile.",
    )

    return recommendations[:6]
