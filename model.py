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
    
    def get_timeframe(self):
        """
        Opens the `soft_training.sqlite` database and retrieves the timestamp of the first and last entry.
        Returns:
            tuple: (start_time, end_time) as datetime objects.
        """
        conn = sqlite3.connect(TRAINING_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM SOFTWARE")
        result = cursor.fetchone()
        conn.close()

        if result and result[0] and result[1]:
            start_time = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(result[1], "%Y-%m-%d %H:%M:%S")
            return start_time, end_time
        else:
            raise ValueError("No data available in the database.")

    def extract_key_data(self):
        return self._extract_data_by_interval("Keyboard", ["key", "key_interval", "timestamp"])

    def extract_mouse_data(self):
        return self._extract_data_by_interval("Click", ["click_type", "click_interval", "position", "timestamp"])

    def extract_focus_data(self):
        return self._extract_data_by_interval("App in Focus", ["duration", "timestamp"])

    def _extract_data_by_interval(self, data_type, columns):
        # Open the training database and fetch the first and last timestamps
        DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_training.sqlite")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get the first and last timestamps
        cursor.execute(f"""
            SELECT MIN(timestamp), MAX(timestamp) FROM SOFTWARE WHERE TYPE = ?;
        """, (data_type,))
        first_timestamp, last_timestamp = cursor.fetchone()

        if not first_timestamp or not last_timestamp:
            conn.close()
            return []  # Return empty list if no data exists for the given type

        # Convert timestamps to datetime objects
        first_time = datetime.strptime(first_timestamp, "%Y-%m-%d %H:%M:%S")
        last_time = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")

        # Initialize the loop and results
        results = []
        current_time = first_time

        while current_time <= last_time:
            next_time = current_time + timedelta(seconds=30)

            # Fetch records for the current 30-second interval
            cursor.execute(f"""
                SELECT {", ".join(columns)} FROM SOFTWARE 
                WHERE TYPE = ? AND timestamp >= ? AND timestamp < ?;
            """, (data_type, current_time.strftime("%Y-%m-%d %H:%M:%S"), next_time.strftime("%Y-%m-%d %H:%M:%S")))
            
            interval_data = cursor.fetchall()
            results.append(interval_data)

            # Move to the next interval
            current_time = next_time

        conn.close()
        return results
    
    def train(self):
        # Extract the data for training
        key_data = self.extract_key_data()
        mouse_data = self.extract_mouse_data()
        focus_data = self.extract_focus_data()
        
        print("Key Data:")
        for interval in key_data:
            print(interval)
            print()
        print("Mouse Data:")
        for interval in mouse_data:
            print(interval)
            print()
        print("Focus Data:")
        for interval in focus_data:
            print(interval)
            print()
            
        
        

# Create an instance of the IDS class
ids_instance = IDS()

# Call the train method
ids_instance.train()
