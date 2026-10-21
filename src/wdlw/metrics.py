"""Pure agreement metrics for categorical, paired annotations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KappaResult:
    n: int
    categories: tuple[str, ...]
    confusion_matrix: tuple[tuple[int, ...], ...]
    observed_agreement: float | None
    expected_agreement: float | None
    kappa: float | None
    undefined_reason: str | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready representation with explicit category ordering."""
        payload = asdict(self)
        payload["categories"] = list(self.categories)
        payload["confusion_matrix"] = [list(row) for row in self.confusion_matrix]
        payload["label_counts_a"] = [sum(row) for row in self.confusion_matrix]
        payload["label_counts_b"] = [
            sum(self.confusion_matrix[row][column] for row in range(len(self.categories)))
            for column in range(len(self.categories))
        ]
        return payload


def cohen_kappa(
    labels_a: Sequence[str],
    labels_b: Sequence[str],
    categories: Sequence[str],
) -> KappaResult:
    """Compute nominal Cohen's kappa and its confusion table for paired labels."""
    if len(labels_a) != len(labels_b):
        raise ValueError("paired annotation arrays must have equal length")
    if not categories or len(set(categories)) != len(categories):
        raise ValueError("categories must be a non-empty sequence of unique labels")

    category_index = {category: index for index, category in enumerate(categories)}
    matrix = [[0 for _ in categories] for _ in categories]
    for label_a, label_b in zip(labels_a, labels_b, strict=True):
        if label_a not in category_index:
            raise ValueError(f"unknown label from annotator A: {label_a!r}")
        if label_b not in category_index:
            raise ValueError(f"unknown label from annotator B: {label_b!r}")
        matrix[category_index[label_a]][category_index[label_b]] += 1

    sample_count = len(labels_a)
    if sample_count == 0:
        return KappaResult(
            n=0,
            categories=tuple(categories),
            confusion_matrix=tuple(tuple(row) for row in matrix),
            observed_agreement=None,
            expected_agreement=None,
            kappa=None,
            undefined_reason="no matched labels",
        )

    row_totals = [sum(row) for row in matrix]
    column_totals = [
        sum(matrix[row][column] for row in range(len(categories)))
        for column in range(len(categories))
    ]
    observed = sum(matrix[index][index] for index in range(len(categories))) / sample_count
    expected = sum(row_totals[index] * column_totals[index] for index in range(len(categories))) / (
        sample_count * sample_count
    )

    if math.isclose(expected, 1.0, rel_tol=0.0, abs_tol=1e-12):
        return KappaResult(
            n=sample_count,
            categories=tuple(categories),
            confusion_matrix=tuple(tuple(row) for row in matrix),
            observed_agreement=observed,
            expected_agreement=expected,
            kappa=None,
            undefined_reason="expected agreement is 1; kappa is undefined",
        )

    return KappaResult(
        n=sample_count,
        categories=tuple(categories),
        confusion_matrix=tuple(tuple(row) for row in matrix),
        observed_agreement=observed,
        expected_agreement=expected,
        kappa=(observed - expected) / (1.0 - expected),
        undefined_reason=None,
    )
