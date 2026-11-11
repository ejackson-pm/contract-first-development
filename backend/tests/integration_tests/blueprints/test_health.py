"""Snapshot tests for the health blueprint. Inputs live in health_cases.py."""
import pytest

from tests.integration_tests.blueprints.health_cases import CASES
from tests.integration_tests.snapshot_support import BlueprintRequest, run_request


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
def test_health_blueprint(case, run_blueprint, snapshot_json):
    assert run_blueprint(case) == snapshot_json
