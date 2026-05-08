#pragma once

// Copiez ce fichier vers config.h et renseignez vos valeurs locales.
// Ne committez jamais config.h avec vos identifiants WiFi.

#define WIFI_SSID "Votre_WiFi"
#define WIFI_PASSWORD "Votre_mot_de_passe"

// Exemple depuis le même réseau WiFi que le Mac:
// http://192.168.1.42:5000/api/sensor-data
#define SAFEHOME_API_URL "http://192.168.1.XX:5000/api/sensor-data"
#define DEVICE_ID "safehome_001"

// En développement, l'envoi toutes les 10 secondes facilite la démonstration.
#define SEND_INTERVAL_MS 10000UL

// BME680 I2C
#define BME680_SDA_PIN 21
#define BME680_SCL_PIN 22

// ST7789 SPI
#define TFT_CLK_PIN 18
#define TFT_MOSI_PIN 23
#define TFT_DC_PIN 2
#define TFT_RST_PIN 4
#define TFT_CS_PIN 5

// Beaucoup de modules ST7789 ESP32 sont en 240x240 ou 240x320.
#define TFT_WIDTH 240
#define TFT_HEIGHT 240

// Batterie optionnelle. Laissez -1 si aucune mesure batterie n'est câblée.
#define BATTERY_ADC_PIN -1
#define BATTERY_MIN_VOLTAGE 3.30
#define BATTERY_MAX_VOLTAGE 4.20
