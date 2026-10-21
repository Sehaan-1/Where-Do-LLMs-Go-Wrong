# Contributor and agent guide

## System map

This repository builds a small, reproducible step-level reasoning annotation corpus from locally supplied GSM8K files. The Python toolkit is offline data preparation and analysis, not a model-serving application. A separate static site in `site/` explains the project and provides read-only task/workflow previews; it does not collect or submit annotations.

```text
Pinned GSM8K JSONL files (local inputs)
        │ validate alignment, provenance, sample deterministically
        ▼
Canonical response records (300 responses / 150 paired problems)
        │ split each response at non-empty source line boundaries
        ├──► Label Studio step-task JSON (one task per response step)
        │         │ human annotations, exported by Label Studio
        │         ▼
        │    normalized per-annotator JSONL
        │         ├──► inter-annotator agreement report (Cohen's κ)
        │         └──► first-error / model-condition summaries
        └──► annotation guidelines, source manifest, datasheet

Static project site (`site/`): read-only project facts and previews → links to repository docs
(no annotation writes, API, cookies, analytics, or third-party embeds)
```

### Boundaries, inputs, outputs, and state

- **Source boundary:** `prepare` accepts local GSM8K `test.jsonl` and `example_model_solutions.jsonl` paths. It makes no network calls and does not require model-provider credentials.
- **Transform boundary:** source parsing, paired sampling, trace segmentation, schema checks, Label Studio conversion, and statistics are deterministic Python operations.
- **Annotation boundary:** Label Studio is an optional external UI. The repository owns its import task format, XML template, and normalized JSONL contract; it does not own the Label Studio server, users, or database.
- **Static-site boundary:** `site/` is a read-only HTML/CSS/JS project website. It has no backend, annotation form, telemetry, cookie, browser persistence, remote asset, or third-party embed. Its controls change local preview state only; external services are ordinary links.
- **Stocks/state:** the versioned seed batch and manifest under `data/` are immutable inputs to annotation. Each annotator's normalized labels are a separate file; generated reports live under `reports/` and are not authoritative labels.
- **Outputs:** validated JSONL, Label Studio import JSON, per-annotator JSONL, and machine-readable agreement/analysis reports.
- **External dependencies:** pinned upstream GSM8K data and optional Label Studio. Python runtime validation uses Pydantic. No database, queue, API server, or secrets are required.

### Feedback, failure modes, and blast radius

The human workflow is a balancing loop: disagreements surface ambiguous cases, guideline revisions are versioned, and a fresh blind annotation round measures whether agreement changes. Raw annotator labels are never silently replaced by adjudication. The main bottleneck is human review, not CPU or I/O. A malformed or misaligned source row must stop preparation with file and line context; no partial output should replace a valid batch. Import/export errors are isolated to the affected file, and agreement/analysis must reject invalid labels rather than silently dropping them. Source outages do not affect normal use because the committed seed batch is local. There are no retry loops or concurrent workers in the baseline, so no retry-storm or queue-growth path exists.

Second-order limitations are recorded in the datasheet: the source is historical, uses GSM8K test problems, and the selected model traces are not newly generated or representative of current models. Sampling is for annotation coverage, not a substitute for a fresh benchmark study. Never describe pending tasks as human-annotated data or report agreement before actual independent labels exist.

## Repository layout

- `src/wdlw/`: typed domain models, validation, transforms, CLI, and analysis.
- `site/`: static project frontend (`index.html`, privacy and terms pages, local CSS/JS); no server-side state.
- `scripts/render_guidelines.py`: reproducible Markdown-to-PDF build for the annotation guide.
- `tests/`: unit, contract, site/accessibility-contract, and failure-path tests; fixtures are small and the site preview is checked against the seed source text.
- `data/annotation_batch.jsonl`: versioned, unlabeled seed responses.
- `data/manifest.json`: source revision, sampling recipe, counts, and checksums.
- `data/annotations/`: per-annotator outputs (not merged into the seed batch).
- `config/label-studio.xml`: step-level annotation interface.
- `.github/workflows/ci.yml`: automated formatter, lint, type, test, and PDF-freshness checks.
- `docs/`: architecture, data contract, datasheet, guidelines, human annotation runbook, frontend design notes, pilot report, and ADRs.
- `reports/`: generated reports; ignored by Git unless a reviewed report is deliberately added.

## Build, test, lint, and type-check

Use Python 3.11 or newer. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/mypy --strict src/wdlw tests scripts
.venv/bin/pytest -q
node --check site/assets/site.js
.venv/bin/python scripts/render_guidelines.py
.venv/bin/python -m wdlw --help
```

For reproducible preparation, obtain the exact source revision and paths documented in `docs/datasheet.md`, then run:

```bash
.venv/bin/python -m wdlw prepare \
  --test-jsonl /path/to/grade_school_math/data/test.jsonl \
  --solutions-jsonl /path/to/grade_school_math/data/example_model_solutions.jsonl \
  --output data/annotation_batch.jsonl --manifest data/manifest.json
```

The CLI must fail closed on invalid input, use explicit paths, preserve provenance, and write output atomically. It must never fetch source files or call an LLM implicitly. `wdlw --verbose <command>` emits structured JSON transition events to stderr with a per-run correlation ID; events must not contain prompts, model traces, or annotator rationale.

## Conventions and operational boundaries

- Keep modules focused and under 1,000 lines; target 200–500 lines where practical.
- Use Python type annotations throughout and Pydantic validation at JSON, file, and CLI boundaries. Avoid `Any` unless a third-party export format requires a narrow raw boundary; normalize immediately.
- Keep domain logic pure where possible. File I/O, Label Studio wire-format handling, CLI parsing, and report formatting belong in separate modules.
- Do not mutate source records, auto-correct model text, infer human labels from final-answer correctness, or overwrite annotator files.
- Use explicit error messages with path, line, response ID, or step ID. Do not swallow exceptions or print stack traces as normal CLI output.
- Preserve original source model identifiers and include source/license attribution. Store pseudonymous annotator IDs only; do not collect personal data.
- Any change to a data field, label definition, state transition, or external interface requires updating `docs/data-contract.md`, the relevant ADR, and tests.
- Maintain a hard boundary between source-level `answer_correct` metadata and human step annotations. The Label Studio UI must not expose the model name or source correctness flag to annotators.
- Keep the static site read-only. Do not add forms, tracking, cookies, third-party embeds, or remote assets without an explicit privacy review; keep `site/privacy.html` and `site/terms.html` accurate if behavior changes.
