from flask import Flask, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("data/data.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    """
    Muestra una página con todos los dispositivos registrados en la tabla 'devices'.
    Cada recuadro tiene: nombre, tipo y estado actual.
    Al pulsar, redirige a /device/<device_name>.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    devices = cursor.fetchall()
    conn.close()
    return render_template("home.html", devices=devices)

@app.route("/device/<device_name>")
def device_detail(device_name):
    """
    Dependiendo del tipo de dispositivo, muestra una página distinta:
      - estacion: gráficas con temp, hum, pres
      - microdos: estado, flow_set, time_left en tiempo real
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=?", (device_name,))
    device = cursor.fetchone()
    if not device:
        return "Dispositivo no encontrado", 404
    
    if device["device_type"] == "estacion":
        # Cargar últimas mediciones de measurements_estacion
        cursor.execute("SELECT * FROM measurements_estacion ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        # Pasar datos a la plantilla (gráficas Chart.js, etc.)
        return render_template("device_estacion.html", device=device, rows=rows)
    
    elif device["device_type"] == "microdos":
        # Cargar últimas mediciones de measurements_microdos
        cursor.execute("SELECT * FROM measurements_microdos ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        # Pasar info a una plantilla distinta
        return render_template("device_microdos.html", device=device, row=last_row)
    
    else:
        conn.close()
        return f"Sin plantilla para el tipo: {device['device_type']}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
