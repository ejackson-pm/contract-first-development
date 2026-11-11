import pytest
from syrupy.extensions.json import JSONSnapshotExtension

from application import create_app


@pytest.fixture(name="app")
def fixture_app():
    """The production app from create_app(): same blueprints and JSON provider."""
    app = create_app()
    app.config["TESTING"] = True
    yield app


@pytest.fixture(name="client")
def fixture_client(app):
    with app.app_context():
        with app.test_client() as client:
            yield client


@pytest.fixture(name="snapshot_json")
def fixture_snapshot_json(snapshot):
    """Store each snapshot as its own .json file under __snapshots__/<test module>/."""
    return snapshot.with_defaults(extension_class=JSONSnapshotExtension)
