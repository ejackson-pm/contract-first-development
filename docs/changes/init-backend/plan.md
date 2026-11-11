# init-backend: plan

Guiding principle: this is a demonstration codebase, not a long-lived or deployed application. Prefer clean implementations and good coding practices over production hardening such as size limits, retries, auth or observability. When a tutorial step exists only for production, leave it out.

Build order: apply "API Setup" (`docs/research/REST API POC Setup Tutorial.md`) first, then overlay "Type Generation" (`docs/research/OpenAPI to Pydantic Types Tutorial.md`). The decisions below resolve where the two tutorials clash. Where a decision says "Type Generation wins" or "API Setup wins", follow that tutorial for that point only.

## Decision log

Decided 2026-11-09.

### Application structure

**D1. Blueprint export names: Type Generation wins.**
Blueprints are module-level constants named `<NAME>_API` (for example `HEALTH_API`), as in production. Replace API Setup's `health_bp` and `example_bp`.

**D2. Drop the examples blueprint.**
`/api/examples`, `app/blueprints/example.py` and `app/services/example_service.py` were placeholders. Remove them. `create_app()` registers only the real blueprints.

**D3. No internal `pm_*` packages: API Setup wins.**
Remove every reference to `pm_auth`, `pm_lifeconsts`, `pm_utils` and anything installed through `$(JIGX)`. Rewrite those parts with plain Flask and Pydantic. This removes:
- the auth decorators (`bypass_default_token_check`, `verify_portal_token`, `perm`)
- `wrap_blueprint_routes_with_sentry`
- `make_success` and `make_error` (see D10)

**D4. Runtime dependencies come from public PyPI.**
Install everything the implementation needs from PyPI. Leave out only the organisation's `pm_*` packages.

**D5. Types: only generated types, plus types that cannot be generated.**
The OpenAPI contract is a YAML file under `openapi/`, and it is the only spec. Hand-written types are allowed only where the generator cannot produce them.

**D5a. Drop `flask_pydantic_spec`** (resolves Q1).
Do not install `flask_pydantic_spec`. Do not create `app/blueprints/types/spec.py` or `app/blueprints/types/utils.py`, and remove `@api_spec.validate` from the blueprints. Handlers validate input explicitly with the generated model's `model_validate`. The YAML file is the only OpenAPI document, and the project generates no Swagger docs from the models.

**D6. Use a `.env` file.**
The Makefile loads it with `include .env` and `export`. After D3, the only remaining variable is `PM_APP_NAME`, which names the logger.

**D7. Add a basic Makefile: Type Generation wins.**
Update API Setup to include a minimal Makefile. It defines what Type Generation relies on: `VENV_DIR`, `VENV_SHELL`, `install`, `help`, `check-pytest-packages` and `TEST_FLAGS`. It also has the Type Generation targets: `validate-openapi`, `generate-types`, `check-types`, `test-snapshots` and `update-snapshots`.

### HTTP conventions

**D10. No response envelope helpers.**
Do not port `make_success` or `make_error`. Return responses with plain `jsonify`.

**D10a. No response envelope** (resolves Q2).
Endpoints return the generated response model directly, with no `{"status", "data"}` wrapper. Do not port `ResponseDataSchema[T]` or `ErrorResponseSchema[T]`. Errors return a small JSON body such as `{"error": "..."}`. Define that body in the OpenAPI spec so it is generated too.

**D3a. Remove `pm_utils` from `spec.md`** (resolves Q3).
`spec.md` no longer mentions `pm_utils`, `$(JIGX)` or the envelope.

**D21. `/file-upload` takes one PDF per request** (narrows Q4).
`spec.md` previously said "possibly multiple PDFs", which was a mistake. The endpoint accepts one file and returns one `upload_id`.

**D22. No upload size limit.**
Upload size limits are a production concern, and this is a demonstration codebase that is never deployed. Do not set `MAX_CONTENT_LENGTH`, add a `413` handler, or document a size limit in the spec.

**D23. Send the PDF as `multipart/form-data` with one `file` field** (resolves Q4).
Multipart suits the upload because the file is passed on to S3. In this POC, S3 is an in-memory stand-in (D20).
- The handler reads the file from `request.files["file"]` and checks by hand that it is present and is a PDF.
- The response (`upload_id`) is a generated model.
- This is the standard browser upload, and `@hey-api/openapi-ts` types it on the frontend.

