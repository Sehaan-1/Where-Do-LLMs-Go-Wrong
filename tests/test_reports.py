from __future__ import annotations

import pytest

from wdlw.agreement import build_agreement_report
from wdlw.analysis import build_analysis_report
from wdlw.models import ErrorType, UiStatus

from .helpers import make_annotation, make_batch


def test_agreement_report_includes_status_and_conditional_type_kappa() -> None:
    batch = make_batch(2)
    annotations_a = []
    annotations_b = []
    for record_index, record in enumerate(batch):
        if record_index % 2 == 0:
            statuses: tuple[UiStatus, ...] = ("correct", "first_error", "downstream_error")
            error_type: ErrorType = (
                "arithmetic_error" if record_index == 0 else "misread_or_omission"
            )
        else:
            statuses = ("correct", "correct", "correct")
            error_type = "misread_or_omission"
        annotations_a.append(
            make_annotation(record, "annotator-a", statuses, error_type=error_type)
        )
        annotations_b.append(
            make_annotation(record, "annotator-b", statuses, error_type=error_type)
        )

    report = build_agreement_report(batch, annotations_a, annotations_b)
    status_metric = report["step_status"]
    type_metric = report["first_error_type_when_location_matches"]
    assert isinstance(status_metric, dict)
    assert status_metric["kappa"] == 1.0
    assert status_metric["n"] == 12
    assert isinstance(type_metric, dict)
    assert type_metric["n"] == 2
    assert type_metric["kappa"] == 1.0
    location_metric = report["first_error_location"]
    assert isinstance(location_metric, dict)
    assert location_metric["agreement"] == 1.0


def test_agreement_rejects_same_annotator_or_no_overlap() -> None:
    batch = make_batch(1)
    annotation = make_annotation(
        batch[0],
        "annotator-a",
        ("correct", "first_error", "downstream_error"),
    )
    with pytest.raises(ValueError, match="two different annotator IDs"):
        build_agreement_report(batch, [annotation], [annotation])

    other = make_annotation(
        batch[1],
        "annotator-b",
        ("correct", "correct", "correct"),
    )
    with pytest.raises(ValueError, match="no overlapping response"):
        build_agreement_report(batch, [annotation], [other])


def test_analysis_keeps_source_accuracy_separate_from_human_labels() -> None:
    batch = make_batch(2)
    response = batch[0]
    annotation = make_annotation(
        response,
        "annotator-a",
        ("correct", "correct", "correct"),
    )
    report = build_analysis_report(batch, [annotation])
    source = report["source_answer_correctness_by_model"]
    human = report["human_annotation_summary_by_model"]
    assert isinstance(source, dict)
    assert isinstance(human, dict)
    source_summary = source["6b_finetuning"]
    human_summary = human["6b_finetuning"]
    assert isinstance(source_summary, dict)
    assert isinstance(human_summary, dict)
    assert source_summary["source_incorrect"] == 1
    assert human_summary["annotated_responses"] == 1
    assert human_summary["responses_without_first_error"] == 1
