import logging
import random
from datetime import datetime, timedelta
import sqlite3
import os
import ollama
import pandas as pd

ACTIVITY_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")
TRAINING_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_training.sqlite")

class IDS:
    def test(self):
        thirty_seconds_ago = datetime.now() - timedelta(seconds=30)
        thirty_seconds_ago_str = thirty_seconds_ago.strftime("%Y-%m-%d %H:%M:%S")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(ACTIVITY_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT type, title, timestamp FROM software WHERE timestamp >= ? AND timestamp <= ?",
                        (thirty_seconds_ago_str, now_str))
        rows = cursor.fetchall()
        conn.close()



        # ACHINTYA TERRITORY INFERENCE

        n = random.randint(0,1)
        
        return n
    
    
    def extract_key_data():
    # Database: soft_activity.sqlite in the user's Documents folder
        DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Query 1: Total Keystrokes
        cursor.execute("""
            SELECT key, key_interval, timestamp FROM SOFTWARE WHERE TYPE = "Keyboard";
        """)
        result = cursor.fetchall()
        conn.close()

        return result

    def extract_mouse_data():
        DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Query 1: Total Keystrokes
        cursor.execute("""
            SELECT click_type, click_interval, position, timestamp FROM SOFTWARE WHERE TYPE = "Click";
        """)
        result = cursor.fetchall()
        # print(result)
        conn.close()

        return result

    def extract_focus_data():
        DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Query 1: Total Keystrokes
        cursor.execute("""
            SELECT duration, timestamp FROM SOFTWARE WHERE TYPE = "App in Focus";
        """)
        result = cursor.fetchall()
        # print(result)
        conn.close()
        return result
    
    def train():
        print("helo")