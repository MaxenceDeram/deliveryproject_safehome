from __future__ import annotations

"""
Repères de prévention utilisés par SafeHome.

- CO2 < 1000 ppm : bon indicateur pratique de ventilation lorsque la mesure
  vient d'un capteur CO2 dédié comme SCD40/SCD41.
- Humidité optimale prototype : 40-60 %.
- Température confort prototype : 19-22 °C.
- PM2.5 / PM10 : repères OMS à utiliser uniquement si un capteur de particules
  dédié est ajouté plus tard.
- COV BME680 : estimation indirecte basée sur la résistance gaz, pas un
  diagnostic médical ni une mesure réglementaire certifiée.
"""

DISCLAIMER = (
    "SafeHome fournit des indicateurs de prévention et de confort. "
    "Il ne remplace pas un diagnostic médical ni un dispositif réglementaire certifié."
)

SUMMARY_GUIDELINES = {
    "co2": "CO2 < 1000 ppm : bon indicateur de ventilation avec SCD40/SCD41.",
    "humidity": "Humidité optimale : 40-60 %.",
    "temperature": "Température confort : 19-22 °C.",
    "particles": "PM2.5 / PM10 selon recommandations OMS si capteurs dédiés ajoutés.",
    "voc": "BME680 COV/gaz = estimation indirecte, pas diagnostic médical.",
}

WHO_AQG_2021_URL = "https://www.who.int/publications/i/item/9789240034228"
WHO_HOUSEHOLD_AIR_URL = "https://www.who.int/news-room/fact-sheets/detail/household-air-pollution-and-health"
ASHRAE_62_URL = "https://www.ashrae.org/technical-resources/bookstore/standards-62-1-62-2"
ASHRAE_CO2_BRIEF_URL = (
    "https://www.ashrae.org/file%20library/about/government%20affairs/public%20policy%20resources/"
    "briefs/indoor-carbon-dioxide-ventilation-and-indoor-air-quality_2023.pdf"
)
EPA_HUMIDITY_URL = "https://www.epa.gov/mold/mold-course-chapter-2"


SENSITIVE_PEOPLE = [
    "personnes asthmatiques",
    "personnes âgées",
    "nourrissons",
    "patients hospitalisés",
    "personnes ayant une maladie respiratoire ou cardiovasculaire",
]


