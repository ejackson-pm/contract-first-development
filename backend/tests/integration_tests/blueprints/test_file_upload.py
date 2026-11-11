"""Snapshot tests for the file upload blueprint. Inputs live in file_upload_cases.py."""
import pytest
from syrupy.matchers import path_type

from tests.integration_tests.blueprints.file_upload_cases import CASES
from tests.integration_tests.snapshot_support import BlueprintRequest, run_request

# upload_id is a fresh UUID on every run: snapshot its type, not its value.
DYNAMIC_FIELDS = path_type({"body.upload_id": (str,)})


@pytest.fixture(name="run_blueprint")
def fixture_run_blueprint(client):
    """Return a callable that runs one request case."""

    def _run(case: BlueprintRequest) -> dict:
        return run_request(client, case)

    return _run


@pytest.mark.parametrize(
    "case",
    [case for case, _ in CASES],
    ids=[name for _, name in CASES],
)
def test_file_upload_blueprint(case, run_blueprint, snapshot_json):
    assert run_blueprint(case) == snapshot_json(matcher=DYNAMIC_FIELDS)
