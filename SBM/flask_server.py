from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)  # Enables CORS for all requests

# Set database path
DB_PATH = os.path.join(os.path.expanduser("~"), "documents", "tab_activity.sqlite")

# Ensure the directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            url TEXT,
            domain TEXT,
            tab_id INTEGER,
            window_id INTEGER,
            entry_time TEXT,
            exit_time TEXT,
            key_pressed TEXT,
            click_type TEXT,
            x INTEGER,
            y INTEGER,
            scroll_direction TEXT,
            scroll_distance REAL,
            scroll_interval REAL,
            interactive_element TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route('/log_activity', methods=['POST'])
def log_activity():
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    # Debugging output
    print("Received:", data)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity (action, url, domain, tab_id, window_id, entry_time, exit_time, key_pressed, click_type, x, y, scroll_direction, scroll_distance, scroll_interval, interactive_element, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("action"), data.get("url"), data.get("domain"), data.get("tab_id"), data.get("window_id"),
            data.get("entry_time"), data.get("exit_time"), data.get("key_pressed"), data.get("click_type"),
            data.get("x"), data.get("y"), data.get("scroll_direction"), data.get("scroll_distance"), 
            data.get("scroll_interval"), data.get("interactive_element"), data.get("timestamp")
        ))
        conn.commit()
        conn.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        print("❌ Error saving data to database:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
