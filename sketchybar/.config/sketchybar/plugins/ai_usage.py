#!/usr/bin/env python3
"""Render unified Codex + Gemini + Claude (Antigravity) subscription quota bars."""

from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import re
import select
import shutil
import stat
import struct
import subprocess
import tempfile
import time
import zlib

ITEM_NAME = "ai_usage"

# Render at 2x resolution; SketchyBar displays at 0.5 scale.
IMAGE_HEIGHT = 32
BAR_HEIGHT = 8
EDGE_PAD = 2
GROUP_GAP = 12
DIVIDER_WIDTH = 2

# Per-stack bar width (2x px) by number of visible provider stacks.
STACK_BAR_WIDTHS = {
    1: 84,  # 88 px -> 44 pt image inside width=48
    2: 76,  # 168 px -> 84 pt image inside width=88
    3: 64,  # 220 px -> 110 pt image inside width=114
}

CODEX_COLOR = (220, 220, 220, 255)
CODEX_TRACK = (185, 185, 185, 90)
CODEX_DASH = (185, 185, 185, 255)

GEMINI_COLOR = (122, 162, 247, 255)  # #7aa2f7
GEMINI_TRACK = (122, 162, 247, 65)
GEMINI_DASH = (122, 162, 247, 190)

CLAUDE_COLOR = (217, 119, 87, 255)   # #d97757 (Claude orange)
CLAUDE_TRACK = (217, 119, 87, 65)
CLAUDE_DASH = (217, 119, 87, 190)

PROVIDER_STYLES = {
    "codex": (CODEX_COLOR, CODEX_TRACK, CODEX_DASH),
    "gemini": (GEMINI_COLOR, GEMINI_TRACK, GEMINI_DASH),
    "claude": (CLAUDE_COLOR, CLAUDE_TRACK, CLAUDE_DASH),
}

DIVIDER_COLOR = (185, 185, 185, 70)
WARN_AMBER = (224, 175, 104, 255)    # #e0af68 (< 25%)
WARN_CORAL = (247, 118, 142, 255)    # #f7768e (< 10%)

HEADER_CODEX_COLOR = "0xffa9b1d6"
HEADER_GEMINI_COLOR = "0xff7aa2f7"
HEADER_CLAUDE_COLOR = "0xffd97757"
MUTED_TEXT_COLOR = "0xff8b93a6"
NORMAL_TEXT_COLOR = "0xffffffff"

SHORT_WINDOW_TOKENS = ("5h", "5-hour", "five", "hour", "session", "short", "daily", "primary")
WEEKLY_WINDOW_TOKENS = ("week", "7d", "secondary")
ALL_PROVIDERS = ("codex", "gemini", "claude")


def enabled_providers(raw=None):
    if raw is None:
        raw = os.environ.get("SKETCHYBAR_AI_PROVIDERS", "auto")
    text = str(raw).strip().lower()
    if not text or text == "auto":
        return list(ALL_PROVIDERS)
    selected = [p for p in ALL_PROVIDERS if p in {part.strip() for part in text.split(",")}]
    return selected or list(ALL_PROVIDERS)


def active_providers(enabled, codex_values, gemini_buckets, claude_buckets=()):
    """Auto-collapse to only providers with active quota."""
    if len(enabled) == 1:
        return list(enabled)
    has_data = {
        "codex": any(v is not None for v in codex_values),
        "gemini": bool(gemini_buckets),
        "claude": bool(claude_buckets),
    }
    shown = [p for p in enabled if has_data.get(p)]
    if shown:
        return shown
    # When nothing has synced yet, fall back to non-claude enabled providers.
    fallback = [p for p in enabled if p != "claude"]
    return fallback or list(enabled)


def cache_directory(base=None):
    path = Path(base) if base else Path(tempfile.gettempdir()) / f"sketchybar-ai-usage-{os.getuid()}"
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Unsafe AI usage cache directory")
    return path


