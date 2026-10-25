"""Navigation/label contracts across the real served shells, without account actions."""

from html.parser import HTMLParser
from xml.etree import ElementTree

from conftest import NOW
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app


class PageLabels(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.references = []
        self.sections = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if identifier := values.get("id"):
            assert identifier not in self.ids, f"Duplicate ID: {identifier}"
            self.ids.add(identifier)
        for attribute in ("for", "aria-controls", "aria-labelledby", "aria-describedby"):
            self.references.extend((values.get(attribute) or "").split())
        if tag in {"section", "details", "main", "nav", "aside", "form", "dialog"}:
            self.sections.append(tag)

    def handle_endtag(self, tag):
        if tag in {"section", "details", "main", "nav", "aside", "form", "dialog"}:
            assert self.sections and self.sections.pop() == tag, f"Misnested {tag}"


def test_redesigned_shells_keep_accessible_labels_and_balanced_workflows(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        for route in (
            "/workspace",
            "/desk",
            "/strategies",
            "/investment-policy",
            "/analysis",
            "/activity",
            "/portfolio",
            "/console",
            "/setup",
            "/dashboard",
            "/discovery",
            "/holdings",
            "/backtesting",
            "/paper",
            "/settings",
            "/learn",
        ):
            response = client.get(route)
            assert response.status_code == 200
            page = PageLabels()
            page.feed(response.text)
            assert not page.sections, route
            assert set(page.references) <= page.ids, route
            assert 'name="color-scheme" content="light dark"' in response.text, route
            assert 'name="description"' in response.text, route
            assert 'type="password"' in response.text, route
            if route in {
                "/desk",
                "/strategies",
                "/paper",
                "/activity",
                "/portfolio",
                "/console",
                "/setup",
            }:
                assert response.text.index("/dialogs.js") < response.text.index(
                    "/workspace-bridge.js"
                )


def test_local_icon_asset_and_references_preserve_security_and_visible_text(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        asset = client.get("/icons.svg")
        assert asset.status_code == 200
        assert asset.headers["content-type"].startswith("image/svg+xml")
        assert asset.headers["cache-control"] == "no-store"
        assert asset.headers["x-content-type-options"] == "nosniff"
        assert "default-src 'self'" in asset.headers["content-security-policy"]
        symbols = {child.attrib["id"] for child in ElementTree.fromstring(asset.text)}
        for route in (
            "/workspace",
            "/dashboard",
            "/analysis",
            "/investment-policy",
            "/backtesting",
            "/console",
            "/setup",
            "/strategies",
            "/activity",
            "/portfolio",
        ):
            page = client.get(route).text
            parser = IconLabels(symbols)
            parser.feed(page)
            assert parser.icons > 0, route
            assert parser.action_labels and all(parser.action_labels), route


class IconLabels(HTMLParser):
    def __init__(self, symbols):
        super().__init__()
        self.symbols = symbols
        self.icons = 0
        self.current_label = None
        self.action_labels = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"button", "a"}:
            self.current_label = ""
        if tag == "svg" and values.get("class") == "icon":
            self.icons += 1
            assert values["aria-hidden"] == "true"
            assert values["focusable"] == "false"
        if tag == "use":
            assert values["href"].startswith("/icons.svg#")
            assert values["href"].split("#", 1)[1] in self.symbols

    def handle_data(self, data):
        if self.current_label is not None:
            self.current_label += data

    def handle_endtag(self, tag):
        if tag in {"button", "a"} and self.current_label is not None:
            self.action_labels.append(self.current_label.strip())
            self.current_label = None


def test_theme_and_responsive_rules_follow_canonical_defaults(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        css = client.get("/dashboard.css").text
        # A consolidated base placed after this breakpoint previously hid content behind a sidebar.
        assert css.index(".workspace-sidebar {") < css.index("@media(max-width:767px)")
        assert "@media(prefers-color-scheme:dark)" in css
        assert "@media(prefers-reduced-motion:reduce)" in css
        assert "--surface:#22323f" in css
        assert "background:#f6f8fa" not in css
        setup = client.get("/setup").text
        assert '<body class="setup-page">' in setup
        assert 'id="error-alert" role="alert"' in setup
        assert 'id="loading-state"' in setup
