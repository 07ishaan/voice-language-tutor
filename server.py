"""Voice Language Tutor: Groq (brain) + Voicebox (voice) + your microphone.

Run:  python server.py   then open http://localhost:8000
"""
import asyncio
import json
import os
import secrets
from pathlib import Path
from typing import Literal

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
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
# "voicebox" = call the Voicebox app, "chatterbox" = run the Chatterbox model inside this server.
TTS_BACKEND = os.environ.get("TTS_BACKEND", "voicebox").strip().lower()
APP_SHUTDOWN_TOKEN = os.environ.get("VOICE_TUTOR_APP_TOKEN", "")


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

LANGUAGE_OPTIONS = [
    {"code": "ar", "name": "Arabic", "stt": "ar-SA"},
    {"code": "da", "name": "Danish", "stt": "da-DK"},
    {"code": "de", "name": "German", "stt": "de-DE"},
    {"code": "el", "name": "Greek", "stt": "el-GR"},
    {"code": "en", "name": "English", "stt": "en-US"},
    {"code": "es", "name": "Spanish", "stt": "es-ES"},
    {"code": "fi", "name": "Finnish", "stt": "fi-FI"},
    {"code": "fr", "name": "French", "stt": "fr-FR"},
    {"code": "he", "name": "Hebrew", "stt": "he-IL"},
    {"code": "hi", "name": "Hindi", "stt": "hi-IN"},
    {"code": "it", "name": "Italian", "stt": "it-IT"},
    {"code": "ja", "name": "Japanese", "stt": "ja-JP"},
    {"code": "ko", "name": "Korean", "stt": "ko-KR"},
    {"code": "ms", "name": "Malay", "stt": "ms-MY"},
    {"code": "nl", "name": "Dutch", "stt": "nl-NL"},
    {"code": "no", "name": "Norwegian", "stt": "nb-NO"},
    {"code": "pl", "name": "Polish", "stt": "pl-PL"},
    {"code": "pt", "name": "Portuguese", "stt": "pt-PT"},
    {"code": "ru", "name": "Russian", "stt": "ru-RU"},
    {"code": "sv", "name": "Swedish", "stt": "sv-SE"},
    {"code": "sw", "name": "Swahili", "stt": "sw-KE"},
    {"code": "tr", "name": "Turkish", "stt": "tr-TR"},
    {"code": "zh", "name": "Chinese", "stt": "zh-CN"},
]
LANGUAGE_BY_CODE = {item["code"]: item for item in LANGUAGE_OPTIONS}
CONFIGURED_LANGUAGE_CODE = os.environ.get("VOICEBOX_LANGUAGE") or CHAR["tts_language"]
DEFAULT_LANGUAGE_CODE = CONFIGURED_LANGUAGE_CODE if CONFIGURED_LANGUAGE_CODE in LANGUAGE_BY_CODE else "ja"
JLPT_LEVELS = ["N5", "N4", "N3", "N2", "N1"]
CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def default_level_for_character() -> str:
    levels = JLPT_LEVELS if DEFAULT_LANGUAGE_CODE == "ja" else CEFR_LEVELS
    current = str(CHAR["learner_level"]).upper()
    return next((level for level in levels if level in current), levels[0])


DEFAULT_LEARNER_LEVEL = default_level_for_character()


def build_system_prompt(c: dict, response_length: str = "normal") -> str:
    length_rules = {
        "short": "Keep each target-language reply to one concise sentence.",
        "normal": "Keep each target-language reply to 1 to 3 short sentences.",
        "detailed": "Give a fuller target-language reply in 3 to 5 clear sentences, with useful detail at the learner's level.",
    }
    rules = [
        f"Reply only in {c['target_language']}, using vocabulary and grammar for a "
        f"learner at level {c['learner_level']}.",
        length_rules.get(response_length, length_rules["normal"]),
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


app = FastAPI()


class ChatRequest(BaseModel):
    history: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]
    response_length: Literal["short", "normal", "detailed"] = "normal"
    language_code: str = DEFAULT_LANGUAGE_CODE
    learner_level: str = DEFAULT_LEARNER_LEVEL


