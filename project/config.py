import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
FLASK_ENV = os.getenv("FLASK_ENV", "development")

DATABASE = os.path.join(BASE_DIR, "users.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

VAULT_PASSPHRASE = os.getenv("VAULT_KEY", "dev-vault-passphrase-change-me")

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = FLASK_ENV == "production"
SESSION_COOKIE_SAMESITE = "Lax"
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

DEBUG = FLASK_ENV == "development"
