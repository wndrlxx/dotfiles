#!/usr/bin/env python3
"""Show Codex and Pi agents using local Herdr and Rex status events."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import stat
import subprocess
import time
import unicodedata

SUPPORTED_AGENTS = {"codex", "pi"}
STATES = {"working": ("Working", "◌", "0xffe0af68"),
          "waiting": ("Input", "?", "0xfff7768e"),
          "done": ("Done", "✓", "0xff7dcfff"),
          "error": ("Error", "!", "0xfff7768e")}
RENDER_STATES = {"working": "working", "blocked": "waiting", "done": "done", "error": "error"}
TOPOLOGY = ["pane.created", "pane.closed", "pane.exited", "pane.moved",
            "pane.agent_detected", "pane.focused", "tab.focused", "workspace.focused", "workspace.closed"]


def default_socket():
    config = Path(os.environ.get("HERDR_CONFIG_PATH", str(Path.home() / ".config/herdr/config.toml")))
    return os.environ.get("HERDR_SOCKET_PATH") or str(config.parent / "herdr.sock")


def request(path, method, params):
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(3)
        connection.connect(str(path))
        connection.sendall((json.dumps({"id": "sketchybar", "method": method, "params": params}) + "\n").encode())
        return connection
    except BaseException:
        connection.close()
        raise


def list_agents(path):
    with request(path, "agent.list", {}) as connection, connection.makefile("rb") as stream:
        data = stream.readline(2 * 1024 * 1024)
        response = json.loads(data)
        return [agent for agent in response["result"]["agents"] if agent.get("agent") in SUPPORTED_AGENTS]


def subscribe(path, pane_ids):
    subscriptions = [{"type": event} for event in TOPOLOGY]
    subscriptions += [{"type": "pane.agent_status_changed", "pane_id": pane} for pane in sorted(pane_ids)]
    return request(path, "events.subscribe", {"subscriptions": subscriptions})


def receive_events(connection, buffer):
    chunk = connection.recv(65536)
    if not chunk:
        raise ConnectionError("Herdr disconnected")
    buffer += chunk
    if len(buffer) > 2 * 1024 * 1024:
        raise ValueError("Oversized Herdr event")
    changed = False
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        message = json.loads(line)
        if "error" in message:
            raise ValueError("Herdr subscription rejected")
        changed = changed or "event" in message
    return buffer, changed


def rex_command(executable):
    if executable is None:
        executable = shutil.which("rex")
        if not executable:
            for app in ("Rex.app", "Rex Beta.app"):
                bundled = f"/Applications/{app}/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex"
                if os.access(bundled, os.X_OK):
                    executable = bundled
                    break
    if not executable:
        return None
    script = Path(__file__).resolve().with_name("rex_agent_status.lua")
    return [executable, "--autostart=false", "--timeout", "3s", "do", str(script),
            "--all", "--fail-fast"]


def stop_rex(process):
    process.stdout.close()
    process.terminate()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def parse_rex_snapshot(data):
    snapshot = json.loads(data)
    if not isinstance(snapshot, dict) or any(
        not isinstance(agent, dict) or agent.get("pane_id") != pane
        for pane, agent in snapshot.items()
    ):
        raise ValueError("Invalid Rex snapshot")
    return list(snapshot.values())


def receive_rex(fd, buffer, agents):
    chunk = os.read(fd, 65536)
    if not chunk:
        raise ConnectionError("Rex disconnected")
    buffer += chunk
    if len(buffer) > 2 * 1024 * 1024:
        raise ValueError("Oversized Rex snapshot")
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        agents = parse_rex_snapshot(line)
    return buffer, agents


def groups(agents):
    result = {state: [] for state in STATES}
    for agent in agents:
        if agent.get("agent") not in SUPPORTED_AGENTS:
            continue
        state = RENDER_STATES.get(agent.get("agent_status"))
        if state:
            title = (agent.get("name") or agent.get("terminal_title_stripped")
                     or agent.get("terminal_title") or agent["pane_id"])
            title = " ".join(str(title).split())
            if agent.get("source") == "Rex":
                title = "Rex · " + "".join(char for char in title if unicodedata.category(char) not in {"Cc", "Cf"})
            result[state].append((agent["pane_id"], title[:80]))
    for rows in result.values():
        rows.sort()
    return result


class Renderer:
    def __init__(self, executable="sketchybar"):
        self.executable = executable
        self.previous = None

    def render(self, agents, force=False):
        grouped = groups(agents)
        if grouped == self.previous and not force:
            return
        command = [self.executable]
        nearest_usage = next((state for state, rows in grouped.items() if rows), None)
        for state, (label, icon, color) in STATES.items():
            name = f"codex_state.{state}"
            rows = grouped[state]
            command += ["--set", name, f"drawing={'on' if rows else 'off'}",
                        f"padding_right={10 if state == nearest_usage else 6}",
                        f"icon={icon}", f"icon.color={color}", f"label={label}: {len(rows)}",
                        f"label.color={color}"]
            if not rows:
                command += ["popup.drawing=off"]
            command += ["--remove", f"/^{re.escape(name)}\\.row\\./"]
            for index, (_, title) in enumerate(rows):
                child = f"{name}.row.{index}"
                command += ["--add", "item", child, f"popup.{name}", "--set", child,
                            "icon.drawing=off", f"label={title}", "label.color=0xffffffff",
                            "label.padding_left=10", "label.padding_right=10"]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.previous = grouped


def private_directory(path):
    path = Path(path)
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Unsafe Codex status directory")
    return path


def watcher(path, bar_pid, directory, executable, rex_executable):
    directory = private_directory(directory)
    lock = os.open(directory / "watcher.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    control_path = str(directory / "refresh.sock")
    deadline = time.monotonic() + 2
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            try:
                owner = json.loads((directory / "watcher.json").read_text())
                if owner.get("bar_pid") == bar_pid:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as wake:
                        wake.sendto(b"refresh", control_path)
                    os.close(lock)
                    return
            except (OSError, ValueError):
                pass
            if time.monotonic() > deadline:
                os.close(lock)
                raise RuntimeError("Previous Codex status watcher has not exited")
            time.sleep(0.05)  # Startup handoff only.
    control = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    queue = select.kqueue()
    connection = None
    rex = None
    renderer = Renderer(executable)
    try:
        Path(control_path).unlink(missing_ok=True)
        control.bind(control_path)
        (directory / "watcher.json").write_text(json.dumps({"bar_pid": bar_pid, "pid": os.getpid()}))
        queue.control([
            select.kevent(control.fileno(), filter=select.KQ_FILTER_READ, flags=select.KQ_EV_ADD),
            select.kevent(bar_pid, filter=select.KQ_FILTER_PROC, flags=select.KQ_EV_ADD,
                          fflags=select.KQ_NOTE_EXIT)], 0, 0)
        os.kill(bar_pid, 0)
        buffer, panes = b"", set()
        herdr_agents, rex_agents, rex_buffer = [], [], b""
        rex_retry_at = float("inf") if rex_executable == "" else 0
        refresh, force, retry_at = True, True, 0
        while True:
            if refresh:
                refresh = False
                try:
                    herdr_agents = list_agents(path)
                    current_panes = {agent["pane_id"] for agent in herdr_agents}
                    if connection is None or current_panes != panes:
                        if connection:
                            connection.close()
                        connection = subscribe(path, current_panes)
                        connection.setblocking(False)
                        queue.control([select.kevent(connection.fileno(), filter=select.KQ_FILTER_READ,
                                                      flags=select.KQ_EV_ADD)], 0, 0)
                        buffer, panes = b"", current_panes
                        # Snapshot again after subscribing to cover changes during setup.
                        herdr_agents = list_agents(path)
                        if {agent["pane_id"] for agent in herdr_agents} != panes:
                            refresh = True
                except (OSError, ValueError, KeyError):
                    if connection:
                        connection.close()
                    connection, buffer = None, b""
                    herdr_agents, retry_at = [], time.monotonic() + 5
            if rex is None and time.monotonic() >= rex_retry_at:
                rex_retry_at = time.monotonic() + 5
                command = rex_command(rex_executable)
                if command:
                    try:
                        rex = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        queue.control([select.kevent(rex.stdout.fileno(), filter=select.KQ_FILTER_READ,
                                                      flags=select.KQ_EV_ADD)], 0, 0)
                    except OSError:
                        if rex:
                            stop_rex(rex)
                        rex = None
            renderer.render(herdr_agents + rex_agents, force=force)
            force = False
            if refresh:
                continue
            deadline = min(float("inf") if connection else retry_at,
                           float("inf") if rex else rex_retry_at)
            timeout = None if deadline == float("inf") else max(0, deadline - time.monotonic())
            events = queue.control(None, 32, timeout)
            for event in events:
                if event.filter == select.KQ_FILTER_PROC:
                    return
                if event.ident == control.fileno():
                    control.recv(1024)
                    refresh, force = True, True
                elif connection and event.ident == connection.fileno():
                    try:
                        buffer, changed = receive_events(connection, buffer)
                        refresh = refresh or changed
                    except BlockingIOError:
                        continue
                    except (OSError, ValueError):
                        connection.close()
                        connection, buffer = None, b""
                        herdr_agents = []
                        retry_at = time.monotonic() + 5
                elif rex and event.ident == rex.stdout.fileno():
                    try:
                        rex_buffer, rex_agents = receive_rex(event.ident, rex_buffer, rex_agents)
                    except (OSError, ValueError):
                        stop_rex(rex)
                        rex, rex_buffer, rex_agents = None, b"", []
                        rex_retry_at = time.monotonic() + 5
            if connection is None and time.monotonic() >= retry_at:
                refresh = True
    finally:
        if rex:
            stop_rex(rex)
        if connection:
            connection.close()
        queue.close()
        control.close()
        Path(control_path).unlink(missing_ok=True)
        os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--popup", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--socket", default=default_socket())
    parser.add_argument("--bar-pid", type=int)
    parser.add_argument("--cache-dir", default=f"/tmp/sketchybar-codex-status-{os.getuid()}")
    parser.add_argument("--sketchybar", default="sketchybar")
    parser.add_argument("--rex", default=os.environ.get("SKETCHYBAR_REX_BIN"),
                        help="Rex CLI path (empty to disable Rex)")
    args = parser.parse_args()
    if args.popup:
        name = os.environ.get("NAME", "")
        if name not in {f"codex_state.{state}" for state in STATES}:
            return
        show = os.environ.get("SENDER") == "mouse.entered"
        subprocess.run([args.sketchybar, "--set", name, f"popup.drawing={'on' if show else 'off'}"], check=True)
    elif args.status:
        try:
            agents = list_agents(args.socket)
        except (OSError, ValueError, KeyError):
            agents = []
        command = rex_command(args.rex)
        if command:
            try:
                snapshot = subprocess.check_output(command + ["snapshot=true"], timeout=5,
                                                   stderr=subprocess.DEVNULL)
                agents += parse_rex_snapshot(snapshot)
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        print(json.dumps({state: len(rows) for state, rows in groups(agents).items()}))
    elif args.watch and args.bar_pid and args.bar_pid > 0:
        watcher(args.socket, args.bar_pid, args.cache_dir, args.sketchybar, args.rex)
    else:
        parser.error("Use --watch --bar-pid PID, --popup, or --status")


if __name__ == "__main__":
    main()
