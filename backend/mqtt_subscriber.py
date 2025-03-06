import paho.mqtt.client as mqtt

# Función callback que se ejecuta al conectarse al broker
def on_connect(client, userdata, flags, rc):
    print("Conectado con resultado: " + str(rc))
    # Nos suscribimos al tópico que publica el ESP32
    client.subscribe("lab/equipo1/temperatura")
    
    
# Función callback que se ejecuta cuando se recibe un mensaje
def on_message(client, userdata, msg):
    print(f"Mensaje recibido en {msg.topic}: {msg.payload.decode()}")

broker = "localhost"  # Asumiendo que Mosquitto corre en el mismo contenedor o en el mismo host
port = 1883

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Conectando al broker MQTT...")

client.connect(broker, port, 60)

# Permanece en un bucle infinito para procesar mensajes
 
client.loop_forever()
