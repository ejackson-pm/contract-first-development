# Lightweight REST API POC: Setup Tutorial

This tutorial walks you through building a minimal Flask REST API that follows the same shape as PolicyMe's `template-pm-restapi` (application factory, blueprints, thin service layer, separate tests) without any of the deployment, auth, secrets, or telemetry machinery.

The result is a local-only demonstration repository. It is never deployed, uses in-memory synthetic data, and binds to localhost only.

## What you'll build

```text
poc-restapi/
├── application.py
├── requirements.txt
├── pytest.ini
├── .gitignore
├── README.md
├── app/
│   ├── __init__.py
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── example.py
│   └── services/
│       ├── __init__.py
│       └── example_service.py
└── tests/
    ├── __init__.py
    └── test_example.py
```

This is the structure from the earlier outline plus a small `health.py` blueprint, which mirrors the template's health endpoint and gives you an instant "is it running?" check.

### Purpose of each file


| Path                              | Purpose                                                                                               |
| --------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `application.py`                  | Entry point. Defines `create_app()` (the application factory) and registers blueprints.               |
| `app/blueprints/health.py`        | `GET /api/health`, a simple liveness check.                                                           |
| `app/blueprints/example.py`       | The demo endpoints. Handles HTTP concerns only: parsing the request, returning status codes and JSON. |
| `app/services/example_service.py` | The behaviour being demonstrated. No Flask imports, so it stays easy to test and reuse.               |
| `tests/test_example.py`           | Exercises the API through Flask's test client.                                                        |
| `requirements.txt`                | Two dependencies: Flask and pytest.                                                                   |
| `pytest.ini`                      | Tells pytest where the project root is so `import app` works.                                         |


## Prerequisites

* Python 3.10 or newer
* `git` (optional, for version control)
* A terminal and a text editor

## Step 1: Create the project and virtual environment

```bash
mkdir poc-restapi && cd poc-restapi
python3 -m venv .venv
```

Activate the environment:

```bash
source .venv/bin/activate
```

## Step 2: Create the folder structure

From inside `poc-restapi/`:

```bash
mkdir -p app/blueprints app/services tests
touch app/__init__.py app/blueprints/__init__.py app/services/__init__.py tests/__init__.py
touch application.py requirements.txt pytest.ini .gitignore README.md
touch app/blueprints/health.py app/blueprints/example.py
touch app/services/example_service.py tests/test_example.py
```

Verify the layout:

```bash
find . -path ./.venv -prune -o -type f -print | sort
```

## Step 3: Add dependencies

`requirements.txt`:

```text
Flask>=3.0,<4
pytest>=8.0
```

Install them:

```bash
pip install -r requirements.txt
```

`pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

`.gitignore`:

```text
.venv/
__pycache__/
.pytest_cache/
*.pyc
```

## Step 4: Write the service layer

`app/services/example_service.py` holds the logic and an in-memory data store. Keeping it free of Flask imports is the main design habit worth demonstrating.

```python
"""Demo business logic backed by an in-memory store (synthetic data only)."""

_items: dict[int, dict] = {}


def reset_items() -> None:
    """Restore the seed data. Used at start-up and by tests."""
    _items.clear()
    _items[1] = {"id": 1, "name": "First example"}
    _items[2] = {"id": 2, "name": "Second example"}


def list_items() -> list[dict]:
    return list(_items.values())


def get_item(item_id: int) -> dict | None:
    return _items.get(item_id)


def create_item(name: str) -> dict:
    new_id = max(_items, default=0) + 1
    item = {"id": new_id, "name": name}
    _items[new_id] = item
    return item


reset_items()
```

## Step 5: Write the blueprints

`app/blueprints/health.py`:

```python
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.get("/health")
def health():
    return jsonify(status="ok")
```

`app/blueprints/example.py`:

```python
from flask import Blueprint, jsonify, request

from app.services import example_service

example_bp = Blueprint("example", __name__, url_prefix="/api/examples")


@example_bp.get("")
def list_examples():
    return jsonify(example_service.list_items())


@example_bp.get("/<int:item_id>")
def get_example(item_id: int):
    item = example_service.get_item(item_id)
    if item is None:
        return jsonify(error="Not found"), 404
    return jsonify(item)


@example_bp.post("")
def create_example():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify(error="'name' is required"), 400
    return jsonify(example_service.create_item(name.strip())), 201
```

Validation is hand-rolled here to keep dependencies minimal. The production template uses Pydantic models for this; see "Optional next steps" if you want to demonstrate that.

## Step 6: Write the application factory

`application.py`:

```python
from flask import Flask

from app.blueprints.example import example_bp
from app.blueprints.health import health_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(example_bp)
    return app


app = create_app()

if __name__ == "__main__":
    # Bind to localhost only; this POC is never exposed beyond your machine.
    app.run(host="127.0.0.1", port=5000, debug=True)
```

Why a factory? It lets tests build a fresh app instance and mirrors how the template is organized.

## Step 7: Run it

```bash
python application.py
```

In a second terminal:

```bash
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/examples
curl http://127.0.0.1:5000/api/examples/1
curl -X POST http://127.0.0.1:5000/api/examples \
  -H "Content-Type: application/json" \
  -d '{"name": "Third example"}'
```

Expected results:


| Request                          | Status | Body                              |
| -------------------------------- | ------ | --------------------------------- |
| `GET /api/health`                | 200    | `{"status": "ok"}`                |
| `GET /api/examples`              | 200    | List of two seeded items          |
| `GET /api/examples/999`          | 404    | `{"error": "Not found"}`          |
| `POST /api/examples` with a name | 201    | The new item with `"id": 3`       |
| `POST /api/examples` with `{}`   | 400    | `{"error": "'name' is required"}` |


## Testing

We have defined testing to another file. We are focusing on snapshot testing with syrupy and pytest instead of unit tests.

## Step 8: Add a short README

Document three things in `README.md`: what the repository demonstrates, the commands from Steps 1, 3 and 7, and a clear note that it is local-only and uses synthetic data.

## Troubleshooting

* `ModuleNotFoundError: No module named 'app'` when running pytest: confirm `pytest.ini` exists in the project root and contains `pythonpath = .`.
* `Address already in use` on port 5000: change the `port` in `application.py`. On macOS, AirPlay Receiver often occupies 5000, so use 5001 if needed.
* `404` on `/api/examples/`: the list route is defined without a trailing slash, so call `/api/examples`.

## Optional next steps

Add these only if they are part of what you're demonstrating:

* Pydantic request and response models, as in `app/blueprints/types/` in the template
* A `services` unit test that avoids Flask entirely
* Feature flags, a database, or authentication, which the template includes but this POC deliberately omits

## What was intentionally left out

The following parts of `template-pm-restapi` are omitted because they have no purpose in a repository that is never deployed: AWS secrets, auth, Flagsmith, Sentry and tracing, the `.circleci/` and `.platform/` deployment configuration, and database health checks.

## Validation note

The code in this tutorial was written against the structure and conventions of the template, but it has not been executed in this environment, since package installation was unavailable. Run `pytest` after Step 8 to confirm everything works on your machine.