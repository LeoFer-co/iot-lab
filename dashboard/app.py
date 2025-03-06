from flask import Flask, render_template, jsonify
import sqlite3

app = Flask(__name__)

def get_measurements():
    conn = sqlite3.connect('data/data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()

    # Invertir el orden para tener los registros en orden cronológico
    rows = rows[::-1]
    # Separar los datos en listas
    timestamps = [row["timestamp"] for row in rows]
    temp_vals  = [row["temp"] for row in rows]
    hum_vals   = [row["hum"] for row in rows]
    pres_vals  = [row["pres"] for row in rows]
    light_vals = [row["light"] for row in rows]
    sound_vals = [row["sound"] for row in rows]
    volt_vals  = [row["voltage"] for row in rows]
    return timestamps, temp_vals, hum_vals, pres_vals, light_vals, sound_vals, volt_vals

@app.route('/')
def index():
    timestamps, temp_vals, hum_vals, pres_vals, light_vals, sound_vals, volt_vals = get_measurements()
    return render_template('index.html',
                           timestamps=timestamps,
                           temp_vals=temp_vals,
                           hum_vals=hum_vals,
                           pres_vals=pres_vals,
                           light_vals=light_vals,
                           sound_vals=sound_vals,
                           volt_vals=volt_vals)

# Endpoint para obtener datos en formato JSON (para la actualización en tiempo real)
@app.route('/data')
def data():
    timestamps, temp_vals, hum_vals, pres_vals, light_vals, sound_vals, volt_vals = get_measurements()
    return jsonify({
        "timestamps": timestamps,
        "temp_vals": temp_vals,
        "hum_vals": hum_vals,
        "pres_vals": pres_vals,
        "light_vals": light_vals,
        "sound_vals": sound_vals,
        "volt_vals": volt_vals
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
