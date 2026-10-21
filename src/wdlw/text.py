"""Pure text normalization and segmentation helpers shared by boundaries."""

from __future__ import annotations

import re


def extract_reference_answer(reference_solution: str) -> str:
    """Extract the final GSM8K answer after a `####` marker."""
    matches: list[str] = re.findall(r"(?m)^####\s*(.*?)\s*$", reference_solution)
    if not matches or not matches[-1].strip():
        raise ValueError("reference solution has no non-empty final #### answer")
    return matches[-1].strip()


def extract_model_final_answer(model_response: str) -> str | None:
    """Extract the final upstream `A:` answer when the model trace provides one."""
    matches: list[str] = re.findall(r"(?m)^\s*A:\s*(.*?)\s*$", model_response)
    if not matches or not matches[-1].strip():
        return None
    return matches[-1].strip()


def answers_equivalent(left: str, right: str) -> bool:
    """Compare source answer markers while tolerating commas and surrounding spaces."""

    def normalize(value: str) -> str:
        return re.sub(r"[\s,]+", "", value).casefold()

    return normalize(left) == normalize(right)


def split_nonempty_lines(text: str) -> list[str]:
    """Return trimmed non-empty lines in order, preserving their internal text."""
    return [line.strip() for line in text.splitlines() if line.strip()]
