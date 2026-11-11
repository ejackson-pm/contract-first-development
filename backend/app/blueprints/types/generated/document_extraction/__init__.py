"""Pydantic models generated from openapi/document_extraction.yaml by `make generate-types`.

DO NOT EDIT. Change the spec and regenerate. Manual edits are overwritten on the
next generation and caught by `make check-types`.

Usage rules
-----------
* Strict types: fields use StrictStr / StrictInt / strict constraints, so values
  are never coerced. "5" is rejected for an integer field. Use these models for
  JSON request bodies and responses only. Query-string and path values always
  arrive as strings: parse them with a hand-written model in
  app/blueprints/types/ (lax types), or declare them as `type: string` in the spec.
* Dates: `format: date` / `format: date-time` become date / datetime. They are
  rendered as ISO 8601 by app.utils.json_provider.PMJSONProvider. Return models
  (or dicts containing them) through jsonify; never format dates by hand.
* Aliases: if the spec uses camelCase names, fields are snake_case with an alias.
  Serialise with by_alias=True (PMJSONProvider already does).
* Customisation: subclass a generated model in a hand-written module. Never edit here.
"""
