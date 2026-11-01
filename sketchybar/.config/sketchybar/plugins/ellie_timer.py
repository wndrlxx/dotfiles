#!/usr/bin/env python3
"""Display Ellie's locally cached running timer; never modify Ellie's data."""

import argparse
import fcntl
import html
import json
import math
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
from ellie_storage import FormatError, firestore_records

DATABASE = Path.home() / "Library/Application Support/Ellie/IndexedDB/https_app.ellieplanner.com_0.indexeddb.leveldb"
TIMER_KEYS = {
    "active", "type", "task_id", "focus_time_original", "focus_time_left",
    "last_start_time", "time_accumulated", "phase", "phase_started_at",
    "phase_time_left", "phase_duration",
}
CACHE_VERSION = 2


def unpack(value):
    if "mapValue" in value:
        return {key: unpack(item) for key, item in value["mapValue"].get("fields", {}).items()}
    if "arrayValue" in value:
        return [unpack(item) for item in value["arrayValue"].get("values", [])]
    for key in ("stringValue", "booleanValue", "timestampValue", "doubleValue"):
        if key in value:
            return value[key]
    if "integerValue" in value:
        return int(value["integerValue"])
    return None


def patch_fields(fields, mutation):
    update = mutation.get("update", {})
    changes = unpack({"mapValue": {"fields": update.get("fields", {})}})
    mask = mutation.get("updateMask")
    if mask is None:
        return changes
    result = dict(fields)
    for field in mask.get("fieldPaths", []):
        parts = field.split(".")
        target, source = result, changes
        for part in parts[:-1]:
            target[part] = dict(target.get(part) or {})
            target = target[part]
            source = source.get(part, {})
        if parts[-1] in source:
            target[parts[-1]] = source[parts[-1]]
        else:
            target.pop(parts[-1], None)
    return result


def snapshot(records):
    records = list(records)
    auth = [(seq, record["value"].get("uid")) for seq, record in records
            if str(record.get("fbase_key", "")).startswith("firebase:authUser:")
            and isinstance(record.get("value"), dict)]
    uid = max(auth, default=(0, None))[1]
    if not uid:
        return {}
    documents = {}
    overlays = []
    for sequence, record in records:
        group, doc_id = record.get("collectionGroup"), record.get("documentId")
        if group == "users" and doc_id == uid and record.get("prefixPath") == []:
            key = ("users", uid)
        elif group == "tasks" and record.get("prefixPath") == ["users", uid]:
            key = ("tasks", doc_id)
        else:
            key = None
        if key and ("document" in record or "noDocument" in record):
            stamp = (tuple(record.get("readTime", [0, 0])), sequence)
            if key not in documents or stamp > documents[key][0]:
                fields = record.get("document", {}).get("fields", {})
                documents[key] = (stamp, unpack({"mapValue": {"fields": fields}}))
        mutation = record.get("overlayMutation")
        if mutation:
            name = mutation.get("update", {}).get("name", "")
            path = name.split("/documents/")[-1].split("/")
            if path == ["users", uid]:
                overlays.append((sequence, ("users", uid), mutation))
            elif len(path) == 4 and path[:3] == ["users", uid, "tasks"]:
                overlays.append((sequence, ("tasks", path[3]), mutation))
    fields = {key: value for key, (_, value) in documents.items()}
    # IndexedDB overlays represent pending local writes, including offline pause/stop.
    for _, key, mutation in sorted(overlays):
        fields[key] = patch_fields(fields.get(key, {}), mutation)
    profile = fields.get(("users", uid), {})
    timer = profile.get("active_timer")
    kind = "stopwatch"
    if not timer or not timer.get("active"):
        timer, kind = profile.get("active_pomodoro"), "pomodoro"
    if not timer or timer.get("active") is not True:
        return {}
    task = fields.get(("tasks", timer.get("task_id")), {})
    title = task.get("description") or "Ellie"
    if not isinstance(title, str):
        title = "Ellie"
    title = html.unescape(re.sub(r"<[^>]*>", "", title))
    title = " ".join(title.split())
    return {"kind": kind, "timer": {k: v for k, v in timer.items() if k in TIMER_KEYS},
            "title": title[:37] + "…" if len(title) > 38 else title}


