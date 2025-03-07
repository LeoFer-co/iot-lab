#include <WiFi.h>
#include <PubSubClient.h>
#include <math.h>

// Configuración Wi-Fi y broker
const char* ssid = "Casa_leo";
const char* password = "Odranoel";
const char* mqtt_server = "192.168.100.10";

// Parámetros del dispositivo UVale
float distance = 0.0;          // Distancia en cm
int maxTime = 60;              // Tiempo total de operación (seg)
int timeLeft = 60;             // Tiempo restante (seg)
String door_state = "cerrado"; // "abierto" o "cerrado"
String uv_state = "apagado";   // "encendido" o "apagado"
float hum = 50.0;              // Humedad en %
float temp = 25.0;             // Temperatura en °C
String status = "idle";        // Estado ("idle", "running", "finalizado", etc.)

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  // Este dispositivo no procesa mensajes entrantes
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_UVale")) {
      // Conectado
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);
  
  // Conectar a Wi-Fi
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado. IP:");
  Serial.println(WiFi.localIP());
  
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  
  Serial.println("UVale ESP Inicializado");
  Serial.println("Comandos disponibles:");
  Serial.println("  distance X    -> establece distancia en cm");
  Serial.println("  start T       -> inicia operación con T segundos (time_left = T, status -> running)");
  Serial.println("  door <estado> -> establece estado de puerta ('abierto' o 'cerrado')");
  Serial.println("  uv <estado>   -> establece estado de luz UV ('encendido' o 'apagado')");
  Serial.println("  hum X         -> establece humedad (%)");
  Serial.println("  temp X        -> establece temperatura (°C)");
  Serial.println("  state <texto> -> establece estado (ej: running, idle, finalizado)");
  Serial.println("  reset         -> reinicia a valores por defecto");
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Procesar comandos desde Monitor Serie
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("distance ")) {
      distance = cmd.substring(9).toFloat();
      Serial.print("Distancia establecida: ");
      Serial.println(distance);
    }
    else if (cmd.startsWith("start ")) {
      maxTime = cmd.substring(6).toInt();
      if (maxTime < 0) maxTime = 60;
      timeLeft = maxTime;
      status = "running";
      Serial.print("Operación iniciada, max_time: ");
      Serial.println(maxTime);
    }
    else if (cmd.startsWith("door ")) {
      door_state = cmd.substring(5);
      Serial.print("Estado de puerta: ");
      Serial.println(door_state);
    }
    else if (cmd.startsWith("uv ")) {
      uv_state = cmd.substring(3);
      Serial.print("Estado de luz UV: ");
      Serial.println(uv_state);
    }
    else if (cmd.startsWith("hum ")) {
      hum = cmd.substring(4).toFloat();
      Serial.print("Humedad establecida: ");
      Serial.println(hum);
    }
    else if (cmd.startsWith("temp ")) {
      temp = cmd.substring(5).toFloat();
      Serial.print("Temperatura establecida: ");
      Serial.println(temp);
    }
    else if (cmd.startsWith("state ")) {
      status = cmd.substring(6);
      Serial.print("Estado actualizado: ");
      Serial.println(status);
    }
    else if (cmd == "reset") {
      status = "idle";
      distance = 0.0;
      timeLeft = 0;
      maxTime = 60;
      door_state = "cerrado";
      uv_state = "apagado";
      hum = 50.0;
      temp = 25.0;
      Serial.println("Reset a valores por defecto");
    }
    else {
      Serial.println("Comando no reconocido.");
    }
  }
  
  // Simulación: si el estado es running, decrementar timeLeft cada segundo
  static unsigned long lastDecrement = 0;
  if (status == "running") {
    if (millis() - lastDecrement >= 1000) {
      lastDecrement = millis();
      if (timeLeft > 0) {
        timeLeft--;
        if (timeLeft <= 0) {
          status = "finalizado";
          Serial.println("Operación finalizada -> 'finalizado'");
        }
      }
    }
  }
  
  // Publicar datos cada 5 segundos
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish >= 5000) {
    lastPublish = millis();
    publishData();
  }
}

void publishData() {
  // Simular la variación lenta de temp y hum usando una función seno
  float angle = (millis() / 1000.0) * (PI / 100); // Avance lento (ciclo completo ~200 seg)
  temp = 25.0 + 5.0 * sin(angle);
  hum = 50.0 + 10.0 * sin(angle + 1);

  char payload[256];
  snprintf(payload, sizeof(payload),
    "{\"device_name\":\"uvale\",\"distance\":%.2f,\"time_left\":%d,\"max_time\":%d,\"door_state\":\"%s\",\"uv_state\":\"%s\",\"hum\":%.2f,\"temp\":%.2f,\"status\":\"%s\"}",
    distance, timeLeft, maxTime, door_state.c_str(), uv_state.c_str(), hum, temp, status.c_str()
  );
  client.publish("lab/devices/uvale/data", payload);
  Serial.print("Publicado: ");
  Serial.println(payload);
}
