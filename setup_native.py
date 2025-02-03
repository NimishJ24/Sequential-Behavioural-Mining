import os
import sqlite3
import json
import platform
import shutil

home_dir = os.path.expanduser("~")
db_path = os.path.join(home_dir, "sbm_data", "tab_activity.sqlite")
os.makedirs(os.path.dirname(db_path), exist_ok=True)
native_host_json_path = ""
native_host_script_path = os.path.join(os.getcwd(), "SBM", "native_host.py")

if platform.system() == "Windows":
    native_host_json_path = os.path.join(
        os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data", "NativeMessagingHosts", "sbm_host.json"
    )
elif platform.system() == "Linux":
    native_host_json_path = os.path.join(home_dir, ".config", "google-chrome", "NativeMessagingHosts", "com.sbm.native_host.json")
elif platform.system() == "Darwin":
    native_host_json_path = os.path.join(home_dir, "Library", "Application Support", "Google", "Chrome", "NativeMessagingHosts", "com.sbm.native_host.json")

os.makedirs(os.path.dirname(native_host_json_path), exist_ok=True)

def create_database():
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                entry_time TEXT,
                exit_time TEXT
            )
        """)
        conn.commit()
        conn.close()
        print(f"✅ SQLite database created at: {db_path}")
    else:
        print(f"✅ SQLite database already exists at: {db_path}")

def create_native_host_script():
    native_host_code = """\
import sys
import json
import sqlite3
import logging
logging.basicConfig(filename='native_host.log', level=logging.DEBUG)

DB_PATH = "{db_path}"

def log_activity(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO activity (url, title, entry_time, exit_time) VALUES (?, ?, ?, ?)",
                   (data["url"], data["title"], data["entry_time"], data["exit_time"]))
    conn.commit()
    conn.close()

def read_input():
    try:
        raw_data = sys.stdin.read()
        message = json.loads(raw_data)
        log_activity(message)
        response = json.dumps({{"success": True}})
        sys.stdout.write(response + "\\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(str(e) + "\\n")

if __name__ == "__main__":
    read_input()
""".format(db_path=db_path)

    if not os.path.exists(native_host_script_path):
        with open(native_host_script_path, "w") as f:
            f.write(native_host_code)
        os.chmod(native_host_script_path, 0o755)
        print(f"✅ Native host script created at: {native_host_script_path}")
    else:
        print(f"✅ Native host script already exists at: {native_host_script_path}")

def create_native_host_json():
    extension_id = "fgiajiopnnaiglhakioljbohcemblmop"
    
    native_host_config = {
        "name": "com.sbm.native_host",
        "description": "Saves SQLite file locally",
        "path": native_host_script_path,
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{extension_id}/"
        ]
    }
    
    with open(native_host_json_path, "w") as f:
        json.dump(native_host_config, f, indent=4)
    
    print(f"✅ Native Messaging JSON created at: {native_host_json_path}")

if __name__ == "__main__":
    create_database()
    create_native_host_script()
    create_native_host_json()
    print("🎯 Setup complete! You can now use `native_host.py`.")

current_dir = os.path.dirname(os.path.abspath(__file__))
json_filename = "sbm_host.json"
src_path = os.path.join(current_dir, json_filename)
extension_dir = os.path.join(current_dir, "extension")
dst_path = os.path.join(extension_dir, json_filename)

try:
    shutil.copy(src_path, dst_path)
    print(f"Successfully copied {json_filename} to {extension_dir}")
except Exception as e:
    print(f"Error copying file: {e}")
