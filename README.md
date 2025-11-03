# aud-out-metro

A lightweight GUI metronome written in Python using Tkinter. It generates a short click tone at the configured BPM and provides a simple stopwatch and beat counter. The app saves the last BPM to `metronome_config.ini`.

## Quick summary

- GUI: Tkinter
- Audio: PyAudio (plays generated sine click); pydub is imported but the app generates a tone if no MP3 is loaded
- Config: `metronome_config.ini` (stores `last_bpm`)
- Launcher script: `run_metronome.sh` (activates `venv` and runs `main.py`)

## Features

- Start/Stop metronome with GUI buttons
- BPM input and +/- controls (range enforced: 30–300)
- Stopwatch display for elapsed time while running
- Beat counter
- Saves last BPM between runs in `metronome_config.ini`
 

## Files of interest

- `main.py` — main application source (Tkinter GUI and audio playback)
- `metronome_config.ini` — configuration (contains `[Settings] / last_bpm`)
- `run_metronome.sh` — helper script that activates `venv` and runs the app
- `GEMINI.md` — notes showing a recommended venv-backed run command

## Requirements

- Python 3.8+ (tested with recent Python 3)
- tkinter (usually included with system Python)
- numpy
- pyaudio (requires PortAudio system library)
- pydub (if you plan to play MP3s instead of the generated tone)

On Debian/Ubuntu you may need system packages before installing PyAudio / pydub's runtime:

```bash
sudo apt update
sudo apt install python3-venv python3-dev build-essential portaudio19-dev ffmpeg
```

Then create a venv and install Python deps:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install numpy pyaudio pydub
```

Note: Installing `pyaudio` via pip may require the `portaudio19-dev` system package as shown above. `pydub` requires `ffmpeg` for many audio formats.

## Run

You can run the app directly from the project root (recommended from inside a virtualenv):

```bash
# activate the venv, if present
source venv/bin/activate
# run the GUI
python3 main.py
```

Or use the included launcher script which assumes `venv` is present at `./venv`:

```bash
./run_metronome.sh
```

GEMINI integration: `GEMINI.md` contains an example absolute path into a venv. Adjust paths for your environment.

## Configuration

The app reads/writes a small INI file named `metronome_config.ini` in the current working directory. Current (and only) setting used:

- `[Settings]` / `last_bpm` — numeric BPM value persisted between runs

Example `metronome_config.ini`:

```ini
[Settings]
last_bpm = 100
```

Review `CHUNK_SIZE` and `samplerate` in `main.py` if you need different audio buffer or sample-rate behavior.

## Behavior notes / implementation details

- The app currently generates a short sine click using `numpy` rather than loading an external MP3. The code initializes a PyAudio stream (`pyaudio.PyAudio`) for output.
- If audio initialization fails, the app logs an error and shows a Tkinter messagebox indicating audio may be limited.
- BPM changes are clamped to the range 30–300 and the click duration is scaled relative to the beat interval (with a small cap).
- The app runs the metronome playback loop in a background thread and uses an event to stop it cleanly.

## Troubleshooting

- ``ModuleNotFoundError`` for `pyaudio` or `numpy`: ensure the virtualenv is activated and you installed packages into it (`pip install numpy pyaudio`).
- PyAudio installation errors: install `portaudio19-dev` (Debian/Ubuntu) or the equivalent for your distro before pip installing.
- If you see an audio initialization error in the logs or a GUI popup: the system audio device or PortAudio may not be available. Confirm your audio device works with other apps and that no other program is blocking it.
- `pydub` playback of MP3s: ensure `ffmpeg` is installed on your system.

## Suggested improvements (low risk)

 - Add a `requirements.txt` or `pyproject.toml` to make dependency installation reproducible.
- Add unit tests (small test for config read/write and BPM bounds).
- Add a packaged installer or systemd service for headless metronome playback if needed.

## Contributing

Contributions welcome. Open an issue or PR describing bug or enhancement. Keep changes focused and add tests when appropriate.

## License

No license is included in this repository. Add a `LICENSE` file (for example MIT) if you want to open-source the project.

## A short review

This repo contains a compact, usable GUI metronome. Implementation is straightforward and easy to read. The main items to watch for are native dependencies for `pyaudio` and the hard-coded WAV output path. Adding a `requirements.txt` and making output paths configurable would improve the project for other users.

