#include <WiFi.h>
#include <PubSubClient.h>

// Configura tus credenciales Wi-Fi
const char* ssid = "Casa_leo";
const char* password = "Odranoel";

// IP del broker MQTT (la IP de tu Raspberry Pi)
const char* mqtt_server = "192.168.100.10";  // Reemplaza X por la IP correcta

WiFiClient espClient;
PubSubClient client(espClient);

// Función callback (opcional, si deseas recibir mensajes)
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Mensaje recibido [");
  Serial.print(topic);
  Serial.print("] ");
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnect() {
  // Intenta reconectar al broker MQTT hasta tener conexión
  while (!client.connected()) {
    Serial.print("Intentando conectar al broker MQTT...");
    if (client.connect("ESP32_Client")) {
      Serial.println("Conectado");
      // Si deseas suscribirte a algún tópico, hazlo aquí:
      // client.subscribe("lab/equipo1/otro_topico");
    } else {
      Serial.print("Fallo, rc=");
      Serial.print(client.state());
      Serial.println(" - Reintentando en 5 segundos");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(10);
  
  // Conectar al Wi-Fi
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  
  // Configurar el servidor MQTT y el callback
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Publicar datos cada 5 segundos
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish > 5000) {
    lastPublish = millis();
    float temperatura = 25.0;  // Valor simulado de temperatura
    char tempStr[8];
    dtostrf(temperatura, 1, 2, tempStr);
    client.publish("lab/equipo1/temperatura", tempStr);
    Serial.print("Publicada temperatura: ");
    Serial.println(tempStr);
  }
}
