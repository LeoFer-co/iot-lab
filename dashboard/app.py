from flask import Flask, render_template
import sqlite3
import json

app = Flask(__name__)

def get_measurements():
    conn = sqlite3.connect('data/data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Tomamos, por ejemplo, los últimos 50 registros
    cursor.execute("SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()

    # Creamos listas separadas para cada tipo de dato
    # Invertimos el orden para que el más antiguo aparezca primero en la gráfica
    timestamps = [row["timestamp"] for row in rows][::-1]
    temp_vals  = [row["temp"] for row in rows][::-1]
    hum_vals   = [row["hum"] for row in rows][::-1]
    pres_vals  = [row["pres"] for row in rows][::-1]
    light_vals = [row["light"] for row in rows][::-1]
    sound_vals = [row["sound"] for row in rows][::-1]
    volt_vals  = [row["voltage"] for row in rows][::-1]

    return timestamps, temp_vals, hum_vals, pres_vals, light_vals, sound_vals, volt_vals

@app.route('/')
def index():
    timestamps, temp_vals, hum_vals, pres_vals, light_vals, sound_vals, volt_vals = get_measurements()
    return render_template('index.html',
        timestamps=json.dumps(timestamps),
        temp_vals=json.dumps(temp_vals),
        hum_vals=json.dumps(hum_vals),
        pres_vals=json.dumps(pres_vals),
        light_vals=json.dumps(light_vals),
        sound_vals=json.dumps(sound_vals),
        volt_vals=json.dumps(volt_vals)
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