class TTSRequest(BaseModel):
    text: str
    language_code: str = DEFAULT_LANGUAGE_CODE


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
        "language_code": DEFAULT_LANGUAGE_CODE,
        "languages": LANGUAGE_OPTIONS,
        "learner_level": DEFAULT_LEARNER_LEVEL,
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
    language = LANGUAGE_BY_CODE.get(req.language_code)
    if not language:
        raise HTTPException(422, "Choose a supported conversation language.")
    valid_levels = JLPT_LEVELS if req.language_code == "ja" else CEFR_LEVELS
    if req.learner_level not in valid_levels:
        raise HTTPException(422, f"Choose a valid level for {language['name']}.")
    profile = {**CHAR, "target_language": language["name"], "learner_level": req.learner_level}

    messages = [{"role": "system", "content": build_system_prompt(profile, req.response_length)}]
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
                token_caps = {"short": 500, "normal": 1000, "detailed": 1800}
                body = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": token_caps[req.response_length],
                }
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


# ---------- Built-in Chatterbox backend (no Voicebox needed) ----------
_cb_model = None
_cb_lock = asyncio.Lock()  # one generation at a time on the GPU


def _load_chatterbox():
    global _cb_model
    if _cb_model is None:
        try:
            import torch
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        except ImportError as e:
            raise RuntimeError(
                "Chatterbox is not installed. See 'Built-in voice' in the README. "
                f"({e})"
            )
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[tts] loading Chatterbox on {device} (first time can take a few minutes)...", flush=True)
        _cb_model = ChatterboxMultilingualTTS.from_pretrained(device=device)
        print(f"[tts] Chatterbox ready on {device}", flush=True)
    return _cb_model


def _chatterbox_wav(text: str, language_code: str) -> bytes:
    import io

    import torchaudio

    model = _load_chatterbox()
    kwargs = {"language_id": language_code}
    ref = CHAR.get("reference_audio")
    if ref:
        ref_path = HERE / "voices" / ref
        if not ref_path.exists():
            raise RuntimeError(f"Reference audio not found: {ref_path}")
        kwargs["audio_prompt_path"] = str(ref_path)
    for key in ("exaggeration", "cfg_weight"):
        if key in CHAR:
            kwargs[key] = CHAR[key]
    wav = model.generate(text, **kwargs)
    buf = io.BytesIO()
    torchaudio.save(buf, wav.cpu(), model.sr, format="wav")
    return buf.getvalue()


@app.post("/api/tts")
async def tts(req: TTSRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Empty text")
    if req.language_code not in LANGUAGE_BY_CODE:
        raise HTTPException(422, "Choose a supported voice language.")

    if TTS_BACKEND == "chatterbox":
        try:
            async with _cb_lock:
                audio = await asyncio.to_thread(_chatterbox_wav, text, req.language_code)
        except RuntimeError as e:
            raise HTTPException(503, str(e))
        return Response(content=audio, media_type="audio/wav")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            profile_id = await resolve_profile_id(client)
            r = await client.post(
                f"{VOICEBOX_URL}/generate",
                json={
                    "text": text,
                    "profile_id": profile_id,
                    "language": req.language_code,
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


@app.post("/api/shutdown")
async def shutdown(request: Request):
    """Allow the dedicated desktop launcher to stop its own local server."""
    if not APP_SHUTDOWN_TOKEN:
        raise HTTPException(404, "Not found")
    supplied = request.headers.get("X-Voice-Tutor-Token", "")
    if not secrets.compare_digest(supplied, APP_SHUTDOWN_TOKEN):
        raise HTTPException(403, "Forbidden")
    running_server = getattr(app.state, "uvicorn_server", None)
    if running_server is None:
        raise HTTPException(503, "Server shutdown is unavailable")
    running_server.should_exit = True
    return {"stopping": True}


@app.on_event("startup")
async def preload():
    if TTS_BACKEND == "chatterbox":
        async def warm():
            try:
                await asyncio.to_thread(_load_chatterbox)
            except Exception as e:  # shown again when the first voice request fails
                print(f"[tts] preload failed: {e}", flush=True)
        asyncio.create_task(warm())


if __name__ == "__main__":
    running_server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8000))
    app.state.uvicorn_server = running_server
    running_server.run()
