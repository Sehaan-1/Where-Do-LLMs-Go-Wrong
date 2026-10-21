# Human annotation runbook

This runbook takes the prepared, unlabeled seed through a blinded human pilot. It does not create labels or study results by itself. The batch remains **unlabeled** until independent annotators complete the workflow below and their exports are validated.

## Pilot design

- **Annotator A:** independently labels all 300 responses (1,355 step tasks).
- **Annotator B:** independently labels the same 30-problem subset as A (60 paired responses, 265 step tasks), exported with seed `2026`.
- Keep model identity, upstream `answer_correct`, and source reference solution hidden. The task UI does show the reference answer; use it only to judge the requested answer/reporting, not as a substitute for checking the reasoning.
- Both annotators use the same frozen version of `docs/annotation_guidelines.md` (currently `1.0`). They must not discuss cases or see one another's labels until their independent exports are frozen.

The 30-problem subset covers both historical model conditions for each selected problem. It is a small tooling and guideline pilot, not a representative model evaluation.

## 1. Freeze and validate the inputs

From the repository root, validate the checked-in batch and record the manifest checksum and guideline version for the study log:

```bash
.venv/bin/python -m wdlw validate --batch data/annotation_batch.jsonl
```

Do not edit the seed batch, task schema, or guidelines mid-round. If a guideline change is necessary, give it a new version and keep the earlier annotations intact. The manifest and batch are the source of truth for the fixed sample.

## 2. Export the task sets

Use distinct, private output paths. These files are generated from the seed and can be regenerated; do not edit task data by hand.

```bash
# A's full pass: 300 responses / 1,355 step tasks
.venv/bin/python -m wdlw export-label-studio \
  --batch data/annotation_batch.jsonl \
  --output /tmp/wdlw-full-v1.json

# B's independent double-annotation pass: 30 paired problems / 60 responses / 265 steps
.venv/bin/python -m wdlw export-label-studio \
  --batch data/annotation_batch.jsonl \
  --sample-problems 30 --seed 2026 \
  --output /tmp/wdlw-double-annotation-v1.json
```

If an output already exists, choose a new filename or deliberately use `--force` to regenerate that task file. Do not reuse an old export after changing the seed or task definition.

## 3. Configure Label Studio and protect blinding

1. Run a Label Studio version approved for the study in an isolated environment or approved private service; it is not a dependency of this repository. Record the exact Label Studio version and project configuration with the study log.
2. Create a project and import `config/label-studio.xml` as its labeling interface. Import the corresponding JSON task file from step 2.
3. Give each annotator a distinct account/pseudonymous study ID. If using a shared project, verify that annotators cannot see one another's completed annotations before the independent passes are finished. If that cannot be guaranteed, use separate projects or isolated exports for the two annotators.
4. Confirm the preview shows the question, reference answer, prior steps, target step, and following steps. Confirm that model identity, `answer_correct`, and the source reference solution are absent.
5. Keep the service private and access-controlled. Do not expose an unauthenticated Label Studio instance to the public internet.

The repository does not manage Label Studio accounts, access controls, or backups. Store raw exports in access-controlled storage: Label Studio exports can contain account metadata in addition to labels and rationales.

## 4. Annotate independently

Use the current [annotation guidelines](annotation_guidelines.md) throughout. Annotators should read the full response context and judge each line, not infer step validity from the final answer or upstream correctness flag. Mark the earliest materially invalid line `first_error`; use `downstream_error` for later consequences. Only the first error receives a taxonomy label. Use `uncertain` sparingly and explain genuinely ambiguous cases in the optional rationale.

Each response is complete only when that annotator has labeled **every** step in it. The importer deliberately rejects a partially labeled response; finish the whole response before exporting it. Annotators should not adjudicate or revise labels after seeing each other's work. Preserve a frozen raw export before any discussion.

## 5. Normalize each annotator's export

