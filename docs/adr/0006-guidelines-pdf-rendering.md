# ADR 0006: Generate the guidelines PDF from Markdown with ReportLab

- **Status:** Accepted
- **Date:** 2026-10-18

## Context and constraints

The project brief calls for a shareable annotation-guidelines PDF, while Markdown should remain the reviewable source of truth. The build must work locally, produce byte-for-byte deterministic output, and not require a hosted service or a heavyweight document toolchain.

## Considered alternatives

- **Commit a hand-maintained PDF:** easy to view but prone to drift from the Markdown guidelines.
- **Pandoc/LaTeX or browser-based HTML-to-PDF:** highly capable, but adds external system dependencies and more operational setup.
- **Small Markdown renderer using ReportLab:** a widely used Python PDF library, installed only in the development extra; the script handles the limited heading/list/inline syntax used by this document.

## Decision

Treat `docs/annotation_guidelines.md` as canonical and generate `docs/annotation_guidelines.pdf` with `scripts/render_guidelines.py`. Pin ReportLab 4.5.1 and its matching type stubs in the development extra; the annotation CLI does not import it. Set ReportLab's invariant mode for stable PDF metadata. Keep renderer behavior deliberately limited and escape text before handing it to ReportLab.

## Consequences and failure modes

- The PDF is reproducible from source and can be regenerated with one command.
- The renderer is not a general Markdown implementation; new Markdown constructs require an explicit renderer change and visual review.
- The PDF may be stale after guideline edits, so the build command is part of verification and the artifact is regenerated in the delivery workflow.
- ReportLab and its type stubs increase development install size, but not the runtime dependency footprint for data processing.
