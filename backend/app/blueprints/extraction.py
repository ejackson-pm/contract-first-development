"""Extraction blueprint. Request/response types are generated from openapi/document_extraction.yaml."""
import logging
import os

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

# Generated types: read the package docstring for usage rules (strict types, dates, aliases).
from app.blueprints.types.generated.document_extraction.models import (
    CreateExtractionRequest,
    CreateExtractionResponse,
    ErrorResponse,
)
from app.services.extraction_service import UploadNotFoundError, create_extraction

LOGGER = logging.getLogger(os.environ["PM_APP_NAME"])

CREATE_EXTRACTION_ENDPOINT = "/api/document-extraction/v1/create-extraction"
EXTRACTION_API = Blueprint("extraction_api", __name__)


@EXTRACTION_API.post(CREATE_EXTRACTION_ENDPOINT)
def post_create_extraction():
    """Submit an uploaded file for data extraction.

    Returns 201 with a CreateExtractionResponse, 400 with an ErrorResponse when the
    body does not match CreateExtractionRequest, or 404 when the upload does not exist.
    """
    try:
        extraction_request = CreateExtractionRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        LOGGER.info("Invalid create extraction request: %s", e.errors(include_input=False))
        return jsonify(ErrorResponse(error="Invalid request body")), 400

    try:
        extraction_response: CreateExtractionResponse = create_extraction(extraction_request)
    except UploadNotFoundError as e:
        return jsonify(ErrorResponse(error=str(e))), 404

    return jsonify(extraction_response), 201
