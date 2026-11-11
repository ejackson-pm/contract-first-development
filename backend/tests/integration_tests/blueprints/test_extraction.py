"""Snapshot tests for the extraction blueprint. Inputs live in extraction_cases.py."""
import pytest
from syrupy.matchers import path_type

from app.services import file_storage
from tests.integration_tests.blueprints.extraction_cases import CASES, EXISTING_UPLOAD_ID
from tests.integration_tests.snapshot_support import BlueprintRequest, run_request

# extraction_id is a fresh UUID on every run: snapshot its type, not its value.
DYNAMIC_FIELDS = path_type({"body.extraction_id": (str,)})


@pytest.fixture(name="run_blueprint")
def fixture_run_blueprint(client):
    """Store the upload the success case refers to, then return a callable that runs one case."""
    file_storage.put_object(EXISTING_UPLOAD_ID, b"%PDF-1.4\n%%EOF\n")

    def _run(case: BlueprintRequest) -> dict:
        return run_request(client, case)

    return _run


@pytest.mark.parametrize(
    "case",
    [case for case, _ in CASES],
    ids=[name for _, name in CASES],
)
def test_extraction_blueprint(case, run_blueprint, snapshot_json):
    assert run_blueprint(case) == snapshot_json(matcher=DYNAMIC_FIELDS)
