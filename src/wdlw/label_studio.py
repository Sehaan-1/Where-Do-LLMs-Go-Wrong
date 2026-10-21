"""Label Studio task projection and strict export normalization."""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from .io import DataFormatError, validation_summary
from .models import (
    ERROR_TYPES,
    SCHEMA_VERSION,
    UI_STATUSES,
    AnnotationRecord,
    ErrorType,
    LabelStudioTask,
    LabelStudioTaskData,
    ResponseRecord,
    StepAnnotation,
    UiStatus,
)
from .validation import index_response_batch, validate_annotation_file


class RawLabelStudioResult(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    from_name: str
    value: dict[str, list[str]]


class RawLabelStudioAnnotation(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    result: list[RawLabelStudioResult]
    completed_by: int | None = Field(default=None, ge=1)
    was_cancelled: bool = False


class RawLabelStudioTask(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    data: LabelStudioTaskData
    annotations: list[RawLabelStudioAnnotation] = Field(default_factory=list)


def build_label_studio_tasks(
    records: Sequence[ResponseRecord],
    *,
    sample_problems: int | None = None,
    seed: int = 2026,
) -> list[LabelStudioTask]:
    """Project response steps into blinded Label Studio tasks.

    When requested, sample whole problem groups so paired model conditions remain
    together in a double-annotation subset.
    """
    index_response_batch(records)
    if seed < 0:
        raise ValueError("seed must be non-negative")

    selected_records = list(records)
    if sample_problems is not None:
        if sample_problems < 1:
            raise ValueError("sample_problems must be at least 1")
        problem_ids = sorted({record.problem_id for record in records})
        if sample_problems > len(problem_ids):
            raise ValueError(
                f"sample_problems {sample_problems} exceeds available problems {len(problem_ids)}"
            )
        chosen = set(random.Random(seed).sample(problem_ids, sample_problems))
        selected_records = [record for record in records if record.problem_id in chosen]

    tasks: list[LabelStudioTask] = []
    for record in selected_records:
        for index, step in enumerate(record.steps):
            prior_steps = "\n".join(item.text for item in record.steps[:index])
            following_steps = "\n".join(item.text for item in record.steps[index + 1 :])
            tasks.append(
                LabelStudioTask(
                    data=LabelStudioTaskData(
                        response_id=record.response_id,
                        problem_id=record.problem_id,
                        step_id=step.step_id,
                        step_number=index + 1,
                        question=record.question,
                        reference_answer=record.reference_answer,
                        prior_steps=prior_steps,
                        current_step=step.text,
                        following_steps=following_steps,
                    )
                )
            )
    return tasks


def _single_choice(
    result_values: list[RawLabelStudioResult],
    name: str,
    *,
    required: bool,
    task_id: str,
) -> str | None:
    matches = [item for item in result_values if item.from_name == name]
    if not matches:
        if required:
            raise DataFormatError(f"Label Studio task {task_id}: missing {name!r} choice")
        return None
    if len(matches) != 1:
        raise DataFormatError(f"Label Studio task {task_id}: duplicate {name!r} result")
    choices = matches[0].value.get("choices", [])
    if len(choices) != 1:
        if not required and not choices:
            return None
        raise DataFormatError(
            f"Label Studio task {task_id}: {name!r} must contain exactly one choice"
        )
    return choices[0]


def _rationale(result_values: list[RawLabelStudioResult], task_id: str) -> str | None:
    matches = [item for item in result_values if item.from_name == "rationale"]
    if not matches:
        return None
    if len(matches) != 1:
        raise DataFormatError(f"Label Studio task {task_id}: duplicate 'rationale' result")
    text_values = matches[0].value.get("text", [])
    text = "\n".join(text_values).strip()
    return text or None


def _validate_task_context(
    task: RawLabelStudioTask,
    response: ResponseRecord,
    step_index: int,
) -> None:
    data = task.data
    step = response.steps[step_index]
    if data.problem_id != response.problem_id:
        raise DataFormatError(f"Label Studio task {response.response_id}: problem_id mismatch")
    if data.step_id != step.step_id or data.step_number != step_index + 1:
        raise DataFormatError(f"Label Studio task {response.response_id}: step identity mismatch")
    if data.question != response.question or data.reference_answer != response.reference_answer:
        raise DataFormatError(f"Label Studio task {response.response_id}: prompt context mismatch")
    if data.current_step != step.text:
        raise DataFormatError(f"Label Studio task {response.response_id}: current step was changed")
    expected_prior = "\n".join(item.text for item in response.steps[:step_index])
    expected_following = "\n".join(item.text for item in response.steps[step_index + 1 :])
    if data.prior_steps != expected_prior or data.following_steps != expected_following:
        raise DataFormatError(
            f"Label Studio task {response.response_id}: surrounding context mismatch"
        )


def normalize_label_studio_export(
    export_value: object,
    records: Sequence[ResponseRecord],
    *,
    annotator_id: str,
    guideline_version: str = "1.0",
    label_studio_user_id: int | None = None,
) -> list[AnnotationRecord]:
    """Normalize one annotator's Label Studio results into JSONL records.

    A shared Label Studio export can contain several annotations per task. In that
    case, provide the numeric `completed_by` value from the export to select one
    annotator; other users' tasks are skipped, not merged.
    """
    if label_studio_user_id is not None and label_studio_user_id < 1:
        raise ValueError("label_studio_user_id must be a positive integer")
    try:
        tasks = TypeAdapter(list[RawLabelStudioTask]).validate_python(export_value)
    except ValidationError as error:
        raise DataFormatError(
            f"invalid Label Studio export ({validation_summary(error)})"
        ) from error

    response_by_id = index_response_batch(records)
    response_order = {record.response_id: index for index, record in enumerate(records)}
    annotations_by_response: dict[str, dict[str, StepAnnotation]] = {}

    for task_number, task in enumerate(tasks, start=1):
        task_annotations = [
            annotation for annotation in task.annotations if not annotation.was_cancelled
        ]
        if not task_annotations:
            continue
        data = task.data
        if label_studio_user_id is None:
            if len(task_annotations) != 1:
                raise DataFormatError(
                    f"Label Studio task {data.response_id}/{data.step_id} has multiple "
                    "annotations; pass --label-studio-user-id from completed_by"
                )
            selected_annotation = task_annotations[0]
        else:
            candidates = [
                annotation
                for annotation in task_annotations
                if annotation.completed_by == label_studio_user_id
            ]
            if len(candidates) > 1:
                raise DataFormatError(
                    f"Label Studio task {data.response_id}/{data.step_id} has multiple "
                    f"annotations for user ID {label_studio_user_id}"
                )
            if not candidates:
                if any(annotation.completed_by is None for annotation in task_annotations):
                    raise DataFormatError(
                        f"Label Studio task {data.response_id}/{data.step_id} lacks "
                        "completed_by metadata needed for user filtering"
                    )
                continue
            selected_annotation = candidates[0]

        response = response_by_id.get(data.response_id)
        if response is None:
            raise DataFormatError(
                f"Label Studio task #{task_number}: unknown response_id {data.response_id!r}"
            )
        step_indices = {step.step_id: index for index, step in enumerate(response.steps)}
        step_index = step_indices.get(data.step_id)
        if step_index is None:
            raise DataFormatError(
                f"Label Studio task {data.response_id}: unknown step_id {data.step_id!r}"
            )
        _validate_task_context(task, response, step_index)

        result_values = selected_annotation.result
        allowed_names = {"status", "error_type", "rationale"}
        unknown_names = {item.from_name for item in result_values} - allowed_names
        if unknown_names:
            unknown_text = ", ".join(sorted(unknown_names))
            raise DataFormatError(
                f"Label Studio task {data.response_id}/{data.step_id}: "
                f"unexpected result field(s): {unknown_text}"
            )

        status_value = _single_choice(
            result_values,
            "status",
            required=True,
            task_id=f"{data.response_id}/{data.step_id}",
        )
        if status_value not in UI_STATUSES:
            raise DataFormatError(
                f"Label Studio task {data.response_id}/{data.step_id}: "
                f"unknown status {status_value!r}"
            )
        status = cast(UiStatus, status_value)
        error_type_value = _single_choice(
            result_values,
            "error_type",
            required=status == "first_error",
            task_id=f"{data.response_id}/{data.step_id}",
        )
        if status == "first_error":
            if error_type_value not in ERROR_TYPES:
                raise DataFormatError(
                    f"Label Studio task {data.response_id}/{data.step_id}: "
                    f"unknown error type {error_type_value!r}"
                )
            error_type: ErrorType | None = cast(ErrorType, error_type_value)
        else:
            if error_type_value is not None:
                raise DataFormatError(
                    f"Label Studio task {data.response_id}/{data.step_id}: "
                    "error_type is only allowed for first_error"
                )
            error_type = None

        verdict_by_status: dict[UiStatus, Literal["correct", "incorrect", "uncertain"]] = {
            "correct": "correct",
            "first_error": "incorrect",
            "downstream_error": "incorrect",
            "uncertain": "uncertain",
        }
        step_annotation = StepAnnotation(
            step_id=data.step_id,
            verdict=verdict_by_status[status],
            is_first_error=status == "first_error",
            error_type=error_type,
            rationale=_rationale(result_values, f"{data.response_id}/{data.step_id}"),
        )
        response_annotations = annotations_by_response.setdefault(data.response_id, {})
        if data.step_id in response_annotations:
            raise DataFormatError(
                f"Label Studio export duplicates task {data.response_id}/{data.step_id}"
            )
        response_annotations[data.step_id] = step_annotation

    normalized: list[AnnotationRecord] = []
    ordered_response_ids = sorted(annotations_by_response, key=response_order.__getitem__)
    for response_id in ordered_response_ids:
        response = response_by_id[response_id]
        step_map = annotations_by_response[response_id]
        expected_step_ids = [step.step_id for step in response.steps]
        if set(step_map) != set(expected_step_ids):
            missing = sorted(set(expected_step_ids) - set(step_map))
            extra = sorted(set(step_map) - set(expected_step_ids))
            raise DataFormatError(
                f"Label Studio response {response_id} must include every step; "
                f"missing={missing}, extra={extra}"
            )
        try:
            annotation = AnnotationRecord(
                schema_version=SCHEMA_VERSION,
                response_id=response_id,
                annotator_id=annotator_id,
                guideline_version=guideline_version,
                step_annotations=[step_map[step_id] for step_id in expected_step_ids],
            )
        except ValidationError as error:
            raise DataFormatError(
                f"invalid annotations for response {response_id} ({validation_summary(error)})"
            ) from error
        normalized.append(annotation)

    if not normalized:
        raise DataFormatError("Label Studio export contains no completed annotation tasks")
    validate_annotation_file(normalized, response_by_id)
    return normalized
