import paho.mqtt.client as mqtt
import sqlite3
import json

# Conectar (o crear) la base de datos en la carpeta data (asegúrate de que esté montada)
conn = sqlite3.connect('data/data.db', check_same_thread=False)
cursor = conn.cursor()

# Crear la tabla measurements con 6 columnas
cursor.execute('''
    CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        temp REAL,
        hum REAL,
        pres REAL,
        light REAL,
        sound REAL,
        voltage REAL
    )
''')
conn.commit()

def on_connect(client, userdata, flags, rc):
    print("Conectado con resultado: " + str(rc))
    # Suscribirse al tópico donde el ESP32 publica la data en JSON
    client.subscribe("lab/equipo1/data")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print("Datos recibidos:", data)
        cursor.execute('''
            INSERT INTO measurements (temp, hum, pres, light, sound, voltage)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data.get("temp"), data.get("hum"), data.get("pres"), data.get("light"), data.get("sound"), data.get("voltage")))
        conn.commit()
    except Exception as e:
        print("Error al procesar el mensaje:", e)

broker = "broker"  # Usamos el nombre del servicio en Docker Compose
port = 1883

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Conectando al broker MQTT...")
client.connect(broker, port, 60)
client.loop_forever()
