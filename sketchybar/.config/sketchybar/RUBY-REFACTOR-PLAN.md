# SketchyBar Ruby refactor plan

Created: 2026-11-17

Goal: replace SketchyBar's Python plugins and their tests with Ruby while
preserving the existing appearance, behavior, and process lifecycle.

Implement this as small, independently testable commits. Keep the bar usable
after each phase and check off a phase only when its completion criteria pass.
Phases 1 and 2 are complete. Phase 2 awaits user review before committing or
starting Phase 3. The current Python implementation and tests
provide the baseline; the unit/integration directory reorganization is already
in place.

## Phase 1: Establish the baseline

- [x] Commit the working Python Open Sunsama implementation and test reorganization.
- [x] Bring the Sunsama work together with current main, preserving the newer
  layout, network widget, and Codex/Pi behavior.
- [x] Run the existing unit and integration suites and verify the running bar.

Completion: a committed, working baseline contains all features to be migrated.
Record relevant idle CPU, memory, and startup measurements for later comparison.

## Phase 2: Add Ruby test infrastructure

- [x] Establish the Ruby version and executable that SketchyBar will use,
  including its service environment and PATH.
- [x] Choose a Ruby test framework and document dependency installation and
  test commands.
- [x] Add Ruby tests alongside the Python tests under `tests/unit/` and
  `tests/integration/`.

Completion: both language suites run independently. Existing Python tests still
pass. See [tests/README.md](tests/README.md) for the current test layout.

## Phase 3: Add shared Ruby support

- [ ] Implement a small SketchyBar command wrapper and shared timer rendering.
- [ ] Implement private cache directories and process locking.
- [ ] Test command arguments, styling, layout, permissions, and duplicate-process
  prevention against the existing behavior.

Completion: Ruby produces the expected bar commands and reliably enforces a
single watcher. Keep shared support limited to what the plugins actually need.

## Phase 4: Port Open Sunsama

- [ ] Port the API client, authentication lookup, response validation, and timer
  calculations.
- [ ] Port the persistent watcher with independent API requests and local ticking.
- [ ] Migrate its unit and integration coverage, then switch its launch command
  to Ruby.

Completion: one-second ticks and five-second polling work immediately after
startup. Slow API/Keychain requests do not block ticking. Hidden-timer fallback,
stale-state expiry, reload reuse, source-change restart, config switching, and
shutdown pass integration tests. Styling and click behavior remain consistent.

## Phase 5: Port independent plugins

- [ ] Port network throughput in its own commit, including its tests.
- [ ] Port the Codex quota display in a separate commit, including its tests.
- [ ] Switch each plugin's launch command only after its replacement passes.

Completion: network thresholds, sustained-activity windows, minimum visibility,
formatting, quota calculations, and generated display assets retain their
existing behavior.

## Phase 6: Port Codex/Pi status

- [ ] Port the socket client, event subscriptions, and status grouping.
- [ ] Port rendering and the persistent observer's locking and lifecycle.
- [ ] Migrate unit/integration tests and switch the observer to Ruby.

Completion: supported agents and their working, waiting, done, and idle states
behave as before. Tests cover new panes, connection recovery, reload reuse,
shutdown, and the absence of idle polling.

## Phase 7: Port Ellie

- [ ] Port the binary storage reader first, preserving its existing fixtures.
- [ ] Compare Ruby decoding with Python for LevelDB records, Snappy data, V8
  values, Firestore records, and pending local changes.
- [ ] Port the timer controller and cache handling, connect the Ruby reader,
  migrate tests, and switch the controller to Ruby.

Completion: storage fixtures and stopwatch, countdown, Pomodoro, pause/stop,
sign-out, unreadable-cache, and app-lifecycle behavior match the baseline.

Ellie's Swift helper remains in scope for compatibility testing, but replacing
it is a separate decision. Porting the Python code does not require removing it.

## Phase 8: Remove Python

- [ ] Remove superseded Python implementations and tests once Ruby parity passes.
- [ ] Update launch commands, documentation, and dependency instructions.
- [ ] Remove unused dependencies and scan for obsolete Python runtime references.
- [ ] Run all Ruby suites, verify the running bar, and compare resource usage
  with the baseline.

Completion: the migrated SketchyBar features have no Python runtime dependency,
all tests pass, and each feature works through startup, reload, and shutdown.

## Working rules

- Migrate each plugin's tests alongside its implementation.
- Keep the Python version available for comparison until its replacement passes.
- Use a separate commit for each independently switchable plugin; split a phase
  into more commits when that makes review and rollback easier.
- Preserve credentials outside the repository and keep real credentials out of
  tests and captured output.
- Record completed work, validation results, and any remaining decisions below.

## Implementation log

### 2026-11-17: Phase 1 completed

- Committed the Python Sunsama implementation and test reorganization as `f62d2e8`.
- Rebased the feature onto local main `ed97121`, preserving the timer-only layout, network widget, and Codex/Pi support in a single linear feature commit. The previous merge commit was removed from the branch.
- Passed all 54 tests (51 unit and 3 integration) and verified the running bar, authenticated API access, reload reuse, and real one-second ticking.
- Startup and idle/active resource measurements were collected; `PYTHON-BASELINE.md` was subsequently removed at the user's request.
- This plan remains untracked and uncommitted. No push or merge into main was performed.

### 2026-11-17: Phase 2 completed, awaiting review

- Revised the launcher to detect mise in `$HOME/.local/bin` or PATH and resolve
  the user's configured Ruby from HOME, independent of service working directory
  and interactive shell activation. There is no system Ruby fallback. The target
  is Ruby 3.4 or newer; the selected mise Ruby is currently 4.0.9.
- Selected Minitest (installed version 6.1.0), added independent Ruby discovery
  and a shared test helper, and documented runtime, dependencies, and commands.
  Ruby tests use Minitest's BDD/spec syntax with `describe`, `it`, and expectations;
  use this style for subsequent migration phases.
- Passed 2 Ruby unit tests and 2 process integration tests (14 assertions total),
  both independently and through the combined runner. The process test verifies
  minimal service-like environment, runtime, argument forwarding, paths with
  spaces, inherited CONFIG_DIR, exit status, HOME-based mise discovery, and
  resolution failure without fallback.
- Passed all 54 existing Python tests (51 unit and 3 integration). The sandboxed
  attempt could not bind local sockets or launch the fixture app; the rerun with
  the required permissions passed. Shell/Ruby syntax and whitespace checks pass.
- Existing plugin launch commands remain unchanged. No commit or push performed;
  paused for the user's phase review before continuing.