GUIDELINES = {
    "pm25": {
        "label": "PM2.5",
        "unit": "µg/m³",
        "api_unit": "µg/m³",
        "measured_by_bme680": False,
        "requires_sensor": "Capteur de particules PM2.5/PM10 dédié",
        "source": "WHO Global Air Quality Guidelines 2021",
        "source_url": WHO_AQG_2021_URL,
        "note": (
            "Reference OMS pour l'air ambiant. SafeHome l'utilise comme repere preventif "
            "pour l'air interieur lorsque des particules sont mesurees par un capteur dedie; "
            "une valeur instantanee ne constitue pas une moyenne reglementaire."
        ),
        "human_explanation": (
            "Les PM2.5 sont des particules fines qui peuvent penetrer profondement dans les poumons. "
            "Le BME680 ne les mesure pas."
        ),
        "levels": [
            {
                "max": 5,
                "status": "good",
                "label": "Reference annuelle OMS",
                "averaging_time": "annuel",
                "interpretation": "Niveau tres faible selon la reference annuelle OMS.",
            },
            {
                "max": 15,
                "status": "medium",
                "label": "Reference 24 h OMS",
                "averaging_time": "24 h",
                "interpretation": "Vigilance preventive, surtout pour les publics sensibles.",
            },
            {
                "min": 15,
                "status": "bad",
                "label": "Au-dessus du repere 24 h OMS",
                "averaging_time": "24 h",
                "interpretation": "Reduire les sources de particules et aerer si l'air exterieur le permet.",
            },
        ],
    },
    "pm10": {
        "label": "PM10",
        "unit": "µg/m³",
        "api_unit": "µg/m³",
        "measured_by_bme680": False,
        "requires_sensor": "Capteur de particules PM2.5/PM10 dédié",
        "source": "WHO Global Air Quality Guidelines 2021",
        "source_url": WHO_AQG_2021_URL,
        "note": (
            "Reference OMS pour l'air ambiant, utilisee ici comme repere preventif interieur "
            "si un capteur de particules est ajoute."
        ),
        "human_explanation": (
            "Les PM10 representent des poussieres et particules respirables. Le BME680 ne les mesure pas."
        ),
        "levels": [
            {
                "max": 15,
                "status": "good",
                "label": "Reference annuelle OMS",
                "averaging_time": "annuel",
                "interpretation": "Niveau faible selon la reference annuelle OMS.",
            },
            {
                "max": 45,
                "status": "medium",
                "label": "Reference 24 h OMS",
                "averaging_time": "24 h",
                "interpretation": "Vigilance preventive et reduction des sources de poussiere.",
            },
            {
                "min": 45,
                "status": "bad",
                "label": "Au-dessus du repere 24 h OMS",
                "averaging_time": "24 h",
                "interpretation": "Limiter les sources de particules et renforcer la ventilation adaptee.",
            },
        ],
    },
    "no2": {
        "label": "NO2",
        "unit": "µg/m³",
        "api_unit": "ppm",
        "measured_by_bme680": False,
        "requires_sensor": "Capteur NO2 dédié",
        "source": "WHO Global Air Quality Guidelines 2021",
        "source_url": WHO_AQG_2021_URL,
        "note": (
            "L'API accepte une valeur NO2 en ppm et la convertit approximativement en µg/m³ "
            "pour comparaison aux reperes OMS. La conversion depend des conditions physiques."
        ),
        "human_explanation": "Le dioxyde d'azote peut provenir de combustions. Le BME680 ne le mesure pas.",
        "levels": [
            {
                "max": 10,
                "status": "good",
                "label": "Reference annuelle OMS",
                "averaging_time": "annuel",
                "interpretation": "Niveau faible selon la reference annuelle OMS.",
            },
            {
                "max": 25,
                "status": "medium",
                "label": "Reference 24 h OMS",
                "averaging_time": "24 h",
                "interpretation": "Vigilance preventive, verifier les sources de combustion.",
            },
            {
                "min": 25,
                "status": "bad",
                "label": "Au-dessus du repere 24 h OMS",
                "averaging_time": "24 h",
                "interpretation": "Reduire les sources de combustion et aerer si possible.",
            },
        ],
    },
    "co": {
        "label": "CO",
        "unit": "mg/m³",
        "api_unit": "ppm",
        "measured_by_bme680": False,
        "requires_sensor": "Capteur CO dédié et calibré",
        "source": "WHO Global Air Quality Guidelines 2021",
        "source_url": WHO_AQG_2021_URL,
        "note": (
            "L'API accepte une valeur CO en ppm et la convertit approximativement en mg/m³ "
            "pour comparaison aux reperes OMS. Un detecteur CO certifie reste necessaire pour la securite."
        ),
        "human_explanation": "Le monoxyde de carbone est un gaz toxique issu de combustions incompletes. Le BME680 ne le mesure pas.",
        "levels": [
            {
                "max": 4,
                "status": "good",
                "label": "Reference 24 h OMS",
                "averaging_time": "24 h",
                "interpretation": "Niveau sous le repere 24 h OMS.",
            },
            {
                "max": 10,
                "status": "medium",
                "label": "Reference 8 h OMS",
                "averaging_time": "8 h",
                "interpretation": "Vigilance, verifier les appareils a combustion.",
            },
            {
                "min": 10,
                "status": "bad",
                "label": "Au-dessus du repere 8 h OMS",
                "averaging_time": "8 h",
                "interpretation": "Action preventive forte; utiliser un detecteur certifie et suivre les consignes de securite.",
            },
        ],
    },
    "ozone": {
        "label": "Ozone",
        "unit": "µg/m³",
        "api_unit": "µg/m³",
        "measured_by_bme680": False,
        "requires_sensor": "Capteur ozone dédié",
        "source": "WHO Global Air Quality Guidelines 2021",
        "source_url": WHO_AQG_2021_URL,
        "note": "Reference OMS air ambiant; ajoutee pour une architecture extensible.",
        "human_explanation": "L'ozone n'est pas mesure par le BME680.",
        "levels": [
            {
                "max": 60,
                "status": "good",
                "label": "Reference saison de pointe OMS",
                "averaging_time": "saison de pointe",
                "interpretation": "Niveau sous le repere saisonnier OMS.",
            },
            {
                "max": 100,
                "status": "medium",
                "label": "Reference 8 h OMS",
                "averaging_time": "8 h",
                "interpretation": "Vigilance preventive.",
            },
            {
                "min": 100,
                "status": "bad",
                "label": "Au-dessus du repere 8 h OMS",
                "averaging_time": "8 h",
                "interpretation": "Limiter l'exposition et verifier les sources/conditions exterieures.",
            },
        ],
    },
    "so2": {
        "label": "SO2",
        "unit": "µg/m³",
        "api_unit": "µg/m³",
        "measured_by_bme680": False,
        "requires_sensor": "Capteur SO2 dédié",
        "source": "WHO Global Air Quality Guidelines 2021",
        "source_url": WHO_AQG_2021_URL,
        "note": "Reference OMS air ambiant; ajoutee pour une architecture extensible.",
        "human_explanation": "Le dioxyde de soufre n'est pas mesure par le BME680.",
        "levels": [
            {
                "max": 40,
                "status": "good",
                "label": "Reference 24 h OMS",
                "averaging_time": "24 h",
                "interpretation": "Niveau sous le repere 24 h OMS.",
            },
            {
                "max": 500,
                "status": "medium",
                "label": "Reference 10 min OMS",
                "averaging_time": "10 min",
                "interpretation": "Vigilance preventive.",
            },
            {
                "min": 500,
                "status": "bad",
                "label": "Au-dessus du repere 10 min OMS",
                "averaging_time": "10 min",
                "interpretation": "Reduire l'exposition et identifier les sources.",
            },
        ],
    },
    "co2": {
        "label": "CO₂",
        "unit": "ppm",
        "api_unit": "ppm",
        "measured_by_bme680": False,
        "requires_sensor": "Capteur CO2 NDIR dédié",
        "source": "ASHRAE Standard 62.1/62.2 and ASHRAE CO2 brief 2023",
        "source_url": ASHRAE_CO2_BRIEF_URL,
        "note": (
            "Le CO2 est un indicateur de ventilation et de confinement, pas une mesure globale de qualite de l'air. "
            "ASHRAE rappelle que ses standards ne fixent pas un seuil universel de CO2 pour garantir une IAQ acceptable; "
            "SafeHome utilise 1000 ppm comme repere preventif courant."
        ),
        "human_explanation": "Un CO2 eleve peut indiquer un renouvellement d'air insuffisant. Le BME680 ne le mesure pas.",
        "levels": [
            {
                "max": 800,
                "status": "good",
                "label": "Air bien renouvele",
                "averaging_time": "instantane indicatif",
                "interpretation": "Confinement faible dans les conditions habituelles.",
            },
            {
                "max": 1000,
                "status": "medium",
                "label": "Vigilance ventilation",
                "averaging_time": "instantane indicatif",
                "interpretation": "Renouveler l'air peut ameliorer le confort.",
            },
            {
                "min": 1000,
                "status": "bad",
                "label": "Ventilation insuffisante possible",
                "averaging_time": "instantane indicatif",
                "interpretation": "Aerer et verifier la ventilation, sans en faire un diagnostic medical.",
            },
        ],
    },
    "humidity": {
        "label": "Humidité relative",
        "unit": "%",
        "api_unit": "%",
        "measured_by_bme680": True,
        "requires_sensor": "BME680 ou capteur humidite",
        "source": "EPA indoor mold guidance / ASHRAE building health guidance",
        "source_url": EPA_HUMIDITY_URL,
        "note": (
            "EPA recommande de garder l'humidite interieure sous 60%, idealement 30-50% si possible. "
            "SafeHome utilise 40-60% comme zone de confort preventive demandee pour le prototype."
        ),
        "human_explanation": "Une humidite trop haute favorise l'inconfort et les moisissures; trop basse, elle peut assécher l'air.",
        "levels": [
            {
                "max": 30,
                "status": "bad",
                "label": "Air sec",
                "interpretation": "Air sec, irritation possible chez certaines personnes.",
            },
            {
                "min": 30,
                "max": 40,
                "status": "medium",
                "label": "Un peu sec",
                "interpretation": "Surveiller le confort et eviter de surchauffer.",
            },
            {
                "min": 40,
                "max": 60,
                "status": "good",
                "label": "Zone de confort",
                "interpretation": "Humidite dans la zone de confort preventive.",
            },
            {
                "min": 60,
                "max": 70,
                "status": "medium",
                "label": "Un peu humide",
                "interpretation": "Verifier la ventilation et la condensation.",
            },
            {
                "min": 70,
                "status": "bad",
                "label": "Trop humide",
                "interpretation": "Risque accru de moisissures et d'inconfort.",
            },
        ],
    },
    "temperature": {
        "label": "Température",
        "unit": "°C",
        "api_unit": "°C",
        "measured_by_bme680": True,
        "requires_sensor": "BME680 ou capteur temperature",
        "source": "ASHRAE Standard 55 thermal comfort principles / SafeHome comfort band",
        "source_url": "https://www.ashrae.org/technical-resources/bookstore/standard-55-thermal-environmental-conditions-for-human-occupancy",
        "note": (
            "La plage 19-22 °C est une zone de confort choisie pour le prototype; "
            "le confort thermique depend aussi de l'activite, des vetements, de l'air et du batiment."
        ),
        "human_explanation": "La temperature influence le confort mais ne suffit pas a diagnostiquer un risque sanitaire.",
        "levels": [
            {
                "min": 19,
                "max": 22,
                "status": "good",
                "label": "Confort",
                "interpretation": "Temperature confortable pour un espace de vie calme.",
            },
            {
                "min": 17,
                "max": 25,
                "status": "medium",
                "label": "Vigilance confort",
                "interpretation": "Inconfort possible selon les personnes et l'usage de la piece.",
            },
            {
                "status": "bad",
                "label": "Inconfort thermique",
                "interpretation": "Corriger progressivement le chauffage, la ventilation ou l'ombrage.",
            },
        ],
    },
    "gas_resistance": {
        "label": "Gaz / COV estimés",
        "unit": "Ω",
        "api_unit": "Ω",
        "measured_by_bme680": True,
        "requires_sensor": "BME680",
        "source": "Bosch BME680 gas resistance signal / SafeHome internal preventive heuristic",
        "source_url": "https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme680/",
        "note": (
            "La resistance gaz du BME680 est un signal indirect, sensible au capteur, a l'humidite et a la calibration. "
            "Les seuils SafeHome ne sont pas des seuils sanitaires; ils servent seulement a signaler une variation possible de COV/gaz."
        ),
        "human_explanation": "Une resistance gaz plus faible peut suggerer davantage de composes volatils, mais l'estimation reste indirecte.",
        "levels": [
            {
                "min": 100000,
                "status": "good",
                "label": "Signal favorable",
                "interpretation": "Resistance elevee, signal gaz estime favorable.",
            },
            {
                "min": 50000,
                "max": 100000,
                "status": "medium",
                "label": "Signal a surveiller",
                "interpretation": "Variation possible de COV/gaz; aerer et eviter les sources odorantes.",
            },
            {
                "max": 50000,
                "status": "bad",
                "label": "Signal defavorable",
                "interpretation": "Presence possible de COV/gaz; estimation uniquement, a confirmer par capteur dedie.",
            },
        ],
    },
    "pressure": {
        "label": "Pression",
        "unit": "hPa",
        "api_unit": "hPa",
        "measured_by_bme680": True,
        "requires_sensor": "BME680",
        "source": "Environmental context",
        "source_url": "",
        "note": "Information environnementale affichee, non utilisee comme risque sante majeur.",
        "human_explanation": "La pression aide a contextualiser l'environnement mais ne pilote pas le score sante SafeHome.",
        "levels": [],
    },
    "battery": {
        "label": "Batterie",
        "unit": "%",
        "api_unit": "%",
        "measured_by_bme680": False,
        "requires_sensor": "Mesure batterie optionnelle",
        "source": "Device telemetry",
        "source_url": "",
        "note": "Telemetrie technique, non sanitaire.",
        "human_explanation": "Permet de savoir si le boitier peut continuer a envoyer des mesures.",
        "levels": [],
    },
}


SOURCE_REFERENCES = [
    {
        "name": "WHO Global Air Quality Guidelines 2021",
        "url": WHO_AQG_2021_URL,
        "scope": "PM2.5, PM10, NO2, CO, ozone, SO2",
    },
    {
        "name": "WHO household air pollution and health",
        "url": WHO_HOUSEHOLD_AIR_URL,
        "scope": "Risques generaux de pollution interieure, combustion et particules.",
    },
    {
        "name": "ASHRAE Standards 62.1 / 62.2",
        "url": ASHRAE_62_URL,
        "scope": "Ventilation et qualite de l'air interieur acceptable par conception batiment.",
    },
    {
        "name": "ASHRAE indoor CO2, ventilation and IAQ brief 2023",
        "url": ASHRAE_CO2_BRIEF_URL,
        "scope": "Usage prudent du CO2 comme indicateur de ventilation, avec limites d'interpretation.",
    },
    {
        "name": "US EPA mold and indoor humidity guidance",
        "url": EPA_HUMIDITY_URL,
        "scope": "Humidite interieure, prevention de l'humidite excessive et des moisissures.",
    },
]
