import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import time
from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Listener as MouseListener
from datetime import datetime  # Import datetime here
import ast
import os
from datetime import timedelta
import sqlite3
import joblib

ACTIVITY_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")
TRAINING_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_training.sqlite")

from data_formatting import extract_key_inference  # Import the data function
from data_formatting import extract_mouse_inference  # Import the data function
from data_formatting import extract_focus_inference

class IntrusionDetector:
    def __init__(self):
        self.keyboard_events = []
        self.mouse_events = []
        self.focus_events = []
        self.model = None
        self.model_filename = "intrusion_model.joblib"

    def take_data(self):
        self.keyboard_events = self.extract_key_data()  # Assign the return value
        #print(self.keyboard_events)  # Print for debugging if needed
        self.mouse_events = self.extract_mouse_data()
        # print(self.mouse_events)
        self.focus_events = self.extract_focus_data()

    def extract_features(self, duration, inference):
        if inference:
            self.take_data()

        # Keyboard Features
        if not self.keyboard_events:
            print("No keyboard events to process.")
            keyboard_features = [[]]  # Replace with empty list in correct format
        else:
            try:
                typing_speed = len(self.keyboard_events) / duration if duration > 0 else 0
                shortcuts = 0
                backspace = 0
                modifiers = {'Key.ctrl', 'Key.ctrl_l', 'Key.ctrl_r', 'Key.alt', 'Key.alt_l', 
                            'Key.alt_r', 'Key.cmd', 'Key.shift', 'Key.shift_l', 'Key.shift_r'}

                values = []
                datetime_data = []
                for event in self.keyboard_events:
                    if not event or len(event) < 1:
                        continue  # Skip empty or malformed events
                    if event[0] in modifiers:
                        shortcuts += 1
                    if event[0] == 'Key.backspace':
                        backspace += 1
                    values.append(event[1])
                    try:
                        timestamp_obj = datetime.strptime(event[2], '%Y-%m-%d %H:%M:%S')
                        datetime_data.append((event[0], event[1], timestamp_obj))
                    except ValueError as e:
                        print(f"Error converting timestamp: {event[2]}. Error: {e}")

                dwell_time = sum(values) / len(values) if values else 0
                time_differences = [datetime_data[i][2] - datetime_data[i-1][2] for i in range(1, len(datetime_data))]
                average_difference = sum(td.total_seconds() for td in time_differences) / len(time_differences) if time_differences else 0

                keyboard_features = [typing_speed, shortcuts, backspace, dwell_time, average_difference]
            except Exception as e:
                print(f"Error processing keyboard data: {e}")
                keyboard_features = [[]]  # Replace with empty list

        # Mouse Features
        if not self.mouse_events:
            print("No mouse events to process.")
            mouse_features = [[]]
        else:
            try:
                click_distances, mouse_speeds, click_times, mouse_positions = [], [], [], []
                double_clicks = 0

                for i, event in enumerate(self.mouse_events):
                    try:
                        position = ast.literal_eval(event[2])
                        x, y = position

                        if i > 0:
                            prev_position = ast.literal_eval(self.mouse_events[i - 1][2])
                            distance = ((x - prev_position[0]) ** 2 + (y - prev_position[1]) ** 2) ** 0.5
                            click_distances.append(distance)
                            mouse_speeds.append(distance / event[1] if event[1] > 0 else 0)

                        click_times.append(time.time())
                        if i > 0 and click_times[i] - click_times[i - 1] < 0.5:
                            double_clicks += 1

                        mouse_positions.append((x, time.time()))
                        if len(mouse_positions) > 1:
                            prev_x, prev_time = mouse_positions[-2]
                            dx = x - prev_x
                            time_diff = time.time() - prev_time
                            if time_diff > 0:
                                mouse_speeds.append(dx / time_diff)

                    except (SyntaxError, ValueError) as e:
                        print(f"Error processing mouse event {i+1}: {e}")

                avg_click_distance = sum(click_distances) / len(click_distances) if click_distances else 0
                avg_mouse_speed = np.mean(mouse_speeds) if mouse_speeds else 0

                mouse_features = [avg_click_distance, avg_mouse_speed, double_clicks]
            except Exception as e:
                print(f"Error processing mouse data: {e}")
                mouse_features = [[]]

        # Focus Features
        if not self.focus_events:
            print("No focus events to process.")
            focus_features = [[]]
        else:
            try:
                durations = []
                for duration, timestamp_str in self.focus_events:
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        durations.append(duration)
                    except ValueError as e:
                        print(f"Error converting focus timestamp: {timestamp_str}. Error: {e}")

                switching_rate = len(durations) - 1
                max_duration = max(durations) if durations else 0
                std_dev_duration = np.std(durations) if durations else 0

                focus_features = [switching_rate, max_duration, std_dev_duration]
            except Exception as e:
                print(f"Error processing focus data: {e}")
                focus_features = [[]]

        # Ensure all features exist in the correct format
        features = {
            "keyboard": keyboard_features,
            "mouse": mouse_features,
            "focus": focus_features
        }

        for key in features:
            if not features[key] or features[key] == [[]]:  # If any feature is missing or empty
                features[key] = [[]]  # Replace with a blank list in the expected format

        return keyboard_features + mouse_features + focus_features  # Return the combined list of features

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
        """
        Extract data from the database grouped into 30-second intervals.
        Ensures there are entries for all intervals, even if they are empty.
        """
        # Open the training database
        DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_training.sqlite")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get the first and last timestamps for the entire database
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM SOFTWARE")
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
            
            # Store interval data (empty or populated)
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

        extracted_features = []

        for k, m, f in zip(key_data, mouse_data, focus_data):
            self.keyboard_events = k
            self.mouse_events = m
            self.focus_events = f

            extracted_features.append(self.extract_features(inference=False, duration=30))

    def load_model(self):
        try:
            self.clf = joblib.load(self.model_filename)  # Load the IsolationForest
            self.scaler = joblib.load(self.model_filename.replace(".joblib", "_scaler.joblib"))  # Load the scaler
            print(f"Model loaded from {self.model_filename}")
            return True
        except FileNotFoundError:
            print(f"Model file {self.model_filename} not found. Training a new model.")
            return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False


    def test(self):
        self.load_model()

        self.keyboard_events = extract_focus_inference()
        self.mouse_events = extract_mouse_inference()
        self.focus_events = extract_focus_inference()
        
        features = self.extract_features(duration=30, inference=True)

        if not features or len(features) == 0:
            raise ValueError("Feature extraction failed: No features generated.")

        return self.clf.predict([features])


# Example usage:
if __name__ == "__main__":
    detector = IntrusionDetector()
    detector.train()