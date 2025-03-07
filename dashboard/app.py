from flask import Flask, render_template, jsonify, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

OFFLINE_THRESHOLD = 10  # segundos para marcar desconexión

def get_db():
    conn = sqlite3.connect("data/data.db")  # Asegúrate de que esta ruta es la misma en todos los servicios
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    """
    Renderiza la plantilla home.html (la cual se actualiza vía JavaScript con el endpoint /devices_data).
    """
    return render_template("home.html")

@app.route("/devices_data")
def devices_data():
    """
    Devuelve en JSON la lista de dispositivos (tabla 'devices') con lógica offline.
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
        except Exception:
            dev_dict["status_final"] = "Desconocido"
        devices_list.append(dev_dict)

    return jsonify(devices_list)

@app.route("/device/<device_name>")
def device_detail(device_name):
    """
    Página de detalle de un dispositivo.
    Si está offline (más de OFFLINE_THRESHOLD segundos sin actualizar), se retorna error 403.
    Según el device_type, se renderiza la plantilla correspondiente:
      - "estacion"        -> device_estacion.html
      - "microdos"        -> device_microdos.html
      - "reactor"         -> device_reactor.html
      - "lc_shaker"       -> device_lc_shaker.html
      - "lecob50"         -> device_lecob50.html
      - "uvale"           -> device_uvale.html
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=?", (device_name,))
    device = cursor.fetchone()
    if not device:
        conn.close()
        return "Dispositivo no encontrado", 404

    # Verificar desconexión
    try:
        last_dt = datetime.strptime(device["last_seen"], "%Y-%m-%d %H:%M:%S")
        diff = (datetime.now() - last_dt).total_seconds()
        if diff > OFFLINE_THRESHOLD:
            conn.close()
            return f"El dispositivo '{device_name}' está desconectado.", 403
    except Exception:
        conn.close()
        return "Error al determinar el estado del dispositivo", 500

    device_type = device["device_type"]
    if device_type == "estacion":
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
        cursor.execute("SELECT * FROM measurements_microdos ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        return render_template("device_microdos.html", device=device, row=last_row)
    elif device_type == "reactor":
        cursor.execute("SELECT * FROM measurements_reactor ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        # Se espera que el dispositivo reactor envíe: temp, speed, time_left, max_time, state
        timestamps, temps, speeds, time_lefts, max_times, states = [], [], [], [], [], []
        for r in reversed(rows):
            timestamps.append(r["timestamp"])
            temps.append(r["temp"])
            speeds.append(r["speed"])
            time_lefts.append(r["time_left"])
            max_times.append(r["max_time"])
            states.append(r["state"])
        return render_template("device_reactor.html",
                               device=device,
                               timestamps=timestamps,
                               temps=temps,
                               speeds=speeds,
                               time_lefts=time_lefts,
                               max_times=max_times,
                               states=states)
    elif device_type == "lc_shaker":
        cursor.execute("SELECT * FROM measurements_lc_shaker ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        // Se espera que el lc_shaker envíe: speed, amp_mayor, amp_menor, oscilaciones, time_left, max_time, state
        let_timestamps = []
        let_speeds = []
        let_amp_mayor = []
        let_amp_menor = []
        let_oscilaciones = []
        let_time_lefts = []
        let_max_times = []
        let_states = []
        for r in reversed(rows):
            let_timestamps.append(r["timestamp"])
            let_speeds.append(r["speed"])
            let_amp_mayor.append(r["amp_mayor"])
            let_amp_menor.append(r["amp_menor"])
            let_oscilaciones.append(r["oscilaciones"])
            let_time_lefts.append(r["time_left"])
            let_max_times.append(r["max_time"])
            let_states.append(r["state"])
        return render_template("device_lc_shaker.html",
                               device=device,
                               timestamps=let_timestamps,
                               speeds=let_speeds,
                               amp_mayor=let_amp_mayor,
                               amp_menor=let_amp_menor,
                               oscilaciones=let_oscilaciones,
                               time_lefts=let_time_lefts,
                               max_times=let_max_times,
                               states=let_states)
    elif device_type == "lecob50":
        cursor.execute("SELECT * FROM measurements_lecob50 ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        return render_template("device_lecob50.html", device=device, row=last_row)
    elif device_type == "uvale":
        cursor.execute("SELECT * FROM measurements_uvale ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        return render_template("device_uvale.html", device=device, row=last_row)
    else:
        conn.close()
        return f"Tipo de dispositivo desconocido: {device_type}", 400

# Endpoints de tiempo real para cada dispositivo

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
    timestamps, temps, hums, press = [], [], [], []
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

@app.route("/device/<device_name>/reactor_data")
def device_reactor_data(device_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=? AND device_type='reactor'", (device_name,))
    dev = cursor.fetchone()
    if not dev:
        conn.close()
        return jsonify({"error": "No existe reactor con ese nombre"}), 404
    cursor.execute("SELECT * FROM measurements_reactor ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    conn.close()
    let_timestamps = []
    let_temps = []
    let_speeds = []
    let_time_lefts = []
    let_max_times = []
    let_states = []
    for r in reversed(rows):
        let_timestamps.append(r["timestamp"])
        let_temps.append(r["temp"])
        let_speeds.append(r["speed"])
        let_time_lefts.append(r["time_left"])
        let_max_times.append(r["max_time"])
        let_states.append(r["state"])
    return jsonify({
        "timestamps": let_timestamps,
        "temps": let_temps,
        "speeds": let_speeds,
        "time_lefts": let_time_lefts,
        "max_times": let_max_times,
        "states": let_states
    })

@app.route("/device/<device_name>/lc_shaker_data")
def device_lc_shaker_data(device_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=? AND device_type='lc_shaker'", (device_name,))
    dev = cursor.fetchone()
    if not dev:
        conn.close()
        return jsonify({"error": "No existe LC_Shaker con ese nombre"}), 404
    cursor.execute("SELECT * FROM measurements_lc_shaker ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    conn.close()
    let_timestamps = []
    let_speeds = []
    let_amp_mayor = []
    let_amp_menor = []
    let_oscilaciones = []
    let_time_lefts = []
    let_max_times = []
    let_states = []
    for r in reversed(rows):
        let_timestamps.append(r["timestamp"])
        let_speeds.append(r["speed"])
        let_amp_mayor.append(r["amp_mayor"])
        let_amp_menor.append(r["amp_menor"])
        let_oscilaciones.append(r["oscilaciones"])
        let_time_lefts.append(r["time_left"])
        let_max_times.append(r["max_time"])
        let_states.append(r["state"])
    return jsonify({
        "timestamps": let_timestamps,
        "speeds": let_speeds,
        "amp_mayor": let_amp_mayor,
        "amp_menor": let_amp_menor,
        "oscilaciones": let_oscilaciones,
        "time_lefts": let_time_lefts,
        "max_times": let_max_times,
        "states": let_states
    })

@app.route("/device/<device_name>/lecob50_data")
def device_lecob50_data(device_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=? AND device_type='lecob50'", (device_name,))
    dev = cursor.fetchone()
    if not dev:
        conn.close()
        return jsonify({"error": "No existe LECOB 50 con ese nombre"}), 404
    cursor.execute("SELECT * FROM measurements_lecob50 ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({
            "on_time": row["on_time"],
            "off_time": row["off_time"],
            "time_left": row["time_left"],
            "max_time": row["max_time"],
            "status": row["status"]
        })
    else:
        return jsonify({"error": "Sin datos aún"}), 200

@app.route("/device/<device_name>/uvale_data")
def device_uvale_data(device_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=? AND device_type='uvale'", (device_name,))
    dev = cursor.fetchone()
    if not dev:
        conn.close()
        return jsonify({"error": "No existe UV ale con ese nombre"}), 404
    cursor.execute("SELECT * FROM measurements_uvale ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({
            "distance": row["distance"],
            "time_left": row["time_left"],
            "max_time": row["max_time"],
            "door_state": row["door_state"],
            "uv_state": row["uv_state"],
            "hum": row["hum"],
            "temp": row["temp"],
            "status": row["status"]
        })
    else:
        return jsonify({"error": "Sin datos aún"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
