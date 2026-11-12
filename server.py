"""Voice Language Tutor: Groq (brain) + Voicebox (voice) + your microphone.

Run:  python server.py   then open http://localhost:8000
"""
import asyncio
import json
import os
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

HERE = Path(__file__).parent


def load_env():
    """Tiny .env reader so no extra package is needed."""
    env_file = HERE / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "").strip()  # empty = pick automatically
# Optional second choice. Models that no longer exist or hit the free limit are skipped automatically.
GROQ_FALLBACK_MODEL = os.environ.get("GROQ_FALLBACK_MODEL", "").strip()
VOICEBOX_URL = os.environ.get("VOICEBOX_URL", "http://localhost:17493").rstrip("/")
CHARACTER = os.environ.get("CHARACTER", "example-japanese")
TTS_TIMEOUT = float(os.environ.get("TTS_TIMEOUT", "180"))


def load_character() -> dict:
    """Read characters/<CHARACTER>.json and fill in defaults."""
    path = HERE / "characters" / f"{CHARACTER}.json"
    if not path.exists():
        raise SystemExit(f"Character file not found: {path}\nCheck CHARACTER in your .env file.")
    c = json.loads(path.read_text(encoding="utf-8"))
    c.setdefault("name", "Tutor")
    c.setdefault("target_language", "Japanese")
    c.setdefault("native_language", "English")
    c.setdefault("learner_level", "beginner")
    c.setdefault("personality", "Friendly and patient.")
    c.setdefault("extra_rules", [])
    c.setdefault("voice_profile", "My Tutor Voice")
    c.setdefault("tts_language", "ja")
    c.setdefault("stt_language", "ja-JP")
    c.setdefault("engine", "chatterbox")
    return c


CHAR = load_character()
# .env values override the character file if you set them.
VOICEBOX_PROFILE = os.environ.get("VOICEBOX_PROFILE") or CHAR["voice_profile"]
VOICEBOX_ENGINE = os.environ.get("VOICEBOX_ENGINE") or CHAR["engine"]
VOICEBOX_LANGUAGE = os.environ.get("VOICEBOX_LANGUAGE") or CHAR["tts_language"]


def build_system_prompt(c: dict) -> str:
    rules = [
        f"Reply only in {c['target_language']}, in 1 to 3 short sentences, using vocabulary and grammar for a "
        f"learner at level {c['learner_level']}.",
        f"If the learner makes a mistake, naturally use the correct form in your reply and mention the "
        f"correction briefly in the {c['native_language']} note.",
        "Occasionally introduce one new word or grammar pattern that fits the learner's level.",
        f"Never mix {c['native_language']} into the {c['target_language']} reply. {c['native_language']} "
        f"is only for the note.",
        "Keep a conversation going: react to what the learner said and ask or invite something back.",
    ] + list(c["extra_rules"])
    rule_text = "\n".join(f"- {r}" for r in rules)
    return (
        f"You are {c['name']}, a {c['target_language']} tutor. Speak as {c['name']}, in character, "
        f"never as an AI assistant.\n\n"
        f"Personality: {c['personality']}\n"
        f"Learner: a native {c['native_language']} speaker studying {c['target_language']} at level {c['learner_level']}.\n\n"
        f"Rules:\n{rule_text}\n\n"
        f"Answer with this JSON object only, nothing else:\n"
        f'{{"target": "your reply in {c["target_language"]}", '
        f'"native": "{c["native_language"]} translation plus a short grammar or vocabulary note if useful"}}'
    )


SYSTEM_PROMPT = build_system_prompt(CHAR)

app = FastAPI()


class ChatRequest(BaseModel):
    history: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]


class TTSRequest(BaseModel):
    text: str


@app.get("/")
async def index():
    return FileResponse(HERE / "index.html")


@app.get("/api/config")
async def config():
    """What the web page needs to know about the current character."""
    return {
        "name": CHAR["name"],
        "title": f"{CHAR['name']} · {CHAR['target_language']} tutor",
        "target_language": CHAR["target_language"],
        "native_language": CHAR["native_language"],
        "stt_language": CHAR["stt_language"],
        "placeholder": CHAR.get("placeholder") or f"Say something in {CHAR['target_language']}",
        "empty_text": f"Say something in {CHAR['target_language']} with the microphone, or type below. "
        f"{CHAR['name']} will answer.",
    }


GROQ_BASE = "https://api.groq.com/openai/v1"
NOT_CHAT = ("whisper", "guard", "tts", "orpheus", "embed", "playai", "distil", "safeguard")
PREFER = ("gpt-oss-120b", "llama-3.3-70b", "qwen", "llama-4", "gpt-oss-20b", "llama-3.1-8b", "llama")

_discovered: list[str] = []
_working_model: list[str] = []  # remembers the model that worked last


def _rank(model_id: str) -> int:
    low = model_id.lower()
    for i, name in enumerate(PREFER):
        if name in low:
            return i
    return len(PREFER)


