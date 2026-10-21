#!/usr/bin/env python3
"""Render the versioned Markdown annotation guide to a compact PDF."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageTemplate,
    Paragraph,
    Preformatted,
)

INLINE_MARKDOWN = re.compile(r"(`[^`]+`|\*\*.+?\*\*|\*[^*]+\*)")
HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
ORDERED_LIST = re.compile(r"^(\d+)\.\s+(.+?)\s*$")


def inline_markup(text: str) -> str:
    """Convert the small inline Markdown subset used in the guide to safe XML."""
    chunks = INLINE_MARKDOWN.split(text)
    rendered: list[str] = []
    for chunk in chunks:
        if chunk.startswith("`") and chunk.endswith("`"):
            rendered.append(
                f'<font name="Courier" color="#344054">{html.escape(chunk[1:-1])}</font>'
            )
        elif chunk.startswith("**") and chunk.endswith("**"):
            rendered.append(f"<b>{html.escape(chunk[2:-2])}</b>")
        elif chunk.startswith("*") and chunk.endswith("*"):
            rendered.append(f"<i>{html.escape(chunk[1:-1])}</i>")
        else:
            rendered.append(html.escape(chunk))
    return "".join(rendered)


def build_story(markdown: str) -> tuple[list[Flowable], dict[str, ParagraphStyle]]:
    """Translate headings, paragraphs, lists, and fenced examples to flowables."""
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "GuideTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#123047"),
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "GuideH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#123047"),
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "GuideH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=colors.HexColor("#24536f"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "GuideH3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#344054"),
            spaceBefore=6,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "GuideBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=colors.HexColor("#202a33"),
            spaceAfter=5,
            allowWidows=0,
            allowOrphans=0,
        ),
        "bullet": ParagraphStyle(
            "GuideBullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            leftIndent=16,
            firstLineIndent=-10,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "GuideCode",
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#344054"),
            backColor=colors.HexColor("#f2f4f7"),
            borderPadding=6,
            spaceBefore=4,
            spaceAfter=7,
        ),
    }

    story: list[Flowable] = []
    paragraph_lines: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            story.append(Paragraph(inline_markup(text), styles["body"]))
            paragraph_lines.clear()

    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["code"], maxLineLength=100))
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            continue
        heading_match = HEADING.match(line)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            key = "title" if level == 1 and not story else f"h{level}"
            story.append(Paragraph(inline_markup(heading_match.group(2)), styles[key]))
            continue
        if line.startswith("- "):
            flush_paragraph()
            story.append(Paragraph("- " + inline_markup(line[2:]), styles["bullet"]))
            continue
        ordered_match = ORDERED_LIST.match(line)
        if ordered_match:
            flush_paragraph()
            label, content = ordered_match.groups()
            story.append(Paragraph(f"{label}. " + inline_markup(content), styles["bullet"]))
            continue
        paragraph_lines.append(line)

    flush_paragraph()
    if code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["code"], maxLineLength=100))
    return story, styles


def _draw_footer(canvas: Canvas, document: BaseDocTemplate) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(20 * mm, 12 * mm, "Where Do LLMs Go Wrong? · Annotation guidelines v1.0")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {document.page}")
    canvas.restoreState()


def render_pdf(source_path: Path, output_path: Path) -> None:
    markdown = source_path.read_text(encoding="utf-8")
    story, _ = build_story(markdown)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = Frame(20 * mm, 20 * mm, 170 * mm, 257 * mm, id="content")
    template = PageTemplate(id="guidelines", frames=[frame], onPage=_draw_footer)
    document = BaseDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="Step-Level Reasoning Annotation Guidelines",
        author="Where Do LLMs Go Wrong? contributors",
    )
    document.addPageTemplates([template])
    # Stable timestamps make the committed PDF byte-for-byte reproducible in CI.
    rl_config.invariant = 1
    document.build(story)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("docs/annotation_guidelines.md"))
    parser.add_argument("--output", type=Path, default=Path("docs/annotation_guidelines.pdf"))
    args = parser.parse_args()
    render_pdf(args.input, args.output)
    print(f"Rendered {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
