import sqlite3
import os

# Path to the SQLite database
db_path = os.path.join(os.path.expanduser("~"), "Documents", "output.sqlite")

# Connect to the SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# SQL command to clear the output table
clear_table_sql = 'DELETE FROM output_summary'

# Execute the SQL command
cursor.execute(clear_table_sql)

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Output table cleared successfully.")