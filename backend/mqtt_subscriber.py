import paho.mqtt.client as mqtt
import sqlite3
import json

DB_PATH = "data/data.db"

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Crear tablas si no existen

# Tabla de dispositivos
cursor.execute('''
  CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name TEXT UNIQUE,
    device_type TEXT,
    last_status TEXT,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
  )
''')

# Para Estación Meteorológica
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_estacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temp REAL,
    hum REAL,
    pres REAL
  )
''')

# Para Microdós
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_microdos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    flow_set REAL,
    time_left INTEGER
  )
''')

# Para Reactor Quitosano
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_reactor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temp REAL,
    speed REAL,
    time_left INTEGER,
    max_time INTEGER,
    state TEXT
  )
''')

# Para LC_Shaker
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_lc_shaker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    speed REAL,
    amp_mayor REAL,
    amp_menor REAL,
    oscilaciones INTEGER,
    time_left INTEGER,
    max_time INTEGER,
    state TEXT
  )
''')

# Para LECOB 50
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_lecob50 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    on_time INTEGER,
    off_time INTEGER,
    time_left INTEGER,
    max_time INTEGER,
    status TEXT
  )
''')

# Para UV ale
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_uvale (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    distance REAL,
    time_left INTEGER,
    max_time INTEGER,
    door_state TEXT,
    uv_state TEXT,
    hum REAL,
    temp REAL,
    status TEXT
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
        subtopic = msg.topic.split("/")[2]  # tipo del dispositivo
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
        
        elif subtopic == "reactor":
            temp = data.get("temp")
            speed = data.get("speed")
            time_left = data.get("time_left")
            max_time = data.get("max_time")
            state = data.get("state")
            cursor.execute('''
              INSERT INTO measurements_reactor (temp, speed, time_left, max_time, state)
              VALUES (?, ?, ?, ?, ?)
            ''', (temp, speed, time_left, max_time, state))
            conn.commit()
            update_device(device_name, "reactor", state)
        
        elif subtopic == "lc_shaker":
            speed = data.get("speed")
            amp_mayor = data.get("amp_mayor")
            amp_menor = data.get("amp_menor")
            oscilaciones = data.get("oscilaciones")
            time_left = data.get("time_left")
            max_time = data.get("max_time")
            state = data.get("state")
            cursor.execute('''
              INSERT INTO measurements_lc_shaker (speed, amp_mayor, amp_menor, oscilaciones, time_left, max_time, state)
              VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (speed, amp_mayor, amp_menor, oscilaciones, time_left, max_time, state))
            conn.commit()
            update_device(device_name, "lc_shaker", state)
        
        elif subtopic == "lecob50":
            on_time = data.get("on_time")
            off_time = data.get("off_time")
            time_left = data.get("time_left")
            max_time = data.get("max_time")
            status = data.get("status")
            cursor.execute('''
              INSERT INTO measurements_lecob50 (on_time, off_time, time_left, max_time, status)
              VALUES (?, ?, ?, ?, ?)
            ''', (on_time, off_time, time_left, max_time, status))
            conn.commit()
            update_device(device_name, "lecob50", status)
        
        elif subtopic == "uvale":
            distance = data.get("distance")
            time_left = data.get("time_left")
            max_time = data.get("max_time")
            door_state = data.get("door_state")
            uv_state = data.get("uv_state")
            hum = data.get("hum")
            temp = data.get("temp")
            status = data.get("status")
            cursor.execute('''
              INSERT INTO measurements_uvale (distance, time_left, max_time, door_state, uv_state, hum, temp, status)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (distance, time_left, max_time, door_state, uv_state, hum, temp, status))
            conn.commit()
            update_device(device_name, "uvale", status)
        
        else:
            print("Dispositivo desconocido:", subtopic)
            
    except Exception as e:
        print("Error procesando mensaje:", e)

broker = "broker"  # Usamos el nombre del servicio en Docker Compose
port = 1883

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Conectando al broker MQTT...")
client.connect(broker, port, 60)
client.loop_forever()
