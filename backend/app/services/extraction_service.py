"""Extraction business logic. Takes and returns generated types only; no Flask here."""
import uuid

from app.blueprints.types.generated.document_extraction.models import (
    CreateExtractionRequest,
    CreateExtractionResponse,
)
from app.services import file_storage


class UploadNotFoundError(Exception):
    """Raised when an extraction refers to an upload that does not exist."""


def create_extraction(extraction_request: CreateExtractionRequest) -> CreateExtractionResponse:
    """Submit an uploaded file to the document data extraction system.

    The extraction system is not called in this POC: the identifier is synthetic.
    """
    if not file_storage.object_exists(extraction_request.upload_id):
        raise UploadNotFoundError(f"No upload exists with upload_id {extraction_request.upload_id}")
    return CreateExtractionResponse(extraction_id=str(uuid.uuid4()))
