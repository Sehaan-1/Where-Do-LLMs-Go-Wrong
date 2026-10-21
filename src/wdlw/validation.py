"""Cross-record invariants for batches and per-annotator label files."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import AnnotationRecord, ResponseRecord


@dataclass(frozen=True)
class AnnotationFileInfo:
    annotator_id: str
    guideline_version: str


def index_response_batch(records: Sequence[ResponseRecord]) -> dict[str, ResponseRecord]:
    """Validate response uniqueness and shared metadata, then index by response ID."""
    if not records:
        raise ValueError("response batch must contain at least one record")

    by_id: dict[str, ResponseRecord] = {}
    by_problem_model: set[tuple[str, str]] = set()
    problem_metadata: dict[str, tuple[int, str, str]] = {}
    source_identity: tuple[str, str, str, str] | None = None

    for record in records:
        if record.response_id in by_id:
            raise ValueError(f"duplicate response_id: {record.response_id}")
        by_id[record.response_id] = record

        problem_model_key = (record.problem_id, record.model_id)
        if problem_model_key in by_problem_model:
            raise ValueError(
                f"duplicate model response for problem {record.problem_id}: {record.model_id}"
            )
        by_problem_model.add(problem_model_key)

        metadata = (record.source_index, record.question, record.reference_answer)
        existing_metadata = problem_metadata.setdefault(record.problem_id, metadata)
        if existing_metadata != metadata:
            raise ValueError(f"paired responses disagree on problem metadata: {record.problem_id}")

        current_source_identity = (
            record.source.dataset,
            record.source.split,
            record.source.repository,
            record.source.revision,
        )
        if source_identity is None:
            source_identity = current_source_identity
        elif source_identity != current_source_identity:
            raise ValueError("a response batch cannot mix source datasets or revisions")

    return by_id


def validate_annotation_file(
    annotations: Sequence[AnnotationRecord],
    responses_by_id: dict[str, ResponseRecord],
) -> AnnotationFileInfo:
    """Validate annotation uniqueness, batch membership, identity, and step coverage."""
    if not annotations:
        raise ValueError("annotation file must contain at least one record")

    response_ids: set[str] = set()
    annotator_ids: set[str] = set()
    guideline_versions: set[str] = set()

    for annotation in annotations:
        if annotation.response_id in response_ids:
            raise ValueError(f"duplicate annotation for response {annotation.response_id}")
        response_ids.add(annotation.response_id)
        annotator_ids.add(annotation.annotator_id)
        guideline_versions.add(annotation.guideline_version)

        response = responses_by_id.get(annotation.response_id)
        if response is None:
            raise ValueError(
                f"annotation references response absent from batch: {annotation.response_id}"
            )
        actual_step_ids = [step.step_id for step in annotation.step_annotations]
        expected_step_ids = [step.step_id for step in response.steps]
        if actual_step_ids != expected_step_ids:
            raise ValueError(
                f"annotation steps do not exactly match response {annotation.response_id}"
            )

    if len(annotator_ids) != 1:
        raise ValueError("each annotation file must contain labels from exactly one annotator")
    if len(guideline_versions) != 1:
        raise ValueError("each annotation file must use exactly one guideline version")

    return AnnotationFileInfo(
        annotator_id=next(iter(annotator_ids)),
        guideline_version=next(iter(guideline_versions)),
    )
