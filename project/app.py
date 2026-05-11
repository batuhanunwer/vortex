import os

from flask import Flask, session

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

from config import (
    SECRET_KEY,
    UPLOAD_FOLDER,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SECURE,
    SESSION_COOKIE_SAMESITE,
    MAX_CONTENT_LENGTH,
    PERMANENT_SESSION_LIFETIME,
    DEBUG,
)
from database import db_kur

from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.messages import messages_bp
from routes.groups import groups_bp
from routes.vault import vault_bp
from routes.admin import admin_bp

from socketio_instance import socketio
import socket_events

app = Flask(__name__, template_folder='../templates', static_folder='../static')
socketio.init_app(app)

app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SESSION_COOKIE_HTTPONLY"] = SESSION_COOKIE_HTTPONLY
app.config["SESSION_COOKIE_SECURE"] = SESSION_COOKIE_SECURE
app.config["SESSION_COOKIE_SAMESITE"] = SESSION_COOKIE_SAMESITE
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["PERMANENT_SESSION_LIFETIME"] = PERMANENT_SESSION_LIFETIME


@app.before_request
def _session_defaults():
    session.permanent = True

@app.context_processor
def inject_unread():
    if "user" in session:
        from database import db
        conn = db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as c FROM messages WHERE receiver=? AND is_read=0", (session["user"],))
        count = c.fetchone()["c"]
        conn.close()
        return dict(msg_count=count)
    return dict(msg_count=0)

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db_kur()

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(groups_bp)
app.register_blueprint(vault_bp)
app.register_blueprint(admin_bp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=DEBUG, allow_unsafe_werkzeug=True)
