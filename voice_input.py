#!/usr/bin/env python3
"""
Удержи RIGHT ALT для записи голоса, отпусти — текст вставится в активное поле.

Запуск:
    sudo ./venv/bin/python voice_input.py
    # или без sudo, если пользователь в группе 'input':
    #   sudo usermod -aG input $USER  (потом перелогиниться)
"""

import json
import math
import os
import struct
import sys
import tempfile
import threading
import time
import wave
import subprocess

import pyaudio
import keyboard
import requests

WHISPER_URL = "http://localhost:8000/v1/audio/transcriptions"
HOTKEY = "right alt"
LANGUAGE = "ru"
MIN_AMPLITUDE = 200

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_input_config.json")

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1

_recording = False
_frames: list[bytes] = []
_lock = threading.Lock()
_audio = pyaudio.PyAudio()
_overlay_proc = None

OVERLAY_SCRIPT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_overlay.py")
VENV_PYTHON     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python")
SYSTEM_PYTHON   = "/usr/bin/python3"


# ── Конфиг ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── Выбор устройства ──────────────────────────────────────────────────────────

def _list_input_devices() -> list[dict]:
    devices = []
    for i in range(_audio.get_device_count()):
        info = _audio.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            devices.append({"index": i, "name": info["name"],
                             "rate": int(info["defaultSampleRate"])})
    return devices


def _select_device(devices: list[dict]) -> dict:
    print("\n=== Доступные микрофоны ===")
    for d in devices:
        print(f"  [{d['index']}] {d['name']}  ({d['rate']} Гц)")
    while True:
        try:
            choice = input("\nВведи номер устройства: ").strip()
            idx = int(choice)
            match = [d for d in devices if d["index"] == idx]
            if match:
                return match[0]
            print("Нет такого устройства, попробуй снова.")
        except (ValueError, EOFError):
            print("Введи число.")


def _detect_rate(device_index: int) -> int:
    info = _audio.get_device_info_by_index(device_index)
    default = int(info["defaultSampleRate"])
    for rate in (16000, 48000, 44100, 22050, default):
        try:
            if _audio.is_format_supported(rate, input_device=device_index,
                                          input_channels=CHANNELS,
                                          input_format=FORMAT):
                return rate
        except Exception:
            continue
    return default


def _setup_device(force: bool = False) -> tuple[int, int]:
    """Возвращает (device_index, sample_rate). При первом запуске спрашивает."""
    cfg = _load_config()
    if not force and "device_index" in cfg:
        idx = cfg["device_index"]
        rate = cfg.get("sample_rate") or _detect_rate(idx)
        name = cfg.get("device_name", f"устройство [{idx}]")
        print(f"Микрофон: {name} (индекс {idx}, {rate} Гц)")
        print("  Для смены устройства запусти с флагом --setup")
        return idx, rate

    devices = _list_input_devices()
    if not devices:
        print("Микрофоны не найдены!", file=sys.stderr)
        sys.exit(1)

    device = _select_device(devices)
    idx = device["index"]
    rate = _detect_rate(idx)

    _save_config({"device_index": idx, "device_name": device["name"], "sample_rate": rate})
    print(f"\nСохранено: {device['name']} ({rate} Гц)")
    return idx, rate


# ── X Display ─────────────────────────────────────────────────────────────────

