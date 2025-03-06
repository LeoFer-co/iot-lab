#include <WiFi.h>
#include <PubSubClient.h>
#include <math.h>  // Para sin()

// Configura tus credenciales Wi-Fi
const char* ssid = "Casa_leo";
const char* password = "Odranoel";

// IP del broker MQTT (la IP de tu Raspberry Pi)
const char* mqtt_server = "192.168.100.10";

WiFiClient espClient;
PubSubClient client(espClient);

// Callback opcional (puedes dejarlo vacío si no necesitas recibir mensajes)
void callback(char* topic, byte* payload, unsigned int length) {
  // Si deseas procesar mensajes entrantes, implementa aquí.
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Intentando conectar al broker MQTT...");
    if (client.connect("ESP32_Client")) {
      Serial.println("Conectado");
      // No es necesario suscribirse si solo publicas
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
    
    // Calcular valores simulados usando funciones seno con menor variación entre puntos.
    // Se reduce la frecuencia cambiando (PI/5) a (PI/50)
    float angle = (millis() / 1000.0) * (PI / 50);  // Frecuencia reducida para suavizar la gráfica
    float temp    = 25.0 + 5.0 * sin(angle);
    float hum     = 50.0 + 10.0 * sin(angle + 1);
    float pres    = 1013.0 + 3.0 * sin(angle + 2);
    float light   = 300.0 + 100.0 * sin(angle + 3);
    float sound   = 60.0 + 5.0 * sin(angle + 4);
    float voltage = 3.3 + 0.1 * sin(angle + 5);
    
    // Crear el string JSON con 6 campos
    char payload[128];
    snprintf(payload, sizeof(payload),
             "{\"temp\":%.2f,\"hum\":%.2f,\"pres\":%.2f,\"light\":%.2f,\"sound\":%.2f,\"voltage\":%.2f}",
             temp, hum, pres, light, sound, voltage);
    
    client.publish("lab/equipo1/data", payload);
    Serial.print("Publicado: ");
    Serial.println(payload);
  }
}
