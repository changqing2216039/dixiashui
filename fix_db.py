import sqlite3
import os
import sys

DB_NAME = "water_env.db"

def fix_database():
    print(f"Opening {DB_NAME}...")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Check current columns
        c.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in c.fetchall()]
        print(f"Existing columns: {cols}")
        
        if 'created_at' not in cols:
            print("Attempting to add 'created_at'...")
            try:
                # Try simple first
                c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("SUCCESS: Added created_at")
            except Exception as e:
                print(f"ERROR adding created_at: {e}")
                # Fallback without default?
                try:
                    c.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
                    print("SUCCESS: Added created_at as TEXT (fallback)")
                except Exception as e2:
                     print(f"ERROR adding created_at fallback: {e2}")
        else:
            print("'created_at' already exists.")
            
        conn.commit()
        
    except Exception as e:
        print(f"General Error: {e}")
    finally:
        conn.close()
        print("Done.")

if __name__ == "__main__":
    fix_database()
