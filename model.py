import logging
import random
from datetime import datetime, timedelta
import sqlite3
import os
import ollama

ACTIVITY_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")
TRAINING_DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_training.sqlite")

class IDS:
    def call_ollama_model(self, summary_text, suspicious = True):
        prompt = f"Generate a 1-2 line summary of the following text. NO INTRO OR ANYTHING:\n\n{summary_text}. We made a behavioural analysis model that predicted that the user is {'' if suspicious else 'not '}suspicious."
        try:
            response = ollama.chat(model="llama3:latest", messages=[{"role": "user", "content": prompt}])
            if 'message' in response and 'content' in response['message']:
                result = response['message']['content']
                return result
            else:
                logging.error("Unexpected response structure from Ollama model")
                return ""
        except KeyError as e:
            logging.error(f"KeyError in parsing Ollama response: {e}")
            return ""
        except Exception as e:
            logging.error(f"Error calling Ollama model: {e}")
            return ""
    
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

        n = random.randint(0,100)

        # Filter out rows where the event type is NULL.
        filtered = [row for row in rows if row[0] is not None]

        # Deduplicate repeated events (a simple approach: remove consecutive events that have the same type and title)
        deduped = []
        prev = None
        for row in filtered:
            if prev is None or (row[0], row[1]) != (prev[0], prev[1]):
                deduped.append(row)
                prev = row

        # Prepare the summary text. (This string would be sent to your Ollama model.)
        summary_lines = [f"{event_type} at {timestamp}" for event_type, title, timestamp in deduped]
        summary_text = "\n".join(summary_lines)
        
        # For this example, we just log the summary.
        print(f"Summary for past 30 seconds:\n{summary_text}")
        result = self.call_ollama_model(summary_text, n)
        print(result)
        
        return n
    
    def train():
        print("helo")