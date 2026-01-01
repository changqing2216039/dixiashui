import sqlite3
import os

DB_NAME = "water_env.db"

if os.path.exists(DB_NAME):
    print(f"Database found: {os.path.abspath(DB_NAME)}")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(users)")
        columns = c.fetchall()
        print("Columns in users table:")
        for col in columns:
            print(col)
            
        col_names = [info[1] for info in columns]
        print(f"Column names list: {col_names}")
        
        if 'created_at' not in col_names:
            print("created_at NOT found in columns")
        else:
            print("created_at FOUND in columns")
            
    except Exception as e:
        print(f"Error inspecting DB: {e}")
    finally:
        conn.close()
else:
    print("Database file not found.")
