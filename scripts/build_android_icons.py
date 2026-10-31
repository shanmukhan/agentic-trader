"""Package the selected square PNG into Android launcher densities using macOS sips."""

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate(source: Path) -> None:
    sips = shutil.which("sips")
    if not sips:
        raise ValueError(
            "macOS sips is required; generated Android resources are already checked in."
        )
    source = source.resolve(strict=True)
    if source.suffix.lower() != ".png" or source.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Choose a square PNG source, at least 432 pixels wide.")
    output = subprocess.check_output(
        [sips, "-g", "pixelWidth", "-g", "pixelHeight", str(source)], text=True
    )
    width = int(re.search(r"pixelWidth: (\d+)", output)[1])
    height = int(re.search(r"pixelHeight: (\d+)", output)[1])
    if width != height or width < 432:
        raise ValueError("Choose a square PNG source, at least 432 pixels wide.")
    resources = ROOT / "android/app/src/main/res"
    with tempfile.TemporaryDirectory(prefix="agentic-icons-") as temporary:
        staged = []
        for density, legacy, foreground in (
            ("mdpi", 48, 108),
            ("hdpi", 72, 162),
            ("xhdpi", 96, 216),
            ("xxhdpi", 144, 324),
            ("xxxhdpi", 192, 432),
        ):
            for name, size in (("ic_launcher", legacy), ("ic_launcher_foreground", foreground)):
                target = resources / ("mipmap-" + density) / (name + ".png")
                generated = Path(temporary) / (density + "-" + name + ".png")
                subprocess.run(
                    [
                        sips,
                        "--resampleHeightWidth",
                        str(size),
                        str(size),
                        str(source),
                        "--out",
                        str(generated),
                    ],
                    check=True,
                    capture_output=True,
                )
                staged.append((generated, target))
        for generated, target in staged:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(generated, target)
    print("Generated five launcher and five adaptive foreground PNG densities from " + source.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=ROOT / "images/Futuristic Fintech Growth Icon.png"
    )
    arguments = parser.parse_args()
    generate(arguments.source)
