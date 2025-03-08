#include <WiFi.h>
#include <PubSubClient.h>

// Ajusta según tu red y broker
const char* ssid = "Casa_leo";
const char* password = "Odranoel";
const char* mqtt_server = "192.168.100.10";

// Parámetros del LC_Shaker
// ------------------------
// Velocidad (0-80 rpm), amplitud mayor y menor en grados,
// oscilaciones, tiempo restante, max_time y estado actual.
float shakerSpeed = 0.0;       // rpm (0-80)
float ampMayor = 0.0;          // en grados
float ampMenor = 0.0;          // en grados
int oscilaciones = 0;
int timeLeft = 0;
int maxTime = 60;              // se setea al iniciar
String shakerState = "idle";   // "agitando", "seteando", "idle", "finalizado"

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  // No recibimos mensajes
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_LCShaker")) {
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

  Serial.println("LC_Shaker inicializado. Comandos disponibles:");
  Serial.println("  speed X       -> establece velocidad (0-80 rpm)");
  Serial.println("  ampM X        -> establece amplitud mayor (°)");
  Serial.println("  ampm X        -> establece amplitud menor (°)");
  Serial.println("  osc X         -> establece número de oscilaciones");
  Serial.println("  start T       -> inicia operación con tiempo T (seg) => 'agitando'");
  Serial.println("  state <texto> -> establece estado (ej: 'agitando', 'idle', 'finalizado')");
  Serial.println("  reset         -> resetea a 'idle' y valores por defecto");
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

    if (cmd.startsWith("speed ")) {
      String val = cmd.substring(6);
      float spd = val.toFloat();
      if (spd < 0) spd = 0;
      if (spd > 80) spd = 80;
      shakerSpeed = spd;
      Serial.print("Velocidad establecida: ");
      Serial.println(shakerSpeed);

    } else if (cmd.startsWith("ampM ")) {
      String val = cmd.substring(5);
      ampMayor = val.toFloat();
      Serial.print("Amplitud mayor establecida: ");
      Serial.println(ampMayor);

    } else if (cmd.startsWith("ampm ")) {
      String val = cmd.substring(5);
      ampMenor = val.toFloat();
      Serial.print("Amplitud menor establecida: ");
      Serial.println(ampMenor);

    } else if (cmd.startsWith("osc ")) {
      String val = cmd.substring(4);
      oscilaciones = val.toInt();
      Serial.print("Oscilaciones establecidas: ");
      Serial.println(oscilaciones);

    } else if (cmd.startsWith("start ")) {
      String val = cmd.substring(6);
      maxTime = val.toInt();
      if (maxTime < 0) maxTime = 0;
      timeLeft = maxTime;
      shakerState = "agitando";
      Serial.print("Operación iniciada, tiempo: ");
      Serial.println(timeLeft);

    } else if (cmd.startsWith("state ")) {
      shakerState = cmd.substring(6);
      Serial.print("Estado actualizado: ");
      Serial.println(shakerState);

    } else if (cmd == "reset") {
      shakerState = "idle";
      shakerSpeed = 0;
      ampMayor = 0;
      ampMenor = 0;
      oscilaciones = 0;
      timeLeft = 0;
      maxTime = 60;
      Serial.println("LC_Shaker reseteado a 'idle'");

    } else {
      Serial.println("Comando no reconocido.");
    }
  }

  // Lógica: si estado es "agitando", decrementar timeLeft
  static unsigned long lastDecrement = 0;
  if (shakerState == "agitando" && timeLeft > 0) {
    if (millis() - lastDecrement >= 1000) {
      lastDecrement = millis();
      timeLeft--;
      if (timeLeft <= 0) {
        shakerState = "finalizado";
        Serial.println("Operación finalizada -> 'finalizado'");
      }
    }
  }

  // Publicar cada 51segundos
  static unsigned long lastPublish = 0;
  if (millis() - lastPublish > 1000) {
    lastPublish = millis();
    publishData();
  }
}

void publishData() {
  // Empaquetamos en JSON
  // device_name:"lc_shaker", subtopic "lc_shaker"
  char payload[256];
  snprintf(payload, sizeof(payload),
    "{\"device_name\":\"lc_shaker\",\"speed\":%.2f,\"amp_mayor\":%.2f,\"amp_menor\":%.2f,\"oscilaciones\":%d,\"time_left\":%d,\"max_time\":%d,\"state\":\"%s\"}",
    shakerSpeed, ampMayor, ampMenor, oscilaciones, timeLeft, maxTime, shakerState.c_str()
  );

  client.publish("lab/devices/lc_shaker/data", payload);
  Serial.print("Publicado: ");
  Serial.println(payload);
}
