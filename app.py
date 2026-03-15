# app.py

from flask import Flask, send_from_directory
from config import Config
from extensions import mongo, login_manager, mail
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
mongo.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.init_app(app)
mail.init_app(app)

# ------------------ BLUEPRINTS ------------------

# Import blueprints
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.user_routes import user_bp
from routes.main_routes import main_bp  # ✅ Main blueprint for index/homepage

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(main_bp)

# ------------------ ROUTES ------------------

# Serve favicon.ico to avoid 404 errors in browser
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# ------------------ MAIN ------------------

if __name__ == '__main__':
    app.run(debug=True)
