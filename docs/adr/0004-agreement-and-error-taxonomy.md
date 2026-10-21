# ADR 0004: First-error labels and agreement reporting

- **Status:** Accepted
- **Date:** 2026-10-18

## Context and constraints

The research question is where a response first becomes invalid, not merely whether its final answer is correct. Annotators should label all step statuses but assign a taxonomy category only to the first error. Agreement must be transparent, reproducible, and not fabricated before human labels exist.

## Considered alternatives

- **Final-answer accuracy only:** cheap, but does not locate reasoning failures.
- **Taxonomy on every bad downstream line:** increases annotator burden and often double-counts propagated consequences.
- **First-error-only taxonomy plus per-step status:** retains the failure location, preserves downstream status, and avoids pretending consequences are independent root causes.
- **Scikit-learn metric dependency:** mature but heavier than needed for a single nominal Cohen's kappa calculation.

## Decision

Use the four ordered UI statuses (`correct`, `first_error`, `downstream_error`, `uncertain`) and the seven-category first-error taxonomy in `docs/annotation_guidelines.md`. Compute exact-match Cohen's kappa from a confusion table for two annotators, along with observed agreement, counts, and unmatched items. Report error-type agreement only when both annotators select the same first-error step, with its conditional denominator. Implement the nominal kappa formula in a small tested pure function to avoid a heavyweight runtime dependency.

## Consequences and failure modes

- Kappa can be undefined when expected agreement is one; report it as `null` with a reason, not zero.
- Imbalanced status prevalence can make kappa misleading; always publish raw agreement, class counts, and matched-item count.
- Conditional taxonomy agreement excludes disagreements about the location of the first error, so it must never be presented alone.
- The metric does not adjudicate correctness. Raw judgments remain separate, and any adjudicated layer requires an explicit process and version.
- The taxonomy captures only the earliest failure; later independent errors are intentionally not typed.
