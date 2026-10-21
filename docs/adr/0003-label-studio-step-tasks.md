# ADR 0003: Label Studio step-level task projection

- **Status:** Accepted
- **Date:** 2026-10-18

## Context and constraints

The annotation unit is a response line, but first-error judgments depend on the question and surrounding reasoning. Annotators must label each line while model identity and upstream answer correctness stay blinded. The tool must be free to run locally and the repository must not own hosted annotation state.

## Considered alternatives

- **Argilla:** a credible open-source annotation platform with useful dataset workflows, but would introduce a second task/export format without a need to use multiple platforms in the pilot.
- **Custom web UI:** offers exact interaction control but creates unnecessary application, auth, and maintenance responsibilities.
- **Label Studio task JSON + XML config:** established import/export workflow, supports text fields and categorical controls, can be self-hosted by the researcher, and remains optional.

## Decision

Generate one Label Studio task per response-step with the prompt, reference answer, preceding steps, target step, and following steps. The UI offers `correct`, `first_error`, `downstream_error`, and `uncertain`; only `first_error` requires one of the seven taxonomy labels. Do not include model IDs, `answer_correct`, or the source reference solution in task data. Normalize exported task results into the repository's per-annotator JSONL schema.

## Consequences and failure modes

- One task per step is straightforward to label and validate, but creates several tasks per response and requires full context in every task.
- Label Studio may change export details; the adapter must validate its expected shape and keep third-party JSON behind a narrow normalization boundary.
- Community exports can include multiple annotations on one task with numeric `completed_by` IDs. When necessary, the importer filters by that ID, but always stores a caller-supplied pseudonymous annotator ID; if the export lacks enough metadata to filter unambiguously, it fails closed.
- The project can be used without running Label Studio by creating conforming annotation JSONL directly.
- If XML behavior differs across Label Studio versions, task-data generation and normalized schema remain stable; only the UI config/adapter needs revision.

## References

- [Label Studio Choices tag](https://labelstud.io/tags/choices) documents single-choice controls, conditional visibility (`visibleWhen`, `whenTagName`, `whenChoiceValue`), and inline layout.
- [Label Studio task import guide](https://labelstud.io/guide/tasks.html) documents JSON task lists whose objects carry a `data` mapping.
- [Label Studio export guide](https://labelstud.io/guide/export) documents per-task annotation arrays and the numeric `completed_by` user ID used by the optional filter.
