from flask import Flask, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

OFFLINE_THRESHOLD = 30  # segundos para considerar un dispositivo "Desconectado"

def get_db():
    conn = sqlite3.connect("data/data.db")  # Ajusta la ruta si es distinto
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    """
    Muestra una página con todos los dispositivos de la tabla 'devices'.
    Si last_seen > 30s, se marca como 'Desconectado'.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    rows = cursor.fetchall()
    conn.close()

    now = datetime.now()
    devices_data = []
    for dev in rows:
        # dev es un Row, lo convertimos a dict
        dev_dict = dict(dev)
        try:
            last_seen_str = dev["last_seen"]  # "YYYY-MM-DD HH:MM:SS"
            last_seen_dt = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
            diff = (now - last_seen_dt).total_seconds()
            if diff > OFFLINE_THRESHOLD:
                dev_dict["status_final"] = "Desconectado"
            else:
                dev_dict["status_final"] = dev["last_status"]  # "publicando", "running", etc.
        except:
            dev_dict["status_final"] = "Desconocido"
        
        devices_data.append(dev_dict)
    
    return render_template("home.html", devices_data=devices_data)

@app.route("/device/<device_name>")
def device_detail(device_name):
    """
    Si el dispositivo está offline, muestra error.
    Si es 'estacion', muestra datos en Chart.js.
    Si es 'microdos', muestra panel de estado.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=?", (device_name,))
    device = cursor.fetchone()
    if not device:
        conn.close()
        return "Dispositivo no encontrado", 404
    
    # Detectar si está desconectado
    try:
        last_seen_dt = datetime.strptime(device["last_seen"], "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - last_seen_dt).total_seconds()
        if diff > OFFLINE_THRESHOLD:
            conn.close()
            return "Dispositivo desconectado", 403
    except:
        conn.close()
        return "Error al determinar estado del dispositivo", 500
    
    # Lógica según tipo
    if device["device_type"] == "estacion":
        # Cargar 30 mediciones
        cursor.execute("SELECT * FROM measurements_estacion ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()

        # Invertir y separar arrays
        timestamps, temps, hums, press = [], [], [], []
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
