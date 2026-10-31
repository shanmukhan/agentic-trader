"""Build a code-only bundle from tracked files, never workstation state or secrets."""

import argparse
import hashlib
import io
import json
import re
import subprocess
import tarfile
import tomllib
from pathlib import Path


def sources(root: Path, project: str) -> list[Path]:
    allowed = {
        "trader": ("src/", "config/"),
        "advisor": ("advisor/", "ui/", "data/", "scripts/", ".streamlit/"),
    }[project]
    names = {
        "trader": {"pyproject.toml", "uv.lock", "README.md"},
        "advisor": {"pyproject.toml", "requirements.lock", "app.py", "README.md"},
    }[project]
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
    if project == "trader":
        # New reviewed runtime modules must be deployable before a Git commit.
        # Untracked state/sample files outside the application package stay excluded.
        tracked += subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                "src/trading_agent",
            ]
        )
    result = []
    for raw in tracked.decode().split("\0"):
        if not raw or not (raw in names or raw.startswith(allowed)):
            continue
        if raw.startswith("src/") and Path(raw).suffix not in {
            ".py",
            ".html",
            ".js",
            ".css",
            ".svg",
        }:
            continue
        path = Path(raw)
        # Even an accidentally tracked credential/database must never be shipped.
        if any(part.startswith(".env") for part in path.parts) or any(
            suffix in raw for suffix in (".sqlite", ".db", "-session.toml", ".local.toml")
        ):
            continue
        source = root / path
        if (
            source.is_symlink()
            or not source.is_file()
            or not source.resolve().is_relative_to(root.resolve())
        ):
            raise ValueError(f"Not a regular project file: {path}")
        result.append(path)
    required = {"trader": "uv.lock", "advisor": "app.py"}[project]
    if Path(required) not in result:
        raise ValueError(f"Missing required {project} file: {required}")
    return sorted(result)


def build(
    trader: Path, advisor: Path | None, output: Path, android_apk: Path | None = None
) -> None:
    roots = [("trader", trader)] + ([("advisor", advisor)] if advisor else [])
    versions = {}
    for name, root in roots:
        version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError(f"Invalid {name} release version; use major.minor.patch")
        versions[name] = version
    manifest: dict[str, object] = {"projects": {}, "versions": versions, "sha256": {}}
    projects = manifest["projects"]
    hashes = manifest["sha256"]
    assert isinstance(projects, dict) and isinstance(hashes, dict)
    with tarfile.open(output, "w:gz") as archive:
        for name, root in roots:
            projects[name] = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
            ).strip()
            for path in sources(root, name):
                target = f"{name}/{path.as_posix()}"
                hashes[target] = hashlib.sha256((root / path).read_bytes()).hexdigest()
                archive.add(root / path, arcname=target, recursive=False)
        if android_apk is not None:
            from trading_agent.mobile.release import verified_release

            # The build script produces this exact reviewed directory layout, never a debug APK.
            release = verified_release(android_apk.parent)
            if android_apk.name != "agentic-trader.apk":
                raise ValueError("Use the signed release directory's agentic-trader.apk")
            manifest["android"] = release
            for name in ("agentic-trader.apk", "android-release.json"):
                target = "trader/downloads/" + name
                hashes[target] = hashlib.sha256(
                    (android_apk.parent / name).read_bytes()
                ).hexdigest()
                archive.add(android_apk.parent / name, arcname=target, recursive=False)
        for path in sorted(Path(__file__).parent.iterdir()):
            if path.is_file() and path.suffix in {".py", ".sh", ".service"}:
                target = f"rpi/{path.name}"
                hashes[target] = hashlib.sha256(path.read_bytes()).hexdigest()
                archive.add(path, arcname=target, recursive=False)
        payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(payload)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(payload))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trader", type=Path, required=True)
    parser.add_argument("--advisor", type=Path, help="Omit for a Trader-only release")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--android-apk", type=Path, help="Include the verified signed production release"
    )
    args = parser.parse_args()
    build(args.trader, args.advisor, args.output, args.android_apk)