async def discover_models(client: httpx.AsyncClient) -> list[str]:
    """Ask Groq which models your key can use right now."""
    if _discovered:
        return _discovered
    r = await client.get(f"{GROQ_BASE}/models", headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
    if r.status_code != 200:
        raise HTTPException(502, f"Could not list Groq models ({r.status_code}): {r.text[:200]}")
    ids = [m["id"] for m in r.json().get("data", []) if not any(x in m["id"].lower() for x in NOT_CHAT)]
    ids.sort(key=_rank)
    _discovered.extend(ids)
    return _discovered


def parse_reply(raw: str) -> tuple[str, str]:
    data = None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                data = None
    if isinstance(data, dict):
        return str(data.get("target", "")).strip(), str(data.get("native", "")).strip()
    return raw.strip(), ""


@app.get("/api/models")
async def models():
    """Open http://localhost:8000/api/models to see which Groq models your key can use."""
    if not GROQ_API_KEY:
        raise HTTPException(500, "GROQ_API_KEY is missing. Add it to the .env file.")
    async with httpx.AsyncClient(timeout=30) as client:
        return {"usable_models": await discover_models(client), "using": _working_model[:1]}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not GROQ_API_KEY:
        raise HTTPException(500, "GROQ_API_KEY is missing. Add it to the .env file.")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in req.history[-20:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"]})

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    last_error = "No usable Groq model was found."

    async with httpx.AsyncClient(timeout=90) as client:
        candidates: list[str] = []
        for name in [*_working_model, GROQ_MODEL, GROQ_FALLBACK_MODEL]:
            if name and name not in candidates:
                candidates.append(name)
        # Add models discovered from Groq itself (skipped models that were already tried).
        try:
            for name in await discover_models(client):
                if name not in candidates:
                    candidates.append(name)
        except HTTPException as e:
            if not candidates:
                raise e

        for model in candidates[:6]:
            for use_json in (True, False):
                body = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 1500}
                if use_json:
                    body["response_format"] = {"type": "json_object"}
                r = await client.post(f"{GROQ_BASE}/chat/completions", headers=headers, json=body)
                if r.status_code == 200:
                    raw = r.json()["choices"][0]["message"].get("content") or ""
                    target, native = parse_reply(raw)
                    if target:
                        _working_model[:] = [model]
                        print(f"[chat] using Groq model: {model}")
                        return {"target": target, "native": native}
                    last_error = f"{model} returned an empty reply."
                    break
                last_error = f"{model}: {r.status_code} {r.text[:200]}"
                # 400 = this model may not support JSON mode, retry once without it.
                if r.status_code == 400 and use_json:
                    continue
                break  # 404 (model gone), 429 (free limit) and others: try the next model

    raise HTTPException(502, f"Groq did not answer. Last error: {last_error}")


_profile_id_cache: dict[str, str] = {}


async def resolve_profile_id(client: httpx.AsyncClient) -> str:
    if VOICEBOX_PROFILE in _profile_id_cache:
        return _profile_id_cache[VOICEBOX_PROFILE]

    r = await client.get(f"{VOICEBOX_URL}/profiles")
    r.raise_for_status()
    data = r.json()
    profiles = data.get("profiles", data) if isinstance(data, dict) else data

    wanted = VOICEBOX_PROFILE.lower()
    for p in profiles:
        if str(p.get("id", "")).lower() == wanted or str(p.get("name", "")).lower() == wanted:
            _profile_id_cache[VOICEBOX_PROFILE] = p["id"]
            return p["id"]
    names = [p.get("name") for p in profiles]
    raise HTTPException(
        500, f"Voicebox profile '{VOICEBOX_PROFILE}' not found. Profiles found: {names}"
    )


@app.post("/api/tts")
async def tts(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Empty text")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            profile_id = await resolve_profile_id(client)
            r = await client.post(
                f"{VOICEBOX_URL}/generate",
                json={
                    "text": text,
                    "profile_id": profile_id,
                    "language": VOICEBOX_LANGUAGE,
                    "engine": VOICEBOX_ENGINE,
                },
            )
        except httpx.ConnectError:
            raise HTTPException(503, "Cannot reach Voicebox. Is the Voicebox app open?")
        print(f"[tts] POST /generate -> {r.status_code} {r.text[:300]}", flush=True)
        if r.status_code >= 400:
            raise HTTPException(502, f"Voicebox error {r.status_code}: {r.text[:300]}")

        generation_id = r.json().get("id")
        if not generation_id:
            raise HTTPException(502, f"Voicebox gave no generation id: {r.text[:300]}")

        # Poll the generation record until it finishes, then download the audio.
        busy = ("generating", "queued", "pending", "processing", "loading", "running")
        waited = 0.0
        while waited < TTS_TIMEOUT:
            h = await client.get(f"{VOICEBOX_URL}/history/{generation_id}")
            status, error = "", None
            if h.status_code == 200:
                info = h.json()
                status = str(info.get("status", "")).lower()
                error = info.get("error")
            if int(waited) % 5 == 0:
                print(f"[tts] waiting {int(waited)}s: status={status or h.status_code}", flush=True)

            if status in ("failed", "error", "cancelled", "canceled") or error:
                raise HTTPException(502, f"Voicebox could not generate the audio: {error or status}")

            if status not in busy:
                a = await client.get(f"{VOICEBOX_URL}/audio/{generation_id}")
                ctype = a.headers.get("content-type", "")
                if a.status_code == 200 and (ctype.startswith("audio") or a.content[:4] == b"RIFF"):
                    print(f"[tts] done in {int(waited)}s ({len(a.content)} bytes)", flush=True)
                    return Response(content=a.content, media_type="audio/wav")
            await asyncio.sleep(1)
            waited += 1
    raise HTTPException(504, "Voicebox took too long to generate audio.")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
