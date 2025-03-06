from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

OFFLINE_THRESHOLD = 10  # segundos para marcar desconexión

def get_db():
    conn = sqlite3.connect("data/data.db")  # Ajusta la ruta si difiere
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    """
    Renderiza la plantilla home.html con un contenedor vacío.
    El llenado/actualización de la lista de dispositivos
    se hace en tiempo real via JavaScript y el endpoint /devices_data.
    """
    return render_template("home.html")

@app.route("/devices_data")
def devices_data():
    """
    Devuelve en JSON la lista de dispositivos (tabla 'devices'),
    indicando si están desconectados (diff > OFFLINE_THRESHOLD) o su estado actual.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    rows = cursor.fetchall()
    conn.close()

    now = datetime.now()
    devices_list = []
    for dev in rows:
        dev_dict = dict(dev)
        try:
            last_seen_str = dev_dict["last_seen"]  # "YYYY-MM-DD HH:MM:SS"
            last_dt = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
            diff = (now - last_dt).total_seconds()
            if diff > OFFLINE_THRESHOLD:
                dev_dict["status_final"] = "Desconectado"
            else:
                dev_dict["status_final"] = dev_dict["last_status"]
        except:
            dev_dict["status_final"] = "Desconocido"
        devices_list.append(dev_dict)

    return jsonify(devices_list)

@app.route("/device/<device_name>")
def device_detail(device_name):
    """
    Página de detalle de un dispositivo.
    Si está desconectado, muestra error 403.
    Si es 'estacion', renderiza device_estacion.html (3 gráficas separadas).
    Si es 'microdos', renderiza device_microdos.html (panel de estado).
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=?", (device_name,))
    device = cursor.fetchone()
    if not device:
        conn.close()
        return "Dispositivo no encontrado", 404

    # Detectar desconexión
    try:
        last_dt = datetime.strptime(device["last_seen"], "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - last_dt).total_seconds()
        if diff > OFFLINE_THRESHOLD:
            conn.close()
            return f"El dispositivo '{device_name}' está desconectado.", 403
    except:
        conn.close()
        return "Error al determinar el estado del dispositivo", 500

    device_type = device["device_type"]

    if device_type == "estacion":
        # Cargar 30 mediciones
        cursor.execute("SELECT * FROM measurements_estacion ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()

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

    elif device_type == "microdos":
        # Última medición
        cursor.execute("SELECT * FROM measurements_microdos ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        return render_template("device_microdos.html", device=device, row=last_row)
    else:
        conn.close()
        return f"Tipo de dispositivo desconocido: {device_type}", 400

# Endpoints de tiempo real para la vista Estación y Microdós (si los usas)
@app.route("/device/<device_name>/estacion_data")
def device_estacion_data(device_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=? AND device_type='estacion'", (device_name,))
    dev = cursor.fetchone()
    if not dev:
        conn.close()
        return jsonify({"error": "No existe la estación con ese nombre"}), 404

    cursor.execute("SELECT * FROM measurements_estacion ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    conn.close()

    timestamps = []
    temps = []
    hums = []
    press = []
    for r in reversed(rows):
        timestamps.append(r["timestamp"])
        temps.append(r["temp"])
        hums.append(r["hum"])
        press.append(r["pres"])

    return jsonify({
        "timestamps": timestamps,
        "temps": temps,
        "hums": hums,
        "press": press
    })

@app.route("/device/<device_name>/microdos_data")
def device_microdos_data(device_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=? AND device_type='microdos'", (device_name,))
    dev = cursor.fetchone()
    if not dev:
        conn.close()
        return jsonify({"error": "No existe microdos con ese nombre"}), 404

    cursor.execute("SELECT * FROM measurements_microdos ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "status": row["status"],
            "flow_set": row["flow_set"],
            "time_left": row["time_left"]
        })
    else:
        return jsonify({"error": "Sin datos aún"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
