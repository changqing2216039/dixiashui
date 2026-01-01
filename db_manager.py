import sqlite3
import hashlib
import json
import os
from datetime import datetime

# Database path configuration for deployment persistence
# If /app/data exists (e.g., mounted volume in Zeabur/Docker), use it.
# Otherwise, use local directory.
DATA_DIR = "/app/data"
if os.path.exists(DATA_DIR) and os.access(DATA_DIR, os.W_OK):
    DB_NAME = os.path.join(DATA_DIR, "water_env.db")
else:
    DB_NAME = "water_env.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Create users table
    # Added role and status for admin features
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Create calculations table
    c.execute('''CREATE TABLE IF NOT EXISTS calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    project_name TEXT,
                    model_type TEXT,
                    parameters TEXT,
                    results TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')
    
    # Create payments table for revenue tracking
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    payment_method TEXT,
                    transaction_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')

    # Create system_settings table for admin config
    c.execute('''CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )''')
    
    conn.commit()
    conn.close()
    
    # Run migrations to ensure existing tables have new columns
    check_migrations()
    
    # Ensure at least one admin exists
    ensure_admin_exists()

def check_migrations():
    """Add new columns to existing tables if they don't exist"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Check users table columns
    try:
        c.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in c.fetchall()]
        
        # Helper to safe add column
        def safe_add_column(table, col_name, col_type):
            if col_name not in columns:
                try:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                    print(f"Added column {col_name} to {table}")
                except sqlite3.OperationalError as e:
                    # Ignore duplicate column errors or other non-critical issues
                    if "duplicate column name" in str(e):
                        pass
                    else:
                        print(f"Error adding column {col_name}: {e}")

        safe_add_column('users', 'role', "TEXT DEFAULT 'user'")
        safe_add_column('users', 'status', "TEXT DEFAULT 'active'")
        # For created_at, older sqlite might fail on non-constant default. 
        # We try with default, if fail, add as TEXT/TIMESTAMP without default.
        try:
             safe_add_column('users', 'created_at', "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except:
             # If safe_add_column failed internally (printed error), try fallback
             safe_add_column('users', 'created_at', "TEXT")
        
        conn.commit()
    except Exception as e:
        print(f"Migration check failed: {e}")
    finally:
        conn.close()

def ensure_admin_exists():
    """Create a default admin user if no admin exists"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM users WHERE role = 'admin'")
    if c.fetchone()[0] == 0:
        # Create default admin: admin / admin123
        admin_pass = hash_password("admin123")
        try:
            c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                      ("admin", admin_pass, "admin"))
            conn.commit()
            print("Default admin account created: admin / admin123")
        except sqlite3.IntegrityError:
            pass # Username might exist as a normal user
            
            # If 'admin' exists but is not admin role, upgrade it
            c.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
            conn.commit()
            
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                  (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, password_hash, role, status FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    
    result = None
    if user:
        if user[3] == 'banned': # Check status
            conn.close()
            return None # Or handled specifically
        if user[1] == hash_password(password):
            result = {"id": user[0], "role": user[2]}
            
            # Update login stats
            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("UPDATE users SET login_count = COALESCE(login_count, 0) + 1, last_login_at = ? WHERE id = ?", (now, user[0]))
                conn.commit()
            except Exception as e:
                print(f"Failed to update login stats: {e}")
                
    conn.close()
    return result

def save_calculation(user_id, project_name, model_type, params, results):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO calculations (user_id, project_name, model_type, parameters, results) VALUES (?, ?, ?, ?, ?)",
              (user_id, project_name, model_type, json.dumps(params), json.dumps(results)))
    conn.commit()
    conn.close()

def get_user_calculations(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, project_name, model_type, created_at FROM calculations WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_calculation_detail(calc_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM calculations WHERE id = ?", (calc_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "user_id": row[1],
            "project_name": row[2],
            "model_type": row[3],
            "parameters": json.loads(row[4]),
            "results": json.loads(row[5]),
            "created_at": row[6]
        }
    return None

# --- Admin & Payment Functions ---

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, username, role, status, created_at FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def update_user_status(user_id, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()

def create_payment(user_id, amount, method, trans_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id, amount, payment_method, transaction_id) VALUES (?, ?, ?, ?)",
              (user_id, amount, method, trans_id))
    conn.commit()
    conn.close()

def get_all_payments():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT p.id, u.username, p.amount, p.payment_method, p.transaction_id, p.status, p.created_at 
        FROM payments p 
        JOIN users u ON p.user_id = u.id 
        ORDER BY p.created_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def update_payment_status(payment_id, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
    conn.commit()
    conn.close()

def get_system_setting(key, default=""):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_system_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# --- User Info & Usage Functions ---

def get_user_full_info(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username, usage_left, login_count, created_at, last_login_at FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    
    # Get purchase count (approved payments)
    c.execute("SELECT count(*) FROM payments WHERE user_id = ? AND status = 'approved'", (user_id,))
    purchase_count = c.fetchone()[0]
    
    conn.close()
    
    if row:
        return {
            "username": row[0],
            "usage_left": row[1] if row[1] is not None else 0,
            "login_count": row[2] if row[2] is not None else 0,
            "created_at": row[3],
            "last_login_at": row[4],
            "purchase_count": purchase_count
        }
    return None

def consume_usage(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Check current usage
    c.execute("SELECT usage_left FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    
    if row and row[0] is not None and row[0] > 0:
        c.execute("UPDATE users SET usage_left = usage_left - 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def admin_update_usage(user_id, delta):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Ensure usage doesn't go below 0
    c.execute("UPDATE users SET usage_left = MAX(0, COALESCE(usage_left, 0) + ?) WHERE id = ?", (delta, user_id))
    conn.commit()
    conn.close()
