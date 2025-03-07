#include <WiFi.h>
#include <PubSubClient.h>

// Configura tus credenciales Wi-Fi
const char* ssid = "Casa_leo";
const char* password = "Odranoel";

// IP del broker MQTT (la IP de tu Raspberry Pi)
const char* mqtt_server = "192.168.100.10";  // Ajusta según tu red

WiFiClient espClient;
PubSubClient client(espClient);

// Función callback MQTT (no la usamos en este ejemplo)
void callback(char* topic, byte* payload, unsigned int length) {}

// Reconexión al broker
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
// --------------------------------
String statusStr = "idle";   // "idle", "seteando", "seteado", "running", "finished"
float flowSet = 10.0;        // ml/min
int timeLeft = 0;            // seg

bool settingFlow = false;    // Indica si estamos en el 1 seg de "seteando"
unsigned long settingFlowStartTime = 0;
unsigned long lastPublish = 0;
unsigned long lastStatusUpdate = 0; // para decrementar timeLeft si "running"

void setup() {
  Serial.begin(115200);
  delay(100);

  // Conexión Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  Serial.println("WiFi conectado.");

  // Configurar el broker MQTT
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  Serial.println("Microdos inicializado. Comandos disponibles:");
  Serial.println("  flow X       -> setea el flujo a X ml/min (simula 'seteando' -> 'seteado')");
  Serial.println("  start T      -> inicia el proceso con tiempo T seg (estado 'running' hasta 0 -> 'finished')");
  Serial.println("  reset        -> vuelve a 'idle', flowSet=10, timeLeft=0");
  Serial.println("Estados posibles: idle, seteando, seteado, running, finished");
}

void loop() {
  // Asegurar conexión MQTT
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Leer comandos del Monitor Serie
  handleSerialCommands();

  // Lógica de "seteando" -> "seteado" (1 segundo)
  if (statusStr == "seteando" && settingFlow) {
    if (millis() - settingFlowStartTime > 10000) {
      // Pasó 1 seg
      statusStr = "seteado";
      settingFlow = false;
      Serial.println("Estado pasa a 'seteado'");
    }
  }

  // Lógica de "running" -> decrementar timeLeft
  if (statusStr == "running") {
    // Para no decrementar cada loop, lo hacemos cada 1 seg
    static unsigned long lastDecrement = 0;
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

  // Publicar cada 5 segundos
  if (millis() - lastPublish > 5000) {
    lastPublish = millis();
    publishData();
  }
}

// ---------------------------------------------------
// Función para leer y procesar comandos del Monitor Serie
// ---------------------------------------------------
void handleSerialCommands() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // Ejemplo: "flow 15" o "start 20" o "reset"
    if (cmd.startsWith("flow ")) {
      // Extraer el valor de flujo
      String valStr = cmd.substring(5);
      float newFlow = valStr.toFloat();
      if (newFlow <= 0) {
        Serial.println("Valor de flujo inválido.");
        return;
      }
      // Simulamos "seteando" -> 1 seg -> "seteado"
      statusStr = "seteando";
      settingFlow = true;
      settingFlowStartTime = millis();
      flowSet = newFlow;
      Serial.println("Recibido comando: flow " + String(newFlow));
      Serial.println("Estado -> 'seteando' (1 seg)...");
    }
    else if (cmd.startsWith("start ")) {
      // Extraer el tiempo
      String valStr = cmd.substring(6);
      int t = valStr.toInt();
      if (t <= 0) {
        Serial.println("Tiempo inválido.");
        return;
      }
      timeLeft = t;
      statusStr = "running";
      Serial.println("Recibido comando: start " + String(t));
      Serial.println("Estado -> 'running', timeLeft=" + String(t));
    }
    else if (cmd == "reset") {
      // Resetea a idle
      statusStr = "idle";
      flowSet = 10.0;
      timeLeft = 0;
      settingFlow = false;
      Serial.println("Recibido comando: reset -> estado 'idle', flowSet=10, timeLeft=0");
    }
    else {
      Serial.println("Comando no reconocido. Ejemplos: flow 15, start 30, reset");
    }
  }
}

// ---------------------------------------------------
// Función para publicar el JSON al tópico
// ---------------------------------------------------
void publishData() {
  char payload[128];
  snprintf(payload, sizeof(payload),
    "{\"device_name\":\"microdos\",\"status\":\"%s\",\"flow_set\":%.2f,\"time_left\":%d}",
    statusStr.c_str(), flowSet, timeLeft);

  client.publish("lab/devices/microdos/data", payload);
  Serial.println(String("Publicado: ") + payload);
}
