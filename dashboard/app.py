from flask import Flask, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db():
    # Abre la base de datos; asegúrate de que la ruta sea la misma en todos los servicios (volumen compartido)
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
      - "estacion": dashboard con gráficas de temperatura, humedad y presión.
      - "microdos": panel de estado que muestra el estado, flujo seteado y tiempo restante.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=?", (device_name,))
    device = cursor.fetchone()
    if not device:
        conn.close()
        return "Dispositivo no encontrado", 404
    
    if device["device_type"] == "estacion":
        # Cargar las últimas 30 mediciones de la estación
        cursor.execute("SELECT * FROM measurements_estacion ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()

        # Preparar arrays para Chart.js: invertir el orden para mostrar el registro más antiguo primero
        timestamps = []
        temps = []
        hums = []
        press = []

        for r in reversed(rows):
            timestamps.append(r["timestamp"])
            temps.append(r["temp"])
            hums.append(r["hum"])
            press.append(r["pres"])

        return render_template(
            "device_estacion.html",
            device=device,
            timestamps=timestamps,
            temps=temps,
            hums=hums,
            press=press
        )
    
    elif device["device_type"] == "microdos":
        # Cargar la última medición del microdosificador
        cursor.execute("SELECT * FROM measurements_microdos ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        return render_template("device_microdos.html", device=device, row=last_row)
    
    else:
        conn.close()
        return f"Sin plantilla para el tipo: {device['device_type']}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
