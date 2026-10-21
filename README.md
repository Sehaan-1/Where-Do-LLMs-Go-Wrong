# Where Do LLMs Go Wrong?

A small, reproducible process-supervision project for annotating **where a multi-step math response first goes wrong**. It keeps the reasoning trace and step labels, rather than reducing every response to right/wrong.

## Current status: seed corpus, not yet human-annotated

The checked-in batch has **300 historical model responses to 150 paired GSM8K test questions**. It uses the released `6b_finetuning` and `175b_finetuning` traces from OpenAI's GSM8K repository, sampled with seed `2026`. The batch has no human step labels yet. The upstream `answer_correct` values are source metadata only; they are not step annotations, and no inter-annotator agreement score is claimed. The [pre-annotation pilot report](docs/pilot_report.md) records the sampling, source correctness counts, analysis plan, and outstanding human-label results. `data/README.md` is a Hugging Face-style dataset card draft; the dataset has not been uploaded to Hugging Face.

No model API is called and no credentials are needed. The source traces are historical, not newly generated or representative of current models. See [the datasheet](docs/datasheet.md), [system map](docs/architecture.md), [data contract](docs/data-contract.md), and [ADRs](docs/adr/).

## Quick start

Python 3.11+ is required. Node.js is used only for the optional frontend JavaScript syntax check; the site preview itself needs no Node runtime.

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

### Static project website

The frontend in `site/` is plain HTML, CSS, and JavaScript. It is a read-only project introduction and task preview, not a submission form or a replacement for Label Studio. It makes no analytics or third-party asset requests, sets no cookies, and stores no annotations.

Preview it from the repository root:

```bash
python3 -m http.server 4173 --bind 0.0.0.0 --directory site
```

The [privacy notice](site/privacy.html), [terms and refund notice](site/terms.html), and [frontend design notes](docs/frontend_design.md) explain the site’s data behavior, scope, and design decisions. No goods or paid services are offered, so refunds do not apply.

Validate the committed seed batch and export all step tasks for Label Studio. Add `--verbose` before the subcommand to emit structured JSON run events with a correlation ID to stderr (no prompt or trace text is logged):

```bash
.venv/bin/python -m wdlw validate --batch data/annotation_batch.jsonl
.venv/bin/python -m wdlw export-label-studio \
  --batch data/annotation_batch.jsonl \
  --output /tmp/wdlw-label-studio.json
```

Import `config/label-studio.xml` as the Label Studio labeling interface, then import the generated task JSON. The UI presents the question, reference answer, and surrounding response context. It intentionally hides model identity and upstream correctness metadata. See the [human annotation runbook](docs/annotation_runbook.md) for the blinded two-annotator pilot procedure, coverage checks, and data-handling guidance.

For a double-annotation pilot on 20% of the 150 paired problems (30 problems, both model conditions), export a repeatable subset:

```bash
.venv/bin/python -m wdlw export-label-studio \
  --batch data/annotation_batch.jsonl \
  --sample-problems 30 --seed 2026 \
  --output /tmp/wdlw-double-annotation.json
```

After one annotator's Label Studio export is saved as JSON, normalize it into a separate file (use a different output path and pseudonymous ID for each annotator):

```bash
.venv/bin/python -m wdlw import-label-studio \
  --batch data/annotation_batch.jsonl \
  --input /path/to/label-studio-export.json \
  --annotator-id annotator-a --guideline-version 1.0 \
  --output data/annotations/annotator-a.jsonl
```

If a shared Label Studio JSON export contains multiple annotations per task, pass `--label-studio-user-id` with the numeric `completed_by` value from that export. The importer then selects only that user's results (and skips tasks they did not annotate); the normalized file stores only the pseudonymous `--annotator-id`. If every task has one annotation, omit the filter. Import each annotator's results independently. Once two files cover overlapping responses:

```bash
.venv/bin/python -m wdlw agreement \
  --batch data/annotation_batch.jsonl \
  --annotator-a data/annotations/annotator-a.jsonl \
  --annotator-b data/annotations/annotator-b.jsonl \
  --output reports/agreement.json
```

Analyze a single annotator's labels separately from the source final-answer accuracy:

```bash
.venv/bin/python -m wdlw analyze \
  --batch data/annotation_batch.jsonl \
  --annotations data/annotations/annotator-a.jsonl \
  --output reports/analysis.json
```

Generated annotation files and reports are ignored by Git by default. Preserve raw annotator files, do not store names or email addresses, and keep adjudication as a separate versioned layer.

## Reproducing the seed batch

The full upstream GSM8K files are not duplicated here. Clone the exact upstream revision and prepare the deterministic sample locally:

```bash
git clone https://github.com/openai/grade-school-math.git /tmp/grade-school-math
git -C /tmp/grade-school-math checkout 3101c7d5072418e28b9008a6636bde82a006892c
.venv/bin/python -m wdlw prepare \
  --test-jsonl /tmp/grade-school-math/grade_school_math/data/test.jsonl \
  --solutions-jsonl /tmp/grade-school-math/grade_school_math/data/example_model_solutions.jsonl \
  --output data/annotation_batch.jsonl \
  --manifest data/manifest.json --force
```

Preparation validates exact question alignment and checks that the reference answer in the test file agrees with the `A:` answer in the model-solutions `ground_truth`. When using the default pinned revision, it also requires exact source-file hashes; for any other checkout, pass its actual `--source-revision`. The manifest records source file hashes, selected source row indices, model conditions, counts, and the resulting batch hash. Sampling is a simple random sample without replacement and is not balanced by correctness.

## Taxonomy and annotation target

Annotators label each non-empty response line as `correct`, `incorrect`, or `uncertain`. The earliest incorrect line is additionally marked as the first error and gets one type; later incorrect lines are marked downstream, not retyped.

The first-error taxonomy is:

- `arithmetic_error`
- `misread_or_omission`
- `invalid_inference`
- `unsupported_claim`
- `unit_or_scale_error`
- `irrelevant_or_redundant`
- `answer_reporting_error`

The full definitions, tie-breakers, example, and agreement cautions are in [annotation guidelines (Markdown)](docs/annotation_guidelines.md) and the shareable [PDF](docs/annotation_guidelines.pdf). Regenerate the PDF after editing the Markdown with `.venv/bin/python scripts/render_guidelines.py`.

## Research and limitations

This seed is suitable for tooling, guideline piloting, and a small human annotation exercise—not for strong claims about today's models. GSM8K is a public benchmark; benchmark overlap is possible. Line breaks are approximate step boundaries. The source repository notes occasional calculator failures in its released traces. See [the datasheet](docs/datasheet.md) before making any research claims.

## Citation and licensing

The dataset source is GSM8K (Cobbe et al., 2021), cited in [Third-party notices](THIRD_PARTY_NOTICES.md). This repository's code and documentation are released under the MIT License; the upstream dataset retains its original attribution and license notice.
