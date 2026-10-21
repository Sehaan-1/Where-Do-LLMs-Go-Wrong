# ADR 0001: Offline Python CLI as the system boundary

- **Status:** Accepted
- **Date:** 2026-10-18

## Context and constraints

The repository starts empty and the deliverable is a small dataset workflow, not a production service. The source files are static JSONL, annotations are human-driven, and no API keys or network-dependent generation should be required. The main operational risks are malformed/misaligned inputs, accidental mutation of annotations, and misleading claims—not request latency.

## Considered alternatives

- **Notebook-only workflow:** quick to prototype, but hidden state and manual steps make the 300-row output hard to reproduce or validate.
- **Web application / API + database:** enables collaboration and centralized state, but adds deployment, auth, migrations, monitoring, and security blast radius unrelated to the pilot's scale.
- **Offline Python package with CLI:** adds a small packaging surface while retaining deterministic, testable commands and local ownership of files.

## Decision

Use a typed Python package with an `argparse` CLI, local JSONL files, Pydantic validation, and pure domain transforms. Do not add a backend service, model-provider client, database, queue, or implicit network fetch. The optional annotation interface is Label Studio, deployed separately by users.

## Consequences and failure modes

- Preparation and reports are reproducible and can run in an isolated environment.
- Human collaboration and access control remain the operator's responsibility; file-based annotation is not a multi-user database.
- Atomic file writes and explicit paths limit damage from validation failures.
- Large-scale annotation or concurrent editing would require a new architecture decision rather than ad hoc shared-file writes.
- Python and Pydantic add install-time dependencies; pinned development commands and strict boundary validation reduce environment drift.
