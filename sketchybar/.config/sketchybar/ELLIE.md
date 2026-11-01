# Ellie timer

The hidden `ellie_timer` controller replaces the weather with the running task
and elapsed time. Python refreshes Ellie's state every five seconds, while the
native watcher advances the displayed time every second between refreshes.
It supports stopwatch, countdown, and Pomodoro
timers. Pausing/stopping the timer, signing out, or quitting Ellie restores the
weather. Click the running timer to open Ellie. The weather keeps updating in
the hidden `weather_data` item while the timer is visible. The existing clock
layout controls placement on notched and external displays.
While running, the stopwatch icon and time use bold amber text on a soft amber
pill; the task name uses a complementary soft warm gold. Weather restores its
normal styling afterward.
The clock and date stay left of the notch. On displays without a notch, they move
right while a timer runs and return to the center otherwise. Text spacing stays
the same in both states.

A small native observer listens for changes to macOS's running-app list. It
enables five-second Python updates only while Ellie is open and restores weather on quit.
While Ellie is closed, Python may run for a weather refresh or wake event, but
does not launch every second or inspect the database. The observer checks the
initial app state, reuses one process across config reloads, and exits when
SketchyBar exits. Python reads its state file instead of launching `pgrep`.
`ellie_watcher.sh` builds the Swift helper once with Apple's command-line tools
and keeps the executable in the private temporary cache, outside the dotfiles.
Python publishes a small `tick.json` time anchor after each refresh. The watcher
observes file-change events and ticks locally without running Python or reading
Ellie's database every second. Pause, stop, and task changes can take a few seconds
to appear; quitting Ellie stops ticking immediately. A ticker with no fresh anchor
expires after 15 seconds. Its one-second ticks invoke only the SketchyBar CLI.

The reader uses Ellie's local Chromium IndexedDB cache. It never opens the
database for writing, contacts a server, or requires an API key or screen capture.
It reads the current LevelDB manifest, merges tables and write-ahead logs, and
applies pending Firestore overlays so offline pause/stop changes take precedence.
Only a shortened title and selected timer fields are saved in a private temporary
cache; credentials and full account documents are not saved or printed.
Cache changes are decoded in a background process so periodic database reads
cannot delay the ticking display. The renderer uses the last confirmed timer
state during refresh and restores weather if a changed cache stays unreadable
for more than three seconds.

This depends on Ellie's internal storage format. Unknown or unreadable formats
restore the weather and log a generic error. Changes made on another device appear once
the desktop app receives them. Run this outside a process-restricted sandbox to
inspect the current display without modifying the bar:

```sh
python3 -B ~/.config/sketchybar/plugins/ellie_timer.py --status
```

Run the storage and timer tests from the `sketchybar` dotfiles directory:

```sh
python3 -B -m unittest discover -s .config/sketchybar/tests -v
```

The macOS lifecycle integration check uses a separate test app and fake bar:

```sh
python3 -B .config/sketchybar/tests/check_ellie_watcher.py "${TMPDIR:-/tmp}/sketchybar-ellie-$(id -u)/ellie-watcher"
```
