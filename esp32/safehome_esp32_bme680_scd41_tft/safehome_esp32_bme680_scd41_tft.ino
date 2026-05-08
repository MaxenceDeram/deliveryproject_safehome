#include <Adafruit_BME680.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SCD4X.h>
#include <Adafruit_ST7789.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <WiFi.h>
#include <Wire.h>

#include "config.h"

Adafruit_BME680 bme;
Adafruit_SCD4X scd4x;
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS_PIN, TFT_DC_PIN, TFT_RST_PIN);

bool bmeOk = false;
bool scdOk = false;
bool apiOk = false;
bool wifiOk = false;
unsigned long lastSendAt = 0;

struct Reading {
  float temperature;
  float humidity;
  float pressure;
  uint32_t gasResistance;
  uint16_t co2;
  int battery;
  bool hasBme;
  bool hasScd;
};

void drawBootScreen(const char* line1, const char* line2 = "") {
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextWrap(false);
  tft.setTextColor(ST77XX_CYAN);
  tft.setTextSize(2);
  tft.setCursor(10, 18);
  tft.print("SafeHome");
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(1);
  tft.setCursor(10, 54);
  tft.print(line1);
  if (strlen(line2) > 0) {
    tft.setCursor(10, 70);
    tft.print(line2);
  }
}

void drawStatusDot(int16_t x, int16_t y, bool ok, uint16_t warnColor = ST77XX_ORANGE) {
  tft.fillCircle(x, y, 4, ok ? ST77XX_GREEN : warnColor);
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
  wifiOk = WiFi.status() == WL_CONNECTED;
  return wifiOk;
}

