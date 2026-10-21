# ADR 0005: Use the released GSM8K model-solution traces

- **Status:** Accepted
- **Date:** 2026-10-18

## Context and constraints

The project brief proposes generating multi-step answers from multiple LLMs. This environment has no model-provider credentials, and inventing model outputs or annotation labels would be misleading. The upstream GSM8K repository already releases aligned test questions and model traces for 6B and 175B fine-tuning conditions, along with correctness metadata.

## Considered alternatives

- **Call current model APIs:** more current, but depends on credentials, variable model versions, quotas, cost, and network failure; this cannot be reproduced by the baseline environment.
- **Use only human reference solutions:** accurate as a target, but contains no model failures to annotate.
- **Use released historical model solutions:** free of API credentials, paired by question, step-formatted, and reproducible from a pinned source snapshot; less representative of today's models.

## Decision

Use `openai/grade-school-math` revision `3101c7d5072418e28b9008a6636bde82a006892c`, sample 150 aligned test problems with seed 2026, and retain `6b_finetuning` and `175b_finetuning` responses (300 total). Keep the source correctness flag as provenance/analysis metadata only. Record the MIT attribution and paper citation. Do not describe this corpus as newly generated, current, representative, or human-annotated.

## Consequences and failure modes

- The baseline is reproducible and costs no model API usage.
- Historical model behavior, benchmark contamination, and source-specific calculator issues limit generalization.
- Model-condition accuracy from a sample of 150 questions has uncertainty; the results are exploratory.
- The complete upstream files remain external; regeneration requires checking out the exact revision. The committed seed batch and checksums make day-to-day work independent of upstream availability.
- A future current-model extension would be a separate source adapter with explicit model/version metadata, secrets from environment variables, bounded network retries, and its own ADR; it must not rewrite the historical seed.
