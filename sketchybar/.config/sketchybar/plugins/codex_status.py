#!/usr/bin/env python3
"""Show Codex agents using Herdr's read-only, local status event stream."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import select
import socket
import stat
import subprocess
import time

STATES = {"working": ("Working", "◌", "0xffe0af68"),
          "waiting": ("Input", "?", "0xfff7768e"),
          "done": ("Done", "✓", "0xff7dcfff")}
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
        return [agent for agent in response["result"]["agents"] if agent.get("agent") == "codex"]


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


def groups(agents):
    result = {state: [] for state in STATES}
    for agent in agents:
        if agent.get("agent") != "codex":
            continue
        state = {"working": "working", "blocked": "waiting", "done": "done"}.get(agent.get("agent_status"))
        if state:
            title = (agent.get("name") or agent.get("terminal_title_stripped")
                     or agent.get("terminal_title") or agent["pane_id"])
            title = " ".join(str(title).split())
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


def watcher(path, bar_pid, directory, executable):
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
        refresh, force, retry_at = True, True, 0
        while True:
            if refresh:
                refresh = False
                try:
                    agents = list_agents(path)
                    current_panes = {agent["pane_id"] for agent in agents}
                    if connection is None or current_panes != panes:
                        if connection:
                            connection.close()
                        connection = subscribe(path, current_panes)
                        connection.setblocking(False)
                        queue.control([select.kevent(connection.fileno(), filter=select.KQ_FILTER_READ,
                                                      flags=select.KQ_EV_ADD)], 0, 0)
                        buffer, panes = b"", current_panes
                        # Snapshot again after subscribing to cover changes during setup.
                        agents = list_agents(path)
                        if {agent["pane_id"] for agent in agents} != panes:
                            refresh = True
                    renderer.render(agents, force=force)
                    force = False
                except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                    if connection:
                        connection.close()
                    connection, buffer = None, b""
                    renderer.render([], force=force)
                    force, retry_at = False, time.monotonic() + 5
            if refresh:
                continue
            timeout = None if connection else max(0, retry_at - time.monotonic())
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
                        renderer.render([])
                        retry_at = time.monotonic() + 5
            if connection is None and time.monotonic() >= retry_at:
                refresh = True
    finally:
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
    args = parser.parse_args()
    if args.popup:
        name = os.environ.get("NAME", "")
        if name not in {f"codex_state.{state}" for state in STATES}:
            return
        show = os.environ.get("SENDER") == "mouse.entered"
        subprocess.run([args.sketchybar, "--set", name, f"popup.drawing={'on' if show else 'off'}"], check=True)
    elif args.status:
        print(json.dumps({state: len(rows) for state, rows in groups(list_agents(args.socket)).items()}))
    elif args.watch and args.bar_pid and args.bar_pid > 0:
        watcher(args.socket, args.bar_pid, args.cache_dir, args.sketchybar)
    else:
        parser.error("Use --watch --bar-pid PID, --popup, or --status")


if __name__ == "__main__":
    main()
