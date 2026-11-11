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
