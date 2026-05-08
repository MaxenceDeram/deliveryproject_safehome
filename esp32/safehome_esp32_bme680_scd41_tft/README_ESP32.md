# SafeHome ESP32 BME680 + SCD40/SCD41 + TFT

Sketch de développement pour un ESP32 WROOM32 avec BME680, SCD40/SCD41 et écran TFT ST7789.

## Matériel

- ESP32 WROOM32 / ESP32 Dev Module
- BME680 en I2C
- SCD40 ou SCD41 en I2C
- Écran TFT ST7789 en SPI
- Câble USB data, pas seulement charge

## Branchement

BME680 + SCD40/SCD41 I2C :

- SDA -> GPIO 21
- SCL -> GPIO 22
- VCC -> 3.3V
- GND -> GND

BME680 :

- CS -> 3.3V pour forcer le mode I2C
- SDO -> GND ou non connecté selon le module
- adresse probable 0x76 si SDO est à GND

SCD40/SCD41 :

- adresse I2C 0x62

TFT ST7789 SPI :

- VCC -> 3.3V
- GND -> GND
- CLK/SCL -> GPIO 18
- MOSI/SDA -> GPIO 23
- DC -> GPIO 2
- RST -> GPIO 4
- CS -> GPIO 5
- BL/LED -> 3.3V

## Librairies Arduino

Installer depuis Arduino IDE > Library Manager :

- Adafruit BME680 Library
- Adafruit SCD4X
- Adafruit Unified Sensor
- Adafruit GFX Library
- Adafruit ST7735 and ST7789 Library
- ArduinoJson

Installer aussi le support de cartes ESP32 via Boards Manager si ce n'est pas déjà fait.

## Configuration

1. Ouvrir le dossier `esp32/safehome_esp32_bme680_scd41_tft/`.
2. Copier `config_example.h` vers `config.h`.
3. Renseigner :
   - `WIFI_SSID`
   - `WIFI_PASSWORD`
   - `SAFEHOME_API_URL`
   - `DEVICE_ID`
4. Sélectionner `ESP32 Dev Module`.
5. Compiler puis téléverser.

Exemple d'URL API :

```cpp
#define SAFEHOME_API_URL "http://192.168.1.42:5000/api/sensor-data"
```

## Trouver l'IP du Mac

Sur WiFi :

```bash
ipconfig getifaddr en0
```

Sur Ethernet :

```bash
ipconfig getifaddr en1
```

Depuis l'ESP32, ne pas utiliser `127.0.0.1` : cela désigne l'ESP32 lui-même. Utiliser l'IP locale du Mac.

## Ce que le sketch envoie

Toutes les 10 secondes en mode développement :

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

Le BME680 fournit température, humidité, pression et résistance gaz/COV estimés. Le SCD40/SCD41 fournit le vrai CO2 en ppm. PM2.5 et PM10 ne sont pas envoyés sans capteur de particules dédié.

## Écran TFT

L'écran affiche :

- WiFi OK/KO
- API OK/KO
- BME680 OK/KO
- SCD40/SCD41 OK/KO
- statut local GOOD / MEDIUM / BAD
- score local indicatif
- température, humidité, CO2, COV estimés

## Dépannage

ESP32 non détecté :

- Essayer un autre câble USB, certains câbles ne font que charger.
- Maintenir `BOOT` au début du téléversement selon la carte.
- Installer le pilote USB série si nécessaire.

Écran noir :

- Vérifier VCC, GND et BL/LED sur 3.3V.
- Vérifier `TFT_CLK_PIN`, `TFT_MOSI_PIN`, `TFT_DC_PIN`, `TFT_RST_PIN`, `TFT_CS_PIN`.
- Tester `TFT_WIDTH` / `TFT_HEIGHT` en 240x240 ou 240x320.
- Tester `TFT_ROTATION` de 0 à 3.

BME680 non détecté :

- Vérifier SDA GPIO 21 et SCL GPIO 22.
- Vérifier que CS est à 3.3V pour le mode I2C.
- Tester SDO à GND pour adresse 0x76, ou laisser selon le module pour 0x77.
- Alimenter en 3.3V.

SCD40/SCD41 non détecté :

- Vérifier l'adresse I2C 0x62.
- Vérifier SDA/SCL sur le même bus que le BME680.
- Attendre quelques secondes après l'alimentation, le capteur peut nécessiter un court délai.

API unreachable :

- Lancer Flask avec `python app.py`.
- Vérifier que Flask écoute sur `0.0.0.0:5000`.
- Vérifier que Mac et ESP32 sont sur le même WiFi.
- Tester depuis un autre appareil : `http://IP_DU_MAC:5000/api/health`.
- Autoriser Python/Terminal dans le firewall macOS.

Mauvais réseau WiFi :

- L'ESP32 utilise souvent le 2.4 GHz.
- Éviter les réseaux invités qui isolent les appareils.
- Vérifier que l'adresse IP du Mac n'a pas changé.
