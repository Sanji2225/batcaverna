from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)

    CORS(app)
    from .routes.optimizer import optimizer_bp
    app.register_blueprint(optimizer_bp, url_prefix='/api/optimizer')

    return app