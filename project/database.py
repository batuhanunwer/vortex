import sqlite3
import os
import re
from project.config import DATABASE

# Render'da "DATABASE_URL" varsa Postgres kullanır, yoksa SQLite
DATABASE_URL = os.getenv("DATABASE_URL")
PLACEHOLDER = "%s" if DATABASE_URL else "?"

def get_connection():
    if DATABASE_URL:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        # Render bazen postgres:// verir ama psycopg2 postgresql:// bekler
        url = DATABASE_URL.replace("postgres://", "postgresql://")
        conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
        conn.autocommit = True
        return conn
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

def db():
    return get_connection()

def _try_exec(cursor, sql):
    try:
        # SQLite vs Postgres placeholder çevirisi (? -> %s)
        if DATABASE_URL:
            sql = sql.replace("?", "%s")
        cursor.execute(sql)
    except Exception:
        pass

def _has_column(cursor, table, column):
    if DATABASE_URL:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
            (table, column)
        )
        return cursor.fetchone() is not None
    else:
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cursor.fetchall())

def db_kur():
    conn = db()
    c = conn.cursor()

    # Tip dönüşümleri
    pk_auto = "SERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
    text_type = "TEXT"
    ts_default = "CURRENT_TIMESTAMP"

    # Tablo Oluşturma SQL'leri
    tables = [
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {pk_auto},
            username {text_type} UNIQUE NOT NULL,
            password {text_type} NOT NULL,
            email {text_type} UNIQUE,
            banned INTEGER DEFAULT 0,
            role {text_type} DEFAULT 'user',
            profile_pic {text_type} DEFAULT 'default.png',
            created_at TIMESTAMP DEFAULT {ts_default},
            last_seen {text_type} DEFAULT 'Yakın zamanda'
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS messages (
            id {pk_auto},
            sender {text_type} NOT NULL,
            receiver {text_type} NOT NULL,
            content {text_type} NOT NULL,
            timestamp TIMESTAMP DEFAULT {ts_default},
            is_read INTEGER DEFAULT 0,
            edited INTEGER DEFAULT 0,
            edited_at {text_type},
            deleted_by_sender INTEGER DEFAULT 0,
            deleted_by_receiver INTEGER DEFAULT 0,
            attachment {text_type}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS rooms (
            id {pk_auto},
            room_name {text_type} NOT NULL UNIQUE,
            creator {text_type} NOT NULL,
            description {text_type} DEFAULT ''
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS room_members (
            id {pk_auto},
            room_id INTEGER NOT NULL,
            username {text_type} NOT NULL,
            joined_at TIMESTAMP DEFAULT {ts_default},
            UNIQUE(room_id, username)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS room_messages (
            id {pk_auto},
            room_id INTEGER NOT NULL,
            sender {text_type} NOT NULL,
            content {text_type} NOT NULL,
            timestamp TIMESTAMP DEFAULT {ts_default},
            edited INTEGER DEFAULT 0,
            edited_at {text_type}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS vault (
            id {pk_auto},
            user_name {text_type} NOT NULL,
            title {text_type} NOT NULL,
            secret_data {text_type} NOT NULL,
            created_at TIMESTAMP DEFAULT {ts_default}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS announcements (
            id {pk_auto},
            content {text_type} NOT NULL,
            created_by {text_type},
            created_at TIMESTAMP DEFAULT {ts_default}
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id {pk_auto},
            admin_user {text_type} NOT NULL,
            action {text_type} NOT NULL,
            target_user {text_type},
            details {text_type},
            timestamp TIMESTAMP DEFAULT {ts_default}
        )
        """
    ]

    for sql in tables:
        c.execute(sql)

    # Indeksler
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)",
        "CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver)",
        "CREATE INDEX IF NOT EXISTS idx_room_messages_room ON room_messages(room_id)",
        "CREATE INDEX IF NOT EXISTS idx_vault_user ON vault(user_name)"
    ]
    
    for sql in indices:
        try:
            c.execute(sql)
        except Exception:
            pass

    if not DATABASE_URL:
        conn.commit()
    
    conn.close()
    print(f"Veritabanı hazır ({'PostgreSQL' if DATABASE_URL else 'SQLite'}).")
