from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

OFFLINE_THRESHOLD = 10  # segundos para marcar desconexión

# Lista estática de dispositivos que queremos ver siempre en el Home
# (nombre, tipo)
PREDEFINED_DEVICES = [
    ("estacion", "estacion"),
    ("microdos", "microdos"),
    ("reactor", "reactor"),
    ("lc_shaker", "lc_shaker"),
    ("lecob50", "lecob50"),
    ("uvale", "uvale"),
    ("camera", "camera")  # Agregado para el streaming de cámara
]

def get_db():
    conn = sqlite3.connect("data/data.db")  # Asegúrate de que sea la misma ruta en Docker
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    """
    Renderiza la plantilla home.html (que se actualiza vía /devices_data).
    """
    return render_template("home.html")

@app.route("/devices_data")
def devices_data():
    """
    Devuelve en JSON la lista de dispositivos, ordenado por 'position'.
    Antes, se asegura de que todos los PREDEFINED_DEVICES existan en la DB,
    para evitar placeholders.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Aseguramos que cada dispositivo predefinido (excepto "camera") exista en la DB con position=9999 por defecto
    for (dev_name, dev_type) in PREDEFINED_DEVICES:
        if dev_name == "camera":
            continue  # La cámara se manejará como especial, sin datos en DB
        cursor.execute("SELECT COUNT(*) FROM devices WHERE device_name=?", (dev_name,))
        c = cursor.fetchone()[0]
        if c == 0:
            cursor.execute("""
                INSERT INTO devices (device_name, device_type, last_status, position)
                VALUES (?, ?, ?, ?)
            """, (dev_name, dev_type, "No data", 9999))
    conn.commit()

    # Consultamos todos los dispositivos, ordenados por 'position'
    cursor.execute("SELECT * FROM devices ORDER BY position ASC")
    rows = cursor.fetchall()
    conn.close()

    # Ajustamos la hora actual a la misma base local (UTC-5)
    now = datetime.utcnow() - timedelta(hours=5)
    final_list = []
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
        final_list.append(dev_dict)

    # Agregamos placeholders para los dispositivos predefinidos que no estén en DB (incluyendo "camera")
    for (dev_name, dev_type) in PREDEFINED_DEVICES:
        exists = any(d["device_name"] == dev_name for d in final_list)
        if not exists:
            final_list.append({
                "device_name": dev_name,
                "device_type": dev_type,
                "last_status": "No data",
                "last_seen": "1970-01-01 00:00:00",
                "status_final": "Desconectado"
            })
    for dev in final_list:
        if dev["device_name"] == "camera":
            dev["status_final"] = "Conectado"
    return jsonify(final_list)

@app.route("/device/<device_name>")
def device_detail(device_name):
    """
    Página de detalle de un dispositivo. Si está offline, error 403.
    Soporta 6 tipos: estacion, microdos, reactor, lc_shaker, lecob50, uvale.
    Además, si device_name es "camera", se muestra la interfaz de streaming.
    """
    # Caso especial para la cámara: no requiere datos en DB
    if device_name == "camera":
        return render_template("device_camera.html")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE device_name=?", (device_name,))
    device = cursor.fetchone()
    if not device:
        conn.close()
        return f"El dispositivo '{device_name}' no tiene datos en la base. Desconectado.", 403

    # Ajustamos la hora actual a la base local (UTC-5)
    now = datetime.utcnow() - timedelta(hours=5)
    try:
        last_dt = datetime.strptime(device["last_seen"], "%Y-%m-%d %H:%M:%S")
        diff = (now - last_dt).total_seconds()
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
        timestamps, temps, temp_sets, speeds, time_lefts, max_times, states = [], [], [], [], [], [], []
        for r in reversed(rows):
            timestamps.append(r["timestamp"])
            temps.append(r["temp"])
            temp_sets.append(r["temp_set"])  # Asumiendo que la columna "temp_set" se agregó en la tabla
            speeds.append(r["speed"])
            time_lefts.append(r["time_left"])
            max_times.append(r["max_time"])
            states.append(r["state"])
        return render_template("device_reactor.html",
                               device=device,
                               timestamps=timestamps,
                               temps=temps,
                               temp_sets=temp_sets,
                               speeds=speeds,
                               time_lefts=time_lefts,
                               max_times=max_times,
                               states=states)
    elif device_type == "lc_shaker":
        cursor.execute("SELECT * FROM measurements_lc_shaker ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        return render_template("device_lc_shaker.html", device=device)
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

    timestamps, temps, temp_sets, speeds, time_lefts, max_times, states = [], [], [], [], [], [], []
    for r in reversed(rows):
        timestamps.append(r["timestamp"])
        temps.append(r["temp"])
        temp_sets.append(r["temp_set"])
        speeds.append(r["speed"])
        time_lefts.append(r["time_left"])
        max_times.append(r["max_time"])
        states.append(r["state"])

    return jsonify({
        "timestamps": timestamps,
        "temps": temps,
        "temp_sets": temp_sets,
        "speeds": speeds,
        "time_lefts": time_lefts,
        "max_times": max_times,
        "states": states
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

    timestamps, speeds, amp_mayors, amp_menors, oscs, time_lefts, max_times, states = [], [], [], [], [], [], [], []
    for r in reversed(rows):
        timestamps.append(r["timestamp"])
        speeds.append(r["speed"])
        amp_mayors.append(r["amp_mayor"])
        amp_menors.append(r["amp_menor"])
        oscs.append(r["oscilaciones"])
        time_lefts.append(r["time_left"])
        max_times.append(r["max_time"])
        states.append(r["state"])
    return jsonify({
        "timestamps": timestamps,
        "speeds": speeds,
        "amp_mayors": amp_mayors,
        "amp_menors": amp_menors,
        "oscs": oscs,
        "time_lefts": time_lefts,
        "max_times": max_times,
        "states": states
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

    cursor.execute("SELECT * FROM measurements_uvale ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"error": "Sin datos aún"}), 200

    timestamps = []
    hum = []
    temp = []
    for r in reversed(rows):
        timestamps.append(r["timestamp"])
        hum.append(r["hum"])
        temp.append(r["temp"])

    last = rows[0]
    return jsonify({
        "distance": last["distance"],
        "time_left": last["time_left"],
        "max_time": last["max_time"],
        "door_state": last["door_state"],
        "uv_state": last["uv_state"],
        "status": last["status"],
        "hum": hum,
        "temp": temp,
        "timestamps": timestamps
    })

@app.route('/api/save_order', methods=['POST'])
def save_order():
    data = request.get_json()
    order = data.get("order", [])
    if not order:
        return jsonify({"error": "No order provided"}), 400

    conn = get_db()
    cursor = conn.cursor()
    for pos, device_name in enumerate(order):
        cursor.execute("UPDATE devices SET position = ? WHERE device_name = ?", (pos, device_name))
    conn.commit()
    conn.close()
    return jsonify({"status": "Order saved successfully"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
