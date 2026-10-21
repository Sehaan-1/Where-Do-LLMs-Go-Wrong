"""Deterministic preparation of the paired GSM8K annotation seed batch."""

from __future__ import annotations

import hashlib
import random
import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .io import DataFormatError, read_jsonl, serialize_jsonl, sha256_file, validation_summary
from .models import (
    MODEL_IDS,
    PINNED_SOURCE_FILE_HASHES,
    SCHEMA_VERSION,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    BatchCounts,
    CorrectnessCounts,
    DatasetManifest,
    ModelId,
    ResponseRecord,
    SourceFileHash,
    SourceMetadata,
    Step,
)
from .text import (
    answers_equivalent,
    extract_model_final_answer,
    extract_reference_answer,
    split_nonempty_lines,
)


class UpstreamTestRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class UpstreamSolutionsRow(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    question: str = Field(min_length=1)
    ground_truth: str = Field(min_length=1)


class UpstreamModelTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    is_correct: bool
    solution: str = Field(min_length=1)


def parse_reference_answer(reference_solution: str) -> str:
    """Compatibility name for extracting a GSM8K reference answer."""
    return extract_reference_answer(reference_solution)


def parse_model_final_answer(model_response: str) -> str | None:
    """Compatibility name for extracting an upstream model answer."""
    return extract_model_final_answer(model_response)


def split_response_steps(model_response: str) -> list[Step]:
    """Use non-empty source lines as annotation units without rewriting their contents."""
    step_texts = split_nonempty_lines(model_response)
    return [
        Step(step_id=f"step-{index:03d}", text=text)
        for index, text in enumerate(step_texts, start=1)
    ]


def _source_model_trace(
    row: UpstreamSolutionsRow,
    model_id: ModelId,
    path: Path,
    line_number: int,
) -> UpstreamModelTrace:
    extras = row.model_extra or {}
    raw_trace: object = extras.get(model_id)
    if raw_trace is None:
        raise DataFormatError(f"{path}:{line_number}: missing selected model field {model_id!r}")
    try:
        return UpstreamModelTrace.model_validate(raw_trace)
    except ValidationError as error:
        raise DataFormatError(
            f"{path}:{line_number}: invalid model field {model_id!r} ({validation_summary(error)})"
        ) from error


def prepare_dataset(
    test_path: Path,
    solutions_path: Path,
    *,
    sample_size: int = 150,
    seed: int = 2026,
    source_revision: str = SOURCE_REVISION,
    source_repository: str = SOURCE_REPOSITORY,
) -> tuple[list[ResponseRecord], DatasetManifest]:
    """Build a reproducible paired sample and its provenance manifest."""
    if sample_size < 1:
        raise ValueError("sample_size must be at least 1")
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ValueError("source_revision must be a 40-character lowercase Git commit hash")
    if not source_repository.startswith("https://"):
        raise ValueError("source_repository must use HTTPS")

    test_hash = sha256_file(test_path)
    solutions_hash = sha256_file(solutions_path)
    if source_revision == SOURCE_REVISION and (
        test_hash != PINNED_SOURCE_FILE_HASHES["test"]
        or solutions_hash != PINNED_SOURCE_FILE_HASHES["example_model_solutions"]
    ):
        raise DataFormatError(
            "source file hashes do not match the default pinned revision; "
            "pass --source-revision for the actual source checkout"
        )

    test_rows = read_jsonl(test_path, UpstreamTestRow)
    solution_rows = read_jsonl(solutions_path, UpstreamSolutionsRow)
    if len(test_rows) != len(solution_rows):
        raise DataFormatError(
            "source files have different row counts: "
            f"{test_path} has {len(test_rows)}, {solutions_path} has {len(solution_rows)}"
        )
    if sample_size > len(test_rows):
        raise ValueError(
            f"sample_size {sample_size} exceeds available source rows {len(test_rows)}"
        )
    if len(test_rows) == 0:
        raise DataFormatError("source files contain no records")

    validated_rows: list[tuple[UpstreamTestRow, str, dict[ModelId, UpstreamModelTrace]]] = []
    for index, (test_row, solution_row) in enumerate(
        zip(test_rows, solution_rows, strict=True), start=1
    ):
        if test_row.question != solution_row.question:
            raise DataFormatError(
                f"source question mismatch at row {index}: {test_path} and {solutions_path}"
            )
        try:
            reference_answer = parse_reference_answer(test_row.answer)
        except ValueError as error:
            raise DataFormatError(
                f"{test_path}:{index}: invalid reference answer ({error})"
            ) from error
        source_reference_answer = parse_model_final_answer(solution_row.ground_truth)
        if source_reference_answer is None:
            raise DataFormatError(f"{solutions_path}:{index}: ground_truth has no final A: answer")
        if not answers_equivalent(reference_answer, source_reference_answer):
            raise DataFormatError(
                f"source reference answer mismatch at row {index}: {test_path} and {solutions_path}"
            )
        traces: dict[ModelId, UpstreamModelTrace] = {}
        for model_id in MODEL_IDS:
            trace = _source_model_trace(solution_row, model_id, solutions_path, index)
            if not split_response_steps(trace.solution):
                raise DataFormatError(
                    f"{solutions_path}:{index}: model field {model_id!r} has no steps"
                )
            traces[model_id] = trace
        validated_rows.append((test_row, reference_answer, traces))

    selected_indices = sorted(random.Random(seed).sample(range(len(validated_rows)), sample_size))
    records: list[ResponseRecord] = []
    correctness_by_model: dict[ModelId, Counter[bool]] = {
        model_id: Counter() for model_id in MODEL_IDS
    }
    response_number = 1

    for source_index in selected_indices:
        test_row, reference_answer, model_traces = validated_rows[source_index]
        problem_id = f"gsm8k-test-{source_index:07d}"
        for model_id in MODEL_IDS:
            model_trace = model_traces[model_id]
            steps = split_response_steps(model_trace.solution)
            if not steps:
                raise DataFormatError(
                    f"{solutions_path}:{source_index + 1}: model field {model_id!r} has no steps"
                )
            try:
                record = ResponseRecord(
                    schema_version=SCHEMA_VERSION,
                    response_id=f"resp-{response_number:06d}",
                    problem_id=problem_id,
                    source_index=source_index,
                    model_id=model_id,
                    question=test_row.question,
                    reference_solution=test_row.answer,
                    reference_answer=reference_answer,
                    model_response=model_trace.solution,
                    model_final_answer=parse_model_final_answer(model_trace.solution),
                    answer_correct=model_trace.is_correct,
                    steps=steps,
                    source=SourceMetadata(
                        dataset="gsm8k",
                        split="test",
                        repository=source_repository,
                        revision=source_revision,
                        model_field=model_id,
                    ),
                )
            except ValidationError as error:
                raise DataFormatError(
                    f"{solutions_path}:{source_index + 1}: invalid response for {model_id!r} "
                    f"({validation_summary(error)})"
                ) from error
            records.append(record)
            correctness_by_model[model_id][model_trace.is_correct] += 1
            response_number += 1

    serialized_batch = serialize_jsonl(records)
    batch_hash = hashlib.sha256(serialized_batch.encode("utf-8")).hexdigest()
    manifest = DatasetManifest(
        schema_version=SCHEMA_VERSION,
        source_repository=source_repository,
        source_revision=source_revision,
        source_files={
            "test": SourceFileHash(
                filename=test_path.name,
                sha256=test_hash,
            ),
            "example_model_solutions": SourceFileHash(
                filename=solutions_path.name,
                sha256=solutions_hash,
            ),
        },
        sampling_method="simple_random_sample_without_replacement",
        seed=seed,
        source_population_rows=len(validated_rows),
        sample_size_problems=sample_size,
        selected_source_indices=selected_indices,
        selected_model_ids=list(MODEL_IDS),
        counts=BatchCounts(
            problems=sample_size,
            responses=len(records),
            steps=sum(len(record.steps) for record in records),
            model_final_answers_missing=sum(
                record.model_final_answer is None for record in records
            ),
        ),
        answer_correct_by_model={
            model_id: CorrectnessCounts(
                total=sample_size,
                correct=correctness_by_model[model_id][True],
                incorrect=correctness_by_model[model_id][False],
            )
            for model_id in MODEL_IDS
        },
        seed_batch_sha256=batch_hash,
    )
    return records, manifest
