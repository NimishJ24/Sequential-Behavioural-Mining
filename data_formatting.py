import os
import sqlite3
from datetime import datetime, timedelta

def get_time_window():
    """
    Returns the current time and the time 30 seconds ago in the correct string format
    """
    current_time = datetime.now()
    time_window = current_time - timedelta(seconds=30)
    return time_window.strftime('%Y-%m-%d %H:%M:%S'), current_time.strftime('%Y-%m-%d %H:%M:%S')

def extract_key_inference():
    start_time, end_time = get_time_window()
    
    conn = sqlite3.connect(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT key, key_interval, timestamp 
        FROM SOFTWARE 
        WHERE TYPE = "Keyboard"
        AND timestamp BETWEEN ? AND ?;
    """, (start_time, end_time))
    
    result = cursor.fetchall()
    conn.close()
    # print(result)
    return result

def extract_mouse_inference():
    start_time, end_time = get_time_window()
    
    conn = sqlite3.connect(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT click_type, click_interval, position, timestamp 
        FROM SOFTWARE 
        WHERE TYPE = "Click"
        AND timestamp BETWEEN ? AND ?;
    """, (start_time, end_time))
    
    result = cursor.fetchall()
    conn.close()
    # print(result)
    return result

ACTIVITY_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")

def create_activity_table():
    conn = sqlite3.connect(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS software (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            title TEXT,
            key TEXT,
            key_interval REAL,
            click_type TEXT,
            click_interval REAL,
            position TEXT,
            scroll_direction TEXT,
            scroll_speed REAL,
            scroll_interval REAL,
            duration REAL,
            cpu_usage REAL,
            memory_usage REAL,
            device_id TEXT,
            device_type TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def extract_focus_inference():
    start_time, end_time = get_time_window()
    
    conn = sqlite3.connect(ACTIVITY_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT duration, timestamp 
        FROM SOFTWARE 
        WHERE TYPE = "App in Focus"
        AND timestamp BETWEEN ? AND ?;
    """, (start_time, end_time))
    
    result = cursor.fetchall()
    conn.close()
    # print(result)
    return result


# create_activity_table()
# extract_key_inference()
# extract_focus_inference()
# extract_mouse_inference()