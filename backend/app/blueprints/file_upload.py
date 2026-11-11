"""File upload blueprint. Response types are generated from openapi/document_extraction.yaml."""
from flask import Blueprint, jsonify, request

# Generated types: read the package docstring for usage rules (strict types, dates, aliases).
from app.blueprints.types.generated.document_extraction.models import ErrorResponse, FileUploadResponse
from app.services.file_upload_service import upload_pdf

FILE_UPLOAD_ENDPOINT = "/api/document-extraction/v1/file-upload"
FILE_UPLOAD_API = Blueprint("file_upload_api", __name__)


@FILE_UPLOAD_API.post(FILE_UPLOAD_ENDPOINT)
def post_file_upload():
    """Upload one PDF, sent as multipart/form-data in the `file` field.

    Returns 201 with a FileUploadResponse, or 400 with an ErrorResponse when the
    file is missing or is not a PDF. The multipart body has no generated type, so
    the handler checks it by hand.
    """
    file = request.files.get("file")
    if file is None:
        return jsonify(ErrorResponse(error="The 'file' field is required")), 400
    if file.mimetype != "application/pdf":
        return jsonify(ErrorResponse(error="The file must be a PDF")), 400

    upload_response: FileUploadResponse = upload_pdf(file.read())
    return jsonify(upload_response), 201
