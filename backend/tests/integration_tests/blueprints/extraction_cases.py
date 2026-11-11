"""Inputs for test_extraction.py: (request, test name) tuples. One snapshot per entry."""
from app.blueprints.extraction import CREATE_EXTRACTION_ENDPOINT
from app.blueprints.types.generated.document_extraction.models import CreateExtractionRequest
from tests.integration_tests.snapshot_support import BlueprintRequest

# The run_blueprint fixture stores a file under this key before each case runs.
EXISTING_UPLOAD_ID = "existing-upload"
MISSING_UPLOAD_ID = "missing-upload"


def post_create_extraction(body: CreateExtractionRequest) -> BlueprintRequest:
    return BlueprintRequest(method="POST", path=CREATE_EXTRACTION_ENDPOINT, body=body)


CASES: list[tuple[BlueprintRequest, str]] = [
    # Success modes
    (post_create_extraction(CreateExtractionRequest(upload_id=EXISTING_UPLOAD_ID)), "extraction_success"),
    # Failure modes driven by state (not input validation)
    (post_create_extraction(CreateExtractionRequest(upload_id=MISSING_UPLOAD_ID)), "rejects_unknown_upload"),
]
