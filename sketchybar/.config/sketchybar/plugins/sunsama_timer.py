#!/usr/bin/env python3
"""Read Open Sunsama's active task timer and render it like Ellie's timer."""

import argparse
import fcntl
import html
import json
import math
import os
import re
import queue
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.dont_write_bytecode = True
from ellie_timer import cache_directory, display, update_bar

ENDPOINT = "https://sunsama-api.andlee.dev/tasks/timer/active"
KEYCHAIN_SERVICE = "sketchybar-open-sunsama"
APP_URL = "https://sunsama.andlee.dev"
POLL_INTERVAL = 5
STALE_AFTER = 15
READ_ERRORS = (OSError, ValueError, TypeError, OverflowError, subprocess.SubprocessError)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API key to another origin via an HTTP redirect.
        return None


def api_key(timeout=5):
    key = os.environ.get("OPEN_SUNSAMA_API_KEY", "").strip()
    if key:
        return key
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode or not result.stdout.strip():
        raise ValueError("Missing API key")
    return result.stdout.strip()


def snapshot(payload):
    if not isinstance(payload, dict) or payload.get("success") is not True or "data" not in payload:
        raise ValueError("Invalid API response")
    task = payload["data"]
    if task is None:
        return {}
    if not isinstance(task, dict):
        raise ValueError("Invalid task")
    started = task.get("timerStartedAt")
    if started is None or task.get("completedAt"):
        return {}
    if not isinstance(started, str):
        raise ValueError("Invalid timer timestamp")
    parsed = datetime.fromisoformat(started.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timer timestamp requires a timezone")
    seconds = task.get("timerAccumulatedSeconds")
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Invalid accumulated seconds")
    title = task.get("title") or "Open Sunsama"
    if not isinstance(title, str):
        raise ValueError("Invalid title")
    title = " ".join(html.unescape(re.sub(r"<[^>]*>", "", title)).split()) or "Open Sunsama"
    return {"title": title[:37] + "…" if len(title) > 38 else title,
            "timer": {"active": True, "type": "stopwatch", "last_start_time": started,
                      "time_accumulated": int(seconds)}}


def current_snapshot(keychain_timeout=5):
    request = Request(ENDPOINT, headers={"X-API-Key": api_key(timeout=keychain_timeout), "Accept": "application/json"})
    with build_opener(NoRedirect()).open(request, timeout=3) as response:
        payload = json.load(response)
    return snapshot(payload)


def read_snapshot(keychain_timeout=5):
    try:
        return current_snapshot(keychain_timeout)
    except READ_ERRORS:
        print("Open Sunsama timer: unable to read active timer", file=sys.stderr)
        return {}


def render(result):
    url = os.environ.get("OPEN_SUNSAMA_APP_URL", APP_URL)
    update_bar(result, click_script="open " + shlex.quote(url))


def alive(pid):
    if type(pid) is not int or pid <= 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_owner(directory):
    try:
        owner = json.loads((directory / "watcher.json").read_text())
        return owner if isinstance(owner, dict) else {}
    except (OSError, ValueError):
        return {}


def notify(directory, signum):
    """Only signal an owner while its lifetime lock is still held."""
    fd = os.open(directory / "watcher.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            pid = read_owner(directory).get("pid")
            if alive(pid):
                try:
                    os.kill(pid, signum)
                except ProcessLookupError:
                    pass


class TimerWatcher:
    def __init__(self, bar_pid):
        self.bar_pid = bar_pid
        self.stopped = threading.Event()
        self.refresh = threading.Event()
        self.wake = threading.Event()
        self.redraw = threading.Event()
        self.results = queue.Queue()

    def request_refresh(self, *_):
        self.redraw.set()
        self.refresh.set()
        self.wake.set()

    def stop(self, *_):
        self.stopped.set()
        self.refresh.set()
        self.wake.set()

    def controller_active(self):
        try:
            result = subprocess.run(["sketchybar", "--query", "sunsama_timer"],
                                    check=True, capture_output=True, text=True, timeout=2)
            script = json.loads(result.stdout)["scripting"]["script"]
            return str(Path(__file__).resolve()) in script
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            return False

    def poll(self):
        while not self.stopped.is_set():
            self.refresh.clear()
            # Older configs have no --stop hook. Stop when they replace this item.
            if not self.controller_active():
                self.stop()
                return
            started = time.monotonic()
            state = read_snapshot()
            self.results.put((state, time.monotonic()))
            self.wake.set()
            # Keep the normal request cadence independent of API latency.
            self.refresh.wait(max(0, POLL_INTERVAL - (time.monotonic() - started)))

    def run(self):
        worker = threading.Thread(target=self.poll, name="sunsama-api", daemon=True)
        worker.start()
        state, sampled_at, last_visible = {}, 0, None
        try:
            while not self.stopped.is_set() and alive(self.bar_pid):
                self.wake.clear()
                while True:
                    try:
                        state, sampled_at = self.results.get_nowait()
                    except queue.Empty:
                        break
                result = display(state) if time.monotonic() - sampled_at < STALE_AFTER else {"running": False}
                visible = (result["running"], result.get("icon"), result.get("label"))
                redraw = self.redraw.is_set()
                self.redraw.clear()
                if visible != last_visible or redraw:
                    try:
                        render(result)
                        last_visible = visible
                    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                        # A reload may temporarily remove the display items.
                        last_visible = None
                delay = 1
                if result["running"]:
                    # Align ticks to the original start time, including fractions.
                    age = max(0, time.time() - result["tick"]["reference_time"])
                    delay = max(0.01, 1 - age % 1)
                self.wake.wait(delay)
        finally:
            self.stop()


def watch(directory, bar_pid):
    if not alive(bar_pid):
        return
    fd = os.open(directory / "watcher.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        # Reuse an unchanged watcher, or replace one after a source/service change.
        version = [Path(__file__).stat().st_mtime_ns,
                   Path(__file__).with_name("ellie_timer.py").stat().st_mtime_ns]
        deadline = time.monotonic() + 3
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                owner = read_owner(directory)
                if owner.get("bar_pid") == bar_pid and owner.get("version") == version:
                    notify(directory, signal.SIGUSR1)
                    return
                notify(directory, signal.SIGTERM)
                if time.monotonic() >= deadline:
                    raise RuntimeError("Open Sunsama timer: previous watcher did not exit")
                time.sleep(0.05)
        watcher = TimerWatcher(bar_pid)
        previous = {sig: signal.signal(sig, handler) for sig, handler in (
            (signal.SIGUSR1, watcher.request_refresh),
            (signal.SIGTERM, watcher.stop), (signal.SIGINT, watcher.stop))}
        fd, pending = tempfile.mkstemp(dir=directory)
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump({"pid": os.getpid(), "bar_pid": bar_pid, "version": version}, handle)
            os.replace(pending, directory / "watcher.json")
            watcher.run()
        finally:
            if os.path.exists(pending):
                os.unlink(pending)
            (directory / "watcher.json").unlink(missing_ok=True)
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--status", action="store_true", help="Print display data without changing the bar")
    modes.add_argument("--watch", action="store_true", help="Run the persistent Python timer")
    modes.add_argument("--stop", action="store_true", help="Stop the persistent timer")
    parser.add_argument("--bar-pid", type=int)
    args = parser.parse_args()
    if args.status:
        print(json.dumps(display(read_snapshot(keychain_timeout=30)), ensure_ascii=False))
        return
    directory = cache_directory("sunsama")
    if args.watch:
        if args.bar_pid is None:
            parser.error("--watch requires --bar-pid")
        watch(directory, args.bar_pid)
    else:
        notify(directory, signal.SIGTERM if args.stop else signal.SIGUSR1)


if __name__ == "__main__":
    main()
