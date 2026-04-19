from flask import Flask, jsonify
from flask_cors import CORS
from google.api_core.exceptions import GoogleAPICallError

from .api.routes import api_bp
from .config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        return jsonify({"error": str(error), "type": "validation_error"}), 400

    @app.errorhandler(KeyError)
    def handle_key_error(error: KeyError):
        field_name = str(error).strip("'")
        return (
            jsonify(
                {
                    "error": f"Missing required field: {field_name}",
                    "type": "validation_error",
                }
            ),
            400,
        )

    @app.errorhandler(GoogleAPICallError)
    def handle_google_api_error(error: GoogleAPICallError):
        message = getattr(error, "message", None) or str(error)
        status_code = getattr(error, "code", None)
        if not isinstance(status_code, int):
            status_code = 400
        return jsonify({"error": message, "type": "google_api_error"}), status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled application error: %s", error)
        return jsonify({"error": "Internal server error", "type": "server_error"}), 500

    return app
