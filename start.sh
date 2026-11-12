#!/usr/bin/env bash
# Mac/Linux launcher. Make it executable once with:  chmod +x start.sh
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
if grep -q "paste_your_groq_key_here" .env; then
  echo "Open the .env file and paste your Groq API key, then run this again."; exit 1
fi
python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null || python3 -m pip install -r requirements.txt
curl -s -m 3 http://localhost:17493/docs >/dev/null || echo "WARNING: Voicebox does not seem to be running."
(sleep 3; (xdg-open http://localhost:8000 || open http://localhost:8000) >/dev/null 2>&1) &
python3 server.py
