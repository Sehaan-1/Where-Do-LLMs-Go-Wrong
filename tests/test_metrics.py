from __future__ import annotations

import pytest

from wdlw.metrics import cohen_kappa


def test_cohen_kappa_perfect_agreement() -> None:
    result = cohen_kappa(
        ["correct", "first_error", "downstream_error", "correct"],
        ["correct", "first_error", "downstream_error", "correct"],
        ["correct", "first_error", "downstream_error", "uncertain"],
    )
    assert result.n == 4
    assert result.observed_agreement == 1.0
    assert result.kappa == 1.0
    assert result.confusion_matrix[0][0] == 2
    report = result.to_dict()
    assert report["label_counts_a"] == [2, 1, 1, 0]
    assert report["label_counts_b"] == [2, 1, 1, 0]


def test_cohen_kappa_chance_corrected_value() -> None:
    result = cohen_kappa(
        ["a", "a", "b", "b"],
        ["a", "b", "a", "b"],
        ["a", "b"],
    )
    assert result.observed_agreement == 0.5
    assert result.expected_agreement == 0.5
    assert result.kappa == 0.0


def test_cohen_kappa_marks_degenerate_prevalence_undefined() -> None:
    result = cohen_kappa(["correct", "correct"], ["correct", "correct"], ["correct", "wrong"])
    assert result.observed_agreement == 1.0
    assert result.kappa is None
    assert result.undefined_reason == "expected agreement is 1; kappa is undefined"


def test_cohen_kappa_rejects_invalid_pairs_and_labels() -> None:
    with pytest.raises(ValueError, match="equal length"):
        cohen_kappa(["a"], [], ["a"])
    with pytest.raises(ValueError, match="unknown label"):
        cohen_kappa(["other"], ["a"], ["a", "b"])


def test_cohen_kappa_empty_input_is_explicitly_undefined() -> None:
    result = cohen_kappa([], [], ["a", "b"])
    assert result.kappa is None
    assert result.undefined_reason == "no matched labels"
