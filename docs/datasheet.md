# Dataset datasheet (pilot seed batch)

## Summary

The repository contains a **300-response, unlabeled annotation seed batch** built from 150 paired GSM8K test problems. The response traces are historical model outputs released with GSM8K; this project does not generate new answers and does not contain human annotations or agreement scores yet. The goal is to support a small, auditable study of the first step-level failure in multi-step math responses.

## Motivation and composition

- **Task:** per-line status annotation (`correct`, `incorrect`, `uncertain`) and taxonomy for the first incorrect step.
- **Source questions:** OpenAI GSM8K `test` split.
- **Source responses:** the released `6b_finetuning` and `175b_finetuning` model-solution fields, paired for the same questions.
- **Unit/count:** 150 questions × 2 response conditions = 300 response records; each record is segmented into non-empty newline-delimited steps.
- **Sampling:** simple random sample without replacement, seed `2026`, from the aligned source test rows. The selected source indices and outcome distribution are recorded in `data/manifest.json`. Sampling is fixed for reproducibility, not balanced by correctness.
- **Labels:** none in the seed batch. `answer_correct` is upstream source metadata only and is not a human step-level annotation.

## Collection and processing

The underlying source was obtained from `openai/grade-school-math` at revision `3101c7d5072418e28b9008a6636bde82a006892c`. The full source files are not duplicated in this repository. Preparation verifies row-level question alignment and cross-checks the `####` reference answer in `test.jsonl` against the `A:` answer in model-solutions `ground_truth`, then selects both model traces for each sampled question. The exact derivation is documented in the manifest and can be regenerated with the CLI and the pinned upstream files. Model response text is preserved; only the step view trims outer whitespace from non-empty lines. The final answer is extracted when the upstream `A:` marker is available; 2 of the 300 sampled responses have no extractable `A:` marker and remain null rather than being guessed. The manifest records this quality count.

The source repository is MIT licensed. The source and paper are cited in `THIRD_PARTY_NOTICES.md` and this datasheet. GSM8K contains human-authored math questions and model-generated solutions; users should review the upstream terms and citation when redistributing derivatives.

## Intended uses

- Training annotators on step-level reasoning judgments.
- Measuring inter-annotator agreement on a clearly defined small pilot.
- Exploring first-error categories on this specific historical model-output sample.
- Developing annotation export, validation, and analysis tooling.

## Out-of-scope and prohibited claims

- This is not yet a completed, human-annotated dataset; do not treat blank labels or `answer_correct` metadata as step-level judgments.
- It is not representative of current frontier models, general mathematical reasoning, or production failure rates.
- Do not claim model superiority from this seed sample without accounting for its size and sampling uncertainty.
- Do not report kappa before independent annotations exist; do not treat LLM-generated labels as human agreement.
- Do not use the historical model traces to infer model capabilities beyond this benchmark and these source conditions.

## Known limitations and risks

- GSM8K is a public benchmark; memorization or training overlap is possible.
- The model traces are historical, source-specific outputs. The upstream repository notes occasional calculation-tool failures in the samples.
- Line breaks are only an approximate step boundary; one line can contain multiple claims, and some conclusions span multiple lines.
- Reference answers can be imperfect; annotators should evaluate reasoning and flag suspected reference errors.
- The sample has 150 paired questions, so fine-grained categories may be sparse. Agreement statistics can be sensitive to prevalence.
- The two source fields are fine-tuning conditions from one historical research release, not independently sampled modern providers.
- No demographic, personally identifying, or sensitive user data is expected in the source.

## Maintenance

`data/manifest.json` is authoritative for source revision, sample seed, row counts, selected model fields, and file hashes. Schema or taxonomy changes require a new version and updated guidelines. Annotator files are stored separately and remain attributable only through pseudonymous IDs. See `docs/annotation_guidelines.md` and `docs/data-contract.md` for operational details.
