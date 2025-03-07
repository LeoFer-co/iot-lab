#include <WiFi.h>
#include <PubSubClient.h>
#include <math.h>

// Credenciales Wi-Fi
const char* ssid = "Casa_leo";
const char* password = "Odranoel";

// Broker MQTT
// Usa la IP o el hostname del broker en tu Docker Compose (p.ej. "broker")
const char* mqtt_server = "192.168.100.10";

// Nombre y subtopic del dispositivo
// Subtopic = "estacion", device_name = "estacion"
WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  // No lo usamos para este dispositivo
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_Estacion")) {
      // No suscribimos nada, solo publicamos
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado. IP: ");
  Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  static unsigned long lastPublish = 0;
  if (millis() - lastPublish > 1000) {
    lastPublish = millis();
    
    // Simulación de valores con sin()
    float angle = (millis() / 1000.0) * (PI / 50); // Ajusta la frecuencia
    float temp = 25.0 + 5.0 * sin(angle);
    float hum  = 50.0 + 10.0 * sin(angle + 1);
    float pres = 1013.0 + 3.0 * sin(angle + 2);
    
    // Empaquetamos en JSON con "device_name": "estacion"
    char payload[128];
    snprintf(payload, sizeof(payload),
      "{\"device_name\":\"estacion\",\"temp\":%.2f,\"hum\":%.2f,\"pres\":%.2f}",
      temp, hum, pres);

    // Publicamos en "lab/devices/estacion/data"
    client.publish("lab/devices/estacion/data", payload);
    Serial.print("Publicado: ");
    Serial.println(payload);
  }
}
