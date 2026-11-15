#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
ROOT="$PWD"
PYTHON="${ROOT}/.venv/bin/python"

fail() {
  printf '\nSetup failed: %s\n' "$1" >&2
  read -r -p 'Press Enter to close...' _ || true
  exit 1
}

if [[ "$(uname -s)" != "Linux" && "$(uname -s)" != "Darwin" ]]; then
  fail 'start.sh supports Linux and macOS. On Windows, run start.bat.'
fi

PYTHON311="$(command -v python3.11 || true)"
if [[ -z "$PYTHON311" ]]; then
  if [[ "$(uname -s)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
    printf 'Python 3.11 is missing. Installing it with Homebrew...\n'
    brew install python@3.11 || fail 'Could not install Python 3.11 with Homebrew.'
    PYTHON311="$(brew --prefix python@3.11)/bin/python3.11"
    [[ -x "$PYTHON311" ]] || fail 'Homebrew installed Python 3.11, but its executable was not found.'
  else
    fail 'Python 3.11 is required. Install Python 3.11, then run start.sh again.'
  fi
fi

if [[ ! -x "$PYTHON" ]]; then
  printf 'Creating the app private Python environment...\n'
  "$PYTHON311" -m venv .venv || fail 'Could not create .venv. Check that Python 3.11 includes venv support.'
fi

"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' \
  || fail 'The existing .venv is not Python 3.11. Remove .venv and run start.sh again.'

if ! "$PYTHON" -c 'import fastapi, uvicorn, httpx, torch, torchaudio; from chatterbox.mtl_tts import ChatterboxMultilingualTTS' >/dev/null 2>&1; then
  printf 'Installing Voice Language Tutor and Chatterbox. This can take several minutes and several GB...\n'
  "$PYTHON" -m pip install --upgrade pip || fail 'Could not upgrade pip.'
  "$PYTHON" -m pip install 'setuptools<81' wheel || fail 'Could not install Python build helpers.'
  "$PYTHON" -m pip install --only-binary=:all: PyYAML==6.0.2 || fail 'Could not install the PyYAML wheel.'
  "$PYTHON" -m pip install -r requirements.txt -r requirements-chatterbox.txt \
    || fail 'Could not install app dependencies. Check your internet connection and disk space.'
  "$PYTHON" -c 'import fastapi, uvicorn, httpx, torch, torchaudio; from chatterbox.mtl_tts import ChatterboxMultilingualTTS' \
    || fail 'Chatterbox did not install correctly. Review the install output above.'
fi

if [[ ! -f .env ]]; then
  cp .env.example .env || fail 'Could not create .env.'
fi

"$PYTHON" configure_first_run.py || fail 'First-run setup was canceled or did not complete.'

if [[ "$(uname -s)" == "Darwin" ]]; then
  OPEN_URL=(open)
else
  if command -v xdg-open >/dev/null 2>&1; then
    OPEN_URL=(xdg-open)
  elif command -v gio >/dev/null 2>&1; then
    OPEN_URL=(gio open)
  else
    fail 'Could not find xdg-open or gio. Install a desktop browser opener, then run start.sh again.'
  fi
fi

if ! APP_TOKEN="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(32))')"; then
  fail 'Could not create the app shutdown token.'
fi
export VOICE_TUTOR_APP_TOKEN="$APP_TOKEN"

URL="http://127.0.0.1:8000/#app_shutdown=${APP_TOKEN}"
(
  for _ in {1..90}; do
    if "$PYTHON" -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/config", timeout=1)' >/dev/null 2>&1; then
      "${OPEN_URL[@]}" "$URL" >/dev/null 2>&1 || true
      exit 0
    fi
    sleep 1
  done
  printf 'The local server did not start. Open %s in a browser after checking the error above.\n' "$URL" >&2
) &

printf 'Starting Voice Language Tutor. Close its browser tab to stop the local server.\n'
"$PYTHON" server.py
