from __future__ import annotations

import json
from pathlib import Path

import pytest

from wdlw.io import DataFormatError, serialize_jsonl
from wdlw.prepare import (
    parse_model_final_answer,
    parse_reference_answer,
    prepare_dataset,
    split_response_steps,
)

TEST_SOURCE_REVISION = "f" * 40


def write_source_files(directory: Path, *, mismatch_question: bool = False) -> tuple[Path, Path]:
    test_path = directory / "test.jsonl"
    solutions_path = directory / "example_model_solutions.jsonl"
    tests: list[dict[str, object]] = []
    solutions: list[dict[str, object]] = []
    for index in range(5):
        question = f"There are {index + 1} apples. How many?"
        tests.append({"question": question, "answer": f"Counted apples.\n#### {index + 1}"})
        solutions.append(
            {
                "question": f"Different question {index}"
                if mismatch_question and index == 2
                else question,
                "ground_truth": f"Counted apples.\nA: {index + 1}",
                "6b_finetuning": {
                    "is_correct": index % 2 == 0,
                    "solution": f"There are {index + 1}.\nA: {index + 1}",
                },
                "175b_finetuning": {
                    "is_correct": True,
                    "solution": f"Count = {index + 1}\nA: {index + 1}",
                },
            }
        )
    test_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in tests),
        encoding="utf-8",
    )
    solutions_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in solutions),
        encoding="utf-8",
    )
    return test_path, solutions_path


def test_default_revision_requires_exact_pinned_source_hashes(tmp_path: Path) -> None:
    test_path, solutions_path = write_source_files(tmp_path)
    with pytest.raises(DataFormatError, match="do not match the default pinned revision"):
        prepare_dataset(test_path, solutions_path, sample_size=1)


def test_prepare_is_deterministic_and_pairs_model_conditions(tmp_path: Path) -> None:
    test_path, solutions_path = write_source_files(tmp_path)
    records_a, manifest_a = prepare_dataset(
        test_path,
        solutions_path,
        sample_size=3,
        seed=44,
        source_revision=TEST_SOURCE_REVISION,
    )
    records_b, manifest_b = prepare_dataset(
        test_path,
        solutions_path,
        sample_size=3,
        seed=44,
        source_revision=TEST_SOURCE_REVISION,
    )

    assert serialize_jsonl(records_a) == serialize_jsonl(records_b)
    assert manifest_a == manifest_b
    assert len(records_a) == 6
    assert manifest_a.counts.problems == 3
    assert manifest_a.source_population_rows == 5
    assert manifest_a.counts.responses == 6
    assert len({record.problem_id for record in records_a}) == 3
    assert [record.model_id for record in records_a[:2]] == [
        "6b_finetuning",
        "175b_finetuning",
    ]
    assert all(record.source.revision == TEST_SOURCE_REVISION for record in records_a)
    assert all(record.steps[-1].text.startswith("A:") for record in records_a)


def test_prepare_fails_closed_on_question_misalignment(tmp_path: Path) -> None:
    test_path, solutions_path = write_source_files(tmp_path, mismatch_question=True)
    with pytest.raises(DataFormatError, match="question mismatch at row 3"):
        prepare_dataset(
            test_path, solutions_path, sample_size=2, source_revision=TEST_SOURCE_REVISION
        )


def test_prepare_rejects_reference_answer_mismatch(tmp_path: Path) -> None:
    test_path, solutions_path = write_source_files(tmp_path)
    rows = [json.loads(line) for line in solutions_path.read_text(encoding="utf-8").splitlines()]
    rows[1]["ground_truth"] = "A: 99"
    solutions_path.write_text(
        "".join(json.dumps(item) + "\n" for item in rows),
        encoding="utf-8",
    )
    with pytest.raises(DataFormatError, match="reference answer mismatch at row 2"):
        prepare_dataset(
            test_path, solutions_path, sample_size=2, source_revision=TEST_SOURCE_REVISION
        )


def test_prepare_validates_model_fields_even_outside_sample(tmp_path: Path) -> None:
    test_path, solutions_path = write_source_files(tmp_path)
    rows = [json.loads(line) for line in solutions_path.read_text(encoding="utf-8").splitlines()]
    del rows[0]["6b_finetuning"]
    solutions_path.write_text(
        "".join(json.dumps(item) + "\n" for item in rows),
        encoding="utf-8",
    )
    # Seed 0 selects source index 3 from five rows, so source index 0 is not sampled.
    with pytest.raises(DataFormatError, match=":1: missing selected model field"):
        prepare_dataset(
            test_path, solutions_path, sample_size=1, seed=0, source_revision=TEST_SOURCE_REVISION
        )


def test_prepare_rejects_row_count_mismatch(tmp_path: Path) -> None:
    test_path, solutions_path = write_source_files(tmp_path)
    solutions_path.write_text(
        "\n".join(solutions_path.read_text(encoding="utf-8").splitlines()[:-1]) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(DataFormatError, match="different row counts"):
        prepare_dataset(
            test_path, solutions_path, sample_size=2, source_revision=TEST_SOURCE_REVISION
        )


def test_answer_extractors_and_step_segmentation() -> None:
    assert parse_reference_answer("work\n#### 70,000\n") == "70,000"
    assert parse_model_final_answer("work\nA: 70,000\n") == "70,000"
    assert parse_model_final_answer("work\nNo answer marker") is None
    steps = split_response_steps("  first line  \n\n second line \n")
    assert [(step.step_id, step.text) for step in steps] == [
        ("step-001", "first line"),
        ("step-002", "second line"),
    ]
