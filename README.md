# Shorts Maker

Type an idea, get a finished vertical short: script, voice, pictures, captions and a subscribe/follow intro.
Free, open source (MIT) and everything runs on your own computer.

## Features

- **Story formats**: Fact explainer, Mystery, Countdown, What if..., Myth vs truth, Legend, Journey. Each one gives the script a beat structure (hook, setup, twist...).
- **Narrator tones** (documentary, mysterious, energetic, dramatic, friendly, playful) that change both the writing and the voice speed.
- **Endings**: invite to follow, cliffhanger, seamless loop, or a question for the comments.
- **Story world**: one line of look and setting that is worked into every picture so a video or series feels like one story.
- **Custom project editor** with per-scene rewrite (presets or your own instruction), hook suggestions, reorder and picture controls.
- **Multi-part series**: plan 3-6 connected parts; each part recaps the last and teases the next, with a "PART n/N" badge.
- Stock footage (Pixabay/Pexels) or AI pictures made locally with stable-diffusion.cpp.
- 30-90 second videos, subscribe / follow / both intro buttons, resume after a failure, auto-update, dark theme.

## Install

1. Install [Python 3.10+](https://www.python.org/downloads/) and [Ollama](https://ollama.com), then run `ollama pull llama3.2`.
2. Download this repository (green **Code** button, **Download ZIP**) and unzip it.
3. Windows: double-click `Start Shorts Maker.bat`. Mac: double-click `Start Shorts Maker.command` (first time, see below).
4. Your browser opens. Add a free [Pixabay key](https://pixabay.com/api/docs/) in **Settings**, or use AI pictures.

Mac, first run only: `xattr -dr com.apple.quarantine <folder>` and `chmod +x "Start Shorts Maker.command"`.
AI pictures need a GPU (Windows) or Apple silicon; Intel Macs should use stock footage.

It checks GitHub for updates each time it starts (source in `update_source.txt`).

## Layout

| File | What it does |
| --- | --- |
| `app.py` | Local web server and job runner |
| `ui.py` | The whole web page (HTML/CSS/JS) |
| `story.py` | Story formats, tones, endings, series helpers |
| `shorts_maker.py` | Script writing, voice, visuals, video building |
| `ai_images.py` | Local AI picture setup and generation |
| `updater.py` | Self-updater |
| `tests/` | Offline unit tests: `python -m unittest discover tests` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). AI can state false facts: always check a script before posting.

License: [MIT](LICENSE)
