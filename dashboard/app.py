from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

def get_measurements():
    conn = sqlite3.connect('data/data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Selecciona los últimos 20 registros
    cursor.execute("SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.route('/')
def index():
    measurements = get_measurements()
    return render_template('index.html', measurements=measurements)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