def timestamp(value):
    if not isinstance(value, str):
        raise FormatError("Missing timer start time")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def display(state, now=None):
    timer = state.get("timer")
    if not timer or timer.get("active") is not True:
        return {"running": False}
    now = time.time() if now is None else now
    if state.get("kind") == "pomodoro":
        started_at = timestamp(timer.get("phase_started_at"))
        elapsed = max(0, math.floor(now - started_at))
        seconds = max(0, int(timer.get("phase_time_left", timer.get("phase_duration", 0))) - elapsed)
        direction = -1
        icon = "☕" if timer.get("phase") in ("short_break", "long_break") else "⏱"
    else:
        started_at = timestamp(timer.get("last_start_time"))
        elapsed = max(0, math.floor(now - started_at))
        if timer.get("type") == "timer":
            seconds = max(0, int(timer.get("focus_time_left", timer.get("focus_time_original", 0))) - elapsed)
            direction = -1
        else:
            seconds = max(0, int(timer.get("time_accumulated", 0)) + elapsed)
            direction = 1
        icon = "⏱"
    tick = {"running": True, "seconds": seconds, "direction": direction, "symbol": icon,
            "reference_time": started_at + elapsed, "sampled_at": now}
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    clock = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
    return {"running": True, "icon": icon, "label": f"{clock} {state['title']}", "tick": tick}


def fingerprint(directory):
    return [(p.name, p.stat().st_mtime_ns, p.stat().st_size)
            for p in sorted(directory.iterdir())
            if p.suffix in (".log", ".ldb", ".sst") or p.name.startswith("MANIFEST-") or p.name == "CURRENT"]


def cache_directory():
    cache_dir = Path(tempfile.gettempdir()) / f"sketchybar-ellie-{os.getuid()}"
    cache_dir.mkdir(mode=0o700, exist_ok=True)
    info = cache_dir.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise FormatError("Unsafe cache directory")
    return cache_dir


