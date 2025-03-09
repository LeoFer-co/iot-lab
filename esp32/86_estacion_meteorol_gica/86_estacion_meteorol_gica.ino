#include <ESP8266WiFi.h>      // En ESP8266 usamos esta librería
#include <PubSubClient.h>
#include <math.h>

// --- Configuración Wi-Fi ---
const char* ssid = "Casa_leo";
const char* password = "Odranoel";

// --- Configuración MQTT ---
const char* mqtt_server = "192.168.100.10"; // IP/broker donde se aloja MQTT

WiFiClient espClient;
PubSubClient client(espClient);

// Callback MQTT (no lo usamos en este ejemplo)
void callback(char* topic, byte* payload, unsigned int length) {  
}

// Función para reconectarnos al broker si se cae la conexión
void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_Estacion")) {
      // No suscribimos a temas, sólo publicamos
    } else {
      delay(5000);  // Espera y reintenta
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);

  // Conexión Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado. IP local: ");
  Serial.println(WiFi.localIP());

  // Inicializar cliente MQTT
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Publicar datos cada 1 segundo (1000 ms)
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish > 1000) {
    lastPublish = millis();

    // Simulación de valores con sin()
    float angle = (millis() / 1000.0) * (PI / 50);
    float temp = 25.0 + 5.0 * sin(angle);
    float hum  = 50.0 + 10.0 * sin(angle + 1);
    float pres = 1013.0 + 3.0 * sin(angle + 2);

    // Empaquetamos en JSON
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
