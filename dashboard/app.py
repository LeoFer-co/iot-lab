from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

OFFLINE_THRESHOLD = 10  # seg para marcar desconexión

def get_db():
    conn = sqlite3.connect("data/data.db")  # Ajusta la ruta si es diferente
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    """
    Lista todos los dispositivos de la tabla 'devices'.
    Si su last_seen supera OFFLINE_THRESHOLD, se marcan como 'Desconectado'.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    rows = cursor.fetchall()
    conn.close()

    now = datetime.now()
    devices_data = []
    for dev in rows:
        dev_dict = dict(dev)
        try:
            last_seen_str = dev_dict["last_seen"]  # p.ej. "YYYY-MM-DD HH:MM:SS"
            last_dt = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
            diff = (now - last_dt).total_seconds()
            if diff > OFFLINE_THRESHOLD:
                dev_dict["status_final"] = "Desconectado"
            else:
                dev_dict["status_final"] = dev_dict["last_status"]
        except:
            dev_dict["status_final"] = "Desconocido"
        devices_data.append(dev_dict)

    return render_template("home.html", devices_data=devices_data)

@app.route("/device/<device_name>")
def device_detail(device_name):
    """
    Página de detalle de un dispositivo. 
    Si está offline, se muestra error 403. 
    Si device_type='estacion', renderiza device_estacion.html, 
    si device_type='microdos', renderiza device_microdos.html.
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
        # Cargar las últimas 30 mediciones
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

    elif device_type == "microdos":
        # Cargar la última medición
        cursor.execute("SELECT * FROM measurements_microdos ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        return render_template("device_microdos.html", device=device, row=last_row)

    else:
        conn.close()
        return f"Tipo de dispositivo desconocido: {device_type}", 400

# --- ENDPOINTS PARA DATOS EN TIEMPO REAL ---
@app.route("/device/<device_name>/estacion_data")
def device_estacion_data(device_name):
    """
    Devuelve JSON con las últimas 30 mediciones (timestamps, temps, hums, press) para la Estación,
    usado por device_estacion.html para actualizar en tiempo real.
    """
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
    """
    Devuelve JSON con la última medición (status, flow_set, time_left) para Microdós,
    usado por device_microdos.html para actualizar en tiempo real.
    """
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