**D11. Create endpoints return 201.**
Any endpoint that creates a resource documents and returns `201`. This replaces the `200` that Type Generation's quotes spec uses for "Quote created".

**D12. Invalid request bodies return 400.**
`flask_pydantic_spec` is dropped (D5a), so there is no 422 path. The handler's explicit `model_validate` returns `400` with the error body from D10a.

**D13. URL scheme: Type Generation wins.**
Paths are versioned in full on the route, with no `url_prefix`: `/api/<service-name>/v1/<resource>`. Pick the service name at implementation time.

### Code style and environment

**D14. Use 4-space indentation** for all hand-written Python, including the code ported from Type Generation, which uses 2 spaces.

**D15. Register blueprints centrally.**
Blueprints are registered only in `create_app()`. The test `app` fixture calls `create_app()` and does not register blueprints itself. The fixture then picks up `PMJSONProvider` automatically, which removes Type Generation's "test fixture without the JSON provider" gotcha.

**D17. Python 3.11.**
Two versions are installed in this environment:
- `python3` is 3.10.12.
- `/usr/bin/python3.11` is 3.11.9.

Type Generation says the generator targets Python 3.11+, so create the venv with `python3.11 -m venv .venv`. API Setup's "3.10 or newer" prerequisite becomes "3.11 or newer".

**D18. Use the Java-based generator.**
Use `openapi-generator-cli[jdk4py]==7.27.0`, which is the latest version on PyPI as of 2026-11-09. Java is not installed in this environment, so the `jdk4py` extra is required. It is a dev-only dependency.

### Testing

**D8. Snapshot tests without a database.**
The goal is to show syrupy snapshot testing against type-safe Pydantic inputs and outputs, not database seeding. From Type Generation's test setup, drop:
- the test database
- the `pm_tenant_id` and `cleanup` fixtures
- `AuthScenario`, `build_headers` and `issue_test_token`, which have no purpose without auth (D3)

Keep these parts:
- the `*_cases.py` inputs file next to each test
- one parametrised test plus one fixture per blueprint
- `JSONSnapshotExtension`, so each case gets its own `.json` file
- `path_type` matchers for generated IDs

**D9. Minimal pytest plugins.**
The only test dependencies are `pytest` and `syrupy`. `PYTEST_PACKAGES_INSTALLED` checks only those two. During implementation, confirm that the `-m syrupy_snapshot` marker used by the Makefile exists. If it doesn't, run `tests/integration_tests/` directly.

**D16. Tests live in `tests/integration_tests/`: Type Generation wins.**
Testing focuses on integration tests through the Flask test client. Remove API Setup's placeholder `tests/test_example.py`.

### Scope

**D19. Omit Type Generation section 10 (agent hooks).**
Leave out the `protect-generated.sh` hook, the managed-settings entry, the standard, and the `.gitattributes` markers. Mention them in the README as a production follow-up.
- Keep `make check-types`. It comes from section 5 and works locally without CI.
- Edit `openapi/generated_init.py.tmpl` so its docstring no longer mentions the shared hook.

**D20. Synthetic in-memory data everywhere.**
There is no database, S3 or external extraction system. Services return hard-coded or in-memory results behind the same function signatures a real implementation would use, as `spec.md` allows.

### Implied by the decisions above

- Requirements files:
  - `requirements.txt` holds runtime dependencies: Flask and Pydantic v2.
  - `requirements-dev.txt` holds dev and test dependencies: pytest, syrupy and `openapi-generator-cli[jdk4py]`.
  - There is no `requirements-circleci.txt`, because API Setup leaves CI out.
- `app/utils/json_provider.py` (`PMJSONProvider`) stays. Nothing in it depends on `pm_*`, and it gives ISO 8601 dates.

## Open questions

**Q1. `flask_pydantic_spec`.** Resolved by D5a.

**Q2. Envelope.** Resolved by D10a.

**Q3. `pm_utils` in `spec.md`.** Resolved by D3a.

**Q4. How the PDF is sent to `/file-upload`.** Resolved by D23.
