from flask import Flask, render_template, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Umbral en segundos para considerar que un dispositivo está offline.
OFFLINE_THRESHOLD = 30

def get_db():
    # Asegúrate de que esta ruta coincide con la usada en tus contenedores (volumen compartido)
    conn = sqlite3.connect("data/data.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    """
    Muestra una página con todos los dispositivos registrados en la tabla 'devices'.
    Para cada dispositivo se calcula el estado final:
      - Si el tiempo transcurrido desde 'last_seen' supera OFFLINE_THRESHOLD, se considera "Desconectado".
      - En caso contrario, se usa el 'last_status'.
    Cada recuadro muestra el nombre, tipo y estado final y, si está online, permite acceder a la página de detalle.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    devices = cursor.fetchall()
    conn.close()

    devices_data = []
    now = datetime.now()
    for dev in devices:
        try:
            dt_last = datetime.strptime(dev["last_seen"], "%Y-%m-%d %H:%M:%S")
            diff = (now - dt_last).total_seconds()
            if diff > OFFLINE_THRESHOLD:
                status = "Desconectado"
            else:
                status = dev["last_status"]
        except Exception as e:
            status = "Desconocido"
        # Convertir el Row a diccionario para que Jinja pueda acceder a las claves de forma directa
        dev_dict = dict(dev)
        dev_dict["status_final"] = status
        devices_data.append(dev_dict)

    return render_template("home.html", devices=devices_data)

@app.route("/device/<device_name>")
def device_detail(device_name):
    """
    Muestra la página de detalle de un dispositivo.  
    - Si el dispositivo está offline (no ha publicado en OFFLINE_THRESHOLD segundos), se muestra un error.
    - Para "estacion": se cargan las últimas 30 mediciones de temperatura, humedad y presión.
    - Para "microdos": se carga la última medición.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=?", (device_name,))
    device = cursor.fetchone()
    if not device:
        conn.close()
        return "Dispositivo no encontrado", 404

    # Calcular si el dispositivo está desconectado
    try:
        dt_last = datetime.strptime(device["last_seen"], "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - dt_last).total_seconds()
        if diff > OFFLINE_THRESHOLD:
            conn.close()
            return "Dispositivo desconectado", 403
    except Exception as e:
        conn.close()
        return "Error al determinar el estado del dispositivo", 500

    if device["device_type"] == "estacion":
        cursor.execute("SELECT * FROM measurements_estacion ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()

        timestamps = []
        temps = []
        hums = []
        press = []
        # Invertir para mostrar el registro más antiguo primero
        for r in reversed(rows):
            timestamps.append(r["timestamp"])
            temps.append(r["temp"])
            hums.append(r["hum"])
            press.append(r["pres"])
        return render_template("device_estacion.html",
                               device=device,
                               timestamps=timestamps,
                               temps=temps,
                               hums=hums,
                               press=press)
    elif device["device_type"] == "microdos":
        cursor.execute("SELECT * FROM measurements_microdos ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        return render_template("device_microdos.html", device=device, row=last_row)
    else:
        conn.close()
        return f"Sin plantilla para el tipo: {device['device_type']}", 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