def _get_display() -> str:
    display = os.environ.get("DISPLAY")
    if display:
        return display
    try:
        out = subprocess.check_output(
            ["bash", "-c",
             "grep -z DISPLAY /proc/$(pgrep -u $(logname) -n gnome-shell 2>/dev/null || "
             "pgrep -u $(logname) -n Xorg 2>/dev/null || "
             "pgrep -u $(logname) -n xorg 2>/dev/null)/environ 2>/dev/null "
             "| tr '\\0' '\\n' | grep DISPLAY"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        if "=" in out:
            return out.split("=", 1)[1]
    except Exception:
        pass
    return ":0"


DISPLAY_VAR = _get_display()


# ── Уведомления ───────────────────────────────────────────────────────────────

def _x_env() -> dict:
    env = {**os.environ, "DISPLAY": DISPLAY_VAR}
    # Ищем XAUTHORITY у процессов пользователя (нужно для запуска под sudo)
    xauth = os.environ.get("XAUTHORITY", "")
    if not xauth or not os.path.exists(xauth):
        try:
            out = subprocess.check_output(
                ["bash", "-c",
                 "grep -z XAUTHORITY /proc/$(pgrep -u $(logname) -n gnome-shell 2>/dev/null || "
                 "pgrep -u $(logname) -n gnome-session 2>/dev/null)/environ 2>/dev/null "
                 "| tr '\\0' '\\n' | grep XAUTHORITY"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
            if "=" in out:
                xauth = out.split("=", 1)[1]
        except Exception:
            pass
    if xauth:
        env["XAUTHORITY"] = xauth
    return env


def _show_overlay(mode: str = "recording") -> None:
    global _overlay_proc
    _hide_overlay()
    env = _x_env()
    existing = env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        [VENV_PYTHON, OVERLAY_SCRIPT, mode],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    _overlay_proc = proc
    def _log_stderr():
        err = proc.stderr.read()  # локальная ссылка, не глобальная
        if err:
            print(f"[overlay stderr] {err.decode()}", file=sys.stderr)
    threading.Thread(target=_log_stderr, daemon=True).start()


def _hide_overlay() -> None:
    global _overlay_proc
    proc = _overlay_proc
    _overlay_proc = None
    if proc and proc.poll() is None:
        proc.kill()  # SIGKILL — мгновенно, без шансов зависнуть
        proc.wait()


def notify(msg: str, urgent: bool = False) -> None:
    args = ["notify-send", "-t", "3000"]
    if urgent:
        args += ["-u", "critical"]
    args += ["Voice Input", msg]
    env = {**os.environ, "DISPLAY": DISPLAY_VAR}
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)


# ── Запись и распознавание ────────────────────────────────────────────────────

def _record_loop(device_index: int, rate: int) -> None:
    stream = _audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK,
    )
    try:
        while _recording:
            _frames.append(stream.read(CHUNK, exception_on_overflow=False))
    finally:
        stream.stop_stream()
        stream.close()


_TERMINAL_CLASSES = {
    "gnome-terminal", "xterm", "konsole", "tilix", "alacritty",
    "kitty", "terminator", "urxvt", "st-256color", "st",
}


def _is_terminal_focused() -> bool:
    try:
        env = {**os.environ, "DISPLAY": DISPLAY_VAR}
        out = subprocess.check_output(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"], text=True,
            stderr=subprocess.DEVNULL, env=env,
        )
        wid = out.strip().split()[-1]
        cls = subprocess.check_output(
            ["xprop", "-id", wid, "WM_CLASS"], text=True,
            stderr=subprocess.DEVNULL, env=env,
        ).lower()
        return any(t in cls for t in _TERMINAL_CLASSES)
    except Exception:
        return False


def _transcribe_and_paste(rate: int) -> None:
    if not _frames:
        notify("Ничего не записано")
        return

    raw = b"".join(_frames)
    samples = struct.unpack(f"{len(raw) // 2}h", raw)
    rms = math.sqrt(sum(s * s for s in samples) / len(samples)) if samples else 0
    print(f"[RMS] {rms:.0f}")
    if rms < MIN_AMPLITUDE:
        _hide_overlay()
        notify("Микрофон не слышит речи")
        print("[тихо, пропускаем]")
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        wf = wave.open(tmp_path, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(_audio.get_sample_size(FORMAT))
        wf.setframerate(rate)
        wf.writeframes(raw)
        wf.close()

        with open(tmp_path, "rb") as f:
            resp = requests.post(
                WHISPER_URL,
                files={"file": ("audio.wav", f, "audio/wav")},
                data={"language": LANGUAGE},
                timeout=60,
            )
        resp.raise_for_status()

        text = resp.json().get("text", "").strip()
        if not text:
            notify("Речь не распознана")
            return

        print(f"[распознано] {text}")

        env = {**os.environ, "DISPLAY": DISPLAY_VAR}
        result = subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode(),
            env=env,
            capture_output=True,
        )
        if result.returncode != 0:
            notify("Ошибка xclip", urgent=True)
            print(f"[xclip ошибка] {result.stderr.decode()}", file=sys.stderr)
            return

        time.sleep(0.1)
        keyboard.send("ctrl+shift+v" if _is_terminal_focused() else "ctrl+v")

        preview = text[:60] + ("…" if len(text) > 60 else "")
        notify(f"✓ {preview}")

    except requests.ConnectionError:
        notify("Ошибка: сервер Whisper не запущен", urgent=True)
        print(f"Ошибка: сервер недоступен на {WHISPER_URL}", file=sys.stderr)
    except Exception as exc:
        notify(f"Ошибка: {exc}", urgent=True)
        print(f"Ошибка: {exc}", file=sys.stderr)
    finally:
        _hide_overlay()
        os.unlink(tmp_path)


# ── Главный цикл ──────────────────────────────────────────────────────────────

def main() -> None:
    force_setup = "--setup" in sys.argv
    device_index, rate = _setup_device(force=force_setup)

    def on_key_event(event: keyboard.KeyboardEvent) -> None:
        global _recording, _frames

        if event.scan_code != 100:  # 100 = KEY_RIGHTALT, 56 = KEY_LEFTALT
            return

        if event.event_type == keyboard.KEY_DOWN:
            with _lock:
                if not _recording:
                    _recording = True
                    _frames = []
                    _show_overlay("recording")
                    print("[запись]")
                    threading.Thread(target=_record_loop,
                                     args=(device_index, rate), daemon=True).start()

        elif event.event_type == keyboard.KEY_UP:
            with _lock:
                if _recording:
                    _recording = False
                    print("[стоп]")
                    threading.Thread(target=_transcribe_and_paste,
                                     args=(rate,), daemon=True).start()

    keyboard.hook_key(HOTKEY, on_key_event)
    print(f"\nГолосовой ввод активен. DISPLAY={DISPLAY_VAR}")
    print(f"  Удержи [{HOTKEY.upper()}] → говори → отпусти.")
    print(f"  Ctrl+C для выхода.\n")
    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\nВыход.")
    finally:
        _audio.terminate()


if __name__ == "__main__":
    main()
