#!/usr/bin/env python3
"""Show default-interface throughput only after three seconds of activity."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

# Decimal MB/s, not MiB/s. Ignore routine background traffic.
MIN_BYTES_PER_SECOND = 1_000_000
SUSTAIN_SECONDS = 3.0
MIN_VISIBLE_SECONDS = 5.0
MAX_SAMPLE_GAP = 2.5


def read_counters():
    """Use one interface to avoid counting link/IP rows or VPN traffic twice."""
    route = subprocess.check_output(
        ["/sbin/route", "-n", "get", "default"], text=True, timeout=2
    )
    interface = next(
        line.split(":", 1)[1].strip()
        for line in route.splitlines()
        if line.strip().startswith("interface:")
    )
    output = subprocess.check_output(
        ["/usr/sbin/netstat", "-ibn", "-I", interface], text=True, timeout=2
    )
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 10 and fields[0] == interface and fields[2].startswith("<Link#"):
            # Read from the end: interfaces without a MAC omit the Address field.
            return interface, int(fields[-5]), int(fields[-2])
    raise ValueError("No link counters for default interface")


def sample(previous, interface, received, sent, now):
    """Return persisted state and an optional label for this sample."""
    state = {
        "interface": interface,
        "received": received,
        "sent": sent,
        "time": now,
        "down_since": None,
        "up_since": None,
        "visible_since": None,
        "directions": [],
    }
    if not previous or previous.get("interface") != interface:
        return state, None
    elapsed = now - previous["time"]
    downloaded = received - previous["received"]
    uploaded = sent - previous["sent"]
    if not 0 < elapsed <= MAX_SAMPLE_GAP or min(downloaded, uploaded) < 0:
        return state, None
    down, up = downloaded / elapsed, uploaded / elapsed
    directions = []
    for direction, speed in (("down", down), ("up", up)):
        if speed <= MIN_BYTES_PER_SECOND:
            continue
        key = f"{direction}_since"
        since = previous.get(key)
        if since is None:
            since = previous["time"]
        state[key] = since
        if now - since >= SUSTAIN_SECONDS:
            directions.append(direction)
    visible_since = previous.get("visible_since")
    if directions:
        state["visible_since"] = now if visible_since is None else visible_since
    elif visible_since is not None and now - visible_since < MIN_VISIBLE_SECONDS:
        state["visible_since"] = visible_since
        directions = previous.get("directions", [])
    state["directions"] = directions
    labels = [
        f"{arrow} {speed / 1_000_000:.2f} MB/s"
        for direction, arrow, speed in (("down", "↓", down), ("up", "↑", up))
        if direction in directions
    ]
    return state, "  ".join(labels) or None


def main():
    name = os.environ.get("NAME", "network")
    # Private per-user cache; monotonic timestamps also reject stale samples.
    cache = Path(tempfile.gettempdir()) / f"sketchybar-network-{os.getuid()}"
    cache.mkdir(mode=0o700, exist_ok=True)
    state_path = cache / "state.json"
    previous = None
    try:
        previous = json.loads(state_path.read_text())
    except (OSError, ValueError):
        pass
    try:
        if os.environ.get("SENDER") in {"system_woke", "forced"}:
            previous = None
        interface, received, sent = read_counters()
        state, label = sample(previous, interface, received, sent, time.monotonic())
    except (OSError, subprocess.SubprocessError, StopIteration, ValueError, KeyError, TypeError):
        state, label = {}, None
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state))
    temporary.replace(state_path)
    properties = [f"drawing={'on' if label else 'off'}"]
    if label:
        properties.append(f"label={label}")
    subprocess.run(["sketchybar", "--set", name, *properties], check=True)


if __name__ == "__main__":
    main()
