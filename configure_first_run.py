"""Create this PC's private settings and optional Chatterbox voice reference."""

from __future__ import annotations

import json
import getpass
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
CHARACTERS = ROOT / "characters"
VOICES = ROOT / "voices"
CHARACTER_FILE = CHARACTERS / "setup-tutor.json"


def read_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("GROQ_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def configured_character() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("CHARACTER="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "example-japanese"


def write_key(key: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    updated = False
    for index, line in enumerate(lines):
        if line.strip().startswith("GROQ_API_KEY="):
            lines[index] = f"GROQ_API_KEY={key}"
            updated = True
            break
    if not updated:
        lines.insert(0, f"GROQ_API_KEY={key}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prompt_api_key() -> str | None:
    """Use a masked dialog where available, or a masked terminal prompt."""
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        key = simpledialog.askstring(
            "Groq API key",
            "Paste your Groq API key here. The characters will be masked.",
            show="*",
            parent=root,
        )
        root.destroy()
        return key.strip() if key is not None else None
    except Exception:
        print("The masked key dialog could not open. Enter the key in the terminal; input stays hidden.")
        return getpass.getpass("Groq API key: ").strip()


def choose_reference() -> str | None:
    print("\nOptional: enter the path to your own reference WAV for a custom voice.")
    print("Press Enter to use Chatterbox's built-in voice. Use audio you have permission to use.")
    while True:
        supplied = input("Reference WAV path (optional): ").strip().strip('"')
        if not supplied:
            return None
        source = Path(supplied).expanduser()
        if not source.is_absolute():
            source = (Path.cwd() / source).resolve()
        if not source.is_file():
            print("That file was not found. Enter a full path or press Enter to skip.")
            continue
        if source.suffix.lower() != ".wav":
            print("Please choose a .wav file, or press Enter to skip.")
            continue
        VOICES.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, VOICES / "setup-reference.wav")
        return "setup-reference.wav"


def main() -> int:
    if not ENV_FILE.exists():
        shutil.copy2(ROOT / ".env.example", ENV_FILE)

    if not read_key():
        print("\nEnter your own Groq API key. It will be saved in this computer's .env file.")
        key = prompt_api_key()
        if key is None:
            print("Key entry canceled. Run the launcher again to retry.")
            return 1
        if not key or "\n" in key or "\r" in key:
            print("No valid API key was received. Run the launcher again to retry.")
            return 1
        write_key(key)

    if configured_character() == "setup-tutor" and not CHARACTER_FILE.exists():
        CHARACTERS.mkdir(parents=True, exist_ok=True)
        character = json.loads((CHARACTERS / "example-japanese.json").read_text(encoding="utf-8"))
        character["name"] = "Haruka"
        character["personality"] = "A calm, friendly Japanese tutor who encourages the learner without lecturing."
        character.pop("reference_audio", None)
        reference = choose_reference()
        if reference:
            character["reference_audio"] = reference
        CHARACTER_FILE.write_text(json.dumps(character, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
