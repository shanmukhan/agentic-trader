"""Build and verify a signed production Android installer without printing signing secrets."""

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
PACKAGE = "com.shanmukhan.agentictrader"


def run(command: list[str], env: dict[str, str], *, capture: bool = False) -> str:
    value = subprocess.run(
        command,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return value.stdout or ""


def build(sdk: Path, output: Path, gradle: str, java_home: Path | None) -> dict[str, object]:
    env = dict(os.environ)
    if java_home:
        env["JAVA_HOME"] = str(java_home)
    env.setdefault("GRADLE_USER_HOME", str(Path("/private/tmp/agentic-android-gradle")))
    keytool = str(java_home / "bin/keytool") if java_home else "keytool"
    signing = ANDROID / ".signing"
    if signing.is_symlink():
        raise ValueError("Signing directory must not be a symbolic link.")
    signing.mkdir(mode=0o700, exist_ok=True)
    identity, store = signing / "identity.json", signing / "release.p12"
    if identity.is_symlink() or store.is_symlink():
        raise ValueError("Signing files must be private regular files.")
    if identity.exists() != store.exists():
        raise ValueError("Incomplete signing identity. Preserve and review it before rebuilding.")
    if not identity.exists():
        password = secrets.token_urlsafe(40)
        with identity.open("x") as file:
            os.chmod(identity, 0o600)
            json.dump({"password": password}, file)
        env["AGENTIC_SIGNING_PASSWORD"] = password
        try:
            run(
                [
                    keytool,
                    "-genkeypair",
                    "-keystore",
                    str(store),
                    "-storetype",
                    "PKCS12",
                    "-storepass:env",
                    "AGENTIC_SIGNING_PASSWORD",
                    "-keypass:env",
                    "AGENTIC_SIGNING_PASSWORD",
                    "-alias",
                    "agentic-trader",
                    "-keyalg",
                    "RSA",
                    "-keysize",
                    "4096",
                    "-validity",
                    "10000",
                    "-dname",
                    "CN=Agentic Trader Android",
                ],
                env,
                capture=True,
            )
        except Exception:
            identity.unlink(missing_ok=True)
            raise
        store.chmod(0o600)
    for path in (identity, store):
        if path.stat().st_mode & 0o077:
            raise ValueError("Signing files require owner-only permissions.")
    env["AGENTIC_SIGNING_STORE"] = str(store)
    env["AGENTIC_SIGNING_PASSWORD"] = json.loads(identity.read_text())["password"]
    (ANDROID / "local.properties").write_text("sdk.dir=" + str(sdk.resolve()) + "\n")
    run([gradle, "-p", str(ANDROID), ":app:assembleProductionRelease", "--no-daemon"], env)
    apk = ANDROID / "app/build/outputs/apk/production/release/app-production-release.apk"
    apksigner = sdk / "build-tools/36.1.0/apksigner"
    result = run(
        [str(apksigner), "verify", "--verbose", "--print-certs", str(apk)], env, capture=True
    )
    match = re.search(r"Signer #1 certificate SHA-256 digest: ([a-fA-F0-9]{64})", result)
    if not match or "Verified using v3 scheme (APK Signature Scheme v3): true" not in result:
        raise ValueError("APK signature verification failed.")
    analyzer = sdk / "cmdline-tools/latest/bin/apkanalyzer"
    manifest = ET.fromstring(run([str(analyzer), "manifest", "print", str(apk)], env, capture=True))
    namespace = "{http://schemas.android.com/apk/res/android}"
    app = manifest.find("application")
    version, code = manifest.get(namespace + "versionName"), manifest.get(namespace + "versionCode")
    if manifest.get("package") != PACKAGE or app is None:
        raise ValueError("Wrong Android application package.")
    if (
        app.get(namespace + "debuggable", "false") != "false"
        or app.get(namespace + "allowBackup") != "false"
    ):
        raise ValueError("Production APK must disable debugging and backup.")
    if app.get(namespace + "usesCleartextTraffic") != "false":
        raise ValueError("Production APK must prohibit cleartext traffic.")
    permissions = [p.get(namespace + "name", "") for p in manifest.findall("uses-permission")]
    allowed = {
        "android.permission.INTERNET",
        "android.permission.USE_BIOMETRIC",
        "android.permission.USE_FINGERPRINT",
        "android.permission.POST_NOTIFICATIONS",
        PACKAGE + ".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
    }
    if not set(permissions) <= allowed:
        raise ValueError(
            "Unexpected production permissions: " + ", ".join(sorted(set(permissions) - allowed))
        )
    output.mkdir(parents=True, exist_ok=True)
    target = output / "agentic-trader.apk"
    shutil.copyfile(apk, target)
    metadata = {
        "version": version,
        "version_code": int(code or "0"),
        "package_name": PACKAGE,
        "build_type": "productionRelease",
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "certificate_sha256": match[1].lower(),
    }
    (output / "android-release.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "build-validation.json").write_text(
        json.dumps(
            {
                **metadata,
                "signature_verified": True,
                "signature_scheme": "v3",
                "debuggable": False,
                "backup_enabled": False,
                "cleartext_enabled": False,
                "permissions": permissions,
                "device_biometrics_acceptance": "Not established by this build",
            },
            indent=2,
        )
        + "\n"
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, default=Path.home() / "Library/Android/sdk")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/android")
    parser.add_argument("--gradle", default=str(ANDROID / "gradlew"))
    parser.add_argument("--java-home", type=Path)
    args = parser.parse_args()
    try:
        value = build(args.sdk, args.output, args.gradle, args.java_home)
    except (OSError, ValueError, subprocess.CalledProcessError):
        print(
            "Android build/signature verification failed. Inspect the build output; "
            "signing secrets were not printed.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(value, indent=2))
    print(
        "Private signing identity retained at android/.signing. "
        "Back it up privately for future updates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
