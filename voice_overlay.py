#!/usr/bin/env python3
"""Floating recording indicator. Run as subprocess, kill to close."""

import json
import math
import os
import subprocess
import sys
import tkinter as tk

MODE = "transcribing" if len(sys.argv) > 1 and sys.argv[1] == "transcribing" else "recording"

W, H = 170, 52
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
POS_FILE = os.path.join(PROJECT_DIR, "overlay_position.json")


def _primary_screen() -> tuple[int, int, int, int]:
    try:
        out = subprocess.check_output(["xrandr", "--current"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if " connected primary" in line:
                part = [p for p in line.split() if "x" in p and "+" in p][0]
                res, ox, oy = part.split("+")
                w, h = res.split("x")
                return int(ox), int(oy), int(w), int(h)
        for line in out.splitlines():
            if " connected" in line and "+" in line:
                part = [p for p in line.split() if "x" in p and "+" in p][0]
                res, ox, oy = part.split("+")
                w, h = res.split("x")
                return int(ox), int(oy), int(w), int(h)
    except Exception:
        pass
    return 0, 0, 1920, 1080


def _load_pos(default_x: int, default_y: int) -> tuple[int, int]:
    try:
        with open(POS_FILE) as f:
            d = json.load(f)
            return d["x"], d["y"]
    except Exception:
        return default_x, default_y


def _save_pos(x: int, y: int) -> None:
    try:
        with open(POS_FILE, "w") as f:
            json.dump({"x": x, "y": y}, f)
    except Exception:
        pass


ox, oy, sw, sh = _primary_screen()
default_x = ox + (sw - W) // 2
default_y = oy + sh - H - 70
start_x, start_y = _load_pos(default_x, default_y)

root = tk.Tk()
root.title("")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.88)
root.configure(bg="#111111")
root.geometry(f"{W}x{H}+{start_x}+{start_y}")

canvas = tk.Canvas(root, width=W, height=H, bg="#111111", highlightthickness=0)
canvas.pack()

# ── Перетаскивание ────────────────────────────────────────────────────────────

_drag_x = 0
_drag_y = 0


def _on_press(event):
    global _drag_x, _drag_y
    _drag_x = event.x
    _drag_y = event.y


def _on_drag(event):
    x = root.winfo_x() + event.x - _drag_x
    y = root.winfo_y() + event.y - _drag_y
    root.geometry(f"+{x}+{y}")


def _on_release(event):
    _save_pos(root.winfo_x(), root.winfo_y())


canvas.bind("<Button-1>", _on_press)
canvas.bind("<B1-Motion>", _on_drag)
canvas.bind("<ButtonRelease-1>", _on_release)

# ── Анимация ──────────────────────────────────────────────────────────────────

_angle = 0.0

BARS    = 9
BAR_W   = 6
BAR_GAP = 3
BARS_X  = (W - (BARS * BAR_W + (BARS - 1) * BAR_GAP)) // 2
MAX_H   = H - 14
_FREQS  = [1.0, 1.4, 0.8, 1.7, 1.1, 0.9, 1.5, 1.2, 0.7]
_PHASES = [i * 0.65 for i in range(BARS)]


def _rounded_bar(x0: int, y0: int, x1: int, y1: int, r: int, color: str) -> None:
    r = min(r, (x1 - x0) // 2, max((y1 - y0) // 2, 1))
    points = [
        x0 + r, y0,   x1 - r, y0,
        x1,     y0,   x1,     y0 + r,
        x1,     y1 - r, x1,   y1,
        x1 - r, y1,   x0 + r, y1,
        x0,     y1,   x0,     y1 - r,
        x0,     y0 + r, x0,   y0,
    ]
    canvas.create_polygon(points, smooth=True, fill=color, outline="")


def _animate_recording():
    global _angle
    canvas.delete("all")
    for i in range(BARS):
        t = math.sin(_angle * _FREQS[i] + _PHASES[i]) * 0.5 + 0.5
        bh = int(5 + t * (MAX_H - 5))
        x0 = BARS_X + i * (BAR_W + BAR_GAP)
        y0 = (H - bh) // 2
        _rounded_bar(x0, y0, x0 + BAR_W, y0 + bh, r=3, color="#ffffff")
    _angle += 0.14
    root.after(30, _animate_recording)


def _animate_transcribing():
    global _angle
    canvas.delete("all")
    start = int((_angle * 4) % 360)
    canvas.create_arc(6, H // 2 - 15, 36, H // 2 + 15,
                      start=start, extent=270,
                      outline="#4fa3e0", width=3, style=tk.ARC)
    canvas.create_text(46, H // 2, text="Распознаю...", fill="#bbbbbb",
                       font=("Sans", 11), anchor="w")
    _angle += 0.12
    root.after(30, _animate_transcribing)


if MODE == "transcribing":
    _animate_transcribing()
else:
    _animate_recording()

root.mainloop()
