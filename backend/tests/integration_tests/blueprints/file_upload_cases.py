"""Inputs for test_file_upload.py: (request, test name) tuples. One snapshot per entry."""
from typing import Optional

from app.blueprints.file_upload import FILE_UPLOAD_ENDPOINT
from tests.integration_tests.snapshot_support import BlueprintRequest, UploadFile

SAMPLE_PDF = UploadFile(
    filename="statement.pdf",
    content=b"%PDF-1.4\n% synthetic test document\n%%EOF\n",
    content_type="application/pdf",
)
SAMPLE_TEXT = UploadFile(
    filename="notes.txt",
    content=b"not a pdf",
    content_type="text/plain",
)


def post_file_upload(file: Optional[UploadFile]) -> BlueprintRequest:
    return BlueprintRequest(method="POST", path=FILE_UPLOAD_ENDPOINT, file=file)


CASES: list[tuple[BlueprintRequest, str]] = [
    # Success modes
    (post_file_upload(SAMPLE_PDF), "pdf_upload_success"),
    # Failure modes checked by the handler (the multipart body has no generated type)
    (post_file_upload(None), "rejects_missing_file"),
    (post_file_upload(SAMPLE_TEXT), "rejects_non_pdf_file"),
]
