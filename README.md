# Voice Language Tutor

Practice a conversation with an AI language tutor. Speak or type, receive a reply in your target language, and listen to it with locally generated speech.

![Voice Language Tutor showing a Japanese conversation, translation dropdown, cached audio controls, language and level selectors, and reply length](docs/tutor-ui.png)

## Windows setup

1. Install or create a [Groq API key](https://console.groq.com/keys).
2. Download or extract this repository, then double-click `start.bat`.
3. On first run, the launcher installs Python 3.11 if needed, creates a private `.venv`, and installs the app and Chatterbox text-to-speech dependencies. If Chrome is missing, it offers to install Chrome through `winget`.
4. Enter your Groq API key in the masked setup dialog. The key is saved in the local `.env` file and is not included in the shareable package.
5. Optionally enter the path to a WAV reference recording for a custom voice. Press Enter to use Chatterbox's built-in voice. Only use a recording you made or have permission to use.
6. The tutor opens in a Chrome app window. Close that window to stop the local server.

The first setup downloads several GB of Python packages. Chatterbox downloads its speech model the first time the server starts, so allow a few minutes and keep the computer online. Later launches reuse the installed environment and downloaded model.

## Conversation controls

- **Conversation language:** choose the language you want to practice. The tutor replies in that language, and speech recognition is configured for it.
- **Level:** choose a Japanese JLPT level from N5 through N1, or a CEFR level for other languages. The tutor adjusts its vocabulary and grammar to the selected level. Language and level choices are remembered in this browser.
- **Reply length:** choose Short, Normal, or Detailed to control how much the tutor says in each response.
- **English translation:** open **Show English translation** below a reply when you need its translation and learning note.
- **Audio:** generated speech stays with its reply for replay during the conversation. Choose **Regenerate audio** to create a fresh version.
- **Speak replies automatically:** have the tutor play audio as soon as a reply is ready, or use **Play voice** when you want to listen.
- **Send recognized speech automatically:** send a recognized utterance right away, or turn this off to review and edit it before sending.
- **New chat:** clear the current conversation and start again.

## Voice and character setup

Chatterbox runs locally and supports speech generation without a separate Voicebox installation. A reference WAV is optional; leaving the path empty uses Chatterbox's built-in voice. The model adds an inaudible watermark to generated audio.

To customize the tutor, edit a JSON file under `characters/` or copy one of the examples. Set `CHARACTER` in your local `.env` to the file name without `.json`, then restart the app. Keep local settings, API keys, reference recordings, and private character files out of public commits.

To create a shareable Windows ZIP, run `package-for-other-pc.ps1`. It includes the app and example characters, but excludes `.env`, local characters, and voice recordings. On another PC, extract the ZIP and double-click `start.bat`; that PC can provide its own Groq key and optional reference WAV during setup.

## Troubleshooting

- **Setup reports an error:** confirm the PC is online and has several GB of free disk space, then run `start.bat` again. The launcher checks dependencies and resumes installation.
- **Groq/API error:** check the key in `.env`. Leave `GROQ_MODEL` empty to let the app choose an available model automatically.
- **No speech audio:** allow the initial Chatterbox model download to finish, then check the server window for `[tts]` errors.
- **Microphone input fails:** open the app in Chrome or Edge, allow microphone access, and check that no other app is using the microphone.

## License

MIT. See `LICENSE`.