from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

SITE_ROOT = Path(__file__).resolve().parents[1] / "site"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.resources: list[str] = []
        self.image_alts: list[str | None] = []
        self.ids: list[str] = []
        self.labels_for: set[str] = set()
        self.inputs: list[dict[str, str | None]] = []
        self.forms = 0
        self.embeds = 0
        self.headings: list[int] = []
        self.landmarks: set[str] = set()
        self.interactive_labels: list[tuple[str, str, str]] = []
        self._active: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "link" and "stylesheet" in (values.get("rel") or "").split():
            self.resources.append(str(values.get("href", "")))
        if tag == "script" and values.get("src"):
            self.resources.append(str(values["src"]))
        if tag == "img":
            self.image_alts.append(values.get("alt"))
            if values.get("src"):
                self.resources.append(str(values["src"]))
        if tag in {"iframe", "object", "embed", "video", "audio"}:
            self.embeds += 1
        if tag == "form":
            self.forms += 1
        if tag == "input":
            self.inputs.append(values)
        if tag == "label" and values.get("for"):
            self.labels_for.add(str(values["for"]))
        if tag in {"main", "nav", "header", "footer"}:
            self.landmarks.add(tag)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings.append(int(tag[1]))
        if tag in {"a", "button", "summary"}:
            self._active.append(
                {
                    "tag": tag,
                    "aria": values.get("aria-label") or "",
                    "text": [],
                }
            )

    def handle_data(self, data: str) -> None:
        for element in self._active:
            text = element["text"]
            if isinstance(text, list):
                text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._active and self._active[-1]["tag"] == tag:
            element = self._active.pop()
            text_parts = element["text"]
            text = " ".join(text_parts) if isinstance(text_parts, list) else ""
            aria = str(element["aria"])
            self.interactive_labels.append((tag, text.strip(), aria.strip()))


def _parse(path: Path) -> tuple[str, SiteParser]:
    html = path.read_text(encoding="utf-8")
    parser = SiteParser()
    parser.feed(html)
    return html, parser


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def test_site_pages_use_local_assets_and_accessible_controls() -> None:
    pages = sorted(SITE_ROOT.glob("*.html"))
    assert {page.name for page in pages} == {"index.html", "privacy.html", "terms.html"}

    for page in pages:
        html, parsed = _parse(page)
        assert html.lower().count("<title>") == 1
        assert parsed.headings.count(1) == 1
        assert {"main", "nav", "header", "footer"}.issubset(parsed.landmarks)
        assert 'href="#main"' in html
        assert "connect-src 'none'" in html
        assert "form-action 'none'" in html
        assert parsed.forms == 0
        assert parsed.embeds == 0
        assert all(alt is not None for alt in parsed.image_alts)
        assert len(parsed.ids) == len(set(parsed.ids))

        for resource in parsed.resources:
            parts = urlsplit(resource)
            assert not parts.scheme and not parts.netloc, (
                f"external subresource in {page.name}: {resource}"
            )
            target = (page.parent / parts.path).resolve()
            assert target.is_file(), f"missing local asset in {page.name}: {resource}"

        for href in parsed.links:
            parts = urlsplit(href)
            if parts.scheme or parts.netloc:
                continue
            target = (page.parent / parts.path).resolve() if parts.path else page
            assert target.is_file(), f"broken local link in {page.name}: {href}"
            if parts.fragment:
                _, target_parser = _parse(target)
                assert parts.fragment in target_parser.ids, (
                    f"missing fragment in {page.name}: {href}"
                )

        for values in parsed.inputs:
            input_id = values.get("id")
            assert values.get("aria-label") or (input_id and input_id in parsed.labels_for)

        for tag, text, aria in parsed.interactive_labels:
            assert text or aria, f"unlabeled {tag} in {page.name}"


def test_site_is_explicit_about_privacy_and_non_commerce() -> None:
    index, _ = _parse(SITE_ROOT / "index.html")
    privacy, _ = _parse(SITE_ROOT / "privacy.html")
    terms, _ = _parse(SITE_ROOT / "terms.html")

    assert "No human step labels have been collected" in index
    assert "wrong step." in index
    assert "no judgment is shown" in index
    assert "No annotation decisions are submitted or saved" in privacy
    assert "does not ask for personal information" in privacy
    assert "does not set or read cookies" in privacy
    assert "no cookie-consent banner" in privacy
    assert "a refund policy is therefore not applicable" in terms
    assert "current-model benchmark" in terms
    assert "0.84" not in index + terms


def test_site_scripts_and_styles_do_not_track_or_persist() -> None:
    script = (SITE_ROOT / "assets" / "site.js").read_text(encoding="utf-8")
    stylesheets = "\n".join(
        path.read_text(encoding="utf-8") for path in (SITE_ROOT / "assets").glob("*.css")
    )

    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "sendBeacon",
        "localStorage",
        "sessionStorage",
        "document.cookie",
    ):
        assert forbidden not in script
    assert "@import" not in stylesheets
    assert "url(http" not in stylesheets


def test_read_only_task_preview_uses_verbatim_source_text() -> None:
    batch_path = SITE_ROOT.parent / "data" / "annotation_batch.jsonl"
    with batch_path.open(encoding="utf-8") as batch_file:
        sample = json.loads(batch_file.readline())

    assert isinstance(sample, dict)
    question = sample.get("question")
    steps = sample.get("steps")
    assert isinstance(question, str)
    assert isinstance(steps, list)

    site_script = (SITE_ROOT / "assets" / "site.js").read_text(encoding="utf-8")
    assert question in site_script
    for step in steps:
        assert isinstance(step, dict)
        text = step.get("text")
        assert isinstance(text, str)
        assert text in site_script


def test_page_palette_meets_text_contrast_targets() -> None:
    stylesheet = (SITE_ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    tokens = dict(
        re.findall(
            r"--(bg|surface|ink|muted|accent|accent-ink):\s*(#[0-9a-fA-F]{6})",
            stylesheet,
        )
    )
    assert set(tokens) == {"bg", "surface", "ink", "muted", "accent", "accent-ink"}
    hero_line = re.search(r"\.hero__line--blue\s*\{([^}]*)\}", stylesheet, re.DOTALL)
    assert hero_line is not None
    assert "color: var(--accent)" in hero_line.group(1)
    assert _contrast_ratio(tokens["ink"], tokens["bg"]) >= 4.5
    assert _contrast_ratio(tokens["muted"], tokens["bg"]) >= 4.5
    assert _contrast_ratio(tokens["muted"], tokens["surface"]) >= 4.5
    assert _contrast_ratio(tokens["ink"], tokens["surface"]) >= 4.5
    assert _contrast_ratio(tokens["accent"], tokens["bg"]) >= 4.5
    assert _contrast_ratio(tokens["accent-ink"], tokens["accent"]) >= 4.5
