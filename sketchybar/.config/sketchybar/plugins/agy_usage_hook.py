#!/usr/bin/env python3
"""Antigravity CLI (agy) statusLine hook that caches Gemini quota for SketchyBar."""

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time

TRIGGER_EVENT = "gemini_usage_updated"
MIN_TRIGGER_INTERVAL = 60.0


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


def extract_snapshot(payload, now=None):
    if not isinstance(payload, dict):
        return None
    quota = payload.get("quota")
    if not isinstance(quota, dict) or not quota:
        return None
    now = time.time() if now is None else now
    snapshot = {
        "quota": quota,
        "captured_at": now,
    }
    plan_tier = payload.get("plan_tier")
    if isinstance(plan_tier, str) and plan_tier.strip():
        snapshot["plan_tier"] = plan_tier.strip()
    return snapshot


def snapshot_signature(snapshot):
    if not isinstance(snapshot, dict):
        return None
    quota = snapshot.get("quota") or {}
    normalized = {}
    for key, value in sorted(quota.items()):
        if not isinstance(value, dict):
            continue
        frac = value.get("remaining_fraction")
        normalized[key] = {
            "remaining_fraction": round(float(frac), 4) if isinstance(frac, (int, float)) else None,
            "reset_time": value.get("reset_time"),
            "disabled": bool(value.get("disabled", False)),
        }
    return {"quota": normalized, "plan_tier": snapshot.get("plan_tier")}


def process_payload(raw_text, cache_dir=None, executable="sketchybar", now=None):
    """Parse agy statusLine JSON, update cache, and notify SketchyBar on change."""
    now = time.time() if now is None else now
    try:
        payload = json.loads(raw_text)
    except (TypeError, ValueError):
        return False

    snapshot = extract_snapshot(payload, now=now)
    if snapshot is None:
        return False

    cache = cache_directory(cache_dir)
    cache_path = cache / "gemini.json"
    previous = read_json_safe(cache_path)

    changed = snapshot_signature(previous) != snapshot_signature(snapshot)
    prev_triggered = (
        previous.get("triggered_at", previous.get("captured_at"))
        if isinstance(previous, dict)
        else None
    )
    stale = not isinstance(prev_triggered, (int, float)) or (now - prev_triggered) >= MIN_TRIGGER_INTERVAL
    should_trigger = changed or stale
    snapshot["triggered_at"] = now if should_trigger else prev_triggered

    write_json_atomic(cache_path, snapshot)

    if should_trigger and (executable != "sketchybar" or shutil.which("sketchybar")):
        try:
            subprocess.run(
                [executable, "--trigger", TRIGGER_EVENT],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1.5,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            return False
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--sketchybar", default="sketchybar")
    parser.add_argument(
        "--wrap",
        default=os.environ.get("AGY_STATUSLINE_WRAP"),
        help="Optional existing statusLine command to forward stdin to.",
    )
    args = parser.parse_args()

    raw = sys.stdin.read()
    try:
        process_payload(raw, cache_dir=args.cache_dir, executable=args.sketchybar)
    except Exception:
        # Never fail so agy never disables the statusLine hook.
        pass

    if args.wrap:
        result = subprocess.run(
            args.wrap,
            shell=True,
            input=raw,
            text=True,
            check=False,
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
