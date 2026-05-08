#include <Adafruit_BME680.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <WiFi.h>
#include <Wire.h>

#include "config.h"

Adafruit_BME680 bme;
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);

bool sensorOk = false;
bool apiOk = false;
unsigned long lastSendAt = 0;

struct Reading {
  float temperature;
  float humidity;
  float pressure;
  uint32_t gasResistance;
  int battery;
};

void drawStatusLine(const char* label, bool ok, int16_t y) {
  tft.setCursor(10, y);
  tft.setTextColor(ok ? ST77XX_GREEN : ST77XX_RED);
  tft.setTextSize(1);
  tft.print(label);
  tft.print(ok ? " OK" : " KO");
}

void drawBootScreen(const char* message) {
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(10, 18);
  tft.print("SafeHome");
  tft.setTextSize(1);
  tft.setCursor(10, 52);
  tft.print(message);
}

int readBatteryPercent() {
  if (BATTERY_ADC_PIN < 0) return -1;

  int raw = analogRead(BATTERY_ADC_PIN);
  float voltage = (raw / 4095.0) * 3.3 * 2.0;
  float percent = (voltage - BATTERY_MIN_VOLTAGE) * 100.0 / (BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE);
  if (percent < 0) percent = 0;
  if (percent > 100) percent = 100;
  return (int)round(percent);
}

bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) {
    delay(300);
  }
  return WiFi.status() == WL_CONNECTED;
}

bool setupSensor() {
  Wire.begin(BME680_SDA_PIN, BME680_SCL_PIN);

  if (!bme.begin(0x76) && !bme.begin(0x77)) {
    return false;
  }

  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
  bme.setGasHeater(320, 150);
  return true;
}

bool readBme680(Reading &reading) {
  if (!sensorOk || !bme.performReading()) {
    return false;
  }

  reading.temperature = bme.temperature;
  reading.humidity = bme.humidity;
  reading.pressure = bme.pressure / 100.0;
  reading.gasResistance = bme.gas_resistance;
  reading.battery = readBatteryPercent();
  return true;
}

String buildPayload(const Reading &reading) {
  StaticJsonDocument<384> doc;
  doc["device_id"] = DEVICE_ID;
  doc["temperature"] = round(reading.temperature * 10.0) / 10.0;
  doc["humidity"] = round(reading.humidity * 10.0) / 10.0;
  doc["pressure"] = round(reading.pressure * 10.0) / 10.0;
  doc["gas_resistance"] = reading.gasResistance;
  if (reading.battery >= 0) {
    doc["battery"] = reading.battery;
  }

  String payload;
  serializeJson(doc, payload);
  return payload;
}

bool postToSafeHome(const Reading &reading) {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  http.begin(SAFEHOME_API_URL);
  http.addHeader("Content-Type", "application/json");

  String payload = buildPayload(reading);
  int httpCode = http.POST(payload);
  String response = http.getString();
  http.end();

  Serial.print("POST ");
  Serial.print(httpCode);
  Serial.print(" ");
  Serial.println(response);

  return httpCode >= 200 && httpCode < 300;
}

String estimatedStatus(uint32_t gasResistance, float humidity, float temperature) {
  if (humidity > 70 || gasResistance < 50000 || temperature > 25) {
    return "Action";
  }
  if (humidity < 40 || humidity > 60 || gasResistance < 100000 || temperature > 22) {
    return "Vigilance";
  }
  return "Correct";
}

void drawReading(const Reading &reading) {
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextWrap(false);

  tft.setCursor(10, 10);
  tft.setTextColor(ST77XX_CYAN);
  tft.setTextSize(2);
  tft.print("SafeHome");

  tft.setTextSize(1);
  drawStatusLine("WiFi", WiFi.status() == WL_CONNECTED, 42);
  drawStatusLine("API", apiOk, 58);
  drawStatusLine("Sensor", sensorOk, 74);

  tft.setTextColor(ST77XX_WHITE);
  tft.setCursor(10, 102);
  tft.setTextSize(2);
  tft.print(estimatedStatus(reading.gasResistance, reading.humidity, reading.temperature));

  tft.setTextSize(1);
  tft.setCursor(10, 138);
  tft.print("Temp: ");
  tft.print(reading.temperature, 1);
  tft.print(" C");

  tft.setCursor(10, 154);
  tft.print("Hum:  ");
  tft.print(reading.humidity, 1);
  tft.print(" %");

  tft.setCursor(10, 170);
  tft.print("Press:");
  tft.print(reading.pressure, 1);
  tft.print(" hPa");

  tft.setCursor(10, 186);
  tft.print("Gaz:  ");
  tft.print(reading.gasResistance / 1000.0, 1);
  tft.print(" kOhm");

  tft.setTextColor(ST77XX_YELLOW);
  tft.setCursor(10, 214);
  tft.print("CO2/PM: non mesures");
}

void setup() {
  Serial.begin(115200);
  delay(500);

  SPI.begin(TFT_CLK_PIN, -1, TFT_MOSI_PIN, TFT_CS_PIN);
  tft.init(TFT_WIDTH, TFT_HEIGHT);
  tft.setRotation(0);
  drawBootScreen("Initialisation...");

  bool wifiOk = connectWifi();
  sensorOk = setupSensor();

  tft.setCursor(10, 78);
  tft.setTextColor(wifiOk ? ST77XX_GREEN : ST77XX_RED);
  tft.print(wifiOk ? "WiFi connecte" : "WiFi indisponible");

  tft.setCursor(10, 94);
  tft.setTextColor(sensorOk ? ST77XX_GREEN : ST77XX_RED);
  tft.print(sensorOk ? "BME680 detecte" : "BME680 non detecte");

  delay(1200);
}

void loop() {
  if (millis() - lastSendAt < SEND_INTERVAL_MS) {
    delay(50);
    return;
  }
  lastSendAt = millis();

  Reading reading;
  if (!readBme680(reading)) {
    sensorOk = false;
    drawBootScreen("Erreur BME680");
    delay(1000);
    return;
  }

  apiOk = postToSafeHome(reading);
  drawReading(reading);
}
