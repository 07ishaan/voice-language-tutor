"""Create a clean Linux/macOS source archive from this checkout."""

from __future__ import annotations

import tarfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FILES = (
    "start.sh",
    "start-macos.command",
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


def main() -> None:
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    archive = release / f"VoiceTutor-Linux-macOS-{stamp}.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        for name in FILES:
            source = ROOT / name
            if not source.is_file():
                raise SystemExit(f"Required package file is missing: {name}")
            entry = tar.gettarinfo(str(source), arcname=f"VoiceTutor/{name}")
            if name in ("start.sh", "start-macos.command"):
                entry.mode = 0o755
            with source.open("rb") as stream:
                tar.addfile(entry, stream)

    print(f"Created {archive}")
    print("The archive excludes .env, .venv, custom characters, and voice recordings.")


if __name__ == "__main__":
    main()
