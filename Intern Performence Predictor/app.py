import os
from flask import Flask

from database import init_db
from auth_routes import auth_bp
from admin_routes import admin_bp
from intern_routes import intern_bp


def create_app() -> Flask:
    """
    Application factory that creates and configures the Flask app.
    This is a common industry-standard pattern and makes testing easier.
    """
    app = Flask(__name__)
    app.secret_key = (
        "your_super_secret_key"  # TODO: move to environment variable in production
    )

    # Configuration for file uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Initialise database and schema
    init_db()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(intern_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