Export the raw Label Studio JSON separately for each annotator. Choose a pseudonymous ID that does not reveal a name or email. If each export contains only one annotator's annotation per task, omit `--label-studio-user-id`. If one shared export contains multiple annotations per task, use the numeric `completed_by` ID for that annotator; obtain the ID from the actual export and do not guess it.

Example for a shared export (replace the example paths and numeric ID with real values):

```bash
.venv/bin/python -m wdlw import-label-studio \
  --batch data/annotation_batch.jsonl \
  --input /private/study-export/annotator-a.json \
  --annotator-id annotator-a --guideline-version 1.0 \
  --label-studio-user-id 12 \
  --output data/annotations/annotator-a-v1.jsonl

.venv/bin/python -m wdlw import-label-studio \
  --batch data/annotation_batch.jsonl \
  --input /private/study-export/annotator-b.json \
  --annotator-id annotator-b --guideline-version 1.0 \
  --label-studio-user-id 19 \
  --output data/annotations/annotator-b-v1.jsonl
```

The numbers above are examples only. For separate one-annotator exports, remove the `--label-studio-user-id` option from each command. Annotator A's export should cover the full pass; annotator B's export should cover the double-annotation subset. The importer skips tasks with no selected annotation, but rejects duplicate, unknown, or incomplete response steps. It also refuses to overwrite existing output files by default. Use a new filename for each annotation round; do not overwrite raw or normalized labels after discussion.

`data/annotations/` is Git-ignored. Keep raw Label Studio exports outside the repository in restricted storage; do not commit account metadata, names, emails, or private rationales.

## 6. Check coverage and compute reports

Once both normalized files exist, generate the agreement report:

```bash
.venv/bin/python -m wdlw agreement \
  --batch data/annotation_batch.jsonl \
  --annotator-a data/annotations/annotator-a-v1.jsonl \
  --annotator-b data/annotations/annotator-b-v1.jsonl \
  --output reports/agreement-pilot-v1.json
```

For a complete planned double pass, check that the report says **60 matched responses and 265 matched steps**. If coverage differs, resolve incomplete or mismatched exports before interpreting the statistics. The report includes status-level agreement, confusion counts, first-error location agreement, and conditional error-type agreement. Kappa can be undefined for degenerate label distributions; retain the reported reason rather than replacing `null` with a number.

Summarize Annotator A's full pass separately:

```bash
.venv/bin/python -m wdlw analyze \
  --batch data/annotation_batch.jsonl \
  --annotations data/annotations/annotator-a-v1.jsonl \
  --output reports/analysis-annotator-a-v1.json
```

The analysis keeps upstream final-answer correctness separate from human step labels. Reports are generated artifacts under the Git-ignored `reports/` directory; validate their denominators and coverage before using them.

## 7. Review disagreements and preserve the audit trail

After both independent exports are frozen, review disagreements against the guidelines. Record any guideline changes as a new version; do not edit the old version or overwrite the original labels. If you need a post-revision agreement estimate, run a fresh blind annotation round and report the version and cohort separately. Keep adjudicated labels in a distinct, documented layer; do not present adjudication as an annotator's original judgment.

Only after the exports, coverage, and report have been reviewed should the [pre-annotation pilot report](pilot_report.md) be updated with human results. Report the exact overlap, denominators, guideline versions, missingness, and limitations. Do not claim findings or agreement scores before real human annotations are available.

## Completion checklist

- [ ] Seed batch validated; batch checksum and guideline version recorded.
- [ ] A completed all 300 responses; B independently completed the same seeded 30-problem subset.
- [ ] Raw exports frozen in access-controlled storage; annotators could not see each other's labels before freezing.
- [ ] Separate pseudonymous normalized files imported without validation errors.
- [ ] Agreement report has 60 matched responses and 265 matched steps, or any deviation is explained.
- [ ] Analysis, disagreement review, and any later guideline revision are versioned and kept distinct from raw labels.
- [ ] Pilot report updated only with verified human results and appropriate limitations.
