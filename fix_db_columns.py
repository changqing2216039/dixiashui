import sqlite3
import os

DB_NAME = "water_env.db"

def fix_database_columns():
    print(f"Checking database: {DB_NAME}")
    if not os.path.exists(DB_NAME):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Get current columns
    c.execute("PRAGMA table_info(users)")
    current_cols = [row[1] for row in c.fetchall()]
    print(f"Current columns in 'users': {current_cols}")
    
    # Columns to ensure exist
    columns_to_add = [
        ('usage_left', 'INTEGER DEFAULT 0'),
        ('login_count', 'INTEGER DEFAULT 0'),
        ('last_login_at', 'TIMESTAMP'),
        ('role', "TEXT DEFAULT 'user'"),
        ('status', "TEXT DEFAULT 'active'"),
        ('created_at', "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]
    
    for col_name, col_def in columns_to_add:
        if col_name not in current_cols:
            print(f"Adding missing column: {col_name}")
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                print(f"Successfully added {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
                # Fallback for some sqlite versions regarding default values
                if "default" in str(e).lower():
                    try:
                        print(f"Retrying {col_name} without default...")
                        col_type = col_def.split()[0] # Just the type
                        c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                        print(f"Successfully added {col_name} (fallback)")
                    except Exception as e2:
                        print(f"Fallback failed for {col_name}: {e2}")
        else:
            print(f"Column '{col_name}' already exists.")
            
    conn.commit()
    conn.close()
    print("Database fix completed.")

if __name__ == "__main__":
    fix_database_columns()
