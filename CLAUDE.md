# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

PTT Whisper is a push-to-talk voice input tool for Ubuntu/GNOME (X11). Hold Right Alt → speak → release: audio is captured, sent to a local Whisper HTTP server, and the transcribed text is pasted via `xclip` + `Ctrl+V`.

## Running the two processes

**Whisper server** (runs as a system service in production, or manually):
```bash
source venv/bin/activate
uvicorn whisper_server:app --host 0.0.0.0 --port 8000
```

**Voice input client** (requires `/dev/input` access — either `sudo` or be in the `input` group):
```bash
sudo ./venv/bin/python voice_input.py
# First run prompts for microphone selection, saved to voice_input_config.json
sudo ./venv/bin/python voice_input.py --setup   # re-run device selection
./venv/bin/python list_devices.py               # list available mics
```

## Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# System packages also required:
sudo apt install xclip x11-xserver-utils
```

`openai-whisper` is installed directly from GitHub (not PyPI).

## Architecture

The system has two independent processes that communicate over HTTP:

| File | Role |
|---|---|
| `whisper_server.py` | FastAPI server; loads Whisper model at startup; exposes `POST /v1/audio/transcriptions` (OpenAI-compatible); saves audio to a temp file, transcribes, deletes it |
| `voice_input.py` | Main client; hooks the `right alt` key via `keyboard`; records PCM via PyAudio into a list of byte frames; on key-up, writes a WAV, POSTs to the server, copies result to clipboard with `xclip`, sends `Ctrl+V` |
| `voice_overlay.py` | Standalone tkinter subprocess launched/killed by `voice_input.py`; accepts `recording` or `transcribing` as argv[1]; animates equalizer bars or a spinner |

**Key design points:**
- `voice_overlay.py` runs as a separate subprocess (not a thread) so tkinter's mainloop doesn't block the audio thread. It is killed with SIGKILL on state changes.
- When running under `sudo`, `DISPLAY` and `XAUTHORITY` are auto-detected by scanning `/proc/<gnome-shell-pid>/environ`.
- Silence is filtered by RMS amplitude (`MIN_AMPLITUDE = 200`) before sending to the server.
- Microphone selection is persisted in `voice_input_config.json` (gitignored pattern; created at runtime).

## Configuration

Edit constants at the top of `voice_input.py`:

| Constant | Default | Purpose |
|---|---|---|
| `HOTKEY` | `right alt` | Push-to-talk key (any `keyboard` key name) |
| `LANGUAGE` | `ru` | Whisper language hint |
| `WHISPER_URL` | `http://localhost:8000/v1/audio/transcriptions` | Server endpoint |
| `MIN_AMPLITUDE` | `200` | RMS threshold below which audio is discarded |

Whisper model size (tradeoff: accuracy vs. VRAM/speed) is set in `whisper_server.py`:
```python
model = whisper.load_model("small")  # tiny | base | small | medium | large
```

## systemd services

`install.sh` installs two services from `systemd/`:
- `whisper-server.service` — system-level (root), starts the FastAPI server
- `ptt-whisper.service` — user-level, starts `voice_input.py`

```bash
sudo bash install.sh   # installs and enables both services
```

Log tailing: `sudo journalctl -u whisper-server -f` / `journalctl --user -u ptt-whisper -f`
