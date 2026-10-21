# Data contract (version 1.0)

This document defines the records and state transitions before implementation. JSON Lines (UTF-8, one JSON object per line) is the canonical on-disk interchange format. All records carry `schema_version: "1.0"`; unknown versions must be rejected rather than guessed.

## Source input

The source adapter reads the official GSM8K `test.jsonl` and `example_model_solutions.jsonl` files from one pinned repository revision.

- Each line of `test.jsonl` has `question` and `answer` strings.
- The corresponding model-solutions line has the same `question`, `ground_truth`, and model-key objects. The selected keys are `6b_finetuning` and `175b_finetuning`; each has `is_correct: bool` and `solution: str`.
- Rows are aligned by zero-based line position and exact question text. A length or question mismatch is a hard error.
- When the default pinned revision is declared, both source-file SHA-256 values must match the checked-in pinned hashes; using a different checkout requires passing its actual 40-character revision rather than silently inheriting the default.
- `reference_solution` is the exact `answer` field from `test.jsonl`; `reference_answer` is extracted from its final `####` marker. The model-solutions `ground_truth` must contain an `A:` answer matching that reference value (commas and surrounding whitespace ignored); this cross-check catches source misalignment. Failure to extract or a mismatch is a hard error. The model's `A:` answer is extracted when present and otherwise stored as `null`; trace text is never changed.

## Canonical response record

One record represents one model response to one problem.

```json
{
  "schema_version": "1.0",
  "response_id": "resp-000001",
  "problem_id": "gsm8k-test-0000123",
  "source_index": 123,
  "model_id": "6b_finetuning",
  "question": "...",
  "reference_solution": "...",
  "reference_answer": "18",
  "model_response": "Line one.\nLine two.\nA: 26",
  "model_final_answer": "26",
  "answer_correct": false,
  "steps": [
    {"step_id": "step-001", "text": "Line one."},
    {"step_id": "step-002", "text": "Line two."},
    {"step_id": "step-003", "text": "A: 26"}
  ],
  "source": {
    "dataset": "gsm8k",
    "split": "test",
    "repository": "https://github.com/openai/grade-school-math",
    "revision": "3101c7d5072418e28b9008a6636bde82a006892c",
    "model_field": "6b_finetuning"
  }
}
```

IDs are deterministic within the fixed seed batch. `source_index` is the upstream zero-based line number; `problem_id` is stable across both paired responses. The manifest records the aligned source population size, sampling seed, and selected source indices, and rejects out-of-range indices. `response_id` is unique across the batch. The `steps` array is made from non-empty response lines in source order; surrounding whitespace is trimmed, while internal text, calculations, punctuation, and the final-answer line are preserved. It is a practical annotation unit, not a claim that each line is a complete semantic reasoning step. Manifest quality counts include the number of responses whose upstream final-answer marker could not be extracted; those values remain `null` rather than guessed.

`answer_correct` is copied from upstream source metadata. It is not a human step label and is not exposed in Label Studio. `reference_solution` and `model_response` are kept verbatim apart from JSON decoding. The seed has 150 paired problems and 300 response records.

## Per-annotator annotation record

Annotations are stored separately from the canonical response records. Each record represents one annotator's complete judgment of one response.

```json
{
  "schema_version": "1.0",
  "response_id": "resp-000001",
  "annotator_id": "annotator-a",
  "guideline_version": "1.0",
  "step_annotations": [
    {"step_id": "step-001", "verdict": "correct", "is_first_error": false, "error_type": null, "rationale": null},
    {"step_id": "step-002", "verdict": "incorrect", "is_first_error": true, "error_type": "arithmetic_error", "rationale": "..."},
    {"step_id": "step-003", "verdict": "incorrect", "is_first_error": false, "error_type": null, "rationale": null}
  ]
}
```

Allowed verdicts are `correct`, `incorrect`, and `uncertain`. `is_first_error` is true exactly for the earliest incorrect step; if no step is incorrect, it is false for all steps. Only the first error has an `error_type`; later incorrect steps are downstream consequences and have no taxonomy label. Correct/uncertain steps cannot have an error type. A complete annotation must cover each record step exactly once, in order. At most one first error is allowed; any trace with an incorrect verdict must have one.

The taxonomy values are:

- `arithmetic_error`
- `misread_or_omission`
- `invalid_inference`
- `unsupported_claim`
- `unit_or_scale_error`
- `irrelevant_or_redundant`
- `answer_reporting_error`

`rationale` is optional, concise, and should explain ambiguous decisions rather than paraphrase the response. Annotator IDs are pseudonymous.

## Label Studio task contract

The export is a JSON array of tasks, one per response-step. Each task's `data` includes `response_id`, `problem_id`, `step_id`, `step_number`, `question`, `reference_answer`, `prior_steps`, `current_step`, and `following_steps`. It deliberately excludes `model_id`, `answer_correct`, and source solution text. The UI statuses map as follows:

| Label Studio status | Canonical verdict | `is_first_error` | Error type |
|---|---|---:|---|
| `correct` | `correct` | false | none |
| `first_error` | `incorrect` | true | required taxonomy label |
| `downstream_error` | `incorrect` | false | none |
| `uncertain` | `uncertain` | false | none |

A normalized annotation export must include a user-supplied pseudonymous annotator ID. For a shared Label Studio export with multiple annotations per task, select one annotator using that export's numeric `completed_by` value; tasks without a matching annotation and cancelled annotations are skipped. If filtering cannot be done unambiguously, import fails. Duplicate or missing steps within an included response are rejected.

## State transitions

`unprepared source → validated response batch → exported annotation tasks → complete per-annotator labels → agreement/analysis report`.

Any validation failure leaves the previous output untouched. Annotation files are not overwritten unless the caller explicitly writes to a new path. Pending tasks are not considered annotations. Agreement requires labels from two independent annotators on the same response-step keys; reports disclose matched/unmatched counts and the guideline version.
