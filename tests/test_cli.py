from __future__ import annotations

import json
from pathlib import Path

from wdlw.cli import main
from wdlw.io import serialize_jsonl

from .helpers import make_batch


def test_verbose_cli_emits_correlated_structured_events(
    tmp_path: Path,
    capsys: object,
) -> None:
    batch_path = tmp_path / "batch.jsonl"
    batch_path.write_text(serialize_jsonl(make_batch(1)), encoding="utf-8")

    assert main(["--verbose", "validate", "--batch", str(batch_path)]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    events = [json.loads(line) for line in captured.err.splitlines()]

    assert [event["event"] for event in events] == [
        "command.started",
        "batch.validated",
        "command.completed",
    ]
    assert len({event["run_id"] for event in events}) == 1
    assert all(event["command"] == "validate" for event in events)
    assert "how many pencils" not in captured.err
    assert json.loads(captured.out)["valid"] is True


def test_prepare_cannot_overwrite_input_even_with_force(tmp_path: Path, capsys: object) -> None:
    test_path = tmp_path / "test.jsonl"
    solutions_path = tmp_path / "solutions.jsonl"
    manifest_path = tmp_path / "manifest.json"
    original = "source must remain intact"
    test_path.write_text(original, encoding="utf-8")

    exit_code = main(
        [
            "prepare",
            "--test-jsonl",
            str(test_path),
            "--solutions-jsonl",
            str(solutions_path),
            "--output",
            str(test_path),
            "--manifest",
            str(manifest_path),
            "--force",
        ]
    )
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert exit_code == 2
    assert "must not overwrite input" in captured.err
    assert test_path.read_text(encoding="utf-8") == original


def test_verbose_cli_logs_failure_without_stack_trace(tmp_path: Path, capsys: object) -> None:
    missing_batch = tmp_path / "missing.jsonl"
    assert main(["--verbose", "validate", "--batch", str(missing_batch)]) == 2
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    events = [json.loads(line) for line in captured.err.splitlines() if line.startswith("{")]

    assert [event["event"] for event in events] == ["command.started", "command.failed"]
    assert "cannot open" in events[-1]["details"]["message"]
    assert "Traceback" not in captured.err
