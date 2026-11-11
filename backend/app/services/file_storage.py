"""In-memory stand-in for the S3 bucket that holds uploaded files (synthetic data only).

The function signatures match what a thin S3 wrapper would expose, so swapping in
boto3 later changes only this module.
"""

_objects: dict[str, bytes] = {}


def put_object(key: str, content: bytes) -> None:
    _objects[key] = content


def object_exists(key: str) -> bool:
    return key in _objects
