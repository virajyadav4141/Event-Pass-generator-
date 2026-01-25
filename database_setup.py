# database_setup.py
import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Users table
c.execute('''
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin','worker','client')) NOT NULL
)
''')

# Events table
c.execute('''
CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    sponsors TEXT,
    total_passes INTEGER DEFAULT 0,
    qr_width INTEGER DEFAULT 150,
    qr_height INTEGER DEFAULT 150,
    qr_margin INTEGER DEFAULT 10,
    max_uses INTEGER DEFAULT 1
)
''')

# Passes table
c.execute('''
CREATE TABLE IF NOT EXISTS pass (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    code TEXT UNIQUE NOT NULL,
    used_count INTEGER DEFAULT 0,
    FOREIGN KEY(event_id) REFERENCES event(id)
)
''')

# Create default admin
admin_password = generate_password_hash("admin123")
c.execute("INSERT OR IGNORE INTO user (username, password_hash, role) VALUES (?, ?, ?)",
          ("admin", admin_password, "admin"))

conn.commit()
conn.close()
print("Database initialized with default admin: admin/admin123")
