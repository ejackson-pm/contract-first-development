"""Health blueprint. The response type is generated from openapi/document_extraction.yaml."""
from flask import Blueprint, jsonify

from app.blueprints.types.generated.document_extraction.models import HealthResponse

HEALTH_ENDPOINT = "/api/document-extraction/v1/health"
HEALTH_API = Blueprint("health_api", __name__)


@HEALTH_API.get(HEALTH_ENDPOINT)
def get_health():
    """Liveness check: returns 200 while the API is running."""
    return jsonify(HealthResponse(status="ok"))
