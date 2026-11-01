# Codex agent indicators

`codex_status.py` observes the default local Herdr session. It shows only Codex
agents managed by Herdr, alongside the existing quota bars:

| Indicator | Herdr state |
| --- | --- |
| Amber `◌ Working: N` (`#E0AF68`) | `working` |
| Pink/red `? Input: N` (`#F7768E`) | `blocked` (approval or user input needed) |
| Cyan `✓ Done: N` (`#7DCFFF`) | `done` |
| Hidden | `idle`, `unknown`, or no matching agents |

Hover an indicator to see the corresponding agents' titles. Herdr owns the
done/idle distinction and when completions are considered seen. Hovering does
not focus an agent or mark it seen.

One persistent Python observer subscribes to Herdr's local Unix socket. It reads
an initial `agent.list`, then refreshes only after relevant status, topology, or
focus events. It sends no prompts, approvals, focus commands, or other agent
mutations. There is no recurring SketchyBar update script. If disconnected, it
hides the indicators and retries the socket every five seconds. Config reloads
reuse the observer, and it exits when SketchyBar exits.

The socket defaults to `~/.config/herdr/herdr.sock`, with `HERDR_SOCKET_PATH` and
`HERDR_CONFIG_PATH` overrides. Other Herdr sessions, remote machines, and Codex
agents outside Herdr are not included. No Codex API keys or new hooks are needed.

Inspect counts without changing the bar:

```sh
python3 -B ~/.config/sketchybar/plugins/codex_status.py --status
```

Tests from the sketchybar dotfiles directory:

```sh
python3 -B -m unittest discover -s .config/sketchybar/tests
python3 -B .config/sketchybar/tests/check_codex_status.py
```

The integration check uses an isolated fake socket and bar; it never changes
real Herdr agents.
