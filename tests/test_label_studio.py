from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import cast

import pytest

from wdlw.io import DataFormatError
from wdlw.label_studio import build_label_studio_tasks, normalize_label_studio_export
from wdlw.models import ErrorType, ResponseRecord, UiStatus

from .helpers import make_batch


def export_for_response(
    response: ResponseRecord,
    statuses: tuple[UiStatus, ...],
    *,
    error_type: ErrorType = "arithmetic_error",
    omit_error_type: bool = False,
) -> list[dict[str, object]]:
    tasks = build_label_studio_tasks([response])
    export: list[dict[str, object]] = []
    for task_model, status in zip(tasks, statuses, strict=True):
        task = cast(dict[str, object], task_model.model_dump(mode="json"))
        result: list[dict[str, object]] = [{"from_name": "status", "value": {"choices": [status]}}]
        if status == "first_error" and not omit_error_type:
            result.append({"from_name": "error_type", "value": {"choices": [error_type]}})
        export.append(
            {
                "data": task["data"],
                "annotations": [{"completed_by": 10, "result": result}],
            }
        )
    return export


def test_task_export_is_blinded_and_includes_full_context() -> None:
    batch = make_batch(2)
    tasks = build_label_studio_tasks(batch)
    assert len(tasks) == sum(len(record.steps) for record in batch)
    first_data = tasks[0].data.model_dump()
    assert "model_id" not in first_data
    assert "answer_correct" not in first_data
    assert "reference_solution" not in first_data
    assert first_data["question"] == batch[0].question
    assert first_data["current_step"] == batch[0].steps[0].text
    assert first_data["following_steps"] == "\n".join(step.text for step in batch[0].steps[1:])


def test_task_export_samples_whole_paired_problems() -> None:
    batch = make_batch(4)
    tasks = build_label_studio_tasks(batch, sample_problems=2, seed=5)
    response_ids = {task.data.response_id for task in tasks}
    selected_records = [record for record in batch if record.response_id in response_ids]
    assert len({record.problem_id for record in selected_records}) == 2
    assert len(selected_records) == 4


def test_label_studio_export_normalizes_first_and_downstream_errors() -> None:
    response = make_batch(1)[0]
    export = export_for_response(
        response,
        ("correct", "first_error", "downstream_error"),
        error_type="arithmetic_error",
    )
    annotations = normalize_label_studio_export(
        export,
        [response],
        annotator_id="annotator-a",
        guideline_version="1.0",
    )
    assert len(annotations) == 1
    assert [step.verdict for step in annotations[0].step_annotations] == [
        "correct",
        "incorrect",
        "incorrect",
    ]
    assert annotations[0].step_annotations[1].is_first_error is True
    assert annotations[0].step_annotations[1].error_type == "arithmetic_error"
    assert annotations[0].step_annotations[2].error_type is None


def test_shared_export_filters_one_annotator_by_completed_by_id() -> None:
    response = make_batch(1)[0]
    error_statuses: tuple[UiStatus, ...] = ("correct", "first_error", "downstream_error")
    correct_statuses: tuple[UiStatus, ...] = ("correct", "correct", "correct")
    export_a = export_for_response(response, error_statuses, error_type="arithmetic_error")
    export_b = export_for_response(response, correct_statuses)
    shared_export: list[dict[str, object]] = []
    for task_a, task_b in zip(export_a, export_b, strict=True):
        annotations_a = cast(list[dict[str, object]], task_a["annotations"])
        annotations_b = cast(list[dict[str, object]], task_b["annotations"])
        annotations_a[0]["completed_by"] = 10
        annotations_b[0]["completed_by"] = 20
        shared_export.append(
            {"data": task_a["data"], "annotations": [annotations_a[0], annotations_b[0]]}
        )

    with pytest.raises(DataFormatError, match="multiple annotations"):
        normalize_label_studio_export(shared_export, [response], annotator_id="annotator-a")

    selected_a = normalize_label_studio_export(
        shared_export,
        [response],
        annotator_id="annotator-a",
        label_studio_user_id=10,
    )
    selected_b = normalize_label_studio_export(
        shared_export,
        [response],
        annotator_id="annotator-b",
        label_studio_user_id=20,
    )
    assert selected_a[0].step_annotations[1].is_first_error is True
    assert all(step.verdict == "correct" for step in selected_b[0].step_annotations)


def test_import_rejects_first_error_without_type() -> None:
    response = make_batch(1)[0]
    export = export_for_response(
        response,
        ("correct", "first_error", "downstream_error"),
        omit_error_type=True,
    )
    with pytest.raises(DataFormatError, match="missing 'error_type' choice"):
        normalize_label_studio_export(export, [response], annotator_id="annotator-a")


def test_import_rejects_incomplete_response_and_tampered_context() -> None:
    response = make_batch(1)[0]
    export = export_for_response(
        response,
        ("correct", "first_error", "downstream_error"),
    )
    with pytest.raises(DataFormatError, match="must include every step"):
        normalize_label_studio_export(export[:-1], [response], annotator_id="annotator-a")

    tampered = export_for_response(
        response,
        ("correct", "first_error", "downstream_error"),
    )
    data = cast(dict[str, object], tampered[0]["data"])
    data["current_step"] = "changed by the exporter"
    with pytest.raises(DataFormatError, match="current step was changed"):
        normalize_label_studio_export(tampered, [response], annotator_id="annotator-a")


def test_label_studio_xml_is_well_formed_and_has_taxonomy() -> None:
    root = ET.parse("config/label-studio.xml").getroot()
    status_control = root.find(".//Choices[@name='status']")
    assert status_control is not None
    assert status_control.attrib["showInline"] == "true"
    error_type_control = root.find(".//Choices[@name='error_type']")
    assert error_type_control is not None
    assert error_type_control.attrib["showInline"] == "false"
    assert error_type_control.attrib["whenTagName"] == "status"
    assert error_type_control.attrib["whenChoiceValue"] == "first_error"
    values = {choice.attrib["value"] for choice in root.findall(".//Choice")}
    assert "first_error" in values
    assert "arithmetic_error" in values
    assert len(values) == 11
