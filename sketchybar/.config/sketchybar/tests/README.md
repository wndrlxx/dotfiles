# SketchyBar tests

Run commands from the `sketchybar` dotfiles directory. Both suites use Python's
standard `unittest` runner and `test_*.py` filenames.

## Unit tests

`unit/` tests plugin logic with fixtures and mocks. These are the fast default:

```sh
python3 -B -m unittest discover -s .config/sketchybar/tests/unit -v
```

## Integration tests

`integration/` tests real processes, local sockets/HTTP, signals, reloads, and
shutdown against isolated fixtures and fake bars. They use no real API credentials
and do not modify the running bar. Local socket access is required. Ellie's test
also needs macOS and Apple's command-line tools; it builds a Swift helper and
launches a separate fixture app. These tests take longer than the unit suite.

```sh
python3 -B -m unittest discover -s .config/sketchybar/tests/integration -v
```

Run just the Open Sunsama integration test:

```sh
python3 -B -m unittest discover -s .config/sketchybar/tests/integration -p test_sunsama_timer.py -v
```

Set `ELLIE_WATCHER_BINARY` to an existing compiled Ellie helper to reuse it during
the Ellie integration test. Otherwise the test builds the current source itself.

To run both suites, discover from their shared parent:

```sh
python3 -B -m unittest discover -s .config/sketchybar/tests -v
```
