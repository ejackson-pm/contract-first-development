# Document Extraction API (contract-first demo)

This Flask API shows contract-first development. The OpenAPI file `openapi/document_extraction.yaml` is the contract. `make generate-types` turns it into Pydantic v2 models. The blueprints and services use only those models for request and response bodies. A change to the contract therefore shows up as a model diff, a type error or a failing snapshot.

The repository is local-only. The server binds to `127.0.0.1`, and all data is synthetic and in memory. An in-memory dict stands in for S3, and the extraction system returns a generated identifier without doing any work. Nothing here runs outside your machine.

## Layout

| Path | Contents |
| --- | --- |
| `openapi/document_extraction.yaml` | The contract. Edit this file, never the generated models. |
| `openapi/generated_init.py.tmpl` | Usage rules rendered into the generated package docstring |
| `app/blueprints/` | HTTP layer: parse the request into a generated type, call a service, return a generated type |
| `app/blueprints/types/generated/` | Generated models. Do not edit. |
| `app/services/` | Business logic. No Flask imports. `file_storage.py` is the S3 stand-in. |
| `app/utils/json_provider.py` | Serialises Pydantic models and renders dates as ISO 8601 |
| `tests/integration_tests/` | Snapshot tests through the Flask test client |

## Endpoints

| Method and path | Success | Errors |
| --- | --- | --- |
| `GET /api/document-extraction/v1/health` | 200 `HealthResponse` | none |
| `POST /api/document-extraction/v1/file-upload` | 201 `FileUploadResponse` | 400 if the `file` field is missing or is not a PDF |
| `POST /api/document-extraction/v1/create-extraction` | 201 `CreateExtractionResponse` | 400 for an invalid body, 404 for an unknown `upload_id` |

Error responses use the generated `ErrorResponse` model: `{"error": "..."}`. Responses have no envelope.

## Set up and run

Requirements: Python 3.11 or newer and GNU Make. You do not need Java, because the `jdk4py` extra bundles a JDK for the generator.

1. Install the runtime and development dependencies into `.venv`:

   ```bash
   make install
   ```

   If `python3.11` on your `PATH` cannot create a working venv, pass the interpreter explicitly, for example `make install PYTHON=/opt/python3.11/bin/python3.11`.

2. Start the API on `http://127.0.0.1:5000`:

   ```bash
   make run
   ```

3. In a second terminal, upload a PDF and submit it for extraction:

   ```bash
   BASE=http://127.0.0.1:5000/api/document-extraction/v1
   curl $BASE/health
   curl -F "file=@statement.pdf;type=application/pdf" $BASE/file-upload
   curl -H "Content-Type: application/json" \
     -d '{"upload_id": "<upload_id from the previous response>"}' \
     $BASE/create-extraction
   ```

Run everything through `make`. The Makefile loads `.env`, which sets `PM_APP_NAME` (the logger name). Without it, the app fails at import.

## Change the contract

1. Edit `openapi/document_extraction.yaml`.
2. Run `make generate-types`. It validates the spec, regenerates `app/blueprints/types/generated/document_extraction/models/` and imports the result as a smoke test.
3. Update the blueprints and services to match the new models.
4. Add or change cases in the `*_cases.py` file next to each test, then run `make update-snapshots`.
5. Review the snapshot diff, then commit the spec, the generated models, the cases and the snapshots together.

`make check-types` regenerates the models and fails if the result differs from what git has. It only passes once the generated files are committed.

## Tests

Each blueprint has one parametrised test in `tests/integration_tests/blueprints/test_<blueprint>.py` and its inputs in the adjacent `<blueprint>_cases.py`. Each case is a generated request model wrapped in a `BlueprintRequest`, and syrupy stores each result as its own `.json` file under `__snapshots__/`. The snapshots record generated identifiers by type, not value.

```bash
make test-snapshots                     # compare against the recorded snapshots
make update-snapshots                   # re-record after an intentional change
make test-snapshots TEST_FLAGS=-vv      # pass extra flags to pytest
```

The tests cover behaviour that depends on configuration or state: success paths, the handler's own file checks and an unknown upload. They do not test Pydantic validation itself.

## Not included

The type generation tutorial also protects generated files from coding agents. This demo leaves that out, and a production service would add it:

- a `.gitattributes` line that marks `app/blueprints/types/generated/**` as `linguist-generated` with `regen-target=generate-types`
- the shared `protect-generated.sh` hook from `hna-agentic-engineering`, which blocks agent edits to marked files
- the managed-settings entry that registers the hook as a gate team settings cannot weaken
- the `docs/standards/generated-code.md` standard that agents read

`make check-types` remains the local check. Auth, CI, real S3 and a real extraction system are also out of scope.
