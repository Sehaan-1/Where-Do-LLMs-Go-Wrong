"""Small synthetic records shared by unit and contract tests."""

from __future__ import annotations

from collections.abc import Sequence

from wdlw.models import (
    SCHEMA_VERSION,
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    AnnotationRecord,
    ErrorType,
    ModelId,
    ResponseRecord,
    SourceMetadata,
    Step,
    StepAnnotation,
    UiStatus,
    Verdict,
)


def make_response(
    response_number: int,
    problem_index: int,
    model_id: ModelId,
    *,
    lines: Sequence[str] | None = None,
    answer_correct: bool = False,
) -> ResponseRecord:
    """Create one schema-valid synthetic response record."""
    if lines is None:
        lines = ("12 + 3 = 15", "15 - 4 = 10", "A: 10")
    steps = [
        Step(step_id=f"step-{index:03d}", text=text) for index, text in enumerate(lines, start=1)
    ]
    return ResponseRecord(
        schema_version=SCHEMA_VERSION,
        response_id=f"resp-{response_number:06d}",
        problem_id=f"gsm8k-test-{problem_index:07d}",
        source_index=problem_index,
        model_id=model_id,
        question=f"Problem {problem_index}: how many pencils remain?",
        reference_solution="12 + 3 = 15\n15 - 4 = 11\n#### 11",
        reference_answer="11",
        model_response="\n".join(lines),
        model_final_answer=lines[-1].removeprefix("A: ").strip(),
        answer_correct=answer_correct,
        steps=steps,
        source=SourceMetadata(
            dataset="gsm8k",
            split="test",
            repository=SOURCE_REPOSITORY,
            revision=SOURCE_REVISION,
            model_field=model_id,
        ),
    )


def make_annotation(
    response: ResponseRecord,
    annotator_id: str,
    statuses: Sequence[UiStatus],
    *,
    error_type: ErrorType = "arithmetic_error",
    guideline_version: str = "1.0",
) -> AnnotationRecord:
    """Create a valid normalized annotation for a complete response."""
    if len(statuses) != len(response.steps):
        raise ValueError("test statuses must align with response steps")
    annotations: list[StepAnnotation] = []
    for step, status in zip(response.steps, statuses, strict=True):
        is_first_error = status == "first_error"
        verdict: Verdict = (
            "correct"
            if status == "correct"
            else "uncertain"
            if status == "uncertain"
            else "incorrect"
        )
        annotations.append(
            StepAnnotation(
                step_id=step.step_id,
                verdict=verdict,
                is_first_error=is_first_error,
                error_type=error_type if is_first_error else None,
                rationale=None,
            )
        )
    return AnnotationRecord(
        schema_version=SCHEMA_VERSION,
        response_id=response.response_id,
        annotator_id=annotator_id,
        guideline_version=guideline_version,
        step_annotations=annotations,
    )


def make_batch(problem_count: int = 2) -> list[ResponseRecord]:
    """Create paired response conditions with shared problem metadata."""
    records: list[ResponseRecord] = []
    response_number = 1
    model_ids: tuple[ModelId, ModelId] = ("6b_finetuning", "175b_finetuning")
    for problem_index in range(problem_count):
        for model_index, model_id in enumerate(model_ids):
            if problem_index == 0 and model_index == 0:
                lines = ("12 + 3 = 15", "15 - 4 = 10", "A: 10")
                correct = False
            else:
                lines = ("12 + 3 = 15", "15 - 4 = 11", "A: 11")
                correct = True
            records.append(
                make_response(
                    response_number,
                    problem_index,
                    model_id,
                    lines=lines,
                    answer_correct=correct,
                )
            )
            response_number += 1
    return records
