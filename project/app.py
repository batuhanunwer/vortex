import os
from flask import Flask, render_template
from project.config import SECRET_KEY
from project.database import db_kur
from project.socketio_instance import socketio

# App instance
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Initialize SocketIO with app
socketio.init_app(app, async_mode='gevent')

# Database Initialization
with app.app_context():
    db_kur()

# Blueprints
from project.routes.auth import auth_bp
from project.routes.dashboard import dashboard_bp
from project.routes.messages import messages_bp
from project.routes.groups import groups_bp
from project.routes.vault import vault_bp
from project.routes.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(groups_bp)
app.register_blueprint(vault_bp)
app.register_blueprint(admin_bp)

# Socket events (must be imported AFTER socketio.init_app)
import project.socket_events

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
