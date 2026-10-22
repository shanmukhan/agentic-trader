"""Validate Phase 2 design artifacts, without importing or running the application."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Markup(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.references: set[str] = set()
        self.sections: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if identifier := values.get("id"):
            assert identifier not in self.ids, f"Duplicate ID: {identifier}"
            self.ids.add(identifier)
        for name in ("for", "aria-controls", "aria-labelledby", "aria-describedby"):
            self.references.update((values.get(name) or "").split())
        if tag in {"main", "nav", "aside", "section", "header", "footer", "dialog", "form"}:
            self.sections.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"main", "nav", "aside", "section", "header", "footer", "dialog", "form"}:
            assert self.sections and self.sections.pop() == tag, f"Misnested {tag}"


def luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return sum(
        value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
    )


def contrast(first: str, second: str) -> float:
    values = sorted((luminance(first), luminance(second)))
    return (values[1] + 0.05) / (values[0] + 0.05)


def main() -> None:
    navigation = json.loads((ROOT / "navigation.json").read_text())
    assert navigation["schema_version"] == 1
    assert navigation["status"] == "phase_2_design_not_runtime_routes"
    ids = [screen["id"] for screen in navigation["screens"]]
    assert len(ids) == len(set(ids)) == 12
    assert navigation["default"] in ids
    aliases: dict[str, str] = {}
    for screen in navigation["screens"]:
        assert screen["title"] and screen["group"] and screen["purpose"]
        assert re.fullmatch(r"[a-z][a-z-]*", screen["id"])
        for alias in screen["legacy"]:
            assert alias not in aliases, f"Ambiguous alias {alias}"
            aliases[alias] = screen["id"]
    assert aliases["desk"] == "dashboard" and aliases["activity"] == "history"
    assert aliases["setup"] == "broker" and aliases["console"] == "risk"
    for fragment in navigation["legacy_fragments"]:
        assert fragment["to"].split("/")[0] in ids
        for key in ("from", "to"):
            assert re.fullmatch(r"[a-z][a-z-]*/[A-Za-z][A-Za-z0-9_-]{0,99}", fragment[key])

    html = (ROOT / "prototype.html").read_text()
    assert len(html.encode()) < 1_000_000
    parser = Markup()
    parser.feed(html)
    assert not parser.sections
    assert parser.references <= parser.ids, parser.references - parser.ids
    assert 'content="light"' in html
    assert "DESIGN PREVIEW · Not connected to an account" in html
    embedded = re.search(
        r'<script id="navigation-data" type="application/json">([\s\S]*?)</script>', html
    )
    assert embedded and json.loads(embedded[1]) == navigation
    scripts = [
        body
        for attrs, body in re.findall(r"<script([^>]*)>([\s\S]*?)</script>", html)
        if "application/json" not in attrs
    ]
    assert len(scripts) == 1
    assert not re.search(
        r"\b(?:fetch|XMLHttpRequest|WebSocket|localStorage|sessionStorage)\s*[.(]", scripts[0]
    ), "Prototype must remain offline and account independent"
    assert not re.search(r"<script[^>]+\bsrc=|<link[^>]+href=|<iframe", html)

    scenarios = json.loads((ROOT / "examples/strategy-scenarios.json").read_text())
    assert scenarios["status"] == "proposed_not_executed"
    assert scenarios["fixture_kind"] == "synthetic" and scenarios["execution"] == "paper_only"
    case_ids = [case["id"] for case in scenarios["cases"]]
    assert case_ids == [f"P{index:02}" for index in range(1, 16)]
    for case in scenarios["cases"]:
        assert case["preconditions"] and case["events"] and case["expected"] and case["parity"]
    strategy = (ROOT / "strategy-and-data-contracts.md").read_text()
    assert scenarios["target_semantics"] in strategy

    documents = sorted(ROOT.rglob("*.md"))
    for document in documents:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if target.startswith(("https:", "http:", "mailto:", "#")):
                continue
            destination = target.split("#")[0].strip("<>")
            assert (document.parent / destination).exists(), f"Broken link {document}: {target}"
    ux = (ROOT / "ux-specification.md").read_text()
    for index in range(1, 13):
        assert f"INV-UI-{index:02}" in ux
    for index in range(1, 4):
        assert f"INV-COMP-{index:02}" in ux

    pairs = [
        ("text", "#172B3A", "#FFFFFF", 4.5),
        ("muted", "#5B6B7D", "#FFFFFF", 4.5),
        ("caption", "#607285", "#FFFFFF", 4.5),
        ("primary", "#FFFFFF", "#0F766E", 4.5),
        ("analysis", "#265D97", "#FFFFFF", 4.5),
        ("selected", "#09665C", "#E7F3F0", 4.5),
        ("positive", "#13754C", "#FFFFFF", 4.5),
        ("negative", "#B42332", "#FFFFFF", 4.5),
        ("warning", "#895300", "#FFF7DF", 4.5),
        ("input boundary", "#81909F", "#FFFFFF", 3.0),
        ("focus", "#087F8C", "#FFFFFF", 3.0),
    ]
    for label, foreground, background, minimum in pairs:
        actual = contrast(foreground, background)
        assert actual >= minimum, f"Insufficient {label} contrast: {actual:.2f}"
    print(
        f"Design contract checks passed: 12 destinations, 15 scenario definitions, "
        f"{len(documents)} linked documents, HTML labels/structure, offline boundary "
        f"and {len(pairs)} contrast pairs. Not browser or financial-runtime acceptance."
    )


if __name__ == "__main__":
    main()
