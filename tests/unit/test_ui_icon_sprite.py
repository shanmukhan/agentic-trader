"""Local decorative icons preserve visible navigation and avoid active SVG content."""

from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

STATIC = Path(__file__).resolve().parents[2] / "src/trading_agent/api/static"
SVG_NS = "{http://www.w3.org/2000/svg}"
ICONS = {
    "dashboard",
    "compass",
    "chart",
    "strategy",
    "backtest",
    "paper",
    "wallet",
    "history",
    "shield",
    "plug",
    "settings",
    "book",
    "lock",
    "unlock",
    "refresh",
    "menu",
    "info",
    "warning",
    "check",
    "plus",
    "save",
    "copy",
    "download",
    "arrow-right",
    "arrow-left",
    "search",
    "close",
    "chevron-right",
    "calendar",
}


def test_icon_sprite_is_local_static_geometry_with_unique_symbols():
    root = ElementTree.parse(STATIC / "icons.svg").getroot()
    symbols = list(root)
    assert len(symbols) == len(ICONS)
    assert {symbol.attrib["id"] for symbol in symbols} == ICONS
    for symbol in symbols:
        assert symbol.tag == SVG_NS + "symbol"
        assert symbol.attrib["viewBox"] == "0 0 24 24"
        assert symbol.attrib["fill"] == "none"
        assert symbol.attrib["stroke"] == "currentColor"
        assert symbol.attrib["stroke-width"] == "1.8"
        assert len(symbol)
    for element in root.iter():
        assert element.tag in {SVG_NS + tag for tag in ("svg", "symbol", "path", "rect", "circle")}
        for key, value in element.attrib.items():
            assert not key.lower().startswith("on")
            assert key not in {"href", "style", "src"}
            assert "url(" not in value.lower()


class WorkspaceIcons(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_link = None
        self.links = {}
        self.uses = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a" and (attributes.get("id") or "").startswith("nav-"):
            self.current_link = attributes["id"]
            self.links[self.current_link] = {"label": "", "icons": []}
        if tag == "svg" and attributes.get("class") == "icon":
            assert attributes.get("aria-hidden") == "true"
            assert attributes.get("focusable") == "false"
            assert attributes.get("width") == attributes.get("height") == "20"
        if tag == "use":
            reference = attributes["href"]
            assert reference.startswith("/icons.svg#")
            self.uses.append(reference.removeprefix("/icons.svg#"))
            if self.current_link:
                self.links[self.current_link]["icons"].append(reference)

    def handle_endtag(self, tag):
        if tag == "a":
            self.current_link = None

    def handle_data(self, data):
        if self.current_link:
            self.links[self.current_link]["label"] += data


def test_workspace_icons_supplement_twelve_visible_navigation_labels():
    page = WorkspaceIcons()
    page.feed((STATIC / "workspace.html").read_text())
    assert len(page.links) == 12
    assert set(page.uses) <= ICONS
    for item in page.links.values():
        assert item["label"].strip()
        assert len(item["icons"]) == 1