bool setupBme680() {
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

bool setupScd41() {
  if (!scd4x.begin()) {
    return false;
  }
  scd4x.startPeriodicMeasurement();
  return true;
}

bool readBme680(Reading &reading) {
  if (!bmeOk || !bme.performReading()) {
    reading.hasBme = false;
    return false;
  }

  reading.temperature = bme.temperature;
  reading.humidity = bme.humidity;
  reading.pressure = bme.pressure / 100.0;
  reading.gasResistance = bme.gas_resistance;
  reading.hasBme = true;
  return true;
}

bool readScd41(Reading &reading) {
  if (!scdOk) {
    reading.hasScd = false;
    return false;
  }

  sensors_event_t humidityEvent;
  sensors_event_t tempEvent;
  uint16_t co2 = 0;

  if (!scd4x.getEvent(&co2, &tempEvent, &humidityEvent)) {
    reading.hasScd = false;
    return false;
  }

  if (co2 == 0) {
    reading.hasScd = false;
    return false;
  }

  reading.co2 = co2;
  reading.hasScd = true;
  return true;
}

String buildPayload(const Reading &reading) {
  StaticJsonDocument<512> doc;
  doc["device_id"] = DEVICE_ID;

  if (reading.hasBme) {
    doc["temperature"] = round(reading.temperature * 10.0) / 10.0;
    doc["humidity"] = round(reading.humidity * 10.0) / 10.0;
    doc["pressure"] = round(reading.pressure * 10.0) / 10.0;
    doc["gas_resistance"] = reading.gasResistance;
  }

  if (reading.hasScd) {
    doc["co2"] = reading.co2;
  }

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

int localScore(const Reading &reading) {
  int score = 100;
  if (reading.hasScd) {
    if (reading.co2 > 1500) score -= 45;
    else if (reading.co2 > 1000) score -= 25;
    else if (reading.co2 > 800) score -= 10;
  }
  if (reading.hasBme) {
    if (reading.humidity < 40 || reading.humidity > 60) score -= 14;
    if (reading.temperature > 25 || reading.temperature < 17) score -= 14;
    if (reading.gasResistance < 50000) score -= 28;
    else if (reading.gasResistance < 100000) score -= 12;
  }
  if (score < 0) score = 0;
  return score;
}

const char* localStatus(const Reading &reading) {
  int score = localScore(reading);
  if (score >= 85) return "GOOD";
  if (score >= 50) return "MEDIUM";
  return "BAD";
}

uint16_t statusColor(const Reading &reading) {
  int score = localScore(reading);
  if (score >= 85) return ST77XX_GREEN;
  if (score >= 50) return ST77XX_ORANGE;
  return ST77XX_RED;
}

void drawReading(const Reading &reading) {
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextWrap(false);

  tft.setTextColor(ST77XX_CYAN);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.print("SafeHome");

  tft.setTextSize(1);
  tft.setTextColor(ST77XX_WHITE);
  tft.setCursor(10, 42);
  tft.print("WiFi");
  drawStatusDot(56, 46, WiFi.status() == WL_CONNECTED);
  tft.setCursor(74, 42);
  tft.print("API");
  drawStatusDot(112, 46, apiOk);
  tft.setCursor(130, 42);
  tft.print("BME");
  drawStatusDot(170, 46, bmeOk);
  tft.setCursor(188, 42);
  tft.print("CO2");
  drawStatusDot(228, 46, scdOk);

  tft.setTextColor(statusColor(reading));
  tft.setTextSize(3);
  tft.setCursor(10, 72);
  tft.print(localStatus(reading));

  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(10, 118);
  tft.print("Score ");
  tft.print(localScore(reading));
  tft.print("/100");

  tft.setTextSize(1);
  tft.setCursor(10, 152);
  tft.print("Temp: ");
  reading.hasBme ? tft.print(reading.temperature, 1) : tft.print("--");
  tft.print(" C");

  tft.setCursor(10, 168);
  tft.print("Hum:  ");
  reading.hasBme ? tft.print(reading.humidity, 1) : tft.print("--");
  tft.print(" %");

  tft.setCursor(10, 184);
  tft.print("CO2:  ");
  reading.hasScd ? tft.print(reading.co2) : tft.print("--");
  tft.print(" ppm");

  tft.setCursor(10, 200);
  tft.print("COV:  ");
  if (reading.hasBme) {
    tft.print(reading.gasResistance / 1000.0, 1);
    tft.print(" kOhm");
  } else {
    tft.print("--");
  }

  tft.setTextColor(ST77XX_YELLOW);
  tft.setCursor(10, 224);
  tft.print(apiOk ? "Envoye a SafeHome" : "API unreachable");
}

void setup() {
  Serial.begin(115200);
  delay(500);

  SPI.begin(TFT_CLK_PIN, -1, TFT_MOSI_PIN, TFT_CS_PIN);
  tft.init(TFT_WIDTH, TFT_HEIGHT);
  tft.setRotation(TFT_ROTATION);
  drawBootScreen("Initialisation...");

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  wifiOk = connectWifi();
  bmeOk = setupBme680();
  scdOk = setupScd41();

  tft.setTextSize(1);
  tft.setCursor(10, 96);
  tft.setTextColor(wifiOk ? ST77XX_GREEN : ST77XX_RED);
  tft.print(wifiOk ? "WiFi connecte" : "WiFi indisponible");

  tft.setCursor(10, 112);
  tft.setTextColor(bmeOk ? ST77XX_GREEN : ST77XX_RED);
  tft.print(bmeOk ? "BME680 detecte" : "BME680 non detecte");

  tft.setCursor(10, 128);
  tft.setTextColor(scdOk ? ST77XX_GREEN : ST77XX_RED);
  tft.print(scdOk ? "SCD40/SCD41 detecte" : "SCD41 non detecte");

  delay(1400);
}

void loop() {
  if (millis() - lastSendAt < SEND_INTERVAL_MS) {
    delay(50);
    return;
  }
  lastSendAt = millis();

  Reading reading;
  reading.temperature = 0;
  reading.humidity = 0;
  reading.pressure = 0;
  reading.gasResistance = 0;
  reading.co2 = 0;
  reading.battery = readBatteryPercent();
  reading.hasBme = false;
  reading.hasScd = false;

  bmeOk = readBme680(reading);
  scdOk = readScd41(reading);

  if (!reading.hasBme && !reading.hasScd) {
    drawBootScreen("Erreur capteurs", "BME680/SCD41 absents");
    delay(1000);
    return;
  }

  apiOk = postToSafeHome(reading);
  drawReading(reading);
}
