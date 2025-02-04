from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import logging
import os

DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "web_activity.sqlite")
print(DB_PATH)

app = Flask(__name__)

CORS(app, origins=["chrome-extension://fgiajiopnnaiglhakioljbohcemblmop"])



logging.basicConfig(filename='flask_server.log', level=logging.DEBUG)

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            url TEXT,
            title TEXT,
            entry_time TEXT,
            exit_time TEXT,
            key_pressed TEXT,
            x INTEGER,
            y INTEGER,
            element TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def log_activity(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity (action, url, title, entry_time, exit_time, key_pressed, x, y, element) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("action"), data.get("url"), data.get("title"),
        data.get("entry_time"), data.get("exit_time"),
        data.get("key_pressed"), data.get("x"), data.get("y"),
        data.get("element")
    ))
    conn.commit()
    conn.close()

@app.route('/log_activity', methods=['POST'])
def log_activity_endpoint():
    try:
        data = request.json
        log_activity(data)
        return jsonify({"success": True}), 200
    except Exception as e:
        logging.error(f"Error logging activity: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