def write_json_atomic(path, payload):
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def read_json_safe(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def read_codex_limits():
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
            remaining_sec = deadline - time.monotonic()
            if remaining_sec <= 0 or not select.select([process.stdout], [], [], remaining_sec)[0]:
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


def codex_remaining(window):
    if not isinstance(window, dict):
        return None
    used = window.get("usedPercent")
    if not isinstance(used, (int, float)) or not math.isfinite(used):
        return None
    return max(0.0, min(100.0, 100.0 - float(used)))


def parse_timestamp(value):
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            return None
    return None


def is_claude_bucket(bucket_id):
    lower = str(bucket_id).strip().lower()
    return lower.startswith("3p-") or lower.startswith("3p_") or lower.startswith("claude")


def format_bucket_name(bucket_id):
    text = str(bucket_id).strip()
    lower = text.lower()
    if lower in ("gemini-weekly", "3p-weekly", "weekly"):
        return "Weekly"
    if lower in ("gemini-5h", "gemini-five-hour", "3p-5h", "3p-five-hour", "5h", "five-hour"):
        return "5-hour"
    cleaned = re.sub(r"^(?:gemini|3p|claude)[-_]", "", text, flags=re.IGNORECASE)
    parts = [part for part in re.split(r"[-_\s]+", cleaned) if part]
    if not parts:
        return text
    formatted = []
    for part in parts:
        if part.lower() in ("5h", "7d", "24h"):
            formatted.append(part.lower())
        elif part.lower() in ("gpt", "oss", "ai"):
            formatted.append(part.upper())
        else:
            formatted.append(part.capitalize())
    return " ".join(formatted)


def bucket_sort_key(bucket):
    key = bucket["id"].lower()
    is_short = any(token in key for token in SHORT_WINDOW_TOKENS)
    is_weekly = any(token in key for token in WEEKLY_WINDOW_TOKENS)
    if is_short and not is_weekly:
        window_rank = 0
    elif is_weekly and not is_short:
        window_rank = 1
    else:
        window_rank = 2
    value = bucket["remaining"]
    return (window_rank, value if value is not None else 101.0, key)


def parse_agy_snapshot(snapshot, now=None):
    """Normalize cached agy statusLine quota snapshot into Gemini and Claude buckets."""
    now = time.time() if now is None else now
    empty = {"gemini_buckets": [], "claude_buckets": [], "plan_tier": None, "captured_at": None}
    if not isinstance(snapshot, dict):
        return empty

    quota = snapshot.get("quota")
    captured_at = parse_timestamp(snapshot.get("captured_at"))
    plan_tier = snapshot.get("plan_tier")
    if not isinstance(plan_tier, str) or not plan_tier.strip():
        plan_tier = None
    else:
        plan_tier = plan_tier.strip()

    if not isinstance(quota, dict):
        return {**empty, "plan_tier": plan_tier, "captured_at": captured_at}

    gemini_buckets = []
    claude_buckets = []
    for bucket_id, entry in quota.items():
        if not isinstance(entry, dict) or entry.get("disabled"):
            continue
        frac = entry.get("remaining_fraction")
        remaining = None
        if isinstance(frac, (int, float)) and math.isfinite(frac):
            pct = float(frac) * 100.0 if 0.0 <= float(frac) <= 1.0 else float(frac)
            remaining = max(0.0, min(100.0, pct))

        reset_ts = parse_timestamp(entry.get("reset_time"))
        if reset_ts is None:
            reset_in = entry.get("reset_in_seconds")
            if isinstance(reset_in, (int, float)) and math.isfinite(reset_in) and captured_at is not None:
                reset_ts = captured_at + float(reset_in)

        expired = reset_ts is not None and now >= reset_ts
        item = {
            "id": str(bucket_id),
            "title": format_bucket_name(bucket_id),
            "remaining": None if expired else remaining,
            "raw_remaining": remaining,
            "resets_at": reset_ts,
            "expired": expired,
        }
        if is_claude_bucket(bucket_id):
            claude_buckets.append(item)
        else:
            gemini_buckets.append(item)

    gemini_buckets.sort(key=bucket_sort_key)
    claude_buckets.sort(key=bucket_sort_key)
    return {
        "gemini_buckets": gemini_buckets,
        "claude_buckets": claude_buckets,
        "plan_tier": plan_tier,
        "captured_at": captured_at,
    }


def select_bar_values(buckets):
    """Pick 1 or 2 bar values from a sorted bucket list."""
    if not buckets:
        return [None, None]
    if len(buckets) == 1:
        return [buckets[0]["remaining"]]
    return [buckets[0]["remaining"], buckets[1]["remaining"]]


def bar_fill_color(value, base_color):
    if value is None:
        return base_color
    if value < 10.0:
        return WARN_CORAL
    if value < 25.0:
        return WARN_AMBER
    return base_color


def _draw_bar(pixels, image_width, left, top, bar_width, value, base_color, track_color, dash_color):
    fill_color = bar_fill_color(value, base_color)
    fill = round(bar_width * value / 100.0) if value is not None else 0
    dash_start = left + (bar_width - 12) // 2
    dash_end = dash_start + 12
    for y in range(top, top + BAR_HEIGHT):
        row_offset = y * image_width
        for x in range(left, left + bar_width):
            if value is None and dash_start <= x < dash_end:
                rgba = dash_color
            elif x - left < fill:
                rgba = fill_color
            else:
                rgba = track_color
            offset = (row_offset + x) * 4
            pixels[offset:offset + 4] = bytes(rgba)


def _draw_provider_stack(pixels, image_width, left, bar_width, values, base_color, track_color, dash_color):
    if len(values) == 1:
        _draw_bar(pixels, image_width, left, 12, bar_width, values[0], base_color, track_color, dash_color)
        return
    slots = list(values[:2])
    while len(slots) < 2:
        slots.append(None)
    for top, value in zip((4, 20), slots):
        _draw_bar(pixels, image_width, left, top, bar_width, value, base_color, track_color, dash_color)


def layout_geometry(count):
    count = max(1, count)
    bar_width = STACK_BAR_WIDTHS.get(count, 64)
    image_width = 2 * EDGE_PAD + count * bar_width + (count - 1) * GROUP_GAP
    item_width = (image_width // 2) + 4
    return image_width, bar_width, item_width


def draw_bars(path, provider_values, shown=ALL_PROVIDERS):
    """Render 2x PNG for 1, 2, or 3 provider stacks separated by subtle dividers."""
    shown = list(shown) or ["gemini"]
    image_width, bar_width, item_width = layout_geometry(len(shown))
    pixels = bytearray(image_width * IMAGE_HEIGHT * 4)

    for index, provider in enumerate(shown):
        left = EDGE_PAD + index * (bar_width + GROUP_GAP)
        base_color, track_color, dash_color = PROVIDER_STYLES[provider]
        _draw_provider_stack(
            pixels, image_width, left, bar_width,
            provider_values.get(provider, [None, None]),
            base_color, track_color, dash_color,
        )
        if index < len(shown) - 1:
            divider_x = left + bar_width + (GROUP_GAP - DIVIDER_WIDTH) // 2
            for y in range(4, 28):
                row_offset = y * image_width
                for x in range(divider_x, divider_x + DIVIDER_WIDTH):
                    offset = (row_offset + x) * 4
                    pixels[offset:offset + 4] = bytes(DIVIDER_COLOR)

    def chunk(kind, data):
        return (struct.pack("!I", len(data)) + kind + data
                + struct.pack("!I", zlib.crc32(kind + data)))

    rows = b"".join(b"\0" + pixels[y * image_width * 4:(y + 1) * image_width * 4]
                    for y in range(IMAGE_HEIGHT))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack("!2I5B", image_width, IMAGE_HEIGHT, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(png)
    temporary.replace(path)
    return item_width


def format_duration(seconds):
    minutes = max(0, math.ceil(seconds / 60))
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def describe_codex_window(title, window, now=None):
    now = time.time() if now is None else now
    value = codex_remaining(window)
    if value is None:
        return f"{title}: unavailable"
    text = f"{title}: {value:.0f}% left"
    reset = parse_timestamp(window.get("resetsAt")) if isinstance(window, dict) else None
    if reset is not None:
        text += " · resets in " + format_duration(reset - now)
    return text


def describe_agy_bucket(bucket, now=None):
    now = time.time() if now is None else now
    title = bucket["title"]
    if bucket["expired"]:
        return f"{title}: reset · open agy to sync"
    value = bucket["remaining"]
    if value is None:
        return f"{title}: unavailable"
    text = f"{title}: {value:.0f}% left"
    reset = bucket.get("resets_at")
    if reset is not None:
        text += " · resets in " + format_duration(reset - now)
    return text


def format_clock(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%-I:%M %p")


def build_popup_rows(codex_windows, codex_error, agy_data, shown=ALL_PROVIDERS, now=None):
    now = time.time() if now is None else now
    shown = list(shown)
    rows = []

    if "codex" in shown:
        rows.append(("Codex", HEADER_CODEX_COLOR))
        if codex_error:
            rows.append((codex_error, MUTED_TEXT_COLOR))
        else:
            rows.append((describe_codex_window("5-hour", codex_windows[0], now), NORMAL_TEXT_COLOR))
            rows.append((describe_codex_window("Weekly", codex_windows[1], now), NORMAL_TEXT_COLOR))

    plan_suffix = f" · {agy_data['plan_tier']}" if agy_data["plan_tier"] else ""

    if "gemini" in shown:
        rows.append((f"Gemini{plan_suffix}", HEADER_GEMINI_COLOR))
        if agy_data["gemini_buckets"]:
            for bucket in agy_data["gemini_buckets"]:
                rows.append((describe_agy_bucket(bucket, now), NORMAL_TEXT_COLOR))
        else:
            rows.append(("Waiting for agy session…", MUTED_TEXT_COLOR))

    if "claude" in shown:
        rows.append((f"Claude{plan_suffix}", HEADER_CLAUDE_COLOR))
        if agy_data["claude_buckets"]:
            for bucket in agy_data["claude_buckets"]:
                rows.append((describe_agy_bucket(bucket, now), NORMAL_TEXT_COLOR))
        else:
            rows.append(("Waiting for agy session…", MUTED_TEXT_COLOR))

    has_agy = "gemini" in shown or "claude" in shown
    if "codex" not in shown and has_agy and agy_data["captured_at"] is not None:
        footer = "Synced " + format_clock(agy_data["captured_at"])
    else:
        footer = "Updated " + format_clock(now)
        if has_agy and agy_data["captured_at"] is not None:
            footer += " · agy " + format_clock(agy_data["captured_at"])
    rows.append((footer, MUTED_TEXT_COLOR))
    return rows


def run_sketchybar(*args, executable="sketchybar"):
    subprocess.run([executable, *args], check=True, timeout=5)


def render_sketchybar(image, rows, item_width=88, previous_ui=None, executable="sketchybar"):
    args = [
        "--set", ITEM_NAME,
        f"background.image={image}",
        "background.image.scale=0.5",
        "background.image.drawing=on",
    ]
    prev_width = previous_ui.get("width") if isinstance(previous_ui, dict) else None
    prev_rows = previous_ui.get("row_count") if isinstance(previous_ui, dict) else None

    if prev_width != item_width:
        args += [f"width={item_width}"]

    if prev_rows is None:
        args += ["--remove", f"/^{re.escape(ITEM_NAME)}\\.row\\./"]
        for index, (label, color) in enumerate(rows):
            child = f"{ITEM_NAME}.row.{index}"
            args += [
                "--add", "item", child, f"popup.{ITEM_NAME}",
                "--set", child,
                "icon.drawing=off",
                f"label={label}",
                f"label.color={color}",
                "label.padding_left=12",
                "label.padding_right=12",
            ]
    else:
        for index in range(len(rows), prev_rows):
            args += ["--remove", f"{ITEM_NAME}.row.{index}"]
        for index, (label, color) in enumerate(rows):
            child = f"{ITEM_NAME}.row.{index}"
            if index >= prev_rows:
                args += ["--add", "item", child, f"popup.{ITEM_NAME}"]
            args += [
                "--set", child,
                "icon.drawing=off",
                f"label={label}",
                f"label.color={color}",
                "label.padding_left=12",
                "label.padding_right=12",
            ]
    run_sketchybar(*args, executable=executable)


def update(sender="routine", cache_dir=None, executable="sketchybar", now=None, providers=None):
    if sender in ("mouse.entered", "mouse.exited", "mouse.exited.global"):
        run_sketchybar(
            "--set", ITEM_NAME,
            "popup.drawing=" + ("on" if sender == "mouse.entered" else "off"),
            executable=executable,
        )
        return
    if sender == "mouse.clicked":
        run_sketchybar("--set", ITEM_NAME, "popup.drawing=toggle", executable=executable)
        return

    enabled = enabled_providers(providers)
    cache = cache_directory(cache_dir)
    with (cache / "update.lock").open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return

        now = time.time() if now is None else now
        codex_cache_path = cache / "codex.json"
        gemini_cache_path = cache / "gemini.json"
        ui_cache_path = cache / "ui.json"

        codex_error = None
        codex_limits = {}
        if "codex" in enabled:
            if sender == "gemini_usage_updated":
                cached = read_json_safe(codex_cache_path)
                if cached is not None:
                    codex_limits = cached.get("limits") or {}
                    codex_error = cached.get("error")
            if sender != "gemini_usage_updated" or (not codex_limits and codex_error is None):
                try:
                    codex_limits = read_codex_limits()
                    write_json_atomic(codex_cache_path, {
                        "limits": codex_limits,
                        "error": None,
                        "updated_at": now,
                    })
                except (OSError, RuntimeError, ValueError) as exc:
                    codex_error = str(exc)
                    codex_limits = {}
                    write_json_atomic(codex_cache_path, {
                        "limits": {},
                        "error": codex_error,
                        "updated_at": now,
                    })

        codex_windows = [codex_limits.get("primary"), codex_limits.get("secondary")]
        codex_values = [codex_remaining(w) for w in codex_windows]

        read_agy = "gemini" in enabled or "claude" in enabled
        agy_snapshot = read_json_safe(gemini_cache_path) if read_agy else None
        agy_data = parse_agy_snapshot(agy_snapshot, now=now)

        provider_values = {
            "codex": codex_values,
            "gemini": select_bar_values(agy_data["gemini_buckets"]),
            "claude": select_bar_values(agy_data["claude_buckets"]),
        }

        shown = active_providers(
            enabled, codex_values, agy_data["gemini_buckets"], agy_data["claude_buckets"]
        )
        image = cache / "bars.png"
        item_width = draw_bars(image, provider_values, shown=shown)
        rows = build_popup_rows(codex_windows, codex_error, agy_data, shown=shown, now=now)
        previous_ui = None if sender == "forced" else read_json_safe(ui_cache_path)
        render_sketchybar(
            image, rows, item_width=item_width, previous_ui=previous_ui, executable=executable
        )
        write_json_atomic(ui_cache_path, {"width": item_width, "row_count": len(rows)})


def main():
    update(sender=os.environ.get("SENDER", "routine"))


if __name__ == "__main__":
    main()
