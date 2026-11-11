import logging

from flask import Flask

from app.blueprints.extraction import EXTRACTION_API
from app.blueprints.file_upload import FILE_UPLOAD_API
from app.blueprints.health import HEALTH_API
from app.utils.json_provider import PMJSONProvider


def create_app() -> Flask:
    app = Flask(__name__)
    app.json = PMJSONProvider(app)  # ISO 8601 dates and Pydantic models for every jsonify response
    app.register_blueprint(HEALTH_API)
    app.register_blueprint(FILE_UPLOAD_API)
    app.register_blueprint(EXTRACTION_API)
    return app


app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Bind to localhost only; this POC is never exposed beyond your machine.
    app.run(host="127.0.0.1", port=5000, debug=True)
