import paho.mqtt.client as mqtt
import sqlite3

# -------------------------
# Configuración de SQLite
# -------------------------

# Conecta (o crea) la base de datos "data.db" en el mismo directorio
conn = sqlite3.connect('data.db', check_same_thread=False)
cursor = conn.cursor()

# Crea la tabla measurements si no existe
cursor.execute('''
    CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# -------------------------
# Funciones de callbacks MQTT
# -------------------------

def on_connect(client, userdata, flags, rc):
    print("Conectado con resultado: " + str(rc))
    # Nos suscribimos al tópico que publica el ESP32
    client.subscribe("lab/equipo1/temperatura")

def on_message(client, userdata, msg):
    mensaje = msg.payload.decode()
    print(f"Mensaje recibido en {msg.topic}: {mensaje}")
    # Inserta el mensaje en la base de datos
    cursor.execute("INSERT INTO measurements (topic, message) VALUES (?, ?)", (msg.topic, mensaje))
    conn.commit()

# -------------------------
# Configuración del cliente MQTT
# -------------------------

broker = "broker"  # Usamos el nombre del servicio en Docker Compose o la IP, según tu configuración
port = 1883

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Conectando al broker MQTT...")
client.connect(broker, port, 60)

# -------------------------
# Bucle principal: procesa mensajes indefinidamente
# -------------------------

client.loop_forever()
