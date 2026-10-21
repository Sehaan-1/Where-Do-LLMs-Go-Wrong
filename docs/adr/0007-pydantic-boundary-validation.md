# ADR 0007: Pydantic v2 for runtime schema validation

- **Status:** Accepted
- **Date:** 2026-10-18

## Context and constraints

Python type hints and mypy cannot validate JSONL, Label Studio exports, or user-supplied CLI data at runtime. The dataset requires strict, versioned records plus cross-field and cross-row invariants. The corpus is small, and the runtime must remain offline.

## Considered alternatives

- **Hand-written standard-library validators:** zero third-party runtime dependencies, but duplicate type, field, and nested-record checks across every file boundary and make error reporting inconsistent.
- **JSON Schema validation:** explicit language-neutral schemas and broad tooling support, but still requires mapping validated objects into typed Python domain records and maintaining two representations.
- **Pydantic v2:** combines runtime parsing/validation and typed Python models, supports strict mode and field/model validators, and fits the file-based scale without adding a service.

## Decision

Use Pydantic v2 for repository-owned data contracts and validate every JSON/JSONL boundary before domain processing. Configure models as strict and `extra="forbid"` by default; allow extra source keys only in the narrow upstream solutions adapter because GSM8K stores model outputs as dynamic fields. Run mypy in strict mode for package, tests, and PDF-build script. Use the Python standard library for serialization, hashing, CLI, sampling, and kappa.

## Consequences and failure modes

- Input errors are reported with file/line/task context and structured field paths; invalid records fail closed.
- Pydantic is a runtime dependency, so its major version is constrained to v2 and install commands are documented.
- Upstream and Label Studio formats remain behind adapters; they are not used directly as domain objects.
- Runtime validation does not prove a source revision is authentic; the pinned seed is protected by recorded file hashes, and alternate revisions must be supplied explicitly with their own provenance.
- Future schema changes require updating the version, contract, and tests rather than relying on implicit coercion.
