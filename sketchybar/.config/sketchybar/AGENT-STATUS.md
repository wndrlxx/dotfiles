# Codex and Pi agent indicators

`codex_status.py` combines Codex and Pi status from the default local Herdr
session and all sessions on the local Rex server. The counts appear alongside
the Codex quota bars.

| Indicator | Herdr state | Rex state |
| --- | --- | --- |
| Amber `◌ Working: N` (`#E0AF68`) | `working` | `working` |
| Pink/red `? Input: N` (`#F7768E`) | `blocked` | `blocked` |
| Cyan `✓ Done: N` (`#7DCFFF`) | `done` | `done` |
| Pink/red `! Error: N` (`#F7768E`) | — | `error` |
| Hidden | `idle`, `unknown`, or no matching agents | `idle` or no matching records |

Hover an indicator to see the agents' titles. Rex rows have a `Rex ·` prefix.
Each terminal manager determines when a completion is considered seen. The
popup reads the current status without changing focus or completion state.

The watcher reads an initial Herdr `agent.list` and subscribes to status,
topology, and focus events on the local Unix socket. A Rex CLI subprocess
reads program status records and follows status and topology events. Rex counts
records reported as `codex` or `pi` via OSC 7501. A disconnect clears that
source's rows and retries its connection after five seconds.

The Herdr socket defaults to `~/.config/herdr/herdr.sock`, with
`HERDR_SOCKET_PATH` and `HERDR_CONFIG_PATH` overrides. The watcher looks for
`rex` on its PATH, then in the Rex and Rex Beta bundles under `/Applications`.
Set `SKETCHYBAR_REX_BIN` to override the executable or set it to an empty
string to disable Rex. The CLI connects with server autostart disabled.

Restart SketchyBar once when upgrading from the Herdr-only watcher. Subsequent
config reloads reuse the watcher, and it exits with SketchyBar.

Inspect the combined counts without changing the bar.

```sh
python3 -B ~/.config/sketchybar/plugins/codex_status.py --status
```

Run the tests from the sketchybar dotfiles directory.

```sh
python3 -B -m unittest discover -s .config/sketchybar/tests/unit
python3 -B .config/sketchybar/tests/integration/test_codex_status.py
```

The integration tests use a fake Herdr socket, Rex executable, and bar. They
cover both sources' status transitions and independent disconnects.
