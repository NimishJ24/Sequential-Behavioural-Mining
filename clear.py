import sqlite3
import os

# Define the SQLite database path
DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "activity.sqlite")

def clear_database():
    if not os.path.exists(DB_PATH):
        print("Database file does not exist.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Delete data from all tables
    for table in tables:
        cursor.execute(f"DELETE FROM {table[0]};")
    
    conn.commit()
    conn.close()
    
    print("Database cleared successfully.")

if __name__ == "__main__":
    clear_database()
