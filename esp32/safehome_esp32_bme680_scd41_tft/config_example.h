#pragma once

// Copy this file to config.h and fill in your local values.
// Never commit config.h with WiFi credentials.

#define WIFI_SSID "Votre_WiFi"
#define WIFI_PASSWORD "Votre_mot_de_passe"

// From the same WiFi network as the Mac:
// http://192.168.1.42:5000/api/sensor-data
#define SAFEHOME_API_URL "http://192.168.1.XX:5000/api/sensor-data"
#define DEVICE_ID "safehome_001"

// Development mode: send every 10 seconds.
#define SEND_INTERVAL_MS 10000UL

// I2C bus: BME680 + SCD40/SCD41
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22

// ST7789 SPI
#define TFT_CLK_PIN 18
#define TFT_MOSI_PIN 23
#define TFT_DC_PIN 2
#define TFT_RST_PIN 4
#define TFT_CS_PIN 5

// Many ST7789 modules are 240x240 or 240x320.
#define TFT_WIDTH 240
#define TFT_HEIGHT 240
#define TFT_ROTATION 0

// Optional battery divider. Keep -1 if not wired.
#define BATTERY_ADC_PIN -1
#define BATTERY_MIN_VOLTAGE 3.30
#define BATTERY_MAX_VOLTAGE 4.20
