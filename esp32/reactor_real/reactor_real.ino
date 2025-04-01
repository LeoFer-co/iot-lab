#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <SoftwareSerial.h>
#include <math.h>

// ---------------------- Variables globales para re-publicación ----------------------
String lastPayload = "";
unsigned long lastDataReceivedTime = 0;
unsigned long lastRepublishTime = 0;

// ---------------------- Configuración de WiFi y MQTT ----------------------
const char* ssid = "Casa_leo";
const char* password = "Odranoel";
const char* mqtt_server = "192.168.100.10";

// ---------------------- Parámetros del Reactor Quitosano ----------------------
float baseTemp = 25.0;          // Temperatura base
float amplitudeTemp = 5.0;      // Oscilación ±5°C (según el código original)
float agitationSpeed = 0;       // Velocidad de agitación (0 a 1000 rpm)
int maxTime = 60;               // Tiempo total de operación (seg)
int timeLeft = 0;               // Tiempo restante (seg)
String reactorState = "inactivo"; // Estado actual (inicialmente "inactivo")

// Temperatura seteada (inicialmente igual a baseTemp)
float tempSet = baseTemp;

WiFiClient espClient;
PubSubClient client(espClient);

// ---------------------- SoftwareSerial para recepción de datos ----------------------
// Se utilizarán los pines numéricos 14 y 12, que corresponden a D5 (RX) y D6 (TX) en el ESP8266.
SoftwareSerial iotSerial(14, 12);  // RX en GPIO14 (D5), TX en GPIO12 (D6)

// ---------------------- Función Helper: Formatear tiempo ----------------------
String formatTime(int seconds) {
  int hh = seconds / 3600;
  int mm = (seconds % 3600) / 60;
  int ss = seconds % 60;
  char buf[9];
  sprintf(buf, "%02d:%02d:%02d", hh, mm, ss);
  return String(buf);
}

// ---------------------- Función MQTT callback ----------------------
void callback(char* topic, byte* payload, unsigned int length) {
  // Este dispositivo no recibe mensajes, solo publica.
}

// ---------------------- Función para reconectar a MQTT ----------------------
void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP_Reactor")) {
      // Conectado, no es necesario suscribir.
    } else {
      delay(5000);
    }
  }
}

