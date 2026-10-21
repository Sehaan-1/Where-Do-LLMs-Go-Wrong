from __future__ import annotations

from pathlib import Path

import pytest

from wdlw.io import DataFormatError, read_jsonl, refuse_existing, write_text_atomic
from wdlw.models import ResponseRecord

from .helpers import make_batch


def test_read_jsonl_reports_line_and_schema_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(DataFormatError, match=r"bad.jsonl:1: invalid ResponseRecord"):
        read_jsonl(path, ResponseRecord)


def test_atomic_write_replaces_complete_content(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "output.txt"
    write_text_atomic(path, "old\n")
    write_text_atomic(path, "new\n")
    assert path.read_text(encoding="utf-8") == "new\n"
    assert list(path.parent.glob("*.tmp")) == []


def test_refuse_existing_requires_explicit_force(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    path.write_text("do not replace", encoding="utf-8")
    with pytest.raises(DataFormatError, match="pass --force"):
        refuse_existing([path], force=False)
    refuse_existing([path], force=True)


def test_response_fixture_is_serializable() -> None:
    batch = make_batch(1)
    assert len(batch) == 2
