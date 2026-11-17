import io
import json
import os
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins"))
import sunsama_timer
from ellie_timer import display


def response(**changes):
    task = {"title": "Write tests", "timerStartedAt": "2026-01-01T00:00:00Z",
            "timerAccumulatedSeconds": 70, "completedAt": None}
    task.update(changes)
    return {"success": True, "data": task}


class SunsamaTimerTests(unittest.TestCase):
    def test_elapsed_time_includes_previous_sessions_and_hours(self):
        state = sunsama_timer.snapshot(response())
        self.assertEqual(display(state, 1767225665)["label"], "02:15 Write tests")
        self.assertEqual(display(state, 1767229265)["label"], "1:02:15 Write tests")

    def test_no_active_task_or_completed_task_hides_timer(self):
        for payload in ({"success": True, "data": None}, response(timerStartedAt=None),
                        response(completedAt="2026-01-01T00:00:00Z")):
            with self.subTest(payload=payload):
                self.assertEqual(display(sunsama_timer.snapshot(payload)), {"running": False})

    def test_invalid_responses_are_rejected(self):
        for payload in ({"success": False}, {}, [], response(timerStartedAt="bad"),
                        response(timerStartedAt="2026-01-01T00:00:00"),
                        response(timerAccumulatedSeconds=-1), response(timerAccumulatedSeconds=True),
                        response(timerAccumulatedSeconds=float("nan")), response(title=123)):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                sunsama_timer.snapshot(payload)

    def test_title_is_cleaned_shortened_and_no_other_task_fields_survive(self):
        payload = response(title="<b>Task</b> &amp;\n work", notes="private", userId="private")
        state = sunsama_timer.snapshot(payload)
        self.assertEqual(state["title"], "Task & work")
        self.assertNotIn("private", json.dumps(state))
        self.assertEqual(len(sunsama_timer.snapshot(response(title="x" * 100))["title"]), 38)

    def test_keychain_key_and_environment_override(self):
        with patch.dict(os.environ, {"OPEN_SUNSAMA_API_KEY": "test-key"}), \
                patch("sunsama_timer.subprocess.run") as run:
            self.assertEqual(sunsama_timer.api_key(), "test-key")
            run.assert_not_called()
        with patch.dict(os.environ, {"OPEN_SUNSAMA_API_KEY": ""}), \
                patch("sunsama_timer.subprocess.run", return_value=Mock(returncode=0, stdout="key\n")) as run:
            self.assertEqual(sunsama_timer.api_key(), "key")
            self.assertIn("sketchybar-open-sunsama", run.call_args.args[0])

    def test_authenticated_get_and_redirects_are_disabled(self):
        opener = Mock()
        opener.open.return_value.__enter__ = Mock(return_value=io.StringIO(json.dumps(response())))
        opener.open.return_value.__exit__ = Mock(return_value=False)
        with patch("sunsama_timer.api_key", return_value="test-key"), \
                patch("sunsama_timer.build_opener", return_value=opener) as build:
            self.assertTrue(display(sunsama_timer.current_snapshot())["running"])
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, sunsama_timer.ENDPOINT)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("X-api-key"), "test-key")
        self.assertIsInstance(build.call_args.args[0], sunsama_timer.NoRedirect)
        self.assertIsNone(sunsama_timer.NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere"))

    def test_fetch_or_keychain_failure_hides_timer_without_exposing_secrets(self):
        for error in (OSError("secret"), ValueError("secret"), subprocess.TimeoutExpired("security", 5)):
            with self.subTest(error=error), \
                    patch("sunsama_timer.current_snapshot", side_effect=error), \
                    patch("sunsama_timer.update_bar") as update, \
                    patch("sys.stderr", new_callable=io.StringIO) as stderr:
                sunsama_timer.render(display(sunsama_timer.read_snapshot()))
                self.assertEqual(update.call_args.args[0], {"running": False})
                self.assertNotIn("secret", stderr.getvalue())

    def test_success_uses_shared_style_with_sunsama_click_target(self):
        with patch("ellie_timer.subprocess.run") as run, \
                patch.dict(os.environ, {"OPEN_SUNSAMA_APP_URL": "https://sunsama.andlee.dev"}):
            sunsama_timer.render(display(sunsama_timer.snapshot(response())))
            command = run.call_args.args[0]
            self.assertEqual(command.count("icon.color=0xfffbbf24"), 2)
            self.assertEqual(command.count("label.color=0xfff5deb3"), 2)
            self.assertEqual(command.count("click_script=open https://sunsama.andlee.dev"), 2)
            self.assertIn("timer", command)
            self.assertIn("timer.notch", command)
            self.assertNotIn("weather", command)

    def test_seconds_tick_immediately_and_continue_during_slow_api_request(self):
        watcher = sunsama_timer.TimerWatcher(123)
        slow_request = threading.Event()
        release = threading.Event()
        rendered = []
        started_at = time.time() - 10
        payload = response(timerStartedAt=sunsama_timer.datetime.fromtimestamp(
            started_at, sunsama_timer.datetime.now().astimezone().tzinfo).isoformat())
        state = sunsama_timer.snapshot(payload)
        requests = []

        def fetch():
            requests.append(time.monotonic())
            if len(requests) > 1:
                slow_request.set()
                release.wait(5)
            return state

        def render(result):
            if result["running"]:
                rendered.append((time.monotonic(), result["label"].split(" ", 1)[0]))

        with patch("sunsama_timer.alive", return_value=True), \
                patch.object(watcher, "controller_active", return_value=True), \
                patch("sunsama_timer.read_snapshot", side_effect=fetch), \
                patch("sunsama_timer.render", side_effect=render), \
                patch("sunsama_timer.POLL_INTERVAL", 0.1):
            thread = threading.Thread(target=watcher.run)
            before = time.monotonic()
            thread.start()
            try:
                self.assertTrue(slow_request.wait(1))
                deadline = time.monotonic() + 3
                while len(rendered) < 3 and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertGreaterEqual(len(rendered), 3, rendered)
                self.assertLess(rendered[0][0] - before, 1)
                self.assertEqual(len({clock for _, clock in rendered[:3]}), 3)
                self.assertTrue(0.7 < rendered[2][0] - rendered[1][0] < 1.3)
            finally:
                watcher.stop()
                release.set()
                thread.join(2)
            self.assertFalse(thread.is_alive())

    def test_poll_schedule_and_stop(self):
        watcher = sunsama_timer.TimerWatcher(123)
        clock = Mock(side_effect=[10, 12, 12])
        with patch("sunsama_timer.time.monotonic", clock), \
                patch.object(watcher, "controller_active", return_value=True), \
                patch("sunsama_timer.read_snapshot", return_value={}), \
                patch.object(watcher.refresh, "wait", side_effect=lambda delay: watcher.stop()) as wait:
            watcher.poll()
        wait.assert_called_once_with(3)

    def test_removing_controller_stops_api_polling(self):
        watcher = sunsama_timer.TimerWatcher(123)
        with patch.object(watcher, "controller_active", return_value=False), \
                patch("sunsama_timer.read_snapshot") as fetch:
            watcher.poll()
        fetch.assert_not_called()
        self.assertTrue(watcher.stopped.is_set())

    def test_stale_sample_and_stopped_task_hide_timer(self):
        for state, age in ((sunsama_timer.snapshot(response()), 16), ({}, 0)):
            with self.subTest(state=state, age=age):
                watcher = sunsama_timer.TimerWatcher(123)
                watcher.results.put((state, time.monotonic() - age))
                with patch("sunsama_timer.alive", return_value=True), \
                        patch.object(watcher, "poll"), \
                        patch("sunsama_timer.render", side_effect=lambda result: watcher.stop()) as render:
                    watcher.run()
                render.assert_called_once_with({"running": False})

    def test_parent_exit_stops_watcher(self):
        watcher = sunsama_timer.TimerWatcher(123)
        with patch("sunsama_timer.alive", return_value=False), patch.object(watcher, "poll"):
            watcher.run()
        self.assertTrue(watcher.stopped.is_set())


if __name__ == "__main__":
    unittest.main()
