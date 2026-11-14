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

1. Get a Groq API key at console.groq.com -> API Keys.
2. Double-click **`start.bat`**. On a clean Windows PC it installs Python 3.11, creates a private environment, installs Chatterbox and the app dependencies, and installs Chrome if needed. Internet access and several GB of free disk space are required.
3. On first launch, enter your Groq API key. You can optionally enter the path to your own WAV reference clip; press Enter to use Chatterbox's built-in voice. The reference clip is copied into this PC's app folder.
4. The tutor opens in a single Chrome app window. Close that window to stop the server. The Chatterbox model downloads on the first server start.

To make a shareable Windows package, run `package-for-other-pc.ps1` from this folder. It creates a ZIP containing only the app and generic tutor files. It excludes `.env`, your local character, and all voice files. Send that ZIP to the other PC, extract it, and double-click `start.bat`.

## Built-in voice (no Voicebox)

Instead of the separate Voicebox app, the tutor can run the [Chatterbox](https://github.com/resemble-ai/chatterbox) speech model itself (MIT licence, supports 23 languages including Japanese, Spanish and French).

The Windows launcher configures this automatically. It detects an NVIDIA driver and selects CUDA 12.4 PyTorch; otherwise it uses CPU PyTorch. A custom reference audio clip is optional; without one, Chatterbox uses its built-in voice.

Chatterbox adds an inaudible watermark to the audio it generates. The first start downloads the model and can take several minutes.

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
- **Reply length:** choose a short, normal, or detailed tutor response.
- **Conversation language:** choose the language to practice from Chatterbox's supported languages; generated speech follows the selection.
- **Level:** choose JLPT N5 to N1 for Japanese, or CEFR A1 to C2 for other languages.
- **English translation:** open *Show English translation* under a reply when you want to see it.
- **Audio replay:** generated audio is kept with its message for replay; use *Regenerate audio* to create a fresh take.
- **Send after speaking:** send your speech as soon as it is recognised, or edit it first.
- **Voice chunks:** how much text is sent to Voicebox at once. Short chunks start sooner. Long chunks can sound smoother but may drift in voice quality and take longer to start.

## Troubleshooting

- **Model not found / Groq error:** open http://localhost:8000/api/models to see which models your key can use. Leave `GROQ_MODEL` empty to choose automatically.
- **Tutor never speaks:** make sure the Voicebox app is open, and watch the `[tts]` lines in the server window.
- **Profile not found:** `voice_profile` must match the profile name in Voicebox exactly. The error lists the names it found.
- **Slow voice:** local speech models can run slower than real time on mid-range GPUs. Try shorter replies or smaller chunks.
- **Speech input does not work:** use Chrome or Edge, allow the microphone, and check your internet connection.

## Swapping the voice engine

All speech goes through the `tts()` function in `server.py`. To use another engine, replace that function so it returns WAV audio for a piece of text.

## Contributing

Issues and pull requests are welcome, especially new example characters, other TTS backends and translations of this README.

## License

MIT. See `LICENSE`.
