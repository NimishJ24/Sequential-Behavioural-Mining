import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import time
import pynput
from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Listener as MouseListener
import threading
import queue
import sys
import math
import psutil
import win32gui
import win32process
from datetime import datetime  # Import datetime here
import ast
import os
from datetime import timedelta
import sqlite3
import joblib

from data_formatting import extract_key_inference  # Import the data function
from data_formatting import extract_mouse_inference  # Import the data function
from data_formatting import extract_focus_inference

ACTIVITY_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")   

class IntrusionDetector:
    def __init__(self):
        self.keyboard_events = []
        self.mouse_events = []
        self.focus_events = []
        self.model = None
        self.model_filename = r"intrusion_model.joblib"
        self.clf = None
        self.scaler = None

    def extract_features(self, duration, inference):
        
        if inference:
            # self.take_data()
            pass
        
        print("-"*15)
        print(self.keyboard_events)

        # Keyboard Features
        if not self.keyboard_events:
            print("No keyboard events to process.")
            keyboard_features = [0] * 5  # Return default values if no events
        else:
            typing_speed = len(self.keyboard_events) / duration if duration > 0 else 0
            shortcuts = 0
            backspace = 0
            modifiers = {'Key.ctrl', 'Key.ctrl_l', 'Key.ctrl_r', 'Key.alt', 'Key.alt_l', 
                        'Key.alt_r', 'Key.cmd', 'Key.shift', 'Key.shift_l', 'Key.shift_r'}

            for event in self.keyboard_events:
                if event[0] in modifiers:
                    shortcuts += 1
                if event[0] == 'Key.backspace':
                    backspace += 1

            values = [int(item[1]) for item in self.keyboard_events]
            dwell_time = sum(values) / len(values) if values else 0

            datetime_data = []
            for item in self.keyboard_events:
                timestamp_str = item[2]
                try:
                    timestamp_obj = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    datetime_data.append((item[0], item[1], timestamp_obj))
                except ValueError as e:
                    print(f"Error converting timestamp: {timestamp_str}. Error: {e}")
                    continue

            time_differences = []
            for i in range(1, len(datetime_data)):
                time_diff = datetime_data[i][2] - datetime_data[i-1][2]
                time_differences.append(time_diff.total_seconds())

            average_difference = sum(time_differences) / len(time_differences) if time_differences else 0

            print(f"Typing speed: {typing_speed}")
            print(f"Error rate: {backspace}")
            print(f"Special keys rate: {shortcuts}")
            print(f"Average Dwell Time: {dwell_time}")
            print(f"Average flight time: {average_difference}")

            keyboard_features = [typing_speed, shortcuts, backspace, dwell_time, average_difference]


        # Mouse Features
        if not self.mouse_events:
            print("No mouse events to process.")
            mouse_features = [0] * 4  # Default values
        else:
            click_distances = []
            mouse_speeds = []
            double_clicks = 0
            click_times = []
            mouse_positions = []

            for i in range(len(self.mouse_events)):
                click_type, click_interval, position_str, timestamp_str = self.mouse_events[i]
                
                # Keep track of all intervals for averaging
                mouse_intervals = []
                if click_interval > 0:  # Only add valid intervals
                    mouse_intervals.append(click_interval)

                try:
                    position = ast.literal_eval(position_str)
                    x, y = position

                    if i > 0:
                        prev_position_str = self.mouse_events[i - 1][2]
                        prev_position = ast.literal_eval(prev_position_str)
                        x1, y1 = prev_position
                        distance = ((x - x1)**2 + (y - y1)**2)**0.5
                        click_distances.append(distance)

                    mouse_speeds.append(distance / click_interval if click_interval > 0 and i > 0 else 0)

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
                    print(f"Error processing mouse data point {i+1}: {e}")
                    mouse_features = [0] * 4  # Updated to 4 default values
                    break  # Exit from the loop if there is an error

            avg_click_distance = sum(click_distances) / len(click_distances) if click_distances else 0
            avg_mouse_speed = np.mean(mouse_speeds) if mouse_speeds else 0
            avg_mouse_interval = sum(mouse_intervals) / len(mouse_intervals) if mouse_intervals else 0

            print(f"Average Click Distance: {avg_click_distance}")
            print(f"Average Mouse Speed: {avg_mouse_speed}")
            print(f"Double Clicks: {double_clicks}")
            print(f"Average Mouse Interval: {avg_mouse_interval}")

            mouse_features = [ avg_mouse_interval, avg_click_distance, avg_mouse_speed, double_clicks]

        # Focus Features
        transitions = []
        previous_app = None


        if self.focus_events is None or not self.focus_events:  # Check for None or empty
            print("No focus events to process.")
            focus_features = [0] * 7  # Default values
        else:
            durations = []
            timestamps = []

            for title, duration, timestamp_str in self.focus_events:

                current_app = title
                if previous_app and current_app != previous_app:
                    transition = f"{previous_app}→{current_app}"
                    transitions.append(transition)
    
                previous_app = current_app


                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    durations.append(duration)
                    timestamps.append(timestamp)
                except ValueError as e:
                    print(f"Error converting focus timestamp: {timestamp_str}. Error: {e}")
                    focus_features = [0] * 7 #Default Values
                    break #Exit from the loop if there is an error

            switching_rate = len(durations) - 1
            max_duration = max(durations) if durations else 0
            mean_duration = np.mean(durations) if durations else 0
            total_transitions = len(transitions)              # Number of app switches
            unique_transitions = len(set(transitions))        # Unique transition patterns
            transition_rate = total_transitions / 30

            print(f"Switching Rate: {switching_rate}")
            print(f"Max Duration: {max_duration}")
            print(f"Average of Duration: {mean_duration}")
            print(f"Transition count: {total_transitions}")
            print(f"Unique transitions: {unique_transitions}")
            print(f"Transition rate: {transition_rate}")

            focus_features = [0, 0, mean_duration, total_transitions, unique_transitions, transition_rate, 0]
            
        all_features = keyboard_features + mouse_features + focus_features
        print(f"Keyboard features: {len(keyboard_features)}")  # Should be 5
        print(f"Mouse features: {len(mouse_features)}")       # Should be 4
        print(f"Focus features: {len(focus_features)}")       # Should be 7
        print(f"Total features: {len(all_features)}")         # Should be 16

        
        return all_features  # Return the combined list of features

    def get_timeframe(self):
        """
        Opens the `soft_training.sqlite` database and retrieves the timestamp of the first and last entry.
        Returns:
            tuple: (start_time, end_time) as datetime objects.
        """
        conn = sqlite3.connect(ACTIVITY_DB_PATH)
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

    def extract_pc_data(self):
        return self._extract_data_by_interval("PC Usage", ["CPU Utilization", ""])

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

            extracted_features.append(self.extract_features(inference=False))
        
        # print("Key Data:")
        # for interval in key_data:
        #     print(interval)
        #     print()
        # print("Mouse Data:")
        # for interval in mouse_data:
        #     print(interval)
        #     print()
        # print("Focus Data:")
        # for interval in focus_data:
        #     print(interval)
        #     print()

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

    def run_inference(self):

        self.load_model()

        self.keyboard_events = extract_key_inference()
        self.mouse_events = extract_mouse_inference()
        self.focus_events = extract_focus_inference()

        my_model = self.clf
        features = self.extract_features(duration=30, inference=True)
        if my_model.predict([features])[0] == 1:
            print("The model predicts: Normal activity")
            return True
        else:
            print("The model predicts Suspicious behaviour")
            return False


# Example usage:
if __name__ == "__main__":
    detector = IntrusionDetector()
    detector.run_inference()


