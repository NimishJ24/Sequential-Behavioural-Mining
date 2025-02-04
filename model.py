import logging
import random
from datetime import datetime, timedelta
import sqlite3
import os
import ollama

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
    
    def train():
        print("helo")