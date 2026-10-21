# Where Do LLMs Go Wrong? A step-level reasoning annotation pilot

> **Pre-annotation draft.** This report describes the prepared seed and planned protocol. Human step annotations have not yet been collected, so first-error findings and inter-annotator agreement are intentionally pending. Do not cite this draft as a completed annotation study.

## Abstract

Final-answer accuracy is a blunt measure for multi-step reasoning: it does not say whether a response failed to parse the problem, made a calculation error, or derived an unsupported conclusion. This pilot prepares a small process-supervision dataset that localizes the first materially invalid step in a math word-problem response. The seed contains 300 historical responses to 150 paired GSM8K test questions, with two released model conditions per problem. Each response is segmented into non-empty source lines; a human annotator will judge each step as correct, incorrect, or uncertain and assign one of seven error types to the earliest incorrect step.

The source batch is reproducible and includes provenance, a datasheet, a versioned schema, and a Label Studio workflow. It is not yet human-labeled. The source's final-answer correctness metadata can describe the seed but is not substituted for step annotations. No kappa score or first-error distribution is reported here.

## Motivation and research questions

A correct final answer can arise from invalid reasoning, while a wrong answer can result from one early omission propagated through otherwise consistent arithmetic. For annotation operations, those cases require different feedback and quality-control decisions. This pilot asks:

1. Which reasoning line is the earliest materially invalid line, and what kind of failure is it?
2. Do two annotators identify the same step and status under the same guidelines?
3. Which taxonomy boundaries (for example, misread information versus invalid inference) produce the most disagreement?

The goal is to validate the annotation process and taxonomy—not to benchmark contemporary model capability.

## Seed construction

The source is the pinned `openai/grade-school-math` repository revision `3101c7d5072418e28b9008a6636bde82a006892c`. We selected 150 source rows uniformly without replacement using seed `2026` and retained both the `6b_finetuning` and `175b_finetuning` traces for every selected question. This gives 300 response records and 1,355 newline-delimited annotation units. The two conditions are paired by problem. The full upstream files are not copied into this repository; source file checksums, selected row indices, and a checksum of the derived batch are in `data/manifest.json`.

In this fixed sample, the upstream correctness field marks 33 of 150 6B responses (22.0%) and 61 of 150 175B responses (40.7%) correct. These figures are descriptive metadata from the released source, not human annotations, and are not evidence of a general model-performance gap. The values are included to characterize the batch and must remain distinct from the step-level labels.

## Annotation protocol

The annotation unit is one non-empty line, including the final-answer line. Annotators see the question, reference answer, preceding steps, target step, and following steps. The interface withholds model identity, source correctness metadata, and the reference solution to reduce anchoring. The status labels are `correct`, `first_error`, `downstream_error`, and `uncertain`; these map to the contract's per-step correctness field. The first error gets exactly one category: arithmetic error, misread or omission, invalid inference, unsupported claim, unit or scale error, irrelevant or redundant reasoning, or answer-reporting error. Later incorrect lines are marked as downstream consequences and are not assigned a second root-cause category.

The planned first round is one full annotation pass over the 300 responses. A second annotator will independently label a seeded 30-problem subset—60 paired response records, approximately 20% of the problems, spanning both model conditions. Annotators should work blind and independently before discussion. Disagreements will be reviewed, guidelines revised with a new version, and a fresh blind pass used for any before/after comparison. The repository preserves raw judgments separately; adjudication must not overwrite them.

## Analysis plan and current status

The primary agreement statistic is Cohen's kappa on the four step statuses for exactly matched response-step IDs. Reports will include raw agreement, confusion matrix, prevalence, number of matched steps, guideline versions, and unmatched coverage. First-error-location agreement is reported at response level. Error-type agreement is conditional on both annotators identifying the same first-error step and will include its denominator. Kappa may be undefined when expected agreement is one; the tool reports `null` with a reason rather than coercing it to zero.

| Measure | Status |
|---|---|
| Seed responses / paired questions | 300 / 150, prepared |
| Annotation guidelines and Label Studio schema | Version 1.0, draft for pilot |
| Human step labels | Not collected |
| First-error taxonomy distribution | Pending human labels |
| Cohen's kappa / raw agreement | Pending independent double annotation |
| Guideline revision / re-measurement | Pending pilot disagreements |

## Limitations

GSM8K is a public benchmark and may overlap model training data. The model outputs are historical OpenAI research-release traces, not fresh generations from current providers; the source project also notes occasional calculator failures in the released samples. The 150-question sample is small, and line breaks are approximate reasoning-step boundaries. The reference answer may itself require review. Accordingly, any post-annotation category comparison will be exploratory and limited to this sample. A broader study should add independently versioned current-model generations, explicit generation settings, a fresh held-out domain, and larger double-annotation coverage.

## Reproducibility and availability

The repository contains the versioned seed JSONL, sampling/source manifest, Pydantic schema, offline CLI, Label Studio XML, annotation guidelines in Markdown and PDF, datasheet, tests, and analysis scripts. The seed can be regenerated from the pinned source files with `python -m wdlw prepare`; exact commands and provenance are in the main README and datasheet. This draft should be revised only after the human pilot is complete and its labels, kappa, disagreement analysis, and limitations have been validated.
