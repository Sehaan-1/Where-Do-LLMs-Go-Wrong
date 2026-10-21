"""Validated JSON/JSONL input, deterministic serialization, and atomic writes."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class DataFormatError(ValueError):
    """Raised when a source or annotation file violates its documented format."""


def validation_summary(error: ValidationError) -> str:
    """Render Pydantic errors without echoing submitted record contents."""
    messages: list[str] = []
    for item in error.errors(include_input=False, include_url=False):
        location = ".".join(str(part) for part in item.get("loc", ())) or "record"
        messages.append(f"{location}: {item.get('msg', 'invalid value')}")
    return "; ".join(messages)


def read_jsonl(path: Path, record_type: type[T]) -> list[T]:
    """Read and validate every non-empty JSONL line, reporting its location."""
    records: list[T] = []
    try:
        source = path.open("r", encoding="utf-8")
    except OSError as error:
        raise DataFormatError(f"cannot open {path}: {error}") from error

    with source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                raise DataFormatError(f"{path}:{line_number}: blank lines are not allowed")
            try:
                raw: object = json.loads(line)
            except json.JSONDecodeError as error:
                raise DataFormatError(
                    f"{path}:{line_number}: invalid JSON at column {error.colno}"
                ) from error
            try:
                records.append(record_type.model_validate(raw))
            except ValidationError as error:
                raise DataFormatError(
                    f"{path}:{line_number}: invalid {record_type.__name__} "
                    f"({validation_summary(error)})"
                ) from error
    return records


def read_json(path: Path) -> object:
    """Read one JSON value while keeping third-party exports untrusted."""
    try:
        with path.open("r", encoding="utf-8") as source:
            return json.load(source)
    except json.JSONDecodeError as error:
        raise DataFormatError(
            f"{path}: invalid JSON at line {error.lineno}, column {error.colno}"
        ) from error
    except OSError as error:
        raise DataFormatError(f"cannot read {path}: {error}") from error


def serialize_jsonl(records: Iterable[BaseModel]) -> str:
    """Serialize Pydantic records as compact UTF-8 JSONL with a final newline."""
    lines = [
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for record in records
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def serialize_json(value: BaseModel | Sequence[BaseModel] | dict[str, object]) -> str:
    """Serialize a domain model, a model sequence, or a JSON-compatible mapping."""
    if isinstance(value, BaseModel):
        payload: object = value.model_dump(mode="json")
    elif isinstance(value, dict):
        payload = value
    else:
        payload = [record.model_dump(mode="json") for record in value]
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_text_atomic(path: Path, content: str) -> None:
    """Replace a text file atomically after fully writing its new contents."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as target:
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary_name, path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary_name)
            raise
    except OSError as error:
        raise DataFormatError(f"cannot atomically write {path}: {error}") from error


def sha256_file(path: Path) -> str:
    """Hash a file incrementally without loading source datasets into memory."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise DataFormatError(f"cannot hash {path}: {error}") from error
    return digest.hexdigest()


def refuse_existing(paths: Sequence[Path], force: bool) -> None:
    """Prevent accidental replacement of seed batches or raw annotator files."""
    if force:
        return
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        joined = ", ".join(existing)
        raise DataFormatError(f"refusing to overwrite existing output(s): {joined}; pass --force")
