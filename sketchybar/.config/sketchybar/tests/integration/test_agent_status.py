"""Exercise the status observer with isolated Herdr, Rex, and SketchyBar fixtures."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest


def wait_for(predicate, message):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (OSError, ValueError, KeyError, IndexError):
            pass
        time.sleep(.05)
    raise AssertionError(message)


def check(with_rex=False):
    with tempfile.TemporaryDirectory(prefix="agent-status-check-", dir="/tmp") as directory:
        root = Path(directory)
        path = root / "herdr.sock"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(path))
        listener.listen()
        listener.settimeout(.2)
        agents, subscribers, subscriptions, methods = [], [], [], []
        stop = threading.Event()

        def serve():
            while not stop.is_set():
                try:
                    connection, _ = listener.accept()
                except socket.timeout:
                    continue
                with connection.makefile("rb") as stream:
                    request = json.loads(stream.readline())
                method = request["method"]
                methods.append(method)
                if method == "agent.list":
                    result = {"type": "agent_list", "agents": list(agents)}
                elif method == "events.subscribe":
                    subscriptions.append(request["params"]["subscriptions"])
                    result = {"type": "subscription_started"}
                else:
                    raise AssertionError(f"Unexpected method: {method}")
                connection.sendall((json.dumps({"id": request["id"], "result": result}) + "\n").encode())
                if method == "events.subscribe":
                    subscribers.append(connection)
                else:
                    connection.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        fakebar = root / "bar"
        fakebar.write_text(f"#!{sys.executable}\n" + '''import json,sys
from pathlib import Path
with Path(__file__).with_name("calls.jsonl").open("a") as f:
    f.write(json.dumps(sys.argv[1:])+"\\n")
''')
        fakebar.chmod(0o700)
        rex_snapshot = root / "rex-snapshot.json"
        fakerex = root / "rex"
        fakerex.write_text(f"#!{sys.executable}\n" + '''import sys,time
from pathlib import Path
assert sys.argv[1:5] == ["--autostart=false", "--timeout", "3s", "do"]
assert sys.argv[6:8] == ["--all", "--fail-fast"]
path = Path(__file__).with_name("rex-snapshot.json")
previous = None
while path.exists():
    try:
        snapshot = path.read_text()
    except FileNotFoundError:
        break
    if snapshot != previous:
        print(snapshot, flush=True)
        previous = snapshot
    if "snapshot=true" in sys.argv:
        break
    time.sleep(.025)
''')
        fakerex.chmod(0o700)

        def update_rex(state=None, kind="codex"):
            temporary = rex_snapshot.with_suffix(".tmp")
            agents = {"rex:1": {"pane_id": "rex:1", "agent_status": state, "agent": kind,
                                "name": "Isolated Rex agent", "source": "Rex"}} if state else {}
            temporary.write_text(json.dumps(agents))
            temporary.replace(rex_snapshot)

        update_rex()
        bar = subprocess.Popen(["/bin/sleep", "120"])
        script = Path(__file__).resolve().parents[2] / "plugins/agent_status.py"
        command = [sys.executable, "-B", str(script), "--watch", "--bar-pid", str(bar.pid),
                   "--socket", str(path), "--cache-dir", str(root / "cache"), "--sketchybar", str(fakebar),
                   "--rex", str(fakerex) if with_rex else ""]
        observer = subprocess.Popen(command)

        def calls():
            return [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]

        def visible(state):
            last = calls()[-1]
            index = last.index(f"agent_state.{state}")
            return last[index + 1] == "drawing=on"

        def update(state, kind, pane):
            agents[:] = [{"agent": kind, "agent_status": state, "pane_id": pane,
                          "terminal_title_stripped": "Isolated agent"}]
            for connection in list(subscribers):
                try:
                    connection.sendall(b'{"event":"pane.agent_detected","data":{}}\n')
                except OSError:
                    subscribers.remove(connection)
                    connection.close()

        try:
            wait_for(lambda: len(calls()) > 0, "Initial idle render missing")
            assert not any(visible(state) for state in ("working", "waiting", "done"))
            for kind, pane in (("codex", "w1:p1"), ("pi", "w1:p2")):
                update("working", kind, pane)
                wait_for(lambda: visible("working"), f"{kind}: Working not shown")
                wait_for(lambda: any(s.get("pane_id") == pane for s in subscriptions[-1]),
                         f"{kind}: New pane not subscribed")
                update("blocked", kind, pane)
                wait_for(lambda: visible("waiting") and not visible("working"), f"{kind}: Waiting state not shown")
                update("done", kind, pane)
                wait_for(lambda: visible("done") and not visible("waiting"), f"{kind}: Done state not shown")
                update("idle", kind, pane)
                wait_for(lambda: not any(visible(state) for state in ("working", "waiting", "done")),
                         f"{kind}: Idle not hidden")
            if with_rex:
                update("working", "codex", "w1:p1")
                update_rex("working")
                wait_for(lambda: "label=Working: 2" in calls()[-1], "Combined Working count missing")
                assert "label=Isolated agent" in calls()[-1]
                assert "label=Rex · Isolated Rex agent" in calls()[-1]
                for state, kind, label in (("blocked", "pi", "Input"), ("done", "antigravity", "Done"), ("error", "pi", "Error")):
                    update_rex(state, kind)
                    wait_for(lambda: f"label={label}: 1" in calls()[-1], f"Rex {label} missing")
                    assert "label=Working: 1" in calls()[-1]
                update_rex("idle")
                wait_for(lambda: not visible("error"), "Idle Rex agent still visible")
                update_rex("blocked")
                wait_for(lambda: visible("waiting"), "Rex Input missing before disconnect")
                update_rex()
                wait_for(lambda: not visible("waiting"), "Removed Rex status still visible")
                update_rex("blocked")
                wait_for(lambda: visible("waiting"), "Updated Rex Input missing")
                rex_snapshot.unlink()
                wait_for(lambda: not visible("waiting"), "Rex Input survived disconnect")
                assert visible("working"), "Rex disconnect hid Herdr Working"
                update_rex("done")
                wait_for(lambda: visible("done"), "Rex did not repopulate after reconnect")
                for connection in subscribers:
                    connection.close()
                wait_for(lambda: not visible("working"), "Herdr Working survived disconnect")
                assert visible("done"), "Herdr disconnect hid Rex Done"
                wait_for(lambda: visible("working"), "Herdr did not repopulate after reconnect")
                status = subprocess.check_output([sys.executable, "-B", str(script), "--status",
                                                  "--socket", str(path), "--rex", str(fakerex)], timeout=8)
                assert json.loads(status) == {"working": 1, "waiting": 0, "done": 1, "error": 0}
            before = len(calls())
            subprocess.run(command, check=True, timeout=5)
            wait_for(lambda: len(calls()) > before, "Reload not rendered")
            owner = json.loads((root / "cache/watcher.json").read_text())
            assert owner["pid"] == observer.pid, "Duplicate observer on reload"
            request_count = len(methods)
            time.sleep(.5)
            assert len(methods) == request_count, "Observer polled while idle"
            bar.terminate()
            bar.wait(timeout=5)
            observer.wait(timeout=5)
            assert observer.returncode == 0
            print("PASS: Codex and Pi working, waiting, done, idle, new panes, reload singleton, no idle polling, bar exit")
        finally:
            for process in (bar, observer):
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            stop.set()
            thread.join(timeout=1)
            listener.close()
            for connection in subscribers:
                connection.close()


class AgentStatusIntegrationTests(unittest.TestCase):
    def test_status_observer_lifecycle(self):
        check()

    def test_herdr_and_rex_lifecycles_are_independent(self):
        check(with_rex=True)


if __name__ == "__main__":
    unittest.main()
