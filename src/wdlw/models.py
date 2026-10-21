"""Validated domain models and versioned data contracts."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .text import (
    answers_equivalent,
    extract_model_final_answer,
    extract_reference_answer,
    split_nonempty_lines,
)

ModelId = Literal["6b_finetuning", "175b_finetuning"]
Verdict = Literal["correct", "incorrect", "uncertain"]
SCHEMA_VERSION: Literal["1.0"] = "1.0"
SOURCE_REPOSITORY = "https://github.com/openai/grade-school-math"
SOURCE_REVISION = "3101c7d5072418e28b9008a6636bde82a006892c"
PINNED_SOURCE_FILE_HASHES = {
    "test": "3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14",
    "example_model_solutions": "4bc62db838f8418365d51c627bd66294cbdca9fb7f01519cb13f0dce8c51580b",
}
MODEL_IDS: tuple[ModelId, ...] = ("6b_finetuning", "175b_finetuning")
UiStatus = Literal["correct", "first_error", "downstream_error", "uncertain"]
ErrorType = Literal[
    "arithmetic_error",
    "misread_or_omission",
    "invalid_inference",
    "unsupported_claim",
    "unit_or_scale_error",
    "irrelevant_or_redundant",
    "answer_reporting_error",
]

ERROR_TYPES: tuple[ErrorType, ...] = (
    "arithmetic_error",
    "misread_or_omission",
    "invalid_inference",
    "unsupported_claim",
    "unit_or_scale_error",
    "irrelevant_or_redundant",
    "answer_reporting_error",
)
UI_STATUSES: tuple[UiStatus, ...] = (
    "correct",
    "first_error",
    "downstream_error",
    "uncertain",
)


class StrictModel(BaseModel):
    """Base class for repository-owned, fail-closed JSON contracts."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Step(StrictModel):
    step_id: str = Field(pattern=r"^step-\d{3,}$")
    text: str = Field(min_length=1)


