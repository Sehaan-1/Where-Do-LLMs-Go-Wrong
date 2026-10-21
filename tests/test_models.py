from __future__ import annotations

import pytest
from pydantic import ValidationError

from wdlw.models import AnnotationRecord, ResponseRecord, StepAnnotation

from .helpers import make_annotation, make_batch


def test_response_record_validates_trace_derived_fields() -> None:
    response = make_batch()[0]
    payload = response.model_dump(mode="json")
    payload["steps"][0]["text"] = "tampered step"
    with pytest.raises(ValidationError, match="steps must exactly match"):
        ResponseRecord.model_validate(payload)

    payload = response.model_dump(mode="json")
    payload["reference_answer"] = "999"
    with pytest.raises(ValidationError, match="reference_answer does not match"):
        ResponseRecord.model_validate(payload)

    payload = response.model_dump(mode="json")
    payload["model_final_answer"] = "999"
    with pytest.raises(ValidationError, match="model_final_answer does not match"):
        ResponseRecord.model_validate(payload)


def test_annotation_requires_one_first_error_for_incorrect_steps() -> None:
    response = make_batch()[0]
    annotation = make_annotation(
        response,
        "annotator-a",
        ("correct", "first_error", "downstream_error"),
    )
    assert annotation.step_annotations[1].error_type == "arithmetic_error"
    assert annotation.step_annotations[2].error_type is None


def test_incorrect_first_error_requires_taxonomy() -> None:
    with pytest.raises(ValidationError, match="first error requires an error_type"):
        StepAnnotation(
            step_id="step-001",
            verdict="incorrect",
            is_first_error=True,
            error_type=None,
        )


def test_downstream_step_cannot_have_error_type() -> None:
    with pytest.raises(ValidationError, match="only the first error may have an error_type"):
        StepAnnotation(
            step_id="step-002",
            verdict="incorrect",
            is_first_error=False,
            error_type="arithmetic_error",
        )


def test_annotation_rejects_missing_or_mislocated_first_error() -> None:
    with pytest.raises(ValidationError, match="earliest incorrect step"):
        AnnotationRecord(
            schema_version="1.0",
            response_id="resp-000001",
            annotator_id="annotator-a",
            guideline_version="1.0",
            step_annotations=[
                StepAnnotation(
                    step_id="step-001",
                    verdict="incorrect",
                    is_first_error=False,
                    error_type=None,
                ),
                StepAnnotation(
                    step_id="step-002",
                    verdict="incorrect",
                    is_first_error=True,
                    error_type="arithmetic_error",
                ),
            ],
        )
