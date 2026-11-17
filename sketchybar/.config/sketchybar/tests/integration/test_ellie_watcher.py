"""macOS integration check using an isolated app, never the user's Ellie app.

Builds the helper automatically; ELLIE_WATCHER_BINARY can select a prebuilt helper.
"""
import json
import os
import plistlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


def wait_for(predicate, message):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.05)
    raise AssertionError(message)


def check(binary):
    with tempfile.TemporaryDirectory(prefix="ellie-watcher-check-") as directory:
        root = Path(directory)
        state = root / "app.json"
        app = root / "EllieWatcherFixture.app"
        executable = app / "Contents/MacOS/EllieWatcherFixture"
        executable.parent.mkdir(parents=True)
        bundle = f"local.sketchybar.ellie-fixture.{os.getpid()}"
        with (app / "Contents/Info.plist").open("wb") as handle:
            plistlib.dump({"CFBundleIdentifier": bundle, "CFBundleExecutable": executable.name,
                          "CFBundleName": "Ellie Watcher Fixture", "CFBundlePackageType": "APPL",
                          "LSUIElement": True}, handle)
        fixture = root / "fixture.swift"
        fixture.write_text('''import AppKit
import Darwin
let app = NSApplication.shared
app.setActivationPolicy(.accessory)
try String(getpid()).write(to: Bundle.main.bundleURL.appendingPathComponent("Contents/pid"), atomically: true, encoding: .utf8)
app.run()
''')
        subprocess.run(["/usr/bin/swiftc", "-module-cache-path", str(Path(binary).parent / "ellie-swift-modules"),
                        str(fixture), "-o", str(executable)], check=True)
        fakebar = root / "fakebar"
        fakebar.write_text(f"#!{sys.executable}\n" + '''import json, sys
from pathlib import Path
with Path(__file__).with_name("calls.jsonl").open("a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
''')
        fakebar.chmod(0o700)
        processes, fixture_pid = [], None

        def start_watcher():
            bar = subprocess.Popen(["/bin/sleep", "120"])
            watcher = subprocess.Popen([binary, str(state), str(bar.pid), str(fakebar), bundle])
            processes.extend([bar, watcher])
            return bar, watcher

        def running(expected):
            return json.loads(state.read_text())["running"] is expected

        def calls():
            return [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]

        try:
            bar, watcher = start_watcher()
            wait_for(lambda: running(False), "Initial closed state not detected")
            subprocess.run(["/usr/bin/open", "-n", str(app)], check=True)
            wait_for(lambda: (app / "Contents/pid").exists(), "Test app did not start")
            fixture_pid = int((app / "Contents/pid").read_text())
            wait_for(lambda: running(True), "App launch event not detected")
            wait_for(lambda: "update_freq=5" in calls()[-1], "Five-second updates not enabled")

            def publish_tick(seconds, direction):
                now = time.time()
                pending = root / "tick.pending"
                pending.write_text(json.dumps({"running": True, "seconds": seconds,
                    "direction": direction, "symbol": "⏱", "reference_time": now, "sampled_at": now}))
                pending.replace(root / "tick.json")

            def tick_calls():
                return [call for call in calls() if any(arg.startswith("icon=") for arg in call)]

            publish_tick(10, 1)
            wait_for(lambda: len(tick_calls()) >= 3, "Native ticker did not advance without Python refreshes")
            self_times = [call[2] for call in tick_calls()[:3]]
            assert self_times == ["icon=⏱ 00:11", "icon=⏱ 00:12", "icon=⏱ 00:13"], self_times
            publish_tick(2, -1)
            wait_for(lambda: any("icon=⏱ 00:00" in call for call in tick_calls()), "Countdown did not reach zero")
            (root / "tick.json").write_text('{"running":false}')
            time.sleep(0.3)
            stopped_count = len(tick_calls())
            time.sleep(1.2)
            assert len(tick_calls()) == stopped_count, "Native ticker kept running after stop"
            before_reload = len(calls())
            subprocess.run([binary, str(state), str(bar.pid), str(fakebar), bundle], check=True, timeout=5)
            wait_for(lambda: len(calls()) > before_reload, "Reload did not reconcile the bar")
            assert json.loads(state.read_text())["watcher_pid"] == watcher.pid, "Duplicate watcher on reload"
            bar.terminate()
            bar.wait(timeout=5)
            watcher.wait(timeout=5)
            bar, watcher = start_watcher()
            wait_for(lambda: running(True), "Already-running app not detected on startup")
            os.kill(fixture_pid, signal.SIGTERM)
            fixture_pid = None
            wait_for(lambda: running(False), "App quit event not detected")
            wait_for(lambda: "update_freq=0" in calls()[-1], "Ticking not disabled on quit")
            assert any("update_freq=5" in call for call in calls())
            bar.terminate()
            bar.wait(timeout=5)
            watcher.wait(timeout=5)
            print("PASS: lifecycle, reload singleton, one-second native ticks, countdown, and stop")
        finally:
            if fixture_pid:
                os.kill(fixture_pid, signal.SIGTERM)
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


class EllieWatcherIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS app lifecycle APIs")
    def test_app_lifecycle_and_timer(self):
        binary = os.environ.get("ELLIE_WATCHER_BINARY")
        if binary:
            check(str(Path(binary).resolve()))
            return
        with tempfile.TemporaryDirectory(prefix="ellie-watcher-build-") as directory:
            root = Path(directory)
            binary = root / "ellie-watcher"
            source = Path(__file__).resolve().parents[2] / "plugins/ellie_watcher.swift"
            subprocess.run(["/usr/bin/swiftc", "-O", "-module-cache-path", str(root / "ellie-swift-modules"),
                            str(source), "-o", str(binary)], check=True)
            check(str(binary))


if __name__ == "__main__":
    unittest.main()
