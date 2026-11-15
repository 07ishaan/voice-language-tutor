"""Create separate clean Linux and macOS source archives."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMMON_FILES = (
    "configure_first_run.py",
    ".env.example",
    "server.py",
    "index.html",
    "requirements.txt",
    "requirements-chatterbox.txt",
    "README.md",
    "LICENSE",
    "characters/example-japanese.json",
    "docs/tutor-ui.png",
)
PLATFORM_FILES = {
    "linux": ("start.sh",),
    "macos": ("start.sh", "start-macos.command"),
}
PLATFORM_LABELS = {"linux": "Linux", "macos": "macOS"}


def create_archive(platform: str) -> Path:
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    archive = release / f"VoiceTutor-{PLATFORM_LABELS[platform]}-v2.1.0.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        for name in (*PLATFORM_FILES[platform], *COMMON_FILES):
            source = ROOT / name
            if not source.is_file():
                raise SystemExit(f"Required package file is missing: {name}")
            entry = tar.gettarinfo(str(source), arcname=f"VoiceTutor/{name}")
            if name in ("start.sh", "start-macos.command"):
                entry.mode = 0o755
            with source.open("rb") as stream:
                tar.addfile(entry, stream)

    print(f"Created {archive}")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "platform",
        nargs="?",
        choices=("linux", "macos", "all"),
        default="all",
        help="which archive to build (default: both)",
    )
    platform = parser.parse_args().platform
    platforms = tuple(PLATFORM_FILES) if platform == "all" else (platform,)
    for item in platforms:
        create_archive(item)
    print("Archives exclude .env, .venv, custom characters, and voice recordings.")


if __name__ == "__main__":
    main()
