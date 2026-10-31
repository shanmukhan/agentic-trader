"""Public installer bytes and hashes only. Credentials and account data are never published."""

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse


def verified_release(directory: Path) -> dict[str, Any]:
    metadata, apk = directory / "android-release.json", directory / "agentic-trader.apk"
    if not metadata.exists() or not apk.exists():
        raise HTTPException(404, "The Android installer has not been published for this release.")
    try:
        if directory.is_symlink() or metadata.is_symlink() or apk.is_symlink():
            raise ValueError
        if not 1 <= apk.stat().st_size <= 100 * 1024 * 1024 or metadata.stat().st_size > 16_384:
            raise ValueError
        value = json.loads(metadata.read_text())
        if (
            value["package_name"] != "com.shanmukhan.agentictrader"
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value["version"])
            or type(value["version_code"]) is not int
            or value["version_code"] < 1
            or not re.fullmatch(r"[a-f0-9]{64}", value["sha256"])
            or not re.fullmatch(r"[a-f0-9]{64}", value["certificate_sha256"])
            or value["build_type"] != "productionRelease"
        ):
            raise ValueError
        with apk.open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != value["sha256"]:
                raise ValueError
        return {
            key: value[key]
            for key in (
                "package_name",
                "version",
                "version_code",
                "sha256",
                "certificate_sha256",
                "build_type",
            )
        } | {"min_android": "11", "min_backend": "0.20.0"}
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Android installer integrity could not be verified.") from None


def mount_release(app: Any, directory: Path, prefix: str) -> None:
    @app.get("/api/mobile/release")
    def metadata() -> dict[str, Any]:
        return verified_release(directory)

    @app.get("/downloads/agentic-trader.apk")
    def installer() -> FileResponse:
        value = verified_release(directory)
        return FileResponse(
            directory / "agentic-trader.apk",
            media_type="application/vnd.android.package-archive",
            filename=f"agentic-trader-{value['version']}.apk",
        )

    @app.get("/android", response_class=HTMLResponse)
    def install_page() -> str:
        try:
            value = verified_release(directory)
        except HTTPException as error:
            if error.status_code != 404:
                raise
            return (
                '<!doctype html><html lang="en"><meta name="viewport" '
                'content="width=device-width,initial-scale=1">'
                "<title>Agentic Trader for Android</title><main>"
                "<h1>Android installer is not available yet</h1>"
                "<p>Publish a verified production APK with this backend release, "
                'then return here to install it.</p><a href="'
                + prefix
                + '/workspace">Open your browser workspace</a></main></html>'
            )
        version = html.escape(value["version"])
        return (
            '<!doctype html><html lang="en"><head><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>Agentic Trader for Android</title>'
            '<link rel="stylesheet" href="' + prefix + '/dashboard.css"></head><body><main>'
            '<section class="panel"><p>AGENTIC TRADER · ANDROID · PAPER ONLY</p>'
            "<h1>Your paper account, protected on your phone.</h1>"
            "<p>Native light-mode screens, strong biometric unlock "
            "and guided daily preparation.</p>"
            '<p><a class="button-link" href="'
            + prefix
            + '/downloads/agentic-trader.apk">Download Android '
            + version
            + "</a></p><ol><li>Install the signed APK using Android’s installer.</li>"
            "<li>Pair this phone once with your server operator token.</li>"
            "<li>Use biometrics to unlock, then choose Prepare today. Review the resulting setup "
            "before applying it.</li></ol><p>Requires Android 11+, a secure screen lock and "
            "hardware-backed strong biometrics. Unsupported hardware is refused. Login and 2FA "
            "remain on Zerodha. A saved draft or download never activates trading.</p>"
            "<p>Cloud backup and screenshots are disabled. Backgrounding locks private access. "
            "Keeping Android updated remains important; "
            "these protections are not a security certification.</p>"
            "<details><summary>Verify this installer</summary><p>Version "
            + version
            + "</p><p>APK SHA-256: "
            + value["sha256"]
            + "</p><p>Signing certificate SHA-256: "
            + value["certificate_sha256"]
            + "</p></details></section></main></body></html>"
        )
