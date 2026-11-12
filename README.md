# Voice Language Tutor

Talk to a language tutor with **any voice you design**. You speak, the tutor answers in text and in a voice of your choice.

- **Brain:** [Groq](https://console.groq.com) (free tier) writes the tutor's replies.
- **Voice:** [Voicebox](https://github.com/jamiepine/voicebox) runs text-to-speech locally on your computer.
- **Ears:** your browser's speech recognition turns what you say into text.
- **Characters:** a tutor is just a small JSON file: name, personality, language, level and voice.

```
You speak -> browser -> text -> Groq -> reply text -> Voicebox -> audio
                                         |-> shown on screen (+ translation and notes)
```

## Quick start (Windows)

1. Install [Python 3.10+](https://python.org) (tick **Add python.exe to PATH**).
2. Install and open the **Voicebox** app. Create a voice profile in it (describe a voice or add a short reference sample) and note its name.
3. Get a free Groq API key at console.groq.com -> API Keys.
4. Double-click **`start.bat`**. On the first run it installs what it needs and opens `.env` for your key.
5. The tutor opens in Chrome or Edge at http://localhost:8000.

Mac/Linux: run `./start.sh` instead.

## Make your own tutor

1. Copy `characters/example-japanese.json` to `characters/my-tutor.json` and edit it.
2. In `.env` set `CHARACTER=my-tutor`.
3. Restart the tutor.

| Field | Meaning | Example |
|---|---|---|
| `name` | The tutor's name | `"Haruka"` |
| `target_language` | Language you are learning | `"Japanese"` |
| `native_language` | Language of translations and notes | `"English"` |
| `learner_level` | Your level | `"JLPT N4 to N3"`, `"A2 to B1"` |
| `personality` | How the tutor behaves and talks | `"Calm, warm and a little teasing"` |
| `extra_rules` | Optional extra instructions (list) | `["Use formal speech"]` |
| `voice_profile` | Name of the profile in Voicebox | `"My Tutor Voice"` |
| `tts_language` | Language code Voicebox speaks | `"ja"`, `"es"`, `"fr"` |
| `stt_language` | Language code for speech recognition | `"ja-JP"`, `"es-MX"`, `"fr-FR"` |
| `engine` | Voicebox engine | `"chatterbox"` |

Files named `characters/local-*.json` are ignored by git, so you can keep private characters on your own machine.

## Voices and consent

- Design a new voice from a description, or clone one only from audio **you recorded or have permission to use**.
- Do not clone real people, such as actors or voice actors, without their consent.
- Characters from games, anime or books are other people's work. Keep personal-use characters in `local-*.json` and do not publish them.

## Settings in the page

- **Voice replies:** speak every reply automatically, or press *Play voice*.
- **Send after speaking:** send your speech as soon as it is recognised, or edit it first.
- **Voice chunks:** how much text is sent to Voicebox at once. Short chunks start sooner. Long chunks can sound smoother but may drift in voice quality and take longer to start.

## Troubleshooting

- **Model not found / Groq error:** open http://localhost:8000/api/models to see which models your key can use. Leave `GROQ_MODEL` empty to choose automatically.
- **The tutor never speaks:** make sure the Voicebox app is open, and watch the `[tts]` lines in the server window.
- **Profile not found:** `voice_profile` must match the profile name in Voicebox exactly. The error lists the names it found.
- **Slow voice:** local speech models can run slower than real time on mid-range GPUs. Try shorter replies or smaller chunks.
- **Speech input does not work:** use Chrome or Edge, allow the microphone, and check your internet connection.

## Swapping the voice engine

All speech goes through the `tts()` function in `server.py`. To use another engine, replace that function so it returns WAV audio for a piece of text.

## Contributing

Issues and pull requests are welcome, especially new example characters, other TTS backends and translations of this README.

## License

MIT. See `LICENSE`.
