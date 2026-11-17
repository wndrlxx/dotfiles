# SketchyBar tests

Run commands from the `sketchybar` dotfiles directory. Ruby and Python discovery
are independent, so both implementations can coexist during migration.

## Ruby runtime and tests

The migration targets mise-managed Ruby 3.4 or newer (currently Ruby 4.0.9).
`plugins/ruby.sh` resolves Ruby with `mise -C "$HOME" which ruby`, then executes
the resolved binary and forwards arguments and exit status. Future migrated
plugins should use `/bin/sh "$PLUGIN_DIR/ruby.sh" "$PLUGIN_DIR/plugin.rb"` in
their SketchyBar launch commands. Existing Python launch commands are unchanged.

The launcher finds mise at `$HOME/.local/bin/mise`, falling back to mise on PATH.
It needs no interactive shell activation and uses the user's home configuration
regardless of the service's working directory. It fails if mise or its configured
Ruby is unavailable, without falling back to system Ruby. Configure Ruby in mise
and install it before starting the bar. SketchyBar supplies `CONFIG_DIR`; external
commands should use absolute paths or explicitly configure PATH when needed.
The launcher does not change the inherited environment or working directory.

Tests use Minitest's BDD/spec syntax (`describe`, `it`, and `_(value).must_equal`
expectations), without an RSpec dependency. Use this style for new Ruby tests.
Minitest 6.1.0 is installed in the selected mise Ruby.
Check availability with `/bin/sh .config/sketchybar/plugins/ruby.sh
-rminitest/autorun -e 'puts Minitest::VERSION'`. If absent, install it into that
runtime with `mise -C "$HOME" exec -- gem install minitest -v 6.1.0`.
Repeat installation when switching to a Ruby without that gem. Do not use `sudo gem`.

```sh
/bin/sh .config/sketchybar/plugins/ruby.sh .config/sketchybar/tests/run.rb unit
/bin/sh .config/sketchybar/plugins/ruby.sh .config/sketchybar/tests/run.rb integration
/bin/sh .config/sketchybar/plugins/ruby.sh .config/sketchybar/tests/run.rb all
```

Ruby tests use `test_*.rb` under the same unit/integration directories and share
`test_helper.rb`. The runner accepts Minitest options after the suite name, such
as `all --verbose`. Individual test files can also be passed to the Ruby launcher.
The integration smoke test starts a real Ruby process with a minimal service-like
environment from a different working directory, checking paths with spaces,
literal arguments, runtime selection, inherited `CONFIG_DIR`, and exit status.
It does not modify the running bar or access credentials.

## Python baseline

The existing suites use Python's standard `unittest` runner and `test_*.py` filenames.

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
