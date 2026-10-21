# ADR 0002: Versioned JSONL records and immutable provenance

- **Status:** Accepted
- **Date:** 2026-10-18

## Context and constraints

The project needs to preserve exact model traces, pair model responses to the same problem, capture step labels independently per annotator, and remain easy to inspect with standard tools. The seed batch is small (300 responses); labels may be revised as guidelines evolve.

## Considered alternatives

- **CSV:** widely supported, but nested steps, typed nulls, and provenance require fragile serialization conventions.
- **SQLite:** provides transactions and queries, but creates a mutable shared store and migration burden for a small static batch.
- **Parquet:** efficient for analytics, but less convenient for hand inspection and Label Studio interchange.
- **Versioned JSONL:** inspectable, streamable, diffable, and adequate at this scale; each row can be validated independently.

## Decision

Use schema-versioned JSONL as canonical storage. Store response records separately from each annotator's labels. Use deterministic response/step IDs, preserve source revision and model field on each response, and validate cross-record step completeness when joining annotations to responses. Keep the seed batch immutable; guideline iterations create new annotation files/version metadata.

## Consequences and failure modes

- Git diffs and row-level tests are straightforward, and no database service is needed.
- Nested text and ordered step lists are natural; consumers must use the schema rather than assume arbitrary JSON.
- JSONL does not itself guarantee uniqueness or atomicity, so the loader validates IDs and the writer uses a temporary file plus atomic replace.
- Labels can be large but remain small for a 300-response pilot. If the corpus grows materially, Parquet may be added as a derived analytical format, not silently substituted as the source of truth.