// ---------------------- Setup ----------------------
void setup() {
  Serial.begin(115200);        // Monitor Serial para depuración
  iotSerial.begin(9600);         // SoftwareSerial para recibir datos del Arduino
  
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
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

// ---------------------- Loop ----------------------
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Procesar comandos desde el Monitor Serial (una línea por ciclo)
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
      reactorState = "Desmineralización running";
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
  
  // Si estamos en estado "running", decrementar timeLeft cada segundo
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
  
  // Simulación de temperatura con oscilación (opcional para debug)
  float angle = (millis() / 1000.0) * (PI / 10);
  float temp = baseTemp + amplitudeTemp * sin(angle);
  
  // ---------------------- Recepción de datos desde Arduino vía SoftwareSerial ----------------------
  if (iotSerial.available()) {
    String dataLine = iotSerial.readStringUntil('\n');
    dataLine.trim();
    if (dataLine.length() > 0) {
      Serial.print("Data recibida: ");
      Serial.println(dataLine);
      
      // Se espera una cadena de 24 campos separados por comas
      const int numFields = 24;
      float fields[numFields];
      int fieldIndex = 0;
      int startIndex = 0;
      int commaIndex = dataLine.indexOf(',');
      while (commaIndex != -1 && fieldIndex < numFields) {
        String part = dataLine.substring(startIndex, commaIndex);
        fields[fieldIndex] = part.toFloat();
        fieldIndex++;
        startIndex = commaIndex + 1;
        commaIndex = dataLine.indexOf(',', startIndex);
      }
      if (fieldIndex < numFields) {
        fields[fieldIndex] = dataLine.substring(startIndex).toFloat();
        fieldIndex++;
      }
      
      // Verificar que se hayan recibido al menos los primeros 6 campos necesarios
      if (fieldIndex >= 6) {
        // Extraer datos requeridos:
        // Campo 0: indicador (1,2 o 3)
        // Campo 1: indicador_estado (0,1,2,3,4)
        // Campo 3: tiempo en milisegundos (convertir a segundos)
        // Campo 4: velocidad actual (speed)
        // Campo 5: temperatura actual (temp)
        int indicadorVal = (int) fields[0];
        int indicadorEstadoVal = (int) fields[1];
        int rawTimeMs = (int) fields[3];
        int timeSec = rawTimeMs / 1000;  // convertir a segundos
        float receivedSpeed = fields[4];
        float receivedTemp = fields[5];
        
        // Seleccionar el valor de temp_ref según indicador:
        // Para desmineralización: temp_ref[0] (campo 7)
        // Para desproteinizacion: temp_ref[1] (campo 10)
        // Para desacetilación: temp_ref[2] (campo 13)
        float receivedTempSet;
        if (indicadorVal == 1) {
          receivedTempSet = fields[7];
        } else if (indicadorVal == 2) {
          receivedTempSet = fields[10];
        } else if (indicadorVal == 3) {
          receivedTempSet = fields[13];
        } else {
          receivedTempSet = tempSet;
        }
        
        // Mapeo para indicador
        String indicadorStr;
        switch (indicadorVal) {
          case 1: indicadorStr = "desmineralizacion"; break;
          case 2: indicadorStr = "desproteinizacion"; break;
          case 3: indicadorStr = "desacetilacion"; break;
          default: indicadorStr = "desconocido"; break;
        }
        
        // Mapeo para indicador_estado
        String indicadorEstadoStr;
        switch (indicadorEstadoVal) {
          case 0: indicadorEstadoStr = "inactivo"; break;
          case 1: indicadorEstadoStr = "reaccion"; break;
          case 2: indicadorEstadoStr = "expulsion"; break;
          case 3: indicadorEstadoStr = "suministro"; break;
          case 4: indicadorEstadoStr = "lavando"; break;
          default: indicadorEstadoStr = "desconocido"; break;
        }
        
        // Determinar el estado ("state") para el dashboard según:
        // - Si indicador_estado == 1:
        //      indicador 1 → "dm running"
        //      indicador 2 → "dp running"
        //      indicador 3 → "da running"
        // - Si indicador_estado == 2 → "expulsion"
        // - Si indicador_estado == 3 → "suministro"
        // - Si indicador_estado == 4 → "lavando"
        // - En otro caso se usa reactorState.
        String stateStr;
        if (indicadorEstadoVal == 1) {
          if (indicadorVal == 1) {
            stateStr = "dm running";
          } else if (indicadorVal == 2) {
            stateStr = "dp running";
          } else if (indicadorVal == 3) {
            stateStr = "da running";
          } else {
            stateStr = reactorState;
          }
        } else if (indicadorEstadoVal == 2) {
          stateStr = "expulsion";
        } else if (indicadorEstadoVal == 3) {
          stateStr = "suministro";
        } else if (indicadorEstadoVal == 4) {
          stateStr = "lavando";
        } else {
          stateStr = reactorState;
        }
        
        // Formatear el tiempo a hh:mm:ss
        String formattedTime = formatTime(timeSec);
        
        // Actualizar la variable global timeLeft (opcional)
        timeLeft = timeSec;
        
        // Construir el payload JSON con las claves exactas
        char payload[256];
        snprintf(payload, sizeof(payload),
          "{\"device_name\":\"reactor\",\"indicador\":\"%s\",\"indicador_estado\":\"%s\",\"temp\":%.2f,\"temp_set\":%.2f,\"speed\":%.2f,\"time_left\":\"%s\",\"max_time\":%d,\"state\":\"%s\"}",
          indicadorStr.c_str(), indicadorEstadoStr.c_str(), receivedTemp, receivedTempSet, receivedSpeed, formattedTime.c_str(), maxTime, stateStr.c_str());
          
        client.publish("lab/devices/reactor/data", payload);
        Serial.print("Publicado: ");
        Serial.println(payload);
        
        // Actualizar la última data recibida y el último payload publicado
        lastPayload = String(payload);
        lastDataReceivedTime = millis();
        lastRepublishTime = millis();
      }
    }
  }
  
  // Si han pasado 3 segundos sin recibir data nueva, re-publicar el último payload
  if (lastPayload.length() > 0 && (millis() - lastDataReceivedTime >= 3000) && (millis() - lastRepublishTime >= 3000)) {
    client.publish("lab/devices/reactor/data", lastPayload.c_str());
    Serial.print("Re-publicado: ");
    Serial.println(lastPayload);
    lastRepublishTime = millis();
  }
}
