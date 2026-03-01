from flask import Flask

from config import Config
from routes.main_routes import main_bp
from routes.api_routes import api_bp


def create_app() -> Flask:
    """Application factory for creating Flask app instances."""
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
