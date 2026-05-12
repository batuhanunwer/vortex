import sqlite3
import os
from project.config import DATABASE

# Render'da "DATABASE_URL" varsa Postgres kullanır, yoksa SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

def db_sorgu_temizle(sql):
    if DATABASE_URL:
        return sql.replace("?", "%s")
    return sql

def get_connection():
    if DATABASE_URL:
        import psycopg2
        from psycopg2.extras import DictCursor
        url = DATABASE_URL.replace("postgres://", "postgresql://")
        conn = psycopg2.connect(url, cursor_factory=DictCursor)
        conn.autocommit = True
        return conn
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

class CursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
    def execute(self, sql, params=()):
        return self.cursor.execute(db_sorgu_temizle(sql), params)
    def fetchone(self):
        return self.cursor.fetchone()
    def fetchall(self):
        return self.cursor.fetchall()
    @property
    def lastrowid(self):
        return getattr(self.cursor, 'lastrowid', 0)
    def __getattr__(self, name):
        return getattr(self.cursor, name)
    def __iter__(self):
        return iter(self.cursor)

class ConnWrapper:
    def __init__(self, conn):
        self.conn = conn
    def cursor(self):
        return CursorWrapper(self.conn.cursor())
    def commit(self):
        if not DATABASE_URL: self.conn.commit()
    def close(self):
        self.conn.close()
    def __getattr__(self, name):
        return getattr(self.conn, name)

def db():
    return ConnWrapper(get_connection())

def db_kur():
    conn = get_connection()
    c = conn.cursor()
    pk = "SERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
    tables = [
        f"CREATE TABLE IF NOT EXISTS users (id {pk}, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, email TEXT UNIQUE, banned INTEGER DEFAULT 0, role TEXT DEFAULT 'user', profile_pic TEXT DEFAULT 'default.png', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_seen TEXT DEFAULT 'Yakın zamanda')",
        f"CREATE TABLE IF NOT EXISTS messages (id {pk}, sender TEXT NOT NULL, receiver TEXT NOT NULL, content TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_read INTEGER DEFAULT 0, edited INTEGER DEFAULT 0, edited_at TEXT, deleted_by_sender INTEGER DEFAULT 0, deleted_by_receiver INTEGER DEFAULT 0, attachment TEXT)",
        f"CREATE TABLE IF NOT EXISTS rooms (id {pk}, room_name TEXT NOT NULL UNIQUE, creator TEXT NOT NULL, description TEXT DEFAULT '')",
        f"CREATE TABLE IF NOT EXISTS room_members (id {pk}, room_id INTEGER NOT NULL, username TEXT NOT NULL, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(room_id, username))",
        f"CREATE TABLE IF NOT EXISTS room_messages (id {pk}, room_id INTEGER NOT NULL, sender TEXT NOT NULL, content TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, edited INTEGER DEFAULT 0, edited_at TEXT)",
        f"CREATE TABLE IF NOT EXISTS vault (id {pk}, user_name TEXT NOT NULL, title TEXT NOT NULL, secret_data TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS announcements (id {pk}, content TEXT NOT NULL, created_by TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        f"CREATE TABLE IF NOT EXISTS admin_logs (id {pk}, admin_user TEXT NOT NULL, action TEXT NOT NULL, target_user TEXT, details TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    ]
    for sql in tables: c.execute(sql)
    for idx in ["idx_msg_s","idx_msg_r","idx_rmsg_r","idx_vlt_u"]:
        t, c_name = ("messages","sender") if "msg_s" in idx else (("messages","receiver") if "msg_r" in idx else (("room_messages","room_id") if "rmsg" in idx else ("vault","user_name")))
        try: c.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {t}({c_name})")
        except: pass
    if not DATABASE_URL: conn.commit()
    conn.close()
    print("Veritabanı hazır.")
