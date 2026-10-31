#!/usr/bin/env python3
"""Read Codex account limits and draw two small remaining-quota bars."""

import fcntl
import json
import math
import os
from pathlib import Path
import select
import shutil
import struct
import subprocess
import tempfile
import time
import zlib
from datetime import datetime


def read_limits():
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("Codex CLI is unavailable")
    process = subprocess.Popen(
        [codex, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    pending = b""
    deadline = time.monotonic() + 25

    def send(message):
        process.stdin.write((json.dumps(message) + "\n").encode())
        process.stdin.flush()

    def receive(request_id):
        nonlocal pending
        while True:
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                message = json.loads(line)
                if message.get("id") == request_id:
                    if "error" in message:
                        raise RuntimeError("Codex could not read account limits")
                    return message["result"]
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                raise RuntimeError("Codex usage request timed out")
            data = os.read(process.stdout.fileno(), 65536)
            if not data:
                raise RuntimeError("Codex app-server exited")
            pending += data

    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "sketchybar_usage", "version": "1.0.0"}}})
        receive(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "account/rateLimits/read"})
        result = receive(2)
        buckets = result.get("rateLimitsByLimitId") or {}
        return buckets.get("codex") or result.get("rateLimits") or {}
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stdin.close()
        process.stdout.close()


def remaining(window):
    if not window:
        return None
    used = window.get("usedPercent")
    if not isinstance(used, (int, float)) or not math.isfinite(used):
        return None
    return max(0, min(100, 100 - used))


def draw_bars(path, windows):
    # Render at 2x resolution; SketchyBar displays this at 44 x 16 points.
    width, height = 88, 32
    pixels = bytearray(width * height * 4)
    for top, window in zip((4, 20), windows):
        value = remaining(window)
        color = (109, 211, 144, 255)
        if value is not None and value <= 10:
            color = (245, 105, 105, 255)
        elif value is not None and value <= 25:
            color = (245, 198, 97, 255)
        fill = round(84 * value / 100) if value is not None else 0
        for y in range(top, top + 8):
            for x in range(2, 86):
                rgba = color if x - 2 < fill else (180, 185, 195, 90)
                # Unknown limits have a short neutral dash in the track.
                if value is None and 38 <= x < 50:
                    rgba = (180, 185, 195, 255)
                offset = (y * width + x) * 4
                pixels[offset:offset + 4] = bytes(rgba)

    def chunk(kind, data):
        return (struct.pack("!I", len(data)) + kind + data
                + struct.pack("!I", zlib.crc32(kind + data)))

    rows = b"".join(b"\0" + pixels[y * width * 4:(y + 1) * width * 4]
                    for y in range(height))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(png)
    temporary.replace(path)


def describe(title, window):
    value = remaining(window)
    if value is None:
        return f"{title}: unavailable"
    text = f"{title}: {value:.0f}% remaining"
    reset = window.get("resetsAt")
    if isinstance(reset, (int, float)):
        text += " · resets " + datetime.fromtimestamp(reset).strftime("%a %-I:%M %p")
    return text


def sketchybar(*args):
    subprocess.run(["sketchybar", *args], check=True, timeout=5)


def main():
    sender = os.environ.get("SENDER", "routine")
    if sender in ("mouse.entered", "mouse.exited", "mouse.exited.global"):
        sketchybar("--set", "codex_usage", "popup.drawing=" + (
            "on" if sender == "mouse.entered" else "off"))
        return

    cache = Path(tempfile.gettempdir()) / f"sketchybar-codex-{os.getuid()}"
    cache.mkdir(mode=0o700, exist_ok=True)
    with (cache / "update.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        error = None
        try:
            limits = read_limits()
        except (OSError, RuntimeError, ValueError) as exc:
            error = str(exc)
            limits = {}
        windows = [limits.get("primary"), limits.get("secondary")]
        image = cache / "bars.png"
        draw_bars(image, windows)
        sketchybar(
            "--set", "codex_usage", f"background.image={image}",
            "background.image.scale=0.5", "background.image.drawing=on",
            "--set", "codex_usage.primary", "label=" + describe("5-hour", windows[0]),
            "--set", "codex_usage.secondary", "label=" + describe("Weekly", windows[1]),
            "--set", "codex_usage.status", "label=" + (
                error or "Updated " + datetime.now().strftime("%-I:%M %p")),
        )


if __name__ == "__main__":
    main()
