"""File upload business logic. Returns generated types only; no Flask here."""
import uuid

from app.blueprints.types.generated.document_extraction.models import FileUploadResponse
from app.services import file_storage


def upload_pdf(content: bytes) -> FileUploadResponse:
    """Store a PDF and return the identifier the client uses to refer to it."""
    upload_id = str(uuid.uuid4())
    file_storage.put_object(upload_id, content)
    return FileUploadResponse(upload_id=upload_id)
