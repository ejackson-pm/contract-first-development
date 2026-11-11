# Generating Pydantic Types from an OpenAPI Spec with openapi-generator (Python)

This tutorial shows how to use the `openapi-generator-cli` PyPI package in a PolicyMe Flask REST API to generate Pydantic v2 request and response types from an OpenAPI spec file, use those types in a blueprint and service, and cover the blueprint with snapshot-based integration tests. It follows the lightweight REST API layout derived from `template-pm-restapi` (blueprints, services, utils and tests under `app/` and `tests/`), the `flask_pydantic_spec` validation pattern, and the shared Makefile layout used by `life-restapi-main` and `global-restapi-crm`.

## 1. Summary of the python generator page

The [python generator documentation](https://openapi-generator.tech/docs/generators/python) covers the `python` generator for OpenAPI Generator.

* What it is: a stable client generator (`-g python`) that "Generates a Python client library". It targets Python 3.11+ and uses Mustache templates. It generates more than models (API classes, `api_client.py`, `configuration.py`, `rest.py`), so this tutorial keeps only the `models/` package.
* Output style: models are Pydantic v2 `BaseModel` classes with strict types (for example `StrictStr`). Numbers map to `Union[StrictFloat, StrictInt]` by default (`mapNumberTo`).
* Config options that matter for us (passed with `--additional-properties`):


| Option                                     | What it does                                                                                                                       | Default                         | How we use it                                            |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------- |
| `packageName`                              | Python package name for generated code                                                                                             | `openapi_client`                | Set to the dotted import path inside our app             |
| `generateSourceCodeOnly`                   | Only emit library source (no `setup.py`, `pyproject.toml`, etc.)                                                                   | `false`                         | `true`                                                   |
| `hideGenerationTimestamp`                  | Leaves the timestamp out of file headers                                                                                           | `true`                          | Keep `true` so regenerations diff cleanly                |
| `library`                                  | HTTP client flavour: `urllib3`, `asyncio`, `httpx`, `httpx2`                                                                       | `urllib3`                       | Not relevant, since we discard the client code           |
| `sourceFolder`                             | `src` layout vs flat layout                                                                                                        | unset (flat)                    | Leave unset                                              |
| `mapNumberTo`                              | Python type for `number`                                                                                                           | `Union[StrictFloat, StrictInt]` | Default is fine; `Decimal` is an option for money fields |
| `disallowAdditionalPropertiesIfNotPresent` | `true` keeps the legacy behaviour (`additionalProperties` treated as false when absent); `false` follows the OAS/JSON Schema specs | `true`                          | Default is fine                                          |
| `lazyImports`                              | Enables lazy imports                                                                                                               | `false`                         | Leave off                                                |
| `compatibleWithPythonLegacy`               | Mimics the old `python-legacy` generator                                                                                           | `false`                         | Leave off                                                |


* Feature support: OAS3 composition (`allOf`, `oneOf`, `anyOf`, `not`), polymorphism and unions, enums (including arrays and maps of enums), `null`, `uuid`, `date` and `date-time`, and JSON and XML wire formats.
* Reserved words: names such as `schema`, `json`, `from_dict`, `model_dump`, `model_config`, `date` and `field` are reserved. Schema properties with those names get renamed in the generated code, so avoid them in spec property names.

## 2. Packages to add

### Development and test dependencies

```text
# requirements-dev.txt (installed by make install)
openapi-generator-cli[jdk4py]==7.27.0
syrupy>=6,<7

# requirements-circleci.txt (installed by make install-circleci and in CI)
syrupy>=6,<7
```

* `openapi-generator-cli`: the PyPI package version tracks the upstream generator version, so pinning it pins the generator. Bump it on purpose, then regenerate and review the diff. It is only needed to generate code, so it is not in `requirements-circleci.txt` and is never deployed.
* The generator is a Java program and needs JDK 11+. The `[jdk4py]` extra bundles a JDK through pip, so nobody needs Java installed locally. If your machine already has Java 11+, you can use plain `openapi-generator-cli==7.27.0`.
* `syrupy`: the pytest snapshot plugin used by the integration tests in section 9. Syrupy 6.x supports Python 3.10+ and pytest 8+, which covers our Python 3.11 / pytest 9 services. It must be in `requirements-circleci.txt` because the snapshot tests run in CI.
* Local installs go through `jigx` / Artifact Registry in repos that use the `$(JIGX)` prefix. If an install hangs or 404s, confirm the package is available through the internal PyPI proxy.

### Runtime dependencies

None beyond what the template already has. The generated models import only `pydantic` (v2), `typing_extensions` (a pydantic dependency) and the standard library. Because we copy only `models/`, the generated client's runtime dependencies (`urllib3`, `python-dateutil`) are not needed.

### `.gitignore`

```text
# OpenAPI generator scratch output
.openapi-gen/
```

## 3. Repository layout

This follows the lightweight REST API template (`application.py` at the root, `app/blueprints/` for the HTTP layer, `app/services/` for business logic, `tests/` for tests), plus the pieces this tutorial adds.

```text
<service>-restapi/
├── application.py                  # app factory: JSON provider + blueprint registration
├── Makefile
├── README.md
├── requirements.txt
├── requirements-dev.txt            # + openapi-generator-cli, syrupy
├── requirements-circleci.txt       # + syrupy
├── .gitattributes                  # marks generated code for the shared agent hook and PR diffs (section 10)
├── openapi/
│   ├── quotes.yaml                 # source-of-truth spec (hand-written)
│   └── generated_init.py.tmpl      # usage rules rendered into every generated package
├── app/
│   ├── __init__.py
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── quotes.py               # HTTP layer: parse request type, call service, return response type
│   │   └── types/
│   │       ├── __init__.py
│   │       ├── spec.py             # api_spec (flask_pydantic_spec)
│   │       ├── utils.py            # ResponseDataSchema / ErrorResponseSchema envelopes
│   │       └── generated/          # generated: never edit by hand
│   │           ├── __init__.py
│   │           └── quotes/
│   │               ├── __init__.py # rendered from openapi/generated_init.py.tmpl
│   │               └── models/     # copied from openapi-generator output
│   ├── services/
│   │   ├── __init__.py
│   │   └── quote_service.py        # business logic that works only with generated types
│   └── utils/
│       ├── __init__.py
│       └── json_provider.py        # ISO 8601 dates for every JSON response (section 7)
└── tests/
    ├── __init__.py
    └── integration_tests/
        ├── __init__.py
        ├── conftest.py             # app/client fixtures + snapshot_json fixture
        ├── snapshot_support.py     # BlueprintRequest, AuthScenario, build_headers
        └── blueprints/
            ├── __init__.py
            ├── quotes_cases.py     # snapshot inputs, adjacent to the test
            ├── test_quotes.py      # one test + one fixture
            └── __snapshots__/
                └── test_quotes/    # one .json snapshot per case
```

How the layers relate:

* `app/blueprints/quotes.py` only deals with HTTP: it parses the request into the generated request type, calls the service and returns the generated response type.
* `app/services/quote_service.py` holds the behaviour and takes and returns generated types only, so it never touches Flask.
* `app/blueprints/types/` keeps the hand-written envelopes and spec configuration next to the generated models, matching `template-pm-restapi`.
* Tests live under `tests/integration_tests/` because the suite exercises blueprints end to end against the test database (section 9).
* Agent hooks, skills and standards are not in the service repo. They come from `hna-agentic-engineering`, cloned alongside it (section 10).

## 4. Example OpenAPI spec

`openapi/quotes.yaml`:

```yaml
openapi: 3.0.3
info:
  title: Quotes API
  version: 1.0.0
paths:
  /api/global-template/v1/quotes:
    post:
      operationId: createQuote
      tags: [Quotes]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateQuoteRequest'
      responses:
        '200':
          description: Quote created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CreateQuoteResponse'
components:
  schemas:
    ProductType:
      type: string
      enum: [home, auto, bundle]
    CreateQuoteRequest:
      type: object
      required: [product_type, province, coverage_amount]
      properties:
        product_type:
          $ref: '#/components/schemas/ProductType'
        province:
          type: string
          minLength: 2
          maxLength: 2
          description: Two-letter province code, e.g. ON
        coverage_amount:
          type: integer
          minimum: 1
          description: Requested coverage amount in CAD
        effective_date:
          type: string
          format: date
          description: Requested policy effective date (ISO 8601, YYYY-MM-DD)
    CreateQuoteResponse:
      type: object
      required: [quote_id, product_type, monthly_premium]
      properties:
        quote_id:
          type: string
          description: Identifier of the created quote
        product_type:
          $ref: '#/components/schemas/ProductType'
        monthly_premium:
          type: number
          description: Monthly premium in CAD
        effective_date:
          type: string
          format: date
          description: Policy effective date (ISO 8601, YYYY-MM-DD)
```

Envelope convention: our endpoints return `{"status": 200, "data": {...}}` through `make_success`, and errors return `{"status": 500, "error": ...}` through `make_error`. Keep the hand-written generic wrappers `ResponseDataSchema[T]` and `ErrorResponseSchema[T]` in `app/blueprints/types/utils.py`, and put only the payload schemas (the `data` part) in the spec. If you document the envelope inline in the spec, the generator emits an extra wrapper model that you can ignore.

Dates and date-times: always declare them as `type: string` with `format: date` or `format: date-time`. The generator then types them as `date` / `datetime`, and the app's JSON provider (section 7) renders them as ISO 8601.

## 5. Makefile targets

Add this section to the existing Makefile, below "Application Execution". It reuses the `VENV_DIR`, `VENV_SHELL` and `check-*-packages` patterns that are already there.

```makefile
# =============================================================================
# OpenAPI -> Pydantic Type Generation
# =============================================================================

# Override per spec, e.g. make generate-types OPENAPI_SPEC=openapi/payments.yaml OPENAPI_TYPES_NAME=payments
OPENAPI_SPEC ?= openapi/quotes.yaml
OPENAPI_TYPES_NAME ?= quotes
OPENAPI_TYPES_ROOT := app/blueprints/types/generated
OPENAPI_TYPES_DIR := $(OPENAPI_TYPES_ROOT)/$(OPENAPI_TYPES_NAME)
OPENAPI_TYPES_PKG := $(subst /,.,$(OPENAPI_TYPES_DIR))
OPENAPI_INIT_TEMPLATE := openapi/generated_init.py.tmpl
OPENAPI_TMP_DIR := .openapi-gen

GENERATOR_INSTALLED := $(shell \
	test -x $(VENV_DIR)/bin/openapi-generator-cli && \
	echo "installed" || \
	echo "not_installed" \
)

.PHONY: check-generator-packages validate-openapi generate-types check-types

# Install openapi-generator-cli (requirements-dev.txt) if needed
check-generator-packages: $(VENV_DIR)
	@if [ "$(GENERATOR_INSTALLED)" != "installed" ]; then \
		echo "openapi-generator-cli not found, installing development dependencies..."; \
		$(MAKE) install; \
	fi

# Validate the OpenAPI spec
validate-openapi: check-generator-packages
	@echo "Validating $(OPENAPI_SPEC)..."
	$(VENV_SHELL) openapi-generator-cli validate -i $(OPENAPI_SPEC)

# Generate Pydantic models from the OpenAPI spec (models only)
generate-types: validate-openapi
	@echo "Generating Pydantic types from $(OPENAPI_SPEC) into $(OPENAPI_TYPES_DIR)..."
	rm -rf $(OPENAPI_TMP_DIR)
	$(VENV_SHELL) openapi-generator-cli generate \
		-g python \
		-i $(OPENAPI_SPEC) \
		-o $(OPENAPI_TMP_DIR) \
		--additional-properties=packageName=$(OPENAPI_TYPES_PKG),generateSourceCodeOnly=true,hideGenerationTimestamp=true \
		--global-property=apiTests=false,modelTests=false,apiDocs=false,modelDocs=false
	rm -rf $(OPENAPI_TYPES_DIR)
	mkdir -p $(OPENAPI_TYPES_DIR)
	touch $(OPENAPI_TYPES_ROOT)/__init__.py
	sed 's|{{SPEC}}|$(OPENAPI_SPEC)|g' $(OPENAPI_INIT_TEMPLATE) > $(OPENAPI_TYPES_DIR)/__init__.py
	cp -R $(OPENAPI_TMP_DIR)/$(OPENAPI_TYPES_DIR)/models $(OPENAPI_TYPES_DIR)/models
	rm -rf $(OPENAPI_TMP_DIR)
	$(VENV_SHELL) python3 -c "import $(OPENAPI_TYPES_PKG).models"
	@echo "Done. Import types from $(OPENAPI_TYPES_PKG).models"

# Fail if the committed types are out of date with the spec (use in CI or pre-push)
check-types: generate-types
	@git diff --exit-code -- $(OPENAPI_TYPES_DIR) && \
	test -z "$$(git status --porcelain -- $(OPENAPI_TYPES_DIR))" || \
	(echo "Generated types are stale: run make generate-types and commit the result." && exit 1)
```

Add these lines to the existing `help` target (the snapshot targets are added in section 9):

```makefile
	@echo "Code Generation:"
	@echo "  validate-openapi Validate the OpenAPI spec"
	@echo "  generate-types   Generate Pydantic types from OPENAPI_SPEC"
	@echo "  check-types      Fail if generated types are out of date"
	@echo ""
	@echo "Snapshot Tests:"
	@echo "  test-snapshots   Run blueprint snapshot tests"
	@echo "  update-snapshots Re-record snapshots after an intentional change"
	@echo ""
```

How it works:

* `packageName` is set to the dotted path `app.blueprints.types.generated.quotes`. The generator writes absolute imports (`from app.blueprints.types.generated.quotes.models.product_type import ProductType`), so the copied models import cleanly from inside our app.
* The generator writes everything to the scratch directory `.openapi-gen/`. Only `models/` is copied into the app, so the client code (`api/`, `api_client.py`, `rest.py`, `configuration.py`), docs and tests never enter the repo.
* The package `__init__.py` is rendered from `openapi/generated_init.py.tmpl`, so the usage rules in section 6 sit inline with the generated code.
* The last step imports the generated package, so a broken generation fails `make` straight away instead of at app start-up.
* Makefile recipe lines must start with a tab character, not spaces.

Run it:

```bash
make generate-types
# or for another spec
make generate-types OPENAPI_SPEC=openapi/payments.yaml OPENAPI_TYPES_NAME=payments
```

Commit the generated `app/blueprints/types/generated/` directory. Deploys and CI then never need Java, and spec changes show up as reviewable model diffs.

## 6. What the generated types look like

The generated `create_quote_request.py` is roughly:

```python
class CreateQuoteRequest(BaseModel):
    """
    CreateQuoteRequest
    """ # noqa: E501
    product_type: ProductType
    province: Annotated[str, Field(min_length=2, strict=True, max_length=2)] = Field(description="Two-letter province code, e.g. ON")
    coverage_amount: Annotated[int, Field(strict=True, ge=1)] = Field(description="Requested coverage amount in CAD")
    effective_date: Optional[date] = Field(default=None, description="Requested policy effective date (ISO 8601, YYYY-MM-DD)")
    __properties: ClassVar[List[str]] = ["product_type", "province", "coverage_amount", "effective_date"]

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    # also generated: to_str(), to_json(), from_json(), to_dict(), from_dict()
```

### Usage rules live inline with the generated code

Rules about how to use generated types belong where developers (and agents) read them: in the generated package itself. `make generate-types` renders this template into `app/blueprints/types/generated/<name>/__init__.py`, so the rules show up on hover in the IDE, in `help()` and in any agent that opens the package.

`openapi/generated_init.py.tmpl`:

```python
"""Pydantic models generated from {{SPEC}} by `make generate-types`.

DO NOT EDIT. Change the spec and regenerate. Manual edits are overwritten on the
next generation, blocked for coding agents by the shared protect-generated hook
from hna-agentic-engineering, and caught in CI by `make check-types`.

Usage rules
-----------
* Strict types: fields use StrictStr / StrictInt / strict constraints, so values
  are never coerced. "5" is rejected for an integer field. Use these models for
  JSON request bodies and responses only. Query-string and path values always
  arrive as strings: parse them with a hand-written model in
  app/blueprints/types/ (lax types), or declare them as `type: string` in the spec.
* Dates: `format: date` / `format: date-time` become date / datetime. They are
  rendered as ISO 8601 by app.utils.json_provider.PMJSONProvider. Return models
  (or dicts containing them) through make_success; never format dates by hand.
* Aliases: if the spec uses camelCase names, fields are snake_case with an alias.
  Serialise with by_alias=True (PMJSONProvider already does).
* Customisation: subclass a generated model in a hand-written module (for example
  to add ExcludableModel behaviour or json_schema_extra examples). Never edit here.
"""
```

Where the spec has query parameters, repeat the strict-type note in each parameter's `description`, so it also appears in the generated Swagger docs.

## 7. ISO 8601 for all dates and date-times

`make_success` and `make_error` build responses with Flask's `jsonify`, which uses the app's JSON provider. Flask's default provider renders `date` and `datetime` in HTTP-date format (for example `Tue, 01 Dec 2026 00:00:00 GMT`). Replace it once, app-wide, so every date in every response is ISO 8601. That covers generated models, `to_dict()` output, hand-built dicts and anything else that goes through `jsonify`.

`app/utils/json_provider.py`:

```python
"""App-wide JSON provider: ISO 8601 dates and Pydantic model support for jsonify."""
from datetime import date, datetime, time
from typing import Any

from flask.json.provider import DefaultJSONProvider
from pydantic import BaseModel


def to_json_compatible(value: Any) -> Any:
  """Convert values the stdlib json module cannot serialise.

  - Pydantic models: dumped in JSON mode with wire names (aliases), omitting None.
  - date / datetime / time: ISO 8601 via isoformat(). Use timezone-aware UTC
    datetimes so the offset is included (2026-12-01T14:30:00+00:00).
  - Everything else: Flask's defaults (UUID, Decimal, dataclasses, ...).
  """
  if isinstance(value, BaseModel):
    return value.model_dump(mode="json", by_alias=True, exclude_none=True)
  if isinstance(value, (datetime, date, time)):
    return value.isoformat()
  return DefaultJSONProvider.default(value)


class PMJSONProvider(DefaultJSONProvider):
  """DefaultJSONProvider with ISO 8601 dates and Pydantic model serialisation."""

  default = staticmethod(to_json_compatible)
```

Register it in the app factory (`application.py`), before any blueprint is used:

```python
from flask import Flask

from app.blueprints.health import HEALTH_API
from app.blueprints.quotes import QUOTES_API
from app.utils.json_provider import PMJSONProvider


def create_app() -> Flask:
  app = Flask(__name__)
  app.json = PMJSONProvider(app)  # ISO 8601 dates for every jsonify / make_success response
  app.register_blueprint(HEALTH_API)
  app.register_blueprint(QUOTES_API)
  return app
```

Keep the integration test `app` fixture in step with production: set `app.json = PMJSONProvider(app)` there too (section 9). The snapshot tests then lock in the ISO 8601 output, because any regression changes the recorded date strings.

## 8. Blueprint and service using the generated request and response types

`app/services/quote_service.py` (2-space indentation to match the template):

```python
"""Quote business logic. Takes and returns generated types only; no Flask here."""
import uuid

from app.blueprints.types.generated.quotes.models import CreateQuoteRequest, CreateQuoteResponse

SUPPORTED_PROVINCES = frozenset({"ON", "AB"})  # example configuration
PREMIUM_RATE = 0.00012  # example rate


class QuoteNotAvailableError(Exception):
  """Raised when a product cannot be quoted for the requested configuration."""


def create_quote(quote_request: CreateQuoteRequest) -> CreateQuoteResponse:
  """Price a quote. Input is already validated by the generated request type."""
  if quote_request.province not in SUPPORTED_PROVINCES:
    raise QuoteNotAvailableError(
      f"{quote_request.product_type.value} quotes are not available in {quote_request.province}"
    )
  return CreateQuoteResponse(
    quote_id=str(uuid.uuid4()),
    product_type=quote_request.product_type,
    monthly_premium=round(quote_request.coverage_amount * PREMIUM_RATE, 2),
    effective_date=quote_request.effective_date,
  )
```

`app/blueprints/quotes.py`:

```python
"""Quotes blueprint. Request/response types are generated from openapi/quotes.yaml."""
import logging
import os

from flask import Blueprint, request
from flask_pydantic_spec import Response as ApiSpecResponse
from pm_auth.decorators import bypass_default_token_check, verify_portal_token
from pm_auth.permissions import perm
from pm_lifeconsts.consts import WEBFORM_ACTIONS, WEBFORM_IDENTIFIERS
from pm_utils.request_helpers import make_error, make_success
from pm_utils.sentry_helpers import wrap_blueprint_routes_with_sentry
from pydantic import ValidationError

# Generated types: read the package docstring for usage rules (strict types, dates, aliases).
from app.blueprints.types.generated.quotes.models import CreateQuoteRequest, CreateQuoteResponse
from app.blueprints.types.spec import api_spec
from app.blueprints.types.utils import ErrorResponseSchema, ResponseDataSchema
from app.services.quote_service import QuoteNotAvailableError, create_quote

PM_APP_NAME = os.environ["PM_APP_NAME"]
LOGGER = logging.getLogger(PM_APP_NAME)

QUOTES_ENDPOINT = "/api/global-template/v1/quotes"
QUOTES_API = wrap_blueprint_routes_with_sentry(Blueprint("quotes_api", __name__))


@QUOTES_API.route(QUOTES_ENDPOINT, methods=["POST"])
@bypass_default_token_check
# Placeholder identifier: use the permission that guards your endpoint.
@verify_portal_token([perm(WEBFORM_IDENTIFIERS.QUOTES, WEBFORM_ACTIONS.EXECUTE)])
@api_spec.validate(
  # Generated request type: validation + Swagger documentation
  body=CreateQuoteRequest,
  # Generated response type wrapped in our standard envelope
  resp=ApiSpecResponse(
    HTTP_200=ResponseDataSchema[CreateQuoteResponse],
    HTTP_400=ErrorResponseSchema[str],
    HTTP_401=ErrorResponseSchema[str],  # Returned by auth wrappers
    HTTP_403=ErrorResponseSchema[str],  # Returned by auth wrappers
    HTTP_500=ErrorResponseSchema[str],
  ),
  tags=["Quotes"],
)
def post_quote():
  """Global Template Create Quote Endpoint

  **Path:** POST /api/global-template/v1/quotes

  **Summary:**
  Creates a quote from the request body and returns the priced quote.

  **Path Parameters:** None

  **Query Parameters:** None

  **Headers:**
  - Authorization (str, required): Bearer portal token.
  - X-Tenant-Id (UUID, required): Tenant identifier.

  **Authentication/Security:**
  - Portal token with the quotes EXECUTE permission.

  **Business Logic:**
  - Parses the body into the generated CreateQuoteRequest type.
  - Returns 400 when the product is not available for the requested configuration.
  - Returns a CreateQuoteResponse wrapped in ResponseDataSchema.

  **Version:** v1
  """
  # Parse into the generated type explicitly so the handler is typed even when
  # PM_ENABLE_ENDPOINT_VALIDATION is off (in which case @api_spec.validate is a no-op).
  try:
    quote_request = CreateQuoteRequest.model_validate(request.get_json(silent=True) or {})
  except ValidationError as e:
    LOGGER.info("Invalid create quote request: %s", e.errors(include_input=False))
    return make_error(400, "Invalid request body")

  try:
    quote_response: CreateQuoteResponse = create_quote(quote_request)
  except QuoteNotAvailableError as e:
    return make_error(400, str(e))
  except Exception:
    LOGGER.exception("Failed to create quote")
    return make_error(500, "Internal Server Error")

  # PMJSONProvider serialises the generated model (aliases, ISO 8601 dates).
  return make_success(quote_response, 200)
```

Why the handler parses the body itself: in our services, `@api.validate` is controlled by `PM_ENABLE_ENDPOINT_VALIDATION` (plus `PM_ENABLE_ENDPOINT_VALIDATION_WARN_MODE` for soft-fail). When validation is off, the decorator does nothing. Calling `CreateQuoteRequest.model_validate(...)` explicitly gives the handler a typed object in every mode. The `@api_spec.validate(...)` declaration still drives Swagger docs and the 422 / response validation when the flag is on.

The decorator stack mirrors existing blueprints such as `hd_benefits_template.py`: `@bypass_default_token_check`, then `@verify_portal_token([...])`, then `@api_spec.validate(...)`. `WEBFORM_IDENTIFIERS.QUOTES` is a placeholder; replace it with the real identifier for your endpoint.

## 9. Integration tests with syrupy snapshots

The suite exercises blueprints end to end and compares each response with a recorded snapshot. Inputs are generated request objects, so the tests stay predictable. They run under pytest with the same fixture structure as the rest of `tests/integration_tests/`, against the test database that boots with the tests in CI and locally.

What to cover:

* Success modes: each meaningful configuration that produces a 200 (for example with and without optional fields).
* Failure modes driven by configuration or state: business-rule errors, missing records, downstream failures.
* AuthN and AuthZ: no token, a token without the required permission, and the authorised path.
* Not input validation: Pydantic and the generated types own that. We do not test whether Pydantic works, only whether a given configuration produces an error or a success.

How it fits together:

* `quotes_cases.py` sits next to the test file and exports `CASES`, a list of `(request object, test name)` tuples. Adding a scenario means adding one tuple.
* `test_quotes.py` has a single parametrised test and a single fixture that registers the blueprint, runs the request and returns the status code and JSON body.
* Each case's result is compared with a syrupy snapshot. With `JSONSnapshotExtension`, every case gets its own `.json` file under `__snapshots__/test_quotes/`, so large success responses stay out of the test code and are reviewed as separate files in pull requests.

### Shared snapshot support

`tests/integration_tests/snapshot_support.py` (reused by every blueprint's snapshot tests):

```python
"""Shared types and helpers for blueprint snapshot tests."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class AuthScenario(str, Enum):
  """Authentication / authorisation configurations a case can run under."""

  AUTHORISED = "authorised"
  NO_TOKEN = "no_token"
  MISSING_PERMISSION = "missing_permission"


@dataclass(frozen=True)
class BlueprintRequest:
  """One request to run against a blueprint. Bodies are generated request types."""

  method: str
  path: str
  body: Optional[BaseModel] = None
  auth: AuthScenario = AuthScenario.AUTHORISED

  def json_body(self) -> Optional[dict[str, Any]]:
    if self.body is None:
      return None
    return self.body.model_dump(mode="json", by_alias=True, exclude_none=True)


def build_headers(auth: AuthScenario, tenant_id: str) -> dict[str, str]:
  """Map an auth scenario to request headers. The only place tests decide auth."""
  headers = {"X-tenant-id": tenant_id}
  if auth is AuthScenario.NO_TOKEN:
    return headers
  token = issue_test_token(with_permission=auth is AuthScenario.AUTHORISED)
  headers["Authorization"] = f"Bearer {token}"
  return headers


def issue_test_token(with_permission: bool) -> str:
  """Return a portal token for the test environment.

  Implement with the token helpers your repo's integration tests already use, so
  AUTHORISED gets a token that carries the endpoint's permission and
  MISSING_PERMISSION gets a valid token without it.
  """
  raise NotImplementedError("Wire issue_test_token to your repo's test token helper")
```

`tests/integration_tests/conftest.py` additions:

```python
import os

import pytest
from flask import Flask
from syrupy.extensions.json import JSONSnapshotExtension

from app.utils.json_provider import PMJSONProvider


@pytest.fixture(name="app")
def fixture_app():
  """Flask application set up. Mirrors production JSON handling."""
  app = Flask(os.environ["PM_APP_NAME"])
  app.config["TESTING"] = True
  app.json = PMJSONProvider(app)  # same ISO 8601 rendering as create_app()
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
```

If your `conftest.py` already defines `app` and `client`, keep them and add the `app.json = PMJSONProvider(app)` line and the `snapshot_json` fixture.

### Inputs file, adjacent to the test

`tests/integration_tests/blueprints/quotes_cases.py`:

```python
"""Inputs for test_quotes.py: (request, test name) tuples. One snapshot per entry."""
from datetime import date

from app.blueprints.quotes import QUOTES_ENDPOINT
from app.blueprints.types.generated.quotes.models import CreateQuoteRequest, ProductType
from tests.integration_tests.snapshot_support import AuthScenario, BlueprintRequest

HOME_ON = CreateQuoteRequest(
  product_type=ProductType.HOME,
  province="ON",
  coverage_amount=500_000,
  effective_date=date(2026, 12, 1),
)


def post_quote(body: CreateQuoteRequest, auth: AuthScenario = AuthScenario.AUTHORISED) -> BlueprintRequest:
  return BlueprintRequest(method="POST", path=QUOTES_ENDPOINT, body=body, auth=auth)


CASES: list[tuple[BlueprintRequest, str]] = [
  # Success modes
  (post_quote(HOME_ON), "home_quote_success"),
  (
    post_quote(CreateQuoteRequest(product_type=ProductType.BUNDLE, province="AB", coverage_amount=750_000)),
    "bundle_quote_success_without_effective_date",
  ),
  # Failure modes driven by configuration (not input validation)
  (
    post_quote(CreateQuoteRequest(product_type=ProductType.AUTO, province="QC", coverage_amount=50_000)),
    "auto_quote_unavailable_in_province",
  ),
  # AuthN / AuthZ
  (post_quote(HOME_ON, auth=AuthScenario.NO_TOKEN), "rejects_missing_token"),
  (post_quote(HOME_ON, auth=AuthScenario.MISSING_PERMISSION), "rejects_token_without_permission"),
]
```

### The single test and fixture

`tests/integration_tests/blueprints/test_quotes.py`:

```python
"""Snapshot tests for the quotes blueprint. Inputs live in quotes_cases.py."""
import pytest
from syrupy.matchers import path_type

from app.blueprints.quotes import QUOTES_API
from tests.integration_tests.blueprints.quotes_cases import CASES
from tests.integration_tests.snapshot_support import BlueprintRequest, build_headers

# quote_id is a fresh UUID on every run: snapshot its type, not its value.
DYNAMIC_FIELDS = path_type({"body.data.quote_id": (str,)})


@pytest.fixture(name="run_blueprint")
def fixture_run_blueprint(app, client, pm_tenant_id):
  """Register the blueprint and return a callable that runs one request case."""
  app.register_blueprint(QUOTES_API)

  def _run(case: BlueprintRequest) -> dict:
    response = client.open(
      case.path,
      method=case.method,
      json=case.json_body(),
      headers=build_headers(case.auth, pm_tenant_id),
    )
    return {"status_code": response.status_code, "body": response.get_json()}

  return _run


@pytest.mark.parametrize(
  "case",
  [case for case, _ in CASES],
  ids=[name for _, name in CASES],
)
def test_quotes_blueprint(case, run_blueprint, snapshot_json):
  assert run_blueprint(case) == snapshot_json(matcher=DYNAMIC_FIELDS)
```

`pm_tenant_id` is the tenant fixture from the template's integration tests (built from `insert_pm_tenant`). Use whichever tenant fixture your `conftest.py` provides. If the blueprint writes to the test database, the existing tenant and `cleanup` fixtures keep each case isolated.

### Snapshot files

The first run fails because no snapshots exist yet. Syrupy treats a missing snapshot as a failure, not just a changed one. Record them with `make update-snapshots`, review them, and commit the `__snapshots__/` directory with the test code.

```text
tests/integration_tests/blueprints/__snapshots__/test_quotes/
  test_quotes_blueprint[auto_quote_unavailable_in_province].json
  test_quotes_blueprint[bundle_quote_success_without_effective_date].json
  test_quotes_blueprint[home_quote_success].json
  test_quotes_blueprint[rejects_missing_token].json
  test_quotes_blueprint[rejects_token_without_permission].json
```

`test_quotes_blueprint[home_quote_success].json` will look roughly like this:

```json
{
  "body": {
    "data": {
      "effective_date": "2026-12-01",
      "monthly_premium": 60.0,
      "product_type": "home",
      "quote_id": "<class 'str'>"
    },
    "status": 200
  },
  "status_code": 200
}
```

The ISO 8601 `effective_date` is recorded in the snapshot, so a regression in date formatting fails the suite.

### Makefile targets for snapshots

Add `syrupy` to the existing pytest package check, then add the targets under "Testing and Quality Assurance":

```makefile
PYTEST_PACKAGES_INSTALLED := $(shell \
	test -d $(VENV_DIR) && \
	$(VENV_DIR)/bin/python -c "import pytest, pytest_mock, pytest_env, pytest_cov, syrupy" 2>/dev/null && \
	echo "installed" || \
	echo "not_installed" \
)

.PHONY: test-snapshots update-snapshots

# Run blueprint snapshot tests (syrupy marks every test that uses the snapshot fixture)
test-snapshots: check-pytest-packages
	@echo "Running snapshot tests..."
	$(VENV_SHELL) python3 -m pytest tests/integration_tests/ -m syrupy_snapshot $(TEST_FLAGS)

# Re-record snapshots after an intentional change; review the diff before committing
update-snapshots: check-pytest-packages
	@echo "Updating snapshots..."
	$(VENV_SHELL) python3 -m pytest tests/integration_tests/ -m syrupy_snapshot --snapshot-update $(TEST_FLAGS)
```

Notes:

* `--snapshot-update` also deletes snapshots that are no longer used, so renaming a case removes its old file.
* Run the snapshot suite with the same `PM_ENABLE_ENDPOINT_VALIDATION` setting everywhere (tests run strict). Auth and validation ordering decide whether a case records 401 or 422, so a different flag value changes the snapshot.
* Treat snapshot diffs in PRs as behaviour changes: a changed status code, field or error message should be intentional and called out in the PR description.

## 10. Protecting generated files

Generated code must only change through `make generate-types`. Agent-side protection follows the HNA Context Registry model (ADR HNA 005). Shared hooks, standards and managed gates live once in `hna-agentic-engineering`, which is cloned next to the service repos, and its `install.sh` wires them into each engineer's harness (Claude Code or Cursor). Service repos don't carry their own agent hooks. They only declare which of their files are generated.


| Piece                                | Lives in                  | Purpose                                                                   |
| ------------------------------------ | ------------------------- | ------------------------------------------------------------------------- |
| `.gitattributes` entry               | Service repo              | Declares which files are generated and which make target regenerates them |
| `.agent/hooks/protect-generated.sh`  | `hna-agentic-engineering` | Shared hook: blocks agent edits to any file a repo marks as generated     |
| `.agent/settings.managed.json` entry | `hna-agentic-engineering` | Registers the hook as a managed gate that team settings cannot weaken     |
| `docs/standards/generated-code.md`   | `hna-agentic-engineering` | Model-agnostic rule agents read before acting; linked from `CLAUDE.md`    |
| `make check-types`                   | Service repo (CI)         | Backstop for edits no agent hook can see                                  |


### 10.1 In the service repo: declare generated files

`.gitattributes`:

```text
app/blueprints/types/generated/** linguist-generated=true regen-target=generate-types
```

* `linguist-generated=true` is the marker the shared hook looks for. GitHub also uses it to collapse generated files in PR diffs, so reviewers focus on the spec change and the snapshot diffs.
* `regen-target` is a custom attribute (git lets repos define their own). The hook reads it to tell the agent which make target to run. Add one line per generated folder, for example a second spec's output or generated TypeScript in the frontend repo.

Nothing else agent-specific goes in the service repo: no `.claude/` or `.cursor/` hook config and no hook scripts.

### 10.2 In hna-agentic-engineering: the shared hook

`.agent/hooks/protect-generated.sh` sits next to the existing protection hooks such as `protect-tests.sh`:

```bash
#!/usr/bin/env bash
# protect-generated.sh: block agent edits to generated files in any repo.
#
# Shared hook for hna-agentic-engineering. A file is protected when the repo that
# owns it marks it `linguist-generated` in .gitattributes, so service repos opt in
# with one .gitattributes line and this hook needs no per-repo configuration.
# An optional `regen-target` attribute names the make target that regenerates it.
#
# Input: hook payload JSON on stdin. Reads tool_input.file_path (Claude Code),
# tool_input.notebook_path, or a top-level file_path.
# Exit 2 blocks the edit and sends stderr to the agent; exit 0 allows it.
# Fails open (exit 0) on anything it cannot interpret, so it never wedges an agent.
set -uo pipefail

payload="$(cat)"

read_field() {
  printf '%s' "$payload" | python3 -c '
import json, sys
try:
  p = json.load(sys.stdin)
except Exception:
  sys.exit(0)
if not isinstance(p, dict):
  sys.exit(0)
t = p.get("tool_input") or {}
if sys.argv[1] == "path":
  print(t.get("file_path") or t.get("notebook_path") or p.get("file_path") or "")
else:
  print(p.get("cwd") or "")
' "$1" 2>/dev/null
}

file_path="$(read_field path)"
[ -n "$file_path" ] || exit 0

case "$file_path" in
  /*) abs_path="$file_path" ;;
  *)  base="$(read_field cwd)"; abs_path="${base:-$PWD}/$file_path" ;;
esac

# The file (or its folder) may not exist yet when an agent creates it: use the
# nearest existing parent to find the owning repository.
dir="$(dirname "$abs_path")"
while [ ! -d "$dir" ] && [ "$dir" != "/" ]; do dir="$(dirname "$dir")"; done
repo_root="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || exit 0
dir_real="$(cd "$dir" && pwd -P)"
rel_path="${dir_real#"$repo_root"}/${abs_path#"$dir"/}"
rel_path="${rel_path#/}"

attr_value() {
  local out
  out="$(git -C "$repo_root" check-attr "$1" -- "$rel_path" 2>/dev/null)" || return 0
  printf '%s' "${out##*: }"
}

case "$(attr_value linguist-generated)" in
  true|set) ;;
  *) exit 0 ;;
esac

regen="$(attr_value regen-target)"
case "$regen" in
  unspecified|unset|set|"") how="regenerate it with the repo's generator (see its CLAUDE.md or Makefile)" ;;
  *) how="run \`make $regen\`" ;;
esac

echo "Blocked: $rel_path is generated code (marked linguist-generated in $(basename "$repo_root")/.gitattributes). Do not edit it directly. Change its source (for example the OpenAPI spec) and $how." >&2
exit 2
```

How it behaves:

* It finds the repo that owns the target file and asks git whether that file is `linguist-generated`, so one hook covers every HNA repo (backend, frontend, satellites) with no per-repo configuration.
* Exit code 2 blocks the edit and returns the message to the agent, which then edits the spec and runs `make generate-types`.
* It handles absolute and relative paths, and new files in folders that don't exist yet.
* It fails open on payloads it cannot interpret and on paths outside a git repo, so a malformed event never wedges an agent session.

### 10.3 Register it as a managed gate

ADR HNA 005 puts organisation-mandated protections such as test protection in `.agent/settings.managed.json`, where engineers and agents cannot bypass them and team settings cannot weaken them. Protecting generated code is the same kind of gate, so register it there next to the `protect-tests.sh` entry rather than in the team-editable `.agent/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$HNA_AGENTIC_ENGINEERING_DIR/.agent/hooks/protect-generated.sh\""
          }
        ]
      }
    ]
  }
}
```

* Merge this into the existing `PreToolUse` array; don't replace the file.
* Use the same path form as the existing `protect-tests.sh` entry. `$HNA_AGENTIC_ENGINEERING_DIR` is a placeholder for however that entry finds the registry clone.
* `install.sh` turns the managed settings into each harness's own format. For Cursor, check which hook event it maps this entry to. If that event fires after the edit rather than before it, the hook can only report the edit, and `make check-types` stays the enforcement point.

### 10.4 Add the standard agents read

The hook is the enforcement point; the standard explains the rule before an agent hits it. ADR HNA 005 keeps the process model-agnostic, so the rule lives in plain Markdown that any harness can read.

`docs/standards/generated-code.md`:

```markdown
# Generated code

Files marked `linguist-generated` in a repo's `.gitattributes` are generated. Never edit them directly.

* Change the source (an OpenAPI spec under `openapi/`, for example) and run the make target named by the file's `regen-target` attribute, for example `make generate-types`.
* To customise a generated type, subclass it in a hand-written module.
* Commit the source change and the regenerated files together.
* Enforced by `.agent/hooks/protect-generated.sh` (managed gate) and by each repo's `make check-types` in CI.
```

Link it from the registry's `CLAUDE.md` under the standards that apply to every repo.

### 10.5 Roll it out and verify

1. Merge the hook, the managed-settings entry and the standard into `hna-agentic-engineering`.
2. Engineers pull the registry and re-run `install.sh` so their Claude Code or Cursor setup picks up the new gate.
3. Add the `.gitattributes` line to each service repo that has generated code.
4. Check the hook from a service repo clone. The first command should print a "Blocked" message and exit 2; the second should exit 0:

```bash
echo '{"tool_input":{"file_path":"'"$PWD"'/app/blueprints/types/generated/quotes/models/product_type.py"}}' \
  | "$HNA_AGENTIC_ENGINEERING_DIR/.agent/hooks/protect-generated.sh"; echo "exit $?"
echo '{"tool_input":{"file_path":"'"$PWD"'/app/blueprints/quotes.py"}}' \
  | "$HNA_AGENTIC_ENGINEERING_DIR/.agent/hooks/protect-generated.sh"; echo "exit $?"
```

### 10.6 CI backstop

The hook only sees the agent's file-editing tools. `make check-types` regenerates and fails if the committed models differ from the spec, so it catches everything else: human edits, shell-based edits (`sed`, scripts) and engineers who haven't re-run `install.sh`.

## 11. Day-to-day workflow

1. Edit `openapi/quotes.yaml` (the spec is the source of truth).
2. Run `make generate-types`.
3. Update the service and blueprint to match the regenerated models. Type errors and failing snapshots show what changed.
4. Add or adjust cases in `quotes_cases.py`, run `make update-snapshots`, and review the new or changed snapshot files.
5. Commit the spec, the regenerated `app/blueprints/types/generated/`, the cases and the snapshots together.
6. CI runs the snapshot suite; optionally add `make check-types` to CI or pre-push.

## 12. Gotchas

* Strict types and query parameters: the rule is documented inline in every generated package's docstring (section 6) and in the spec's parameter descriptions.
* Date formatting: handled app-wide by `PMJSONProvider` (section 7). If a date shows up in HTTP-date format, the response did not go through an app with the provider registered, most often a test `app` fixture without `app.json = PMJSONProvider(app)`.
* Generated files: declared in `.gitattributes`, protected by the shared `protect-generated.sh` managed gate from `hna-agentic-engineering`, and backstopped by `make check-types` (section 10). If an agent edits generated code anyway, check that the engineer has pulled the registry and re-run `install.sh`.
* Snapshot hygiene: never hand-edit `.json` snapshots. Change the code or the case and run `make update-snapshots`. Replace dynamic values (IDs, timestamps) with `path_type` matchers, not by deleting fields. If a filtered run (`TEST_PATTERN=...`) reports unused snapshots, add `--snapshot-warn-unused` for that run.
* Swagger examples: generated fields carry `description` from the spec but not our `flask_pydantic_spec` `example=` values. Add `example:` in the spec if you want them in docs.
* Reserved names: properties called `schema`, `json`, `date`, `field`, `model_config` and similar are renamed by the generator. Avoid them in new specs.
* Import side effects: the smoke-test import in `generate-types` loads `app/__init__.py` and `app/blueprints/types/__init__.py`. If those need environment variables, the Makefile's `include .env` / `export` already provides them. Make sure `.env` exists locally.
* Package allowlists: if a CI check restricts which packages can appear in requirements files, `openapi-generator-cli` and `syrupy` may need to be added to the allowlist.
* Upgrading the generator: bump the pin in `requirements-dev.txt`, run `make install && make generate-types`, and review the model diff and the snapshot suite before merging. Generated output can change between versions.

## Sources

* [Documentation for the python Generator | OpenAPI Generator](https://openapi-generator.tech/docs/generators/python)
* [openapi-generator-cli on PyPI](https://pypi.org/project/openapi-generator-cli/)
* [OpenAPI Generator CLI Installation](https://openapi-generator.tech/docs/installation/)
* [syrupy documentation](https://syrupy-project.github.io/syrupy/)
* [Python REST API template and lightweight layout (Glean chat)](https://app.glean.com/chat/e677656075e1421694df39d7dc3e287a)
* [template-pm-restapi example blueprint](https://github.com/policyme/template-pm-restapi/blob/master/app/blueprints/example.py)
* [template-pm-restapi example types](https://github.com/policyme/template-pm-restapi/blob/master/app/blueprints/types/example.py)
* [template-pm-restapi integration tests](https://github.com/policyme/template-pm-restapi/blob/master/tests/integration_tests/test_endpoints.py)
* [hd-restapi-main benefits template blueprint (decorator stack)](https://github.com/policyme/hd-restapi-main/blob/develop/app/blueprints/hd_benefits_template.py)
* [pm_utils request_helpers (make_success / jsonify)](https://github.com/policyme/global-libpy-utils/blob/master/pm_utils/request_helpers.py)
* [hna-agentic-engineering](https://github.com/policyme/hna-agentic-engineering)
* [ADR HNA 005 - AI-Native SDLC Context Registry](https://www.notion.so/3e281a5de32580c585ecd60c47514dcc)
* [HNA-937 AI-Native SDLC support](https://policyme.atlassian.net/browse/HNA-937)
* [life-restapi-main Makefile](https://github.com/policyme/life-restapi-main/blob/develop/Makefile)
* [global-restapi-crm Makefile](https://github.com/policyme/global-restapi-crm/blob/develop/Makefile)
* [Enable Pydantic endpoint validation (WARN mode) skill](https://github.com/policyme/global-pmagentic-engineering/blob/master/skills/cursor_enable-pydantic-validation-warn-mode/SKILL.md)

