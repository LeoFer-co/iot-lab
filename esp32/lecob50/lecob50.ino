#include <WiFi.h>
#include <PubSubClient.h>

// Ajusta según tu red y broker
const char* ssid = "Casa_leo";
const char* password = "Odranoel";
const char* mqtt_server = "192.168.100.10";

// Parámetros de LECOB 50
// --------------------------------
// on_time y off_time en segundos, time_left, max_time, status
int onTime = 0;       // tiempo encendido (seg)
int offTime = 0;      // tiempo apagado (seg)
int timeLeft = 0;     // tiempo restante
int maxTime = 60;     // tiempo total de la operación
String lecobStatus = "idle";  // "idle", "running iluminando", "running no iluminando", "finalizado"

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  // No recibimos mensajes en este ejemplo
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_LECOB50")) {
      // Conectado
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);

  // Conexión Wi-Fi
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado. IP: ");
  Serial.println(WiFi.localIP());

  // Configurar el broker MQTT
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  Serial.println("LECOB 50 inicializado. Comandos disponibles:");
  Serial.println("  on_time X    -> establece tiempo encendido (seg)");
  Serial.println("  off_time X   -> establece tiempo apagado (seg)");
  Serial.println("  start T      -> iniciar ciclo con tiempo T (seg)");
  Serial.println("  state <texto> -> estado (idle, running iluminando, running no iluminando, finalizado)");
  Serial.println("  reset        -> reinicia a 'idle'");
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Procesar comandos desde el Monitor Serie
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.startsWith("on_time ")) {
      onTime = cmd.substring(8).toInt();
      Serial.print("Tiempo encendido: ");
      Serial.println(onTime);
    }
    else if (cmd.startsWith("off_time ")) {
      offTime = cmd.substring(9).toInt();
      Serial.print("Tiempo apagado: ");
      Serial.println(offTime);
    }
    else if (cmd.startsWith("start ")) {
      maxTime = cmd.substring(6).toInt();
      if (maxTime < 0) maxTime = 0;
      timeLeft = maxTime;
      // Suponemos que inicia "running iluminando"
      lecobStatus = "running iluminando";
      Serial.print("Ciclo iniciado, max_time: ");
      Serial.println(maxTime);
    }
    else if (cmd.startsWith("state ")) {
      lecobStatus = cmd.substring(6);
      Serial.print("Estado actualizado: ");
      Serial.println(lecobStatus);
    }
    else if (cmd == "reset") {
      lecobStatus = "idle";
      onTime = 0;
      offTime = 0;
      timeLeft = 0;
      maxTime = 60;
      Serial.println("LECOB 50 reseteado a 'idle'");
    }
    else {
      Serial.println("Comando no reconocido. Ejemplo: on_time 10, off_time 5, start 30, state running iluminando, reset");
    }
  }

  // Simulación de "running" -> decrementar timeLeft
  // Podrías simular un ciclo en el que se enciende y apaga la luz
  // En este ejemplo, solo decrece el timeLeft en "running" si su status lo indica
  if (lecobStatus.startsWith("running")) {
    static unsigned long lastDecrement = 0;
    if (millis() - lastDecrement >= 1000) {
      lastDecrement = millis();
      if (timeLeft > 0) {
        timeLeft--;
        // Podrías alternar "running iluminando" y "running no iluminando"
        // según onTime/offTime, etc.
        if (timeLeft <= 0) {
          lecobStatus = "finalizado";
          Serial.println("Ciclo finalizado -> 'finalizado'");
        }
      }
    }
  }

  // Publicar cada 5 segundos
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish > 5000) {
    lastPublish = millis();
    publishData();
  }
}

void publishData() {
  // Empaquetar en JSON
  // device_name: "lecob50"
  // on_time, off_time, time_left, max_time, status
  char payload[256];
  snprintf(payload, sizeof(payload),
    "{\"device_name\":\"lecob50\",\"on_time\":%d,\"off_time\":%d,\"time_left\":%d,\"max_time\":%d,\"status\":\"%s\"}",
    onTime, offTime, timeLeft, maxTime, lecobStatus.c_str()
  );

  client.publish("lab/devices/lecob50/data", payload);
  Serial.print("Publicado: ");
  Serial.println(payload);
}
