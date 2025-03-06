import paho.mqtt.client as mqtt
import sqlite3
import json

DB_PATH = "data/data.db"

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Crear tablas si no existen
cursor.execute('''
  CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name TEXT UNIQUE,
    device_type TEXT,
    last_status TEXT,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
  )
''')
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_estacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temp REAL,
    hum REAL,
    pres REAL
  )
''')
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_microdos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    flow_set REAL,
    time_left INTEGER
  )
''')
conn.commit()

def update_device(device_name, device_type, last_status):
    cursor.execute('''
      INSERT INTO devices (device_name, device_type, last_status)
      VALUES (?, ?, ?)
      ON CONFLICT(device_name) DO UPDATE SET
        device_type=excluded.device_type,
        last_status=excluded.last_status,
        last_seen=CURRENT_TIMESTAMP
    ''', (device_name, device_type, last_status))
    conn.commit()

def on_connect(client, userdata, flags, rc):
    print("Conectado al broker MQTT:", rc)
    client.subscribe("lab/devices/+/data")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        subtopic = msg.topic.split("/")[2]  # 'estacion' o 'microdos'
        device_name = data.get("device_name", subtopic)
        
        if subtopic == "estacion":
            temp = data.get("temp")
            hum  = data.get("hum")
            pres = data.get("pres")
            cursor.execute('''
              INSERT INTO measurements_estacion (temp, hum, pres)
              VALUES (?, ?, ?)
            ''', (temp, hum, pres))
            conn.commit()
            update_device(device_name, "estacion", "publicando")
        
        elif subtopic == "microdos":
            status    = data.get("status")
            flow_set  = data.get("flow_set")
            time_left = data.get("time_left")
            cursor.execute('''
              INSERT INTO measurements_microdos (status, flow_set, time_left)
              VALUES (?, ?, ?)
            ''', (status, flow_set, time_left))
            conn.commit()
            update_device(device_name, "microdos", status)
        
        else:
            print("Dispositivo desconocido:", subtopic)
            
    except Exception as e:
        print("Error procesando mensaje:", e)

broker = "broker"  # En Docker Compose, usamos el nombre del servicio
port = 1883

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Conectando al broker MQTT...")
client.connect(broker, port, 60)
client.loop_forever()
