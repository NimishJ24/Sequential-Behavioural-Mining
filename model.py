import os
import time
import math
import ast
import sqlite3
import joblib
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Database path: use the ACTIVITY_DB_PATH (where your "software" table is stored)
ACTIVITY_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")

class IntrusionDetector:
    def __init__(self):
        # Instead of live event collection, we will extract events from the database.
        self.keyboard_events = []
        self.mouse_events = []
        self.focus_events = []
        self.clf = None
        self.scaler = None
        self.model_filename = "intrusion_model.joblib"
        self.anomaly_count = 0

    # ---------------------------------------------------------------
    # DATA EXTRACTION FROM SQLITE DATABASE (ACTIVITY_DB_PATH)
    # ---------------------------------------------------------------
    def _extract_data_by_interval(self, data_type, columns):
        """
        Extract data from the activity SQLite database grouped into 30-second intervals.
        Ensures there are entries for all intervals (even if empty).
        """
        DB_PATH = ACTIVITY_DB_PATH  # Using the activity DB that contains the "software" table.
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get the earliest and latest timestamp in the database.
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM software")
        first_timestamp, last_timestamp = cursor.fetchone()
        if not first_timestamp or not last_timestamp:
            conn.close()
            return []  # No data available

        first_time = datetime.strptime(first_timestamp, "%Y-%m-%d %H:%M:%S")
        last_time = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")

        results = []
        current_time = first_time
        while current_time <= last_time:
            next_time = current_time + timedelta(seconds=30)
            cursor.execute(f"""
                SELECT {", ".join(columns)} FROM software 
                WHERE type = ? AND timestamp >= ? AND timestamp < ?;
            """, (data_type, current_time.strftime("%Y-%m-%d %H:%M:%S"), next_time.strftime("%Y-%m-%d %H:%M:%S")))
            interval_data = cursor.fetchall()
            results.append(interval_data)
            current_time = next_time
        conn.close()
        return results

    def extract_key_data(self):
        return self._extract_data_by_interval("Keyboard", ["key", "key_interval", "timestamp"])

    def extract_mouse_data(self):
        return self._extract_data_by_interval("Click", ["click_type", "click_interval", "position", "timestamp"])

    def extract_focus_data(self):
        return self._extract_data_by_interval("App in Focus", ["duration", "timestamp"])

    # ---------------------------------------------------------------
    # FEATURE EXTRACTION
    # ---------------------------------------------------------------
    def extract_features(self, duration, inference):
        if inference:
            # Read the latest data from the database for each event type.
            key_data = self.extract_key_data()
            mouse_data = self.extract_mouse_data()
            focus_data = self.extract_focus_data()
            # For simplicity, use the first interval for each type
            self.keyboard_events = key_data[0] if key_data and len(key_data) > 0 else []
            self.mouse_events = mouse_data[0] if mouse_data and len(mouse_data) > 0 else []
            self.focus_events = focus_data[0] if focus_data and len(focus_data) > 0 else []

        # --- Keyboard Features ---
        if not self.keyboard_events:
            print("No keyboard events to process.")
            keyboard_features = [0] * 5
        else:
            try:
                typing_speed = (len(self.keyboard_events) / duration) * 60 if duration > 0 else 0
                shortcuts = 0
                backspace = 0
                modifiers = {'Key.ctrl', 'Key.ctrl_l', 'Key.ctrl_r', 'Key.alt', 'Key.alt_l',
                            'Key.alt_r', 'Key.cmd', 'Key.shift', 'Key.shift_l', 'Key.shift_r'}
                values = []
                datetime_data = []
                for event in self.keyboard_events:
                    # event structure: (key, key_interval, timestamp_str)
                    key_val = event[0]
                    if key_val in modifiers:
                        shortcuts += 1
                    if key_val == 'Key.backspace':
                        backspace += 1
                    values.append(event[1])
                    try:
                        timestamp_obj = datetime.strptime(event[2], '%Y-%m-%d %H:%M:%S')
                        datetime_data.append((key_val, event[1], timestamp_obj))
                    except Exception as e:
                        print(f"Error converting keyboard timestamp: {event[2]}. Error: {e}")
                dwell_time = sum(values) / len(values) if values else 0
                time_differences = [ (datetime_data[i][2] - datetime_data[i-1][2]).total_seconds()
                                    for i in range(1, len(datetime_data)) ]
                average_difference = sum(time_differences) / len(time_differences) if time_differences else 0
                keyboard_features = [typing_speed, shortcuts, backspace, dwell_time, average_difference]
            except Exception as e:
                print(f"Error processing keyboard data: {e}")
                keyboard_features = [0] * 5

        # --- Mouse Features ---
        if not self.mouse_events:
            print("No mouse events to process.")
            mouse_features = [0] * 4
        else:
            try:
                click_distances = []
                mouse_speeds = []
                double_clicks = 0
                mouse_intervals = []
                # We'll also convert timestamps from string to epoch seconds for time difference calculations.
                def parse_ts(ts_str):
                    try:
                        return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').timestamp()
                    except Exception as e:
                        print(f"Error parsing mouse timestamp: {ts_str}. Error: {e}")
                        return None

                for i, event in enumerate(self.mouse_events):
                    # event structure: (click_type, click_interval, position_str, timestamp_str)
                    try:
                        # Parse the position from string.
                        position = ast.literal_eval(event[2])
                        if not position or len(position) != 2:
                            continue
                        x, y = position
                        if i > 0:
                            prev_position = ast.literal_eval(self.mouse_events[i-1][2])
                            if prev_position and len(prev_position) == 2:
                                distance = math.sqrt((x - prev_position[0])**2 + (y - prev_position[1])**2)
                                click_distances.append(distance)
                                if event[1] > 0:
                                    mouse_speeds.append(distance / event[1])
                        # For double-click detection, convert timestamps to seconds.
                        curr_ts = parse_ts(event[3])
                        if i > 0:
                            prev_ts = parse_ts(self.mouse_events[i-1][3])
                            if curr_ts is not None and prev_ts is not None and (curr_ts - prev_ts) < 0.5:
                                double_clicks += 1
                        if event[1] > 0:
                            mouse_intervals.append(event[1])
                    except Exception as e:
                        print(f"Error processing mouse event {i+1}: {e}")
                avg_click_distance = sum(click_distances)/len(click_distances) if click_distances else 0
                avg_mouse_speed = np.mean(mouse_speeds) if mouse_speeds else 0
                avg_mouse_interval = sum(mouse_intervals)/len(mouse_intervals) if mouse_intervals else 0
                mouse_features = [avg_click_distance, avg_mouse_speed, double_clicks, avg_mouse_interval]
            except Exception as e:
                print(f"Error processing mouse data: {e}")
                mouse_features = [0] * 4

        # --- Focus Features ---
        if not self.focus_events:
            print("No focus events to process.")
            focus_features = [0] * 3
        else:
            try:
                durations = []
                for item in self.focus_events:
                    # item structure: (duration, timestamp_str)
                    durations.append(item[0])
                switching_rate = len(durations) - 1
                max_duration = max(durations) if durations else 0
                std_dev_duration = np.std(durations) if durations else 0
                focus_features = [switching_rate, max_duration, std_dev_duration]
            except Exception as e:
                print(f"Error processing focus data: {e}")
                focus_features = [0] * 3

        # Combine all features: (keyboard: 5, mouse: 4, focus: 3) = 12 features.
        combined = keyboard_features + mouse_features + focus_features
        # print("Combined Extracted Features (before padding):", combined)
        # If you expect 16 features, pad with zeros.
        if len(combined) < 16:
            combined += [0] * (16 - len(combined))
        # print("Combined Extracted Features (after padding):", combined)
        return combined

    def get_timeframe(self):
        conn = sqlite3.connect(ACTIVITY_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM software")
        result = cursor.fetchone()
        conn.close()
        if result and result[0] and result[1]:
            start_time = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(result[1], "%Y-%m-%d %H:%M:%S")
            return start_time, end_time
        else:
            raise ValueError("No data available in the database.")

    # ---------------------------------------------------------------
    # MODEL TRAINING & INFERENCE
    # ---------------------------------------------------------------
    def train(self):
        if not self.model_filename:
            # Extract the data for training from the sqlite database.
            key_data = self.extract_key_data()
            mouse_data = self.extract_mouse_data()
            focus_data = self.extract_focus_data()
            extracted_features = []
            # Use zip() to iterate over intervals; note that if intervals differ in length,
            # zip() will stop at the shortest. You may wish to aggregate over all intervals.
            for k, m, f in zip(key_data, mouse_data, focus_data):
                self.keyboard_events = k
                self.mouse_events = m
                self.focus_events = f
                features = self.extract_features(inference=False, duration=30)
                extracted_features.append(features)
            # print("Extracted features for training:", extracted_features)
            
            # Convert to numpy array for scaling
            X_train = np.array(extracted_features)
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            # Train IsolationForest
            self.clf = IsolationForest(
                contamination=0.38,
                random_state=42,
                max_samples='auto',
                bootstrap=True,
                n_estimators=200
            )
            self.clf.fit(X_train_scaled)
            # Save the trained model and scaler
            joblib.dump(self.clf, self.model_filename)
            joblib.dump(self.scaler, self.model_filename.replace(".joblib", "_scaler.joblib"))
            print(f"Model saved to {self.model_filename}")
            print(f"Scaler saved to {self.model_filename.replace('.joblib', '_scaler.joblib')}")

    def load_model(self, model_filename="intrusion_model.joblib"):
        try:
            self.clf = joblib.load(model_filename)
            self.scaler = joblib.load(model_filename.replace(".joblib", "_scaler.joblib"))
            print(f"Model loaded from {model_filename}")
            return True
        except FileNotFoundError:
            print(f"Model file {model_filename} not found. Training a new model.")
            return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def run_inference(self, model_filename="intrusion_model.joblib"):
        # Load (or train) the model if needed.
        if not self.load_model(model_filename):
            print("Training a new model as loading failed.")
            self.train()
        print("\n--- Inference Results ---")
        # Instead of looping, we extract features for the latest interval.
        features = self.extract_features(duration=30, inference=True)
        if not features or len(features) == 0:
            raise ValueError("Feature extraction failed: No features generated.")
        # Scale and predict
        inference_scaled = self.scaler.transform([features])
        prediction = self.clf.predict(inference_scaled)
        # Return True if normal (prediction == 1), False if anomaly (prediction == -1)
        return True if prediction[0] == 1 else False

# =============================================================================
# Example usage:
# Since the data is already stored in the SQLite database (ACTIVITY_DB_PATH),
# we do not need to run event listeners. We simply extract the data,
# train the model, and then run inference.
# =============================================================================
if __name__ == "__main__":
    detector = IntrusionDetector()
    
    # Train the model using existing data from ACTIVITY_DB_PATH
    detector.train()
    
    # Run inference
    detector.run_inference()
