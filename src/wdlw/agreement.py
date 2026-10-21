"""Inter-annotator agreement and first-error location summaries."""

from __future__ import annotations

from collections.abc import Sequence

from .metrics import KappaResult, cohen_kappa
from .models import ERROR_TYPES, UI_STATUSES, AnnotationRecord, ResponseRecord, StepAnnotation
from .validation import index_response_batch, validate_annotation_file


def _ui_status(step: StepAnnotation) -> str:
    if step.verdict == "correct":
        return "correct"
    if step.verdict == "uncertain":
        return "uncertain"
    return "first_error" if step.is_first_error else "downstream_error"


def _first_error_step(annotation: AnnotationRecord) -> str | None:
    for step in annotation.step_annotations:
        if step.is_first_error:
            return step.step_id
    return None


def build_agreement_report(
    records: Sequence[ResponseRecord],
    annotations_a: Sequence[AnnotationRecord],
    annotations_b: Sequence[AnnotationRecord],
) -> dict[str, object]:
    """Compare two independent annotation files on exact response-step matches."""
    response_by_id = index_response_batch(records)
    info_a = validate_annotation_file(annotations_a, response_by_id)
    info_b = validate_annotation_file(annotations_b, response_by_id)
    if info_a.annotator_id == info_b.annotator_id:
        raise ValueError("agreement requires two different annotator IDs")

    annotation_map_a = {item.response_id: item for item in annotations_a}
    annotation_map_b = {item.response_id: item for item in annotations_b}
    response_order = {record.response_id: index for index, record in enumerate(records)}
    common_response_ids = sorted(
        set(annotation_map_a) & set(annotation_map_b), key=response_order.__getitem__
    )
    if not common_response_ids:
        raise ValueError("annotators have no overlapping response annotations")

    labels_a: list[str] = []
    labels_b: list[str] = []
    error_types_a: list[str] = []
    error_types_b: list[str] = []
    location_matches = 0
    matched_step_count = 0

    for response_id in common_response_ids:
        annotation_a = annotation_map_a[response_id]
        annotation_b = annotation_map_b[response_id]
        if len(annotation_a.step_annotations) != len(annotation_b.step_annotations):
            raise ValueError(f"annotators have different step counts for {response_id}")
        for step_a, step_b in zip(
            annotation_a.step_annotations,
            annotation_b.step_annotations,
            strict=True,
        ):
            if step_a.step_id != step_b.step_id:
                raise ValueError(f"annotators' step order differs for {response_id}")
            labels_a.append(_ui_status(step_a))
            labels_b.append(_ui_status(step_b))
            matched_step_count += 1
            if step_a.is_first_error and step_b.is_first_error:
                if step_a.error_type is None or step_b.error_type is None:
                    raise ValueError("first-error annotations must include an error type")
                error_types_a.append(step_a.error_type)
                error_types_b.append(step_b.error_type)

        if _first_error_step(annotation_a) == _first_error_step(annotation_b):
            location_matches += 1

    status_result: KappaResult = cohen_kappa(labels_a, labels_b, UI_STATUSES)
    error_type_result = cohen_kappa(error_types_a, error_types_b, ERROR_TYPES)
    total_steps_a = sum(len(item.step_annotations) for item in annotations_a)
    total_steps_b = sum(len(item.step_annotations) for item in annotations_b)
    total_responses_a = len(annotations_a)
    total_responses_b = len(annotations_b)

    return {
        "schema_version": "1.0",
        "annotators": {
            "a": {
                "annotator_id": info_a.annotator_id,
                "guideline_version": info_a.guideline_version,
            },
            "b": {
                "annotator_id": info_b.annotator_id,
                "guideline_version": info_b.guideline_version,
            },
        },
        "coverage": {
            "annotated_responses_a": total_responses_a,
            "annotated_responses_b": total_responses_b,
            "matched_responses": len(common_response_ids),
            "responses_only_a": total_responses_a - len(common_response_ids),
            "responses_only_b": total_responses_b - len(common_response_ids),
            "matched_steps": matched_step_count,
            "steps_only_a": total_steps_a - matched_step_count,
            "steps_only_b": total_steps_b - matched_step_count,
        },
        "step_status": status_result.to_dict(),
        "first_error_location": {
            "responses_compared": len(common_response_ids),
            "exact_matches": location_matches,
            "agreement": location_matches / len(common_response_ids),
        },
        "first_error_type_when_location_matches": error_type_result.to_dict(),
    }
