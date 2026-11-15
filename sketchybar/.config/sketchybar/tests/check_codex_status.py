"""Exercise the status observer against an isolated fake Herdr socket and bar."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time


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


def check():
    with tempfile.TemporaryDirectory(prefix="codex-status-check-", dir="/tmp") as directory:
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
        bar = subprocess.Popen(["/bin/sleep", "120"])
        script = Path(__file__).resolve().parents[1] / "plugins/codex_status.py"
        command = [sys.executable, "-B", str(script), "--watch", "--bar-pid", str(bar.pid),
                   "--socket", str(path), "--cache-dir", str(root / "cache"), "--sketchybar", str(fakebar)]
        observer = subprocess.Popen(command)

        def calls():
            return [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]

        def visible(state):
            last = calls()[-1]
            index = last.index(f"codex_state.{state}")
            return last[index + 1] == "drawing=on"

        def update(state, kind, pane):
            agents[:] = [{"agent": kind, "agent_status": state, "pane_id": pane,
                          "terminal_title_stripped": "Isolated agent"}]
            for connection in list(subscribers):
                try:
                    connection.sendall(b'{"event":"pane.agent_detected","data":{}}\n')
                except OSError:
                    subscribers.remove(connection)

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


if __name__ == "__main__":
    check()
