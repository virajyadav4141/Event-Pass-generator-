# database_setup.py
import psycopg2
import os
from werkzeug.security import generate_password_hash

DATABASE_URL = os.environ.get("DATABASE_URL")

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()

    # ---------------- Users table ----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS "user" (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('admin','worker','client')) NOT NULL
    )
    """)

    # ---------------- Events table ----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS event (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        sponsors TEXT,
        total_passes INTEGER DEFAULT 0,
        qr_width INTEGER DEFAULT 150,
        qr_height INTEGER DEFAULT 150,
        qr_margin INTEGER DEFAULT 10,
        max_uses INTEGER DEFAULT 1
    )
    """)

    # ---------------- Passes table ----------------
    c.execute("""
    CREATE TABLE IF NOT EXISTS pass (
        id SERIAL PRIMARY KEY,
        event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
        code TEXT UNIQUE NOT NULL,
        used_count INTEGER DEFAULT 0
    )
    """)

    # ---------------- Default Admin ----------------
    admin_password = generate_password_hash("admin123")

    c.execute("""
    INSERT INTO "user" (username, password_hash, role)
    VALUES (%s, %s, %s)
    ON CONFLICT (username) DO NOTHING
    """, ("admin", admin_password, "admin"))

    conn.commit()
    c.close()
    conn.close()

    print("Database initialized with default admin: admin/admin123")


if __name__ == "__main__":
    init_db()
