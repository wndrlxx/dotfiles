"""Check the Python watcher with a local API and fake bar; no real credentials."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import unittest


def wait_for(predicate, message, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.03)
    raise AssertionError(message)


def check():
    task = {"title": "Fixture task", "timerStartedAt": datetime.now(timezone.utc).isoformat(),
            "timerAccumulatedSeconds": 70, "completedAt": None}
    requests = []
    active = [task]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.headers.get("X-API-Key") == "fixture-key"
            requests.append(time.monotonic())
            # Exercise real ticking during a slow refresh, not just a mocked clock.
            if len(requests) == 2:
                time.sleep(2)
            data = json.dumps({"success": True, "data": active[0]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    plugin_dir = Path(__file__).resolve().parents[2] / "plugins"
    with tempfile.TemporaryDirectory(prefix="sunsama-python-check-") as directory:
        root = Path(directory)
        fakebar = root / "sketchybar"
        fakebar.write_text(f"#!{sys.executable}\n" + '''import json, sys, time
from pathlib import Path
with Path(__file__).with_name("calls.jsonl").open("a") as f:
    f.write(json.dumps({"time": time.monotonic(), "args": sys.argv[1:]}) + "\\n")
if "--query" in sys.argv:
    if "sunsama_timer" in sys.argv:
        if Path(__file__).with_name("controller-removed").exists():
            print("Controller removed")
        else:
            print(json.dumps({"scripting":{"script":''' + repr(f"python3 -B {plugin_dir / 'sunsama_timer.py'}") + '''}}))
    else:
        raise AssertionError("Unexpected display query")
''')
        fakebar.chmod(0o700)
        entry = root / "fixture.py"
        entry.write_text(f"import sys\nsys.path.insert(0, {str(plugin_dir)!r})\n"
                         f"import sunsama_timer as timer\ntimer.ENDPOINT = 'http://127.0.0.1:{server.server_port}/active'\n"
                         "timer.main()\n")
        env = {**os.environ, "TMPDIR": str(root), "OPEN_SUNSAMA_API_KEY": "fixture-key",
               "PATH": str(root) + os.pathsep + os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1"}
        cache = root / f"sketchybar-sunsama-{os.getuid()}"
        bar = subprocess.Popen(["/bin/sleep", "120"])
        processes = [bar]

        def command(*args):
            return [sys.executable, "-B", str(entry), *args]

        def calls():
            return [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]

        def ticks():
            return [call for call in calls() if any(arg.startswith("icon=⏱ ") for arg in call["args"])]

        try:
            start = time.monotonic()
            args = command("--watch", "--bar-pid", str(bar.pid))
            watcher = subprocess.Popen(args, env=env)
            processes.append(watcher)
            wait_for(lambda: len(ticks()) >= 3, "No immediate one-second Python ticks")
            assert ticks()[0]["time"] - start < 1.5, ticks()
            assert all("timer" in call["args"] and "timer.notch" in call["args"] for call in ticks())
            assert not any("weather" in call["args"] for call in calls())
            initial = ticks()[:3]
            # The first tick aligns to a task's fractional start boundary, so it
            # may arrive less than a full second after the initial render.
            assert 0 < initial[1]["time"] - initial[0]["time"] < 1.3, initial
            assert 0.7 < initial[2]["time"] - initial[1]["time"] < 1.3, initial
            assert len(requests) == 1, requests
            wait_for(lambda: len(requests) >= 2, "API did not refresh after five seconds")
            assert 4.5 < requests[1] - requests[0] < 5.5, requests
            before = len(ticks())
            wait_for(lambda: len(ticks()) >= before + 2, "Slow request blocked ticking")
            assert watcher.poll() is None
            subprocess.run(args, env=env, check=True, timeout=5)
            assert json.loads((cache / "watcher.json").read_text())["pid"] == watcher.pid
            owner = json.loads((cache / "watcher.json").read_text())
            owner["version"] = [0, 0]
            (cache / "watcher.json").write_text(json.dumps(owner))
            replacement = subprocess.Popen(args, env=env)
            processes.append(replacement)
            wait_for(lambda: json.loads((cache / "watcher.json").read_text())["pid"] == replacement.pid,
                     "Source change did not replace the watcher")
            watcher.wait(timeout=3)
            watcher = replacement
            before_stop = len(calls())
            active[0] = None
            subprocess.run(command(), env=env, check=True, timeout=5)
            wait_for(lambda: any("icon.drawing=off" in call["args"] and "label.drawing=off" in call["args"]
                                for call in calls()[before_stop:]), "Stopped timer was not hidden")
            subprocess.run(command("--stop"), env=env, check=True, timeout=5)
            watcher.wait(timeout=3)
            assert not (cache / "watcher.json").exists()
            watcher = subprocess.Popen(args, env=env)
            processes.append(watcher)
            wait_for(lambda: (cache / "watcher.json").exists(), "Watcher did not restart")
            (root / "controller-removed").touch()
            subprocess.run(command(), env=env, check=True, timeout=5)
            watcher.wait(timeout=3)
            (root / "controller-removed").unlink()
            watcher = subprocess.Popen(args, env=env)
            processes.append(watcher)
            wait_for(lambda: (cache / "watcher.json").exists(), "Watcher did not restart after config change")
            bar.terminate()
            bar.wait(timeout=3)
            watcher.wait(timeout=3)
            print("PASS: immediate ticks, five-second polling, slow requests, reload singleton, source changes, config changes, stop, and parent exit")
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            server.shutdown()
            server.server_close()


class SunsamaTimerIntegrationTests(unittest.TestCase):
    def test_timer_watcher_lifecycle(self):
        check()


if __name__ == "__main__":
    unittest.main()
