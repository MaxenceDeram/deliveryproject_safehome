# SafeHome

SafeHome est un prototype Flask + ESP32 pour surveiller la qualité de l'air intérieur avec une interface dashboard premium sombre.

Le prototype cible :

- ESP32 WROOM32
- BME680 : température, humidité, pression, résistance gaz / COV estimés
- SCD40/SCD41 : vrai CO2 en ppm
- TFT ST7789
- Backend Python Flask
- Frontend HTML/CSS/JS vanilla avec Chart.js

## Limite sanitaire

SafeHome fournit des indicateurs de prévention et de confort. Il ne remplace pas un diagnostic médical ni un appareil réglementaire certifié.

Règles importantes :

- Le BME680 ne mesure pas le CO2.
- Le SCD40/SCD41 mesure le vrai CO2 en ppm.
- Le BME680 ne mesure pas PM2.5 / PM10.
- Les données absentes sont affichées comme `Non mesuré`.
- Les COV BME680 restent une estimation indirecte, pas un diagnostic.

Les repères sont documentés dans `services/health_guidelines.py`.

## Installation Flask

Depuis le dossier `safehome` :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Site local :

```text
http://127.0.0.1:5000
```

Le projet n'a pas de build frontend séparé : le frontend est servi par Flask dans `templates/`, `static/css/` et `static/js/`.

## Tester sans ESP32

Le backend démarre sans mesure par défaut. Le dashboard reste en attente tant que l'ESP32 n'a rien envoyé.

Pour faire une démo volontairement, cliquer sur `Simuler` depuis le dashboard.

Ou appeler :

```bash
curl http://127.0.0.1:5000/api/simulate
```

La simulation est explicitement marquée comme `source: simulation`. Elle peut simuler BME680 + SCD40/SCD41, mais ne prétend pas être une mesure réelle.

## API

### POST `/api/sensor-data`

Payload attendu :

```json
{
  "device_id": "safehome_001",
  "temperature": 22.4,
  "humidity": 48,
  "pressure": 1012.6,
  "gas_resistance": 124000,
  "co2": 412,
  "battery": 82
}
```

Champs futurs optionnels :

```json
{
  "pm25": 4.2,
  "pm10": 12.5,
  "no2": 0.02,
  "co": 0.3
}
```

Exemple curl :

```bash
curl -X POST http://127.0.0.1:5000/api/sensor-data \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "safehome_001",
    "temperature": 22.4,
    "humidity": 48,
    "pressure": 1012.6,
    "gas_resistance": 124000,
    "co2": 412,
    "battery": 82
  }'
```

### GET endpoints

- `/api/current-data` : dernière mesure, score, statuts, métriques, risques et recommandations.
- `/api/history?range=6h|24h|7d|30d` : historique mémoire limité à 500 mesures.
- `/api/recommendations` : recommandations adaptées aux dernières mesures.
- `/api/health` : état API, source, âge de la dernière mesure, batterie et connexion ESP32.
- `/api/guidelines` : repères, sources et limites capteurs.
- `/api/export.csv` : export CSV.
- `/api/simulate` : ajoute une mesure simulée.

## Backend

Fichiers principaux :

- `app.py` : routes Flask.
- `services/air_quality.py` : validation payload, score, statuts, métriques, risques, confiance.
- `services/recommendations.py` : recommandations automatiques.
- `services/health_guidelines.py` : seuils, sources et disclaimer.
- `services/storage.py` : stockage mémoire et historique simulé.

Stockage actuel :

- mémoire simple
- historique limité à 500 mesures
- structure prête à être remplacée par SQLite plus tard

## Score global

Le score combine uniquement les mesures disponibles :

- CO2 si présent
- humidité
- température
- COV/gas resistance BME680
- PM2.5 / PM10 si un capteur dédié les fournit plus tard

Statuts :

- `>= 85` : Excellente
- `70-84` : Bonne
- `50-69` : Vigilance
- `< 50` : Dégradée

## ESP32

Nouveau sketch :

```text
../esp32/safehome_esp32_bme680_scd41_tft/
```

Fichiers :

- `safehome_esp32_bme680_scd41_tft.ino`
- `config_example.h`
- `README_ESP32.md`

Librairies Arduino à installer :

- Adafruit BME680 Library
- Adafruit SCD4X
- Adafruit Unified Sensor
- Adafruit GFX Library
- Adafruit ST7735 and ST7789 Library
- ArduinoJson

## Trouver l'IP du Mac

WiFi :

```bash
ipconfig getifaddr en0
```

Ethernet :

```bash
ipconfig getifaddr en1
```

Dans `config.h`, utiliser l'IP du Mac :

```cpp
#define SAFEHOME_API_URL "http://192.168.1.42:5000/api/sensor-data"
```

Ne pas utiliser `127.0.0.1` depuis l'ESP32.

## Branchement rapide

BME680 + SCD40/SCD41 I2C :

- SDA GPIO 21
- SCL GPIO 22
- VCC 3.3V
- GND GND

TFT ST7789 SPI :

- CLK/SCL GPIO 18
- MOSI/SDA GPIO 23
- DC GPIO 2
- RST GPIO 4
- CS GPIO 5
- BL/LED 3.3V

Voir `../esp32/safehome_esp32_bme680_scd41_tft/README_ESP32.md` pour le câblage complet.

## Dépannage

ESP32 non détecté :

- Essayer un vrai câble USB data.
- Maintenir `BOOT` pendant le début du téléversement.
- Installer le pilote USB série si nécessaire.

Écran noir :

- Vérifier VCC, GND et BL/LED sur 3.3V.
- Vérifier les pins SPI.
- Tester `TFT_WIDTH`, `TFT_HEIGHT` et `TFT_ROTATION`.

BME680 non détecté :

- Vérifier SDA/SCL.
- Vérifier CS à 3.3V.
- Tester adresses 0x76 et 0x77.

SCD41 non détecté :

- Vérifier adresse I2C 0x62.
- Vérifier le bus I2C commun GPIO 21/22.

API unreachable :

- Vérifier que Flask tourne.
- Vérifier que Mac et ESP32 sont sur le même WiFi.
- Autoriser Python/Terminal dans le firewall macOS.
- Tester `http://IP_DU_MAC:5000/api/health`.

## Limites techniques du prototype

- Pas de persistance disque : l'historique mémoire disparaît au redémarrage.
- Pas d'authentification réelle pour l'instant.
- Pas de WebSocket : le dashboard poll l'API toutes les 10 secondes.
- Les COV BME680 sont une estimation indirecte sensible à la calibration.
- Les données extérieures ne sont pas connectées.
- PM2.5 / PM10 restent non mesurés tant qu'un capteur dédié n'est pas ajouté.
