import sqlite3
from project.config import DATABASE


def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _try_exec(cursor, sql):
    try:
        cursor.execute(sql)
    except sqlite3.OperationalError:
        pass


def _has_column(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def db_kur():
    conn = db()
    c = conn.cursor()

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        banned INTEGER DEFAULT 0,
        role TEXT DEFAULT 'user',
        profile_pic TEXT DEFAULT 'default.png',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0,
        edited INTEGER DEFAULT 0,
        edited_at TEXT,
        deleted_by_sender INTEGER DEFAULT 0,
        deleted_by_receiver INTEGER DEFAULT 0,
        attachment TEXT
    )
    """
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT NOT NULL UNIQUE,
        creator TEXT NOT NULL,
        description TEXT DEFAULT ''
    )
    """
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS room_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(room_id, username),
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
    )
    """
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS room_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        sender TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        edited INTEGER DEFAULT 0,
        edited_at TEXT,
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
    )
    """
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS vault (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        title TEXT NOT NULL,
        secret_data TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_user TEXT NOT NULL,
        action TEXT NOT NULL,
        target_user TEXT,
        details TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # Eski veritabanlarına eksik sütunlar
    if not _has_column(c, "rooms", "description"):
        _try_exec(c, "ALTER TABLE rooms ADD COLUMN description TEXT DEFAULT ''")
    if not _has_column(c, "messages", "edited_at"):
        _try_exec(c, "ALTER TABLE messages ADD COLUMN edited_at TEXT")
    if not _has_column(c, "vault", "created_at"):
        _try_exec(c, "ALTER TABLE vault ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    if not _has_column(c, "announcements", "created_by"):
        _try_exec(c, "ALTER TABLE announcements ADD COLUMN created_by TEXT")
    if not _has_column(c, "announcements", "created_at"):
        _try_exec(c, "ALTER TABLE announcements ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    if not _has_column(c, "users", "last_seen"):
        _try_exec(c, "ALTER TABLE users ADD COLUMN last_seen TEXT DEFAULT 'Yakın zamanda'")

    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)"
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver)"
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_room_messages_room ON room_messages(room_id)"
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_vault_user ON vault(user)")

    conn.commit()
    conn.close()
    print("Veritabanı hazır.")
