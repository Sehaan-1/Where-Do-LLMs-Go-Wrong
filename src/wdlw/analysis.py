"""Descriptive summaries separating upstream answer correctness from human labels."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .models import AnnotationRecord, ResponseRecord, StepAnnotation
from .validation import index_response_batch, validate_annotation_file


def _status(step: StepAnnotation) -> str:
    if step.verdict == "correct":
        return "correct"
    if step.verdict == "uncertain":
        return "uncertain"
    return "first_error" if step.is_first_error else "downstream_error"


def build_analysis_report(
    records: Sequence[ResponseRecord],
    annotations: Sequence[AnnotationRecord],
) -> dict[str, object]:
    """Summarize source answer metadata and annotation outcomes as separate measures."""
    response_by_id = index_response_batch(records)
    annotation_info = validate_annotation_file(annotations, response_by_id)
    annotation_by_response = {item.response_id: item for item in annotations}

    source_accuracy: dict[str, object] = {}
    annotated_by_model: dict[str, object] = {}
    models = sorted({record.model_id for record in records})

    for model_id in models:
        model_records = [record for record in records if record.model_id == model_id]
        correct_count = sum(record.answer_correct for record in model_records)
        source_accuracy[model_id] = {
            "responses": len(model_records),
            "source_correct": correct_count,
            "source_incorrect": len(model_records) - correct_count,
            "source_accuracy": correct_count / len(model_records),
        }

        model_annotations: list[tuple[ResponseRecord, AnnotationRecord]] = []
        for response in model_records:
            annotation = annotation_by_response.get(response.response_id)
            if annotation is not None:
                model_annotations.append((response, annotation))

        verdict_counts: Counter[str] = Counter()
        status_counts: Counter[str] = Counter()
        first_error_types: Counter[str] = Counter()
        no_first_error = 0
        annotated_source_correct = 0
        for response, annotation in model_annotations:
            annotated_source_correct += int(response.answer_correct)
            first_error_found = False
            for step in annotation.step_annotations:
                verdict_counts[step.verdict] += 1
                status_counts[_status(step)] += 1
                if step.is_first_error:
                    first_error_found = True
                    if step.error_type is None:
                        raise ValueError(
                            f"first-error label lacks error type in {annotation.response_id}"
                        )
                    first_error_types[step.error_type] += 1
            if not first_error_found:
                no_first_error += 1

        annotated_count = len(model_annotations)
        annotated_by_model[model_id] = {
            "annotated_responses": annotated_count,
            "annotated_source_correct": annotated_source_correct,
            "annotated_source_incorrect": annotated_count - annotated_source_correct,
            "responses_with_first_error": sum(first_error_types.values()),
            "responses_without_first_error": no_first_error,
            "first_error_rate": (
                sum(first_error_types.values()) / annotated_count if annotated_count else None
            ),
            "step_verdict_counts": dict(sorted(verdict_counts.items())),
            "step_status_counts": dict(sorted(status_counts.items())),
            "first_error_type_counts": dict(sorted(first_error_types.items())),
        }

    total_steps = sum(len(record.steps) for record in records)
    return {
        "schema_version": "1.0",
        "annotation": {
            "annotator_id": annotation_info.annotator_id,
            "guideline_version": annotation_info.guideline_version,
            "annotated_responses": len(annotations),
        },
        "corpus": {
            "problems": len({record.problem_id for record in records}),
            "responses": len(records),
            "steps": total_steps,
        },
        "source_answer_correctness_by_model": source_accuracy,
        "human_annotation_summary_by_model": annotated_by_model,
        "interpretation_note": (
            "Source accuracy is copied from upstream GSM8K model metadata; human step labels "
            "are reported only for responses present in the annotation file. These are distinct "
            "measures and must not be conflated."
        ),
    }