def _validate_https_repository(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("repository must be a credential-free HTTPS URL")
    if any(character.isspace() for character in value):
        raise ValueError("repository URL cannot contain whitespace")
    return value


class SourceMetadata(StrictModel):
    dataset: Literal["gsm8k"]
    split: Literal["test"]
    repository: str = Field(min_length=1)
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    model_field: ModelId

    @field_validator("repository")
    @classmethod
    def validate_repository_url(cls, value: str) -> str:
        return _validate_https_repository(value)


class ResponseRecord(StrictModel):
    schema_version: Literal["1.0"]
    response_id: str = Field(pattern=r"^resp-\d{6}$")
    problem_id: str = Field(pattern=r"^gsm8k-test-\d{7}$")
    source_index: int = Field(ge=0)
    model_id: ModelId
    question: str = Field(min_length=1)
    reference_solution: str = Field(min_length=1)
    reference_answer: str = Field(min_length=1)
    model_response: str = Field(min_length=1)
    model_final_answer: str | None = Field(default=None, min_length=1)
    answer_correct: bool
    steps: list[Step] = Field(min_length=1)
    source: SourceMetadata

    @model_validator(mode="after")
    def validate_identity_and_steps(self) -> ResponseRecord:
        expected_problem_id = f"gsm8k-test-{self.source_index:07d}"
        if self.problem_id != expected_problem_id:
            raise ValueError(f"problem_id must match source_index ({expected_problem_id!r})")
        if self.source.model_field != self.model_id:
            raise ValueError("source.model_field must match model_id")
        expected_step_ids = [f"step-{index:03d}" for index in range(1, len(self.steps) + 1)]
        actual_step_ids = [step.step_id for step in self.steps]
        if actual_step_ids != expected_step_ids:
            raise ValueError("step IDs must be contiguous and in source order")
        expected_step_texts = split_nonempty_lines(self.model_response)
        actual_step_texts = [step.text for step in self.steps]
        if actual_step_texts != expected_step_texts:
            raise ValueError("steps must exactly match the non-empty model response lines")
        try:
            extracted_reference = extract_reference_answer(self.reference_solution)
        except ValueError as error:
            raise ValueError("reference_solution has no valid final #### answer") from error
        if not answers_equivalent(extracted_reference, self.reference_answer):
            raise ValueError("reference_answer does not match reference_solution")
        if extract_model_final_answer(self.model_response) != self.model_final_answer:
            raise ValueError("model_final_answer does not match the model response A: marker")
        return self


class StepAnnotation(StrictModel):
    step_id: str = Field(pattern=r"^step-\d{3,}$")
    verdict: Verdict
    is_first_error: bool
    error_type: ErrorType | None
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_error_fields(self) -> StepAnnotation:
        if self.is_first_error and self.verdict != "incorrect":
            raise ValueError("only an incorrect step can be the first error")
        if self.is_first_error and self.error_type is None:
            raise ValueError("the first error requires an error_type")
        if not self.is_first_error and self.error_type is not None:
            raise ValueError("only the first error may have an error_type")
        return self


class AnnotationRecord(StrictModel):
    schema_version: Literal["1.0"]
    response_id: str = Field(pattern=r"^resp-\d{6}$")
    annotator_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    guideline_version: str = Field(pattern=r"^\d+\.\d+$")
    step_annotations: list[StepAnnotation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_step_sequence(self) -> AnnotationRecord:
        step_ids = [step.step_id for step in self.step_annotations]
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("step_annotations contains duplicate step_id values")
        incorrect_indices = [
            index for index, step in enumerate(self.step_annotations) if step.verdict == "incorrect"
        ]
        first_error_indices = [
            index for index, step in enumerate(self.step_annotations) if step.is_first_error
        ]
        if incorrect_indices:
            if first_error_indices != [incorrect_indices[0]]:
                raise ValueError("the earliest incorrect step must be the only first error")
        elif first_error_indices:
            raise ValueError("a trace without incorrect steps cannot have a first error")
        return self


class LabelStudioTaskData(StrictModel):
    response_id: str = Field(pattern=r"^resp-\d{6}$")
    problem_id: str = Field(pattern=r"^gsm8k-test-\d{7}$")
    step_id: str = Field(pattern=r"^step-\d{3,}$")
    step_number: int = Field(ge=1)
    question: str = Field(min_length=1)
    reference_answer: str = Field(min_length=1)
    prior_steps: str
    current_step: str = Field(min_length=1)
    following_steps: str


class LabelStudioTask(StrictModel):
    data: LabelStudioTaskData


class SourceFileHash(StrictModel):
    filename: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class CorrectnessCounts(StrictModel):
    total: int = Field(ge=1)
    correct: int = Field(ge=0)
    incorrect: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> CorrectnessCounts:
        if self.correct + self.incorrect != self.total:
            raise ValueError("correct + incorrect must equal total")
        return self


class BatchCounts(StrictModel):
    problems: int = Field(ge=1)
    responses: int = Field(ge=1)
    steps: int = Field(ge=1)
    model_final_answers_missing: int = Field(ge=0)


class DatasetManifest(StrictModel):
    schema_version: Literal["1.0"]
    source_repository: str = Field(min_length=1)
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_files: dict[str, SourceFileHash]
    sampling_method: Literal["simple_random_sample_without_replacement"]
    seed: int = Field(ge=0)
    source_population_rows: int = Field(ge=1)
    sample_size_problems: int = Field(ge=1)
    selected_source_indices: list[int] = Field(min_length=1)
    selected_model_ids: list[ModelId] = Field(min_length=2)
    counts: BatchCounts
    answer_correct_by_model: dict[ModelId, CorrectnessCounts]
    seed_batch_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("source_repository")
    @classmethod
    def validate_source_repository(cls, value: str) -> str:
        return _validate_https_repository(value)

    @model_validator(mode="after")
    def validate_manifest_counts(self) -> DatasetManifest:
        if len(self.selected_source_indices) != self.sample_size_problems:
            raise ValueError("sample_size_problems must match selected_source_indices")
        if self.sample_size_problems > self.source_population_rows:
            raise ValueError("sample_size_problems cannot exceed source_population_rows")
        if set(self.source_files) != {"test", "example_model_solutions"}:
            raise ValueError("source_files must contain the test and model-solutions files")
        if any(index >= self.source_population_rows for index in self.selected_source_indices):
            raise ValueError("selected_source_indices must be within source_population_rows")
        if len(set(self.selected_source_indices)) != len(self.selected_source_indices):
            raise ValueError("selected_source_indices must be unique")
        if self.selected_source_indices != sorted(self.selected_source_indices):
            raise ValueError("selected_source_indices must be sorted")
        if len(set(self.selected_model_ids)) != len(self.selected_model_ids):
            raise ValueError("selected_model_ids must be unique")
        if self.counts.problems != self.sample_size_problems:
            raise ValueError("manifest problem count must match sample_size_problems")
        if self.counts.model_final_answers_missing > self.counts.responses:
            raise ValueError("missing model-final-answer count cannot exceed response count")
        expected_responses = self.sample_size_problems * len(self.selected_model_ids)
        if self.counts.responses != expected_responses:
            raise ValueError("response count does not match sampled problem/model count")
        if set(self.answer_correct_by_model) != set(self.selected_model_ids):
            raise ValueError("correctness summaries must cover the selected models")
        if any(
            counts.total != self.sample_size_problems
            for counts in self.answer_correct_by_model.values()
        ):
            raise ValueError("each model correctness summary must cover every sampled problem")
        return self
