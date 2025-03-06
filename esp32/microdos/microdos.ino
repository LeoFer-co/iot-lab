#include <WiFi.h>
#include <PubSubClient.h>

// Credenciales Wi-Fi
const char* ssid = "Casa_leo";
const char* password = "Odranoel";

// Broker MQTT
const char* mqtt_server = "192.168.100.10";

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  // No lo usamos para este dispositivo
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_Microdos")) {
      // Solo publicamos
    } else {
      delay(5000);
    }
  }
}

// Variables de ejemplo para Microdós
bool isRunning = false;
float flowSet = 10.0;   // ml/min
int timeLeft = 60;      // en segundos

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();
  
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish > 5000) {
    lastPublish = millis();
    
    // Lógica de ejemplo para simular estado:
    static unsigned long startTime = millis();
    unsigned long elapsed = (millis() - startTime) / 1000;
    if (elapsed < 30) {
      isRunning = true;
      timeLeft = 30 - elapsed;
    } else if (elapsed < 60) {
      isRunning = false;
      timeLeft = 0;
    } else {
      startTime = millis();
    }
    const char* statusStr = isRunning ? "running" : (timeLeft == 0 ? "finished" : "idle");
    
    char payload[128];
    snprintf(payload, sizeof(payload),
      "{\"device_name\":\"microdos\",\"status\":\"%s\",\"flow_set\":%.2f,\"time_left\":%d}",
      statusStr, flowSet, timeLeft);
      
    client.publish("lab/devices/microdos/data", payload);
    Serial.println(payload);
  }
}
