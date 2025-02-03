# import sys
# import json
# import sqlite3

# DB_PATH = "C:\Users\tarus\Documents\tab_activity.sqlite"

# def log_activity(data):
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     cursor.execute("INSERT INTO activity (url, title, entry_time, exit_time) VALUES (?, ?, ?, ?)",
#                    (data["url"], data["title"], data["entry_time"], data["exit_time"]))
#     conn.commit()
#     conn.close()

# def read_input():
#     try:
#         raw_data = sys.stdin.read()
#         message = json.loads(raw_data)
#         log_activity(message)
#         response = json.dumps({"success": True})
#         sys.stdout.write(response + "\n")
#         sys.stdout.flush()
#     except Exception as e:
#         sys.stderr.write(str(e) + "\n")

# if __name__ == "__main__":
#     read_input()


import sys
import json

def read_input():
    input_data = sys.stdin.read()
    return json.loads(input_data) if input_data else {}

def send_response(response):
    message = json.dumps(response)
    sys.stdout.write(message)
    sys.stdout.flush()

def main():
    data = read_input()
    print(f"Received: {data}")
    send_response({"success": True, "message": "Received data successfully"})

if __name__ == "__main__":
    main()
