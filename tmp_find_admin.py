import os
import psycopg2
from psycopg2.extras import DictCursor

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found!")
    exit(1)

url = DATABASE_URL.replace("postgres://", "postgresql://")
conn = psycopg2.connect(url, cursor_factory=DictCursor)
c = conn.cursor()

c.execute("SELECT username, role FROM users WHERE role = 'admin'")
admins = c.fetchall()

if admins:
    print("Admins found:")
    for a in admins:
        print(f"- {a['username']}")
else:
    print("No admin users found.")

conn.close()
