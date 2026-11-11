include .env
export

# =============================================================================
# Environment
# =============================================================================

PYTHON ?= python3.11
VENV_DIR := .venv
VENV_SHELL := . $(VENV_DIR)/bin/activate &&
TEST_FLAGS ?=

.DEFAULT_GOAL := help

.PHONY: help install run

help:
	@echo "Setup:"
	@echo "  install          Create the venv and install runtime and dev dependencies"
	@echo ""
	@echo "Application Execution:"
	@echo "  run              Run the API on http://127.0.0.1:5000"
	@echo ""
	@echo "Code Generation:"
	@echo "  validate-openapi Validate the OpenAPI spec"
	@echo "  generate-types   Generate Pydantic types from OPENAPI_SPEC"
	@echo "  check-types      Fail if generated types are out of date"
	@echo ""
	@echo "Snapshot Tests:"
	@echo "  test-snapshots   Run blueprint snapshot tests"
	@echo "  update-snapshots Re-record snapshots after an intentional change"
	@echo ""
	@echo "Pass extra pytest flags with TEST_FLAGS, e.g. make test-snapshots TEST_FLAGS=-vv"

$(VENV_DIR):
	$(PYTHON) -m venv $(VENV_DIR)

install: $(VENV_DIR)
	$(VENV_SHELL) pip install -r requirements.txt -r requirements-dev.txt

# =============================================================================
# Application Execution
# =============================================================================

run: $(VENV_DIR)
	$(VENV_SHELL) python3 application.py

# =============================================================================
# OpenAPI -> Pydantic Type Generation
# =============================================================================

# Override per spec, e.g. make generate-types OPENAPI_SPEC=openapi/payments.yaml OPENAPI_TYPES_NAME=payments
OPENAPI_SPEC ?= openapi/document_extraction.yaml
OPENAPI_TYPES_NAME ?= document_extraction
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

# Fail if the committed types are out of date with the spec
check-types: generate-types
	@git diff --exit-code -- $(OPENAPI_TYPES_DIR) && \
	test -z "$$(git status --porcelain -- $(OPENAPI_TYPES_DIR))" || \
	(echo "Generated types are stale: run make generate-types and commit the result." && exit 1)

# =============================================================================
# Testing and Quality Assurance
# =============================================================================

PYTEST_PACKAGES_INSTALLED := $(shell \
	test -d $(VENV_DIR) && \
	$(VENV_DIR)/bin/python -c "import pytest, syrupy" 2>/dev/null && \
	echo "installed" || \
	echo "not_installed" \
)

.PHONY: check-pytest-packages test-snapshots update-snapshots

# Install pytest and syrupy (requirements-dev.txt) if needed
check-pytest-packages: $(VENV_DIR)
	@if [ "$(PYTEST_PACKAGES_INSTALLED)" != "installed" ]; then \
		echo "pytest or syrupy not found, installing development dependencies..."; \
		$(MAKE) install; \
	fi

# Run blueprint snapshot tests (syrupy marks every test that uses the snapshot fixture)
test-snapshots: check-pytest-packages
	@echo "Running snapshot tests..."
	$(VENV_SHELL) python3 -m pytest tests/integration_tests/ -m syrupy_snapshot $(TEST_FLAGS)

# Re-record snapshots after an intentional change; review the diff before committing
update-snapshots: check-pytest-packages
	@echo "Updating snapshots..."
	$(VENV_SHELL) python3 -m pytest tests/integration_tests/ -m syrupy_snapshot --snapshot-update $(TEST_FLAGS)
