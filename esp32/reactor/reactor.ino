#include <WiFi.h>
#include <PubSubClient.h>
#include <math.h>

// Configuración de Wi-Fi y broker
const char* ssid = "Casa_leo";
const char* password = "Odranoel";
const char* mqtt_server = "192.168.100.10";

// Parámetros del Reactor Quitosano
float baseTemp = 25.0;          // Temperatura base
float amplitudeTemp = 5.0;      // Oscilación ±3°C
float agitationSpeed = 0;       // Velocidad de agitación (0 a 1000 rpm)
int maxTime = 60;               // Tiempo total de operación (seg)
int timeLeft = 0;               // Tiempo restante (seg)
String reactorState = "inactivo"; // Estado actual

// Nueva variable: Temperatura seteada. Inicialmente igual a baseTemp.
float tempSet = baseTemp;

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  // Este dispositivo no recibe mensajes, solo publica.
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_Reactor")) {
      // Conectado, no es necesario suscribir.
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado.");
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  Serial.println("Reactor Quitosano inicializado.");
  Serial.println("Comandos:");
  Serial.println("  speed X      -> establece velocidad (0-1000 rpm)");
  Serial.println("  start T      -> inicia operación con tiempo T (seg)");
  Serial.println("  state <texto> -> establece estado (ej: 'Desmineralización running')");
  Serial.println("  tempset X    -> establece la temperatura seteada (°C)");
  Serial.println("  reset        -> reinicia a estado inactivo");
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Procesar comandos desde el Monitor Serie (se procesa una sola línea por ciclo)
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("speed ")) {
      String val = cmd.substring(6);
      agitationSpeed = val.toFloat();
      Serial.print("Velocidad establecida: ");
      Serial.println(agitationSpeed);
    } else if (cmd.startsWith("start ")) {
      String val = cmd.substring(6);
      maxTime = val.toInt();
      timeLeft = maxTime;
      reactorState = "Desmineralización running"; // ejemplo inicial
      Serial.print("Operación iniciada, tiempo: ");
      Serial.println(timeLeft);
    } else if (cmd.startsWith("state ")) {
      reactorState = cmd.substring(6);
      Serial.print("Estado actualizado: ");
      Serial.println(reactorState);
    } else if (cmd.startsWith("tempset ")) {
      String val = cmd.substring(8);
      tempSet = val.toFloat();
      Serial.print("Temperatura seteada actualizada: ");
      Serial.println(tempSet);
    } else if (cmd == "reset") {
      reactorState = "inactivo";
      agitationSpeed = 0;
      timeLeft = 0;
      Serial.println("Reactor reseteado a 'inactivo'");
    } else {
      Serial.println("Comando no reconocido.");
    }
  }

  // Si estamos en estado running, decrementar timeLeft cada segundo
  static unsigned long lastDecrement = 0;
  if (reactorState.indexOf("running") != -1 && timeLeft > 0) {
    if (millis() - lastDecrement >= 1000) {
      lastDecrement = millis();
      timeLeft--;
      if (timeLeft <= 0) {
        reactorState = "inactivo";
        Serial.println("Operación finalizada");
      }
    }
  }

  // Simulación de temperatura con oscilación
  float angle = (millis() / 1000.0) * (PI / 10);
  float temp = baseTemp + amplitudeTemp * sin(angle);

  // Publicar datos cada 1 segundo
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish > 1000) {
    lastPublish = millis();
    char payload[256];
    snprintf(payload, sizeof(payload),
      "{\"device_name\":\"reactor\",\"temp\":%.2f,\"temp_set\":%.2f,\"speed\":%.2f,\"time_left\":%d,\"max_time\":%d,\"state\":\"%s\"}",
      temp, tempSet, agitationSpeed, timeLeft, maxTime, reactorState.c_str());
    client.publish("lab/devices/reactor/data", payload);
    Serial.print("Publicado: ");
    Serial.println(payload);
  }
}
