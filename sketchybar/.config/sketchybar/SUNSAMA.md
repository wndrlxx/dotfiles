# Open Sunsama task timer

The Open Sunsama timer uses the same renderer as Ellie: a bold amber stopwatch
and elapsed time on a soft amber pill, with the task title in warm gold. It
uses the `timer` and `timer.notch` slots and follows the existing clock layout.
Clicking it opens https://sunsama.andlee.dev (override with `OPEN_SUNSAMA_APP_URL`).
Stopping the timer, an unavailable API, or an authentication failure restores
the hidden timer state and clears the timer styling and click action. Weather
is not shown in the current bar layout.

## API key in macOS Keychain

In Open Sunsama, open **Settings → API Keys → Create API Key**. Name the key
`SketchyBar`, select **Tasks Read** (`tasks:read`), and deselect the other
permissions. Create the key. Open **Keychain Access**,
select your **login** keychain, and choose **File → New Password Item**:

- Keychain Item Name: `sketchybar-open-sunsama`
- Account Name: your macOS username
- Password: the API key

The widget reads the password using `/usr/bin/security find-generic-password`.
macOS may ask you to allow access the first time; allow access for the widget
to refresh unattended. The key is never stored in dotfiles, timer caches, logs,
or command arguments. `OPEN_SUNSAMA_API_KEY` in SketchyBar's environment is also
supported and takes precedence over Keychain.

The Account Name is only a label: lookup uses the item name, not the account.
If lookup fails, check that the item is in **login** with the exact name above.

Reload SketchyBar after adding the key. The config automatically selects Open
Sunsama when the Keychain item or environment key exists; otherwise it keeps
Ellie. Set `SKETCHYBAR_TIMER_PROVIDER=ellie` or `sunsama` in SketchyBar's environment
to select explicitly. Only one provider controls the timer area at a time.
Environment settings must be inherited by the SketchyBar service, or exported
at the top of `sketchybarrc`; exporting them in an unrelated terminal is insufficient.

The controller sends an authenticated GET to
`https://sunsama-api.andlee.dev/tasks/timer/active` every five seconds, even when
the web app is closed. It reads `{success: true, data: task | null}` and adds
`timerAccumulatedSeconds` to the elapsed time since `timerStartedAt`.
One persistent Python process renders the seconds locally, starting as soon as
the first response arrives. A background thread handles API/Keychain requests so
slow requests do not block ticking. No compiler or native helper is required.
Timer state and the key stay in memory; only the watcher identity is saved in a
private temporary directory. Stop and task changes appear within a polling
interval; samples expire after 15 seconds. Requests have a three-second timeout
and do not follow redirects.

The watcher reuses its process across config reloads, restarts after source changes,
and exits when SketchyBar exits or the config selects Ellie. Wake and reload
events request a fresh API sample and redraw. Keychain access must be allowed for
unattended updates. A manual `--status` check allows 30 seconds to approve the
initial prompt.

Inspect the timer without changing the bar:

```sh
python3 -B ~/.config/sketchybar/plugins/sunsama_timer.py --status
```

Run tests from the `sketchybar` directory:

```sh
python3 -B -m unittest discover -s .config/sketchybar/tests/unit -v
```

The Python watcher integration check uses an isolated fake bar and local API:

```sh
python3 -B .config/sketchybar/tests/integration/test_sunsama_timer.py
```
