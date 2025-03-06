#include <WiFi.h>
#include <PubSubClient.h>
#include <math.h>

// Credenciales Wi-Fi
const char* ssid = "Casa_leo";
const char* password = "Odranoel";

// Broker MQTT: IP de la Raspberry Pi
const char* mqtt_server = "192.168.100.10";

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  // No lo usamos para este dispositivo
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_Estacion")) {
      // No es necesario suscribirse, solo publicamos
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();
  
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish > 5000) {
    lastPublish = millis();
    
    float angle = (millis() / 1000.0) * (PI / 50);
    float temp = 25.0 + 5.0 * sin(angle);
    float hum  = 50.0 + 10.0 * sin(angle + 1);
    float pres = 1013.0 + 3.0 * sin(angle + 2);
    
    char payload[128];
    snprintf(payload, sizeof(payload),
      "{\"device_name\":\"estacion\",\"temp\":%.2f,\"hum\":%.2f,\"pres\":%.2f}",
      temp, hum, pres);
      
    client.publish("lab/devices/estacion/data", payload);
    Serial.println(payload);
  }
}
