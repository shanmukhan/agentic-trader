"""Explicit reverse-proxy path support for the bundled operator workspace.

Only bundled source text is adapted; API responses, submitted data and persisted
financial records are never rewritten. Empty-prefix local serving is byte-identical.
"""

import re
from importlib.resources.abc import Traversable
from typing import Any

# Root-relative HTML attributes and JS URL literals, including template strings.
# Standalone '/' (split/join delimiters) and protocol-relative URLs are untouched.
_ROOT_URL = re.compile(r"([\"'`])/(?P<root>[A-Za-z0-9_.-]+)(?=[/?#\"'`$])")
_PAGES = {
    "api",
    "console",
    "setup",
    "workspace",
    "watchlist",
    "desk",
    "activity",
    "dashboard",
    "discovery",
    "analysis",
    "strategies",
    "investment-policy",
    "backtesting",
    "paper",
    "holdings",
    "portfolio",
    "settings",
    "learn",
    "android",
    "downloads",
    "health",
    "ready",
}


class PublicAssets:
    def __init__(self, source: Traversable, prefix: str, roots: set[str] | None = None):
        self.source = source
        self.prefix = prefix
        self.roots = roots if roots is not None else _PAGES | {p.name for p in source.iterdir()}

    def joinpath(self, *parts: str) -> "PublicAssets":
        return PublicAssets(self.source.joinpath(*parts), self.prefix, self.roots)

    def read_text(self, encoding: str = "utf-8") -> str:
        text = self.source.read_text(encoding=encoding)
        if not self.prefix:
            return text
        text = _ROOT_URL.sub(
            lambda match: (
                match[1] + self.prefix + "/" + match["root"]
                if match["root"] in self.roots
                else match[0]
            ),
            text,
        )
        # These two '/' values are URLs, unlike the many JS string delimiters.
        text = text.replace("win.location.origin + '/'", f"win.location.origin + '{self.prefix}/'")
        text = text.replace("{'/':'dashboard'", "{'" + self.prefix + "/':'dashboard'")
        return text


class PublicPathMiddleware:
    def __init__(self, app: Any, prefix: str):
        self.app, self.prefix = app, prefix

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if self.prefix and scope["type"] in {"http", "websocket"}:
            path = scope.get("path", "")
            if path == self.prefix or path.startswith(self.prefix + "/"):
                scope = dict(scope)
                scope["path"] = path[len(self.prefix) :] or "/"
                raw = scope.get("raw_path", path.encode())
                scope["raw_path"] = raw[len(self.prefix) :] or b"/"
                scope["root_path"] = scope.get("root_path", "") + self.prefix
        await self.app(scope, receive, send)
