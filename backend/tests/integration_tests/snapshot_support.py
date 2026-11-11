"""Shared types and helpers for blueprint snapshot tests."""
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Optional

from flask.testing import FlaskClient
from pydantic import BaseModel


@dataclass(frozen=True)
class UploadFile:
    """A file sent as the `file` field of a multipart/form-data request."""

    filename: str
    content: bytes
    content_type: str


@dataclass(frozen=True)
class BlueprintRequest:
    """One request to run against a blueprint.

    JSON bodies are generated request types. Multipart uploads have no generated
    type (the spec types them as binary), so they use UploadFile.
    """

    method: str
    path: str
    body: Optional[BaseModel] = None
    file: Optional[UploadFile] = None

    def client_kwargs(self) -> dict[str, Any]:
        """Keyword arguments for FlaskClient.open() that send this request's payload."""
        if self.file is not None:
            # Build the stream per call: the test client consumes it.
            upload = (BytesIO(self.file.content), self.file.filename, self.file.content_type)
            return {"data": {"file": upload}, "content_type": "multipart/form-data"}
        if self.body is not None:
            return {"json": self.body.model_dump(mode="json", by_alias=True, exclude_none=True)}
        return {}


def run_request(client: FlaskClient, case: BlueprintRequest) -> dict[str, Any]:
    """Send one case through the test client and return what the snapshot records."""
    response = client.open(case.path, method=case.method, **case.client_kwargs())
    return {"status_code": response.status_code, "body": response.get_json()}
