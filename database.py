import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'ca_portal.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    
    cursor = conn.cursor()

    # Safely migration check for fee_amount and payment_status in appointments
    cursor.execute("PRAGMA table_info(appointments)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'fee_amount' not in columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN fee_amount REAL DEFAULT 0.0")
    if 'payment_status' not in columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN payment_status TEXT DEFAULT 'Unpaid'")

    # Migration check for users (pan_number, gstin_number)
    cursor.execute("PRAGMA table_info(users)")
    u_cols = [c[1] for c in cursor.fetchall()]
    if 'pan_number' not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN pan_number TEXT")
    if 'gstin_number' not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN gstin_number TEXT")

    # Migration check for appointment_documents (is_approved, approved_at)
    cursor.execute("PRAGMA table_info(appointment_documents)")
    d_cols = [c[1] for c in cursor.fetchall()]
    if 'is_approved' not in d_cols:
        cursor.execute("ALTER TABLE appointment_documents ADD COLUMN is_approved INTEGER DEFAULT 0")
    if 'approved_at' not in d_cols:
        cursor.execute("ALTER TABLE appointment_documents ADD COLUMN approved_at TIMESTAMP")


    # Seed default CA accounts if empty
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'ca'")
    ca_count = cursor.fetchone()[0]
    
    if ca_count == 0:
        default_cas = [
            ("CA Rajesh Sharma", "ca.rajesh@example.com", generate_password_hash("password123"), "ca", "+91 9876543210", "Corporate Tax & GST Audit"),
            ("CA Priya Mehta", "ca.priya@example.com", generate_password_hash("password123"), "ca", "+91 9812345678", "Income Tax & Financial Planning"),
            ("CA Amit Verma", "ca.amit@example.com", generate_password_hash("password123"), "ca", "+91 9988776655", "Company Registration & Startup Advisory")
        ]
        cursor.executemany("""
            INSERT INTO users (name, email, password_hash, role, phone, specialization)
            VALUES (?, ?, ?, ?, ?, ?)
        """, default_cas)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
