"""Inputs for test_health.py: (request, test name) tuples. One snapshot per entry."""
from app.blueprints.health import HEALTH_ENDPOINT
from tests.integration_tests.snapshot_support import BlueprintRequest

CASES: list[tuple[BlueprintRequest, str]] = [
    (BlueprintRequest(method="GET", path=HEALTH_ENDPOINT), "health_ok"),
]
