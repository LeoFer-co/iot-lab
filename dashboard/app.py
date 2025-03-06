from flask import Flask, render_template
import sqlite3
import json

app = Flask(__name__)

def get_measurements():
    # Conectar a la base de datos usando la ruta montada (la base se encuentra en ../data/data.db)
    conn = sqlite3.connect('../data/data.db')
    cursor = conn.cursor()
    # Seleccionamos las últimas 50 mediciones ordenadas por timestamp (ajusta según necesites)
    cursor.execute("SELECT timestamp, message FROM measurements ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    # Preparamos los datos en dos listas: tiempos y valores
    timestamps = [row[0] for row in rows][::-1]  # Invertimos para que estén en orden cronológico ascendente
    values = [float(row[1]) for row in rows][::-1]
    return timestamps, values

@app.route('/')
def index():
    timestamps, values = get_measurements()
    # Convertimos los datos a formato JSON para que Chart.js pueda usarlos en JavaScript
    return render_template('index.html', timestamps=json.dumps(timestamps), values=json.dumps(values))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
