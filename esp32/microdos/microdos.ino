#include <WiFi.h>
#include <PubSubClient.h>

// Credenciales Wi-Fi
const char* ssid = "Casa_leo";
const char* password = "Odranoel";

// Broker MQTT (IP o nombre del contenedor)
const char* mqtt_server = "192.168.100.10";

// Subtopic = "microdos", device_name = "microdos"
WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  // No usamos callback para recibir mensajes
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_Microdos")) {
      // Conectado
    } else {
      delay(5000);
    }
  }
}

// Variables globales para Microdós
String statusStr = "idle"; // "idle", "seteando", "seteado", "running", "finished"
float flowSet = 10.0;      // ml/min
int timeLeft = 0;          // seg

bool settingFlow = false;
unsigned long settingFlowStartTime = 0;
unsigned long lastPublish = 0;

// Lógica de simulación adicional
void setup() {
  Serial.begin(115200);
  delay(100);

  // Conexión Wi-Fi
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

  Serial.println("Microdos inicializado.");
  Serial.println("Comandos disponibles via Monitor Serie:");
  Serial.println("  flow X   -> setea el flujo a X ml/min (simula 'seteando' -> 'seteado')");
  Serial.println("  start T  -> inicia con T seg (estado 'running')");
  Serial.println("  reset    -> vuelve a 'idle', flowSet=10, timeLeft=0");
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  handleSerialCommands();

  // "seteando" -> "seteado" tras 1 seg
  if (statusStr == "seteando" && settingFlow) {
    if (millis() - settingFlowStartTime > 1000) {
      statusStr = "seteado";
      settingFlow = false;
      Serial.println("Estado pasa a 'seteado'");
    }
  }

  // "running" -> decrementar timeLeft
  static unsigned long lastDecrement = 0;
  if (statusStr == "running") {
    if (millis() - lastDecrement >= 1000) {
      lastDecrement = millis();
      if (timeLeft > 0) {
        timeLeft--;
        if (timeLeft <= 0) {
          statusStr = "finished";
          Serial.println("Proceso terminado -> 'finished'");
        }
      }
    }
  }

  // Publicar cada 1 seg
  if (millis() - lastPublish > 1000) {
    lastPublish = millis();
    publishData();
  }
}

void handleSerialCommands() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("flow ")) {
      String valStr = cmd.substring(5);
      float newFlow = valStr.toFloat();
      if (newFlow <= 0) {
        Serial.println("Valor de flujo inválido.");
        return;
      }
      statusStr = "seteando";
      settingFlow = true;
      settingFlowStartTime = millis();
      flowSet = newFlow;
      Serial.println("Estado -> 'seteando' (1 seg)...");
    }
    else if (cmd.startsWith("start ")) {
      String valStr = cmd.substring(6);
      int t = valStr.toInt();
      if (t <= 0) {
        Serial.println("Tiempo inválido.");
        return;
      }
      timeLeft = t;
      statusStr = "running";
      Serial.println("Estado -> 'running', timeLeft=" + String(t));
    }
    else if (cmd == "reset") {
      statusStr = "idle";
      flowSet = 10.0;
      timeLeft = 0;
      settingFlow = false;
      Serial.println("Reseteado -> 'idle'");
    }
    else {
      Serial.println("Comando no reconocido. Ej: flow 15, start 30, reset");
    }
  }
}

void publishData() {
  char payload[128];
  snprintf(payload, sizeof(payload),
    "{\"device_name\":\"microdos\",\"status\":\"%s\",\"flow_set\":%.1f,\"time_left\":%d}",
    statusStr.c_str(), flowSet, timeLeft);

  client.publish("lab/devices/microdos/data", payload);
  Serial.println(String("Publicado: ") + payload);
}
