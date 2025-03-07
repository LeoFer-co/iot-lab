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

# Intentamos agregar la columna "position" si no existe
try:
    cursor.execute("ALTER TABLE devices ADD COLUMN position INTEGER DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError as e:
    # Ignoramos el error si la columna ya existe
    if "duplicate column name" not in str(e).lower():
        print("Error al agregar la columna 'position':", e)

# Medidas para Estación Meteorológica
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_estacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temp REAL,
    hum REAL,
    pres REAL
  )
''')

# Medidas para Microdós
cursor.execute('''
  CREATE TABLE IF NOT EXISTS measurements_microdos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    flow_set REAL,
    time_left INTEGER
  )
''')

# Medidas para Reactor Quitosano
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

# Medidas para LC_Shaker
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

# Medidas para LECOB 50
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

# Medidas para UV ale
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
        subtopic = msg.topic.split("/")[2]  # 'estacion', 'microdos', 'reactor', etc.
        device_name = data.get("device_name", subtopic)
        
        if subtopic == "estacion":
            temp = data.get("temp", 0)
            hum  = data.get("hum", 0)
            pres = data.get("pres", 0)
            cursor.execute('''
              INSERT INTO measurements_estacion (temp, hum, pres)
              VALUES (?, ?, ?)
            ''', (temp, hum, pres))
            conn.commit()
            update_device(device_name, "estacion", "publicando")
        
        elif subtopic == "microdos":
            status    = data.get("status", "idle")
            flow_set  = data.get("flow_set", 0)
            time_left = data.get("time_left", 0)
            cursor.execute('''
              INSERT INTO measurements_microdos (status, flow_set, time_left)
              VALUES (?, ?, ?)
            ''', (status, flow_set, time_left))
            conn.commit()
            update_device(device_name, "microdos", status)
        
        elif subtopic == "reactor":
            temp = data.get("temp", 0)
            speed = data.get("speed", 0)
            time_left = data.get("time_left", 0)
            max_time = data.get("max_time", 60)
            state = data.get("state", "inactivo")
            cursor.execute('''
              INSERT INTO measurements_reactor (temp, speed, time_left, max_time, state)
              VALUES (?, ?, ?, ?, ?)
            ''', (temp, speed, time_left, max_time, state))
            conn.commit()
            update_device(device_name, "reactor", state)
        
        elif subtopic == "lc_shaker":
            speed = data.get("speed", 0)
            amp_mayor = data.get("amp_mayor", 0)
            amp_menor = data.get("amp_menor", 0)
            oscilaciones = data.get("oscilaciones", 0)
            time_left = data.get("time_left", 0)
            max_time = data.get("max_time", 60)
            state = data.get("state", "idle")
            cursor.execute('''
              INSERT INTO measurements_lc_shaker (speed, amp_mayor, amp_menor, oscilaciones, time_left, max_time, state)
              VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (speed, amp_mayor, amp_menor, oscilaciones, time_left, max_time, state))
            conn.commit()
            update_device(device_name, "lc_shaker", state)
        
        elif subtopic == "lecob50":
            on_time = data.get("on_time", 0)
            off_time = data.get("off_time", 0)
            time_left = data.get("time_left", 0)
            max_time = data.get("max_time", 60)
            status = data.get("status", "idle")
            cursor.execute('''
              INSERT INTO measurements_lecob50 (on_time, off_time, time_left, max_time, status)
              VALUES (?, ?, ?, ?, ?)
            ''', (on_time, off_time, time_left, max_time, status))
            conn.commit()
            update_device(device_name, "lecob50", status)
        
        elif subtopic == "uvale":
            distance = data.get("distance", 0)
            time_left = data.get("time_left", 0)
            max_time = data.get("max_time", 60)
            door_state = data.get("door_state", "cerrado")
            uv_state = data.get("uv_state", "apagado")
            hum = data.get("hum", 0)
            temp = data.get("temp", 0)
            status = data.get("status", "idle")
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

broker = "broker"  # En Docker Compose, usamos el nombre del servicio
port = 1883

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Conectando al broker MQTT...")
client.connect(broker, port, 60)
client.loop_forever()
