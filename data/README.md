---
language:
  - en
license: mit
task_categories:
  - text-classification
tags:
  - process-supervision
  - reasoning
  - gsm8k
size_categories:
  - n<1K
configs:
  - config_name: seed_batch
    data_files:
      - split: train
        path: annotation_batch.jsonl
---

# Where Do LLMs Go Wrong? — pilot seed batch

## Dataset summary

This pilot contains 300 historical model responses to 150 paired GSM8K test questions. Each record contains a question, the reference solution and answer, one model response, source correctness metadata, provenance, and a newline-segmented list of annotatable steps.

**Important:** `annotation_batch.jsonl` is an unlabeled task seed. It contains no human step labels. The `answer_correct` field is copied from the upstream source and must not be used as a step annotation. Do not report inter-annotator agreement until independent human annotations have been collected.

## Files

- `annotation_batch.jsonl`: canonical 300-response JSONL seed batch (1,355 source-line steps).
- `manifest.json`: pinned source revision and file hashes, source population size, sampling seed and selected row indices, counts (including two missing model `A:` answer markers), and batch checksum.

See the repository's [`docs/datasheet.md`](../docs/datasheet.md) for provenance, intended use, limitations, and licensing; the annotation schema is in [`docs/data-contract.md`](../docs/data-contract.md), and the [human annotation runbook](../docs/annotation_runbook.md) documents the blinded pilot workflow.

## Provenance

Questions and historical `6b_finetuning` / `175b_finetuning` model traces come from `openai/grade-school-math`, revision `3101c7d5072418e28b9008a6636bde82a006892c`. A simple random sample without replacement selected 150 problems using seed `2026`; both model conditions were retained for each selected problem. The full source files are not included. See [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) for attribution and license text.

## Schema

Each JSONL row represents one response. Key fields are `response_id`, `problem_id`, `model_id`, `question`, `reference_answer`, `model_response`, `answer_correct`, `steps`, and `source`. The versioned data contract documents all invariants. Human annotations are kept in separate per-annotator JSONL files and are not mixed into this seed.

## Usage

The data can be read as JSON Lines with Python's `json` module or loaded with the repository CLI. Install the project and validate with:

```bash
python -m pip install -e '.[dev]'
python -m wdlw validate --batch data/annotation_batch.jsonl
```

## Limitations

The traces are historical, from one benchmark release, and not representative of current LLMs. GSM8K is public and may overlap model training data. Source line breaks are approximate step boundaries. The source project notes occasional calculator failures in the released outputs. This seed supports annotation-tooling and a human pilot, not broad capability claims.