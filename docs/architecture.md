# Architecture and system behavior

## Purpose

Create a compact process-supervision dataset: annotate the earliest invalid reasoning step in a model response, while retaining per-step status and source provenance. The Python baseline is reproducible without API keys, hosted services, or an internet connection at runtime. A separate static project site in `site/` presents verified project facts and read-only previews; it is not an annotation service.

## System context and flows

1. A researcher supplies the two JSONL files from a pinned GSM8K checkout.
2. The preparation boundary validates JSON, row counts, question ordering, selected model fields, and source correctness booleans. It samples 150 problems deterministically and takes both selected model responses for each problem.
3. Each model response becomes a canonical record with its original text and one annotatable unit per non-empty newline-delimited line. No labels are inferred from correctness metadata.
4. The export adapter makes one Label Studio task per record-step. The task shows the prompt, reference answer, prior/current/following text, but does not display model identity or the source's correctness flag.
5. Human labels are imported as independent, pseudonymous annotation files. Annotation status transitions are validated before storage.
6. Agreement compares aligned annotations; analysis reports response-level source accuracy separately from human first-error types.
7. The static site presents the current seed status, method, limitations, and policy notes. It serves no annotation writes or user data and links to the repository for full documentation.

## Component boundaries

| Component | Owns | Does not own |
|---|---|---|
| Source adapter | Parsing and validating upstream JSONL; source alignment | Downloading data, changing upstream files |
| Domain/schema | Stable IDs, records, label vocabulary, cross-record invariants | File system or UI concerns |
| Preparation | Seeded sampling, step segmentation, provenance | Human judgment, model inference |
| Label Studio adapter | Task projection and export normalization | Label Studio server, users, identity management |
| Agreement/analysis | Metrics over validated annotations | Adjudication or claims about unannotated records |
| CLI | Arguments, error context, command composition | Domain rules hidden in command handlers |
| Static project site | Read-only presentation of verified project facts, task/workflow previews, and policy notices | Annotation writes, accounts, telemetry, cookies, remote assets, or backend services |

## State and invariants

- Source input is immutable; seed records are reproducibly generated.
- A response ID is unique; a step ID is unique within a response; each response has at least one non-empty step.
- Every annotation covers exactly the response's ordered step IDs once.
- A step is `correct`, `incorrect`, or `uncertain`. An incorrect step is either the single `first_error` or a later `downstream_error`; only the first error receives a taxonomy label.
- If a trace has any incorrect step, it has exactly one `first_error`; if it has none, there is no first error. The first error is the earliest incorrect step in source order, ignoring any prior steps marked uncertain.
- Human labels are append-only per annotator and guideline version; revisions produce a new version/file, not an overwrite.
- Source `answer_correct` is analysis metadata only. It must not populate step labels or be shown in the blinded UI.

## Feedback and dynamic behavior

The expected feedback loop is human double annotation → disagreement review → guideline revision → new independent annotation round → re-measurement. Versioning both guideline and label files keeps this balancing loop observable. No script may treat guideline changes as retroactive relabeling.

The seed corpus is small and static, so concurrency, scaling, cache invalidation, and autoscaling are intentionally out of scope. The meaningful bottleneck is annotator time. Keeping the full trace visible on each step task provides context but increases reading effort; a step task is not an independent sample for response-level accuracy.

## Failure handling and blast radius

- Invalid JSON, absent model keys, malformed GSM8K answer markers, duplicate IDs, or row misalignment fail preparation before the output is replaced.
- Label Studio tasks are generated from validated records; a bad export row fails normalization with task and field context.
- Agreement uses only exact `response_id + step_id` matches and reports unmatched counts; no empty overlap is accepted as a metric.
- A bad annotation file cannot alter the seed batch or another annotator's file.
- Generated reports can be deleted and recomputed; they are not a source of truth.

These boundaries localize failures to one command and one output. The system has no background jobs, third-party request retry path, mutable shared database, or credentials to leak.

## Security and privacy

The Python toolkit has no public service or network listener. Paths are explicit; input JSON and Label Studio exports are validated. `wdlw --verbose` writes JSON transition events to stderr with a per-invocation correlation ID; events contain command/count/error context, never prompts, traces, or rationale. Annotator IDs should be pseudonyms. Do not store names, email addresses, access tokens, or private notes. The task projection deliberately withholds model identity and source correctness to reduce anchoring.

The static site has no server-side state, data-entry form, analytics, cookie, browser persistence, third-party embed, or external subresource. Its Content Security Policy blocks cross-origin subresource connections and form submissions. Hosting providers may still process ordinary request logs; the privacy page says this explicitly. Any future form, tracking, or remote asset requires review of data minimization, consent where applicable, security, policy copy, and the deployment jurisdiction before launch.