def cached_snapshot(directory, wait=True):
    cache_dir = cache_directory()
    cache_path = cache_dir / "timer.json"
    lock_fd = os.open(cache_dir / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        mark = fingerprint(directory)
        try:
            saved = json.loads(cache_path.read_text())
            if (saved.get("version") == CACHE_VERSION and saved.get("source") == str(directory)
                    and saved.get("fingerprint") == [list(row) for row in mark]):
                return saved["state"]
        except (OSError, ValueError, KeyError):
            pass
        for _ in range(3):
            try:
                state = snapshot(firestore_records(directory))
                if fingerprint(directory) == mark:
                    break
            except FileNotFoundError:
                pass  # Chromium may compact tables while we read.
            mark = fingerprint(directory)
        else:
            raise FormatError("Ellie's cache changed during read")
        # Persist only timer fields and the shortened task title, never profiles or credentials.
        fd, name = tempfile.mkstemp(dir=cache_dir)
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump({"version": CACHE_VERSION, "source": str(directory),
                           "fingerprint": mark, "refreshed_at": time.time(), "state": state}, handle)
            os.replace(name, cache_path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return state


def current_snapshot(directory):
    """Keep expensive cache decoding off the display update path."""
    try:
        saved = json.loads((cache_directory() / "timer.json").read_text())
        if saved.get("version") != CACHE_VERSION or saved.get("source") != str(directory):
            saved = {}
    except (OSError, ValueError):
        saved = {}
    if saved.get("fingerprint") == [list(row) for row in fingerprint(directory)]:
        return saved["state"]
    # Start the grace period when a change is detected, not when the previous
    # snapshot was saved: an unchanged database may legitimately sit for hours.
    request_path = cache_directory() / "refresh.json"
    now = time.time()
    try:
        request = json.loads(request_path.read_text())
    except (OSError, ValueError):
        request = {}
    if request.get("base") != saved.get("refreshed_at") or "started_at" not in request:
        request = {"base": saved.get("refreshed_at"), "started_at": now}
        request_path.write_text(json.dumps(request))
    subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--refresh-cache"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    # A background read normally takes under a second. Hide rather than keep an
    # obsolete running timer if the new cache cannot be read for several seconds.
    if now - request["started_at"] > 3:
        return {}
    return saved.get("state", {})


def update_bar(result):
    if result["running"]:
        clock, label = result["label"].split(" ", 1)
        icon, click = f"{result['icon']} {clock}", "open -a Ellie"
        style = ["icon.color=0xfffbbf24", "icon.font=Hack Nerd Font:Bold:12.0",
                 "icon.background.drawing=on", "icon.background.color=0x2efbbf24",
                 "icon.background.height=20", "icon.background.corner_radius=6",
                 "icon.padding_left=7", "icon.padding_right=7"]
    else:
        source = subprocess.run(["sketchybar", "--query", "weather_data"],
                                check=True, capture_output=True, text=True)
        weather = json.loads(source.stdout)
        icon, label, click = weather["icon"]["value"], weather["label"]["value"], ""
        style = ["icon.color=0xffffffff", "icon.font=Hack Nerd Font:12.0",
                 "icon.background.drawing=off", "icon.padding_left=0", "icon.padding_right=0"]
    # clock_layout.sh owns drawing and display associations for both weather slots.
    # Non-notched displays move the clock/date right only while a timer runs.
    command = ["sketchybar"]
    for name in ("weather", "weather.notch"):
        gap = 7 if result["running"] or name.endswith(".notch") else 4
        label_color = "0xfff5deb3" if result["running"] else "0xffffffff"
        command += ["--set", name, f"icon={icon}", f"label={label}", f"click_script={click}",
                    f"label.color={label_color}", f"label.padding_left={gap}", *style]
    for name in ("clock", "date", "clock.notch", "date.notch"):
        position = "q" if name.endswith(".notch") else ("right" if result["running"] else "center")
        padding = 0
        label_left = 7 if name.endswith(".notch") else 0
        label_right = 0 if name.endswith(".notch") else 4
        command += ["--set", name, f"position={position}", f"padding_left={padding}",
                    f"label.padding_left={label_left}", f"label.padding_right={label_right}"]
    subprocess.run(command, check=True)


def ellie_running():
    """Read state maintained by the native app observer; never spawn pgrep."""
    try:
        state = json.loads((cache_directory() / "app.json").read_text())
        watcher_pid = state.get("watcher_pid")
        if not isinstance(watcher_pid, int) or watcher_pid <= 0:
            return False
        os.kill(watcher_pid, 0)  # Cheap liveness check; no subprocess or app scan.
        return state.get("running") is True
    except (OSError, ValueError, TypeError):
        return False


def publish_tick(result):
    """Give the native ticker only a time anchor; it never reads Ellie's DB."""
    directory = cache_directory()
    fd, name = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(result.get("tick", {"running": False}), handle)
        os.replace(name, directory / "tick.json")
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="Print timer display data without updating SketchyBar")
    parser.add_argument("--refresh-cache", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.refresh_cache:
        try:
            cached_snapshot(DATABASE, wait=False)
        except BlockingIOError:
            pass  # A previous invocation is already refreshing it.
        return
    try:
        read_state = cached_snapshot if args.status else current_snapshot
        result = display(read_state(DATABASE)) if ellie_running() else {"running": False}
    except (OSError, ValueError, KeyError, IndexError, TypeError, RecursionError):
        # A stale running clock is worse than hiding the widget after a format change.
        print("Ellie timer: unable to read the current local timer state", file=sys.stderr)
        result = {"running": False}
    if args.status:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if not ellie_running():
            result = {"running": False}  # Ellie may have quit during a read.
        update_bar(result)
        publish_tick(result)


if __name__ == "__main__":
    main()
