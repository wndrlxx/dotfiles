"""Run with: python3 -B -m unittest discover -s .config/sketchybar/tests -v"""

import copy
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins"))
import ellie_timer
from ellie_storage import FormatError, V8Reader, database_entries, live_files, log_records, snappy, table_entries
from ellie_timer import cached_snapshot, display, snapshot, update_bar


def uint(number):
    result = bytearray()
    while number >= 128:
        result.append((number & 127) | 128)
        number >>= 7
    result.append(number)
    return bytes(result)


def blob(value):
    return uint(len(value)) + value


def log(payload, kind=1):
    return struct.pack("<IHB", 1, len(payload), kind) + payload


def table(rows):
    def block(items):
        body = b"".join(b"\0" + uint(len(k)) + uint(len(v)) + k + v for k, v in items)
        return body + struct.pack("<II", 0, 1)

    data = block(rows)
    index = block([(b"last", uint(0) + uint(len(data)))])
    handle = b"\0\0" + uint(len(data) + 5) + uint(len(index))
    return (data + b"\0" * 5 + index + b"\0" * 5
            + handle.ljust(40, b"\0") + bytes.fromhex("57fb808b247547db"))


def typed(value):
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {k: typed(v) for k, v in value.items()}}}
    return {"stringValue": value}


def records(timer=None):
    timer = timer or {"active": True, "task_id": "task", "type": "stopwatch",
                      "time_accumulated": 10, "last_start_time": "2026-01-01T00:00:00Z"}
    return [
        (1, {"fbase_key": "firebase:authUser:example", "value": {"uid": "user"}}),
        (2, {"collectionGroup": "users", "documentId": "user", "prefixPath": [],
             "readTime": [100, 0], "document": {"fields": {
                 "active_timer": typed(timer), "api_key": typed("must-not-be-cached")}}}),
        (3, {"collectionGroup": "tasks", "documentId": "task", "prefixPath": ["users", "user"],
             "readTime": [100, 0], "document": {"fields": {"description": typed("Example task")}}}),
    ]


class StorageTests(unittest.TestCase):
    def test_fragmented_log_and_incomplete_tail(self):
        first = log(b"a" * (32768 - 7), 2)
        data = first + log(b"second", 4) + log(b"truncated")[:-3]
        self.assertEqual(list(log_records(data)), [b"a" * (32768 - 7) + b"second"])

    def test_snappy_overlapping_copy_and_invalid_reference(self):
        self.assertEqual(snappy(b"\x06\x00a\x12\x01\x00"), b"aaaaaa")
        with self.assertRaises(FormatError):
            snappy(b"\x06\x12\x01\x00")

    def test_table_reader(self):
        rows = [(b"key1", b"value1"), (b"key2", b"value2")]
        self.assertEqual(list(table_entries(table(rows))), rows)

    def test_manifest_compaction_and_wal_tombstone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "CURRENT").write_text("MANIFEST-000001\n")
            # Add old table 2, compact into 3, and advance WAL to 4.
            add = lambda n: b"\x07\0" + uint(n) + uint(20) + blob(b"first") + blob(b"last")
            edit = add(2) + b"\x06\0\x02" + add(3) + b"\x02\x04"
            (root / "MANIFEST-000001").write_bytes(log(edit))
            key = lambda k, seq: k + struct.pack("<Q", (seq << 8) | 1)
            (root / "000002.ldb").write_bytes(table([(key(b"obsolete", 1), b"stale")]))
            (root / "000003.ldb").write_bytes(table([(key(b"timer", 2), b"running")]))
            batch = struct.pack("<QI", 3, 2) + b"\0" + blob(b"timer") + b"\x01" + blob(b"keep") + blob(b"new")
            (root / "000004.log").write_bytes(log(batch))
            (root / "000001.log").write_bytes(log(struct.pack("<QI", 1, 1) + b"\x01" + blob(b"old") + blob(b"old")))
            self.assertEqual([p.name for p in live_files(root)], ["000003.ldb", "000004.log"])
            self.assertEqual(database_entries(root), [(4, b"new")])

    def test_v8_fixture_from_node(self):
        # Node v8.serialize({active: true, title: 'Study', readTime: [10, 20]}).
        data = bytes.fromhex("ff0f6f22066163746976655422057469746c652205537475647922087265616454696d654102491449282400027b03")
        self.assertEqual(V8Reader(data).value(), {"active": True, "title": "Study", "readTime": [10, 20]})
        self.assertEqual(V8Reader(data.replace(b"\xff\x0f", b"\xff\x10", 1)).value()["title"], "Study")


class TimerTests(unittest.TestCase):
    def test_app_state_uses_watcher_without_starting_a_process(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch("ellie_timer.tempfile.gettempdir", return_value=directory), \
                patch("ellie_timer.subprocess.run") as run:
            state_path = ellie_timer.cache_directory() / "app.json"
            state_path.write_text(json.dumps({"watcher_pid": os.getpid(), "running": True}))
            self.assertTrue(ellie_timer.ellie_running())
            state_path.write_text(json.dumps({"watcher_pid": os.getpid(), "running": False}))
            self.assertFalse(ellie_timer.ellie_running())
            with patch("ellie_timer.os.kill", side_effect=ProcessLookupError):
                self.assertFalse(ellie_timer.ellie_running())
            run.assert_not_called()

    def test_closed_app_does_not_read_database(self):
        with patch("sys.argv", ["ellie_timer.py"]), \
                patch("ellie_timer.ellie_running", return_value=False), \
                patch("ellie_timer.current_snapshot") as read, \
                patch("ellie_timer.publish_tick") as publish, \
                patch("ellie_timer.update_bar") as update:
            ellie_timer.main()
            read.assert_not_called()
            update.assert_called_once_with({"running": False})
            publish.assert_called_once_with({"running": False})

    def test_display_does_not_wait_for_slow_database_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "db"
            database.mkdir()
            wal = database / "000001.log"
            wal.write_bytes(b"initial")
            with patch("ellie_timer.tempfile.gettempdir", return_value=directory), \
                    patch("ellie_timer.firestore_records", return_value=records()):
                expected = cached_snapshot(database)
                wal.write_bytes(b"changed")
                with patch("ellie_timer.cached_snapshot", side_effect=AssertionError("Refresh blocked the clock")), \
                        patch("ellie_timer.subprocess.Popen") as worker:
                    self.assertEqual(ellie_timer.current_snapshot(database), expected)
                    worker.assert_called_once()

    def test_refresh_grace_starts_at_change_and_failed_refresh_expires(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "db"
            database.mkdir()
            wal = database / "000001.log"
            wal.write_bytes(b"initial")
            with patch("ellie_timer.tempfile.gettempdir", return_value=directory), \
                    patch("ellie_timer.firestore_records", return_value=records()), \
                    patch("ellie_timer.time.time", return_value=1000):
                expected = cached_snapshot(database)
                wal.write_bytes(b"changed")
                with patch("ellie_timer.subprocess.Popen"), patch("ellie_timer.time.time", return_value=10000):
                    self.assertEqual(ellie_timer.current_snapshot(database), expected)
                with patch("ellie_timer.subprocess.Popen"), patch("ellie_timer.time.time", return_value=10004):
                    self.assertEqual(ellie_timer.current_snapshot(database), {})

    def test_only_non_notched_clock_and_date_move_right_while_timer_runs(self):
        for running in (True, False):
            with self.subTest(running=running), patch("ellie_timer.subprocess.run") as run:
                run.return_value = Mock(stdout='{"icon":{"value":"☀"},"label":{"value":"12°C"}}')
                update_bar({"running": running, "icon": "⏱", "label": "01:23 Study"})
                command = run.call_args.args[0]
                for name in ("clock", "date", "clock.notch", "date.notch"):
                    offset = command.index(name)
                    expected = "q" if name.endswith(".notch") else ("right" if running else "center")
                    self.assertEqual(command[offset + 1], f"position={expected}")
                    padding = 0
                    self.assertEqual(command[offset + 2], f"padding_left={padding}")
                    left = 7 if name.endswith(".notch") else 0
                    right = 0 if name.endswith(".notch") else 4
                    self.assertEqual(command[offset + 3], f"label.padding_left={left}")
                    self.assertEqual(command[offset + 4], f"label.padding_right={right}")

    def test_timer_replaces_both_weather_slots_without_changing_layout(self):
        with patch("ellie_timer.subprocess.run") as run:
            update_bar({"running": True, "icon": "⏱", "label": "01:23 Study"})
        command = run.call_args.args[0]
        self.assertEqual(command.count("label=Study"), 2)
        self.assertEqual(command.count("icon=⏱ 01:23"), 2)
        self.assertEqual(command.count("icon.background.drawing=on"), 2)
        self.assertEqual(command.count("icon.color=0xfffbbf24"), 2)
        self.assertEqual(command.count("label.color=0xfff5deb3"), 2)
        self.assertIn("weather", command)
        self.assertIn("weather.notch", command)
        self.assertEqual(command.count("click_script=open -a Ellie"), 2)
        self.assertFalse(any(arg.startswith(("drawing=", "display=")) for arg in command))

    def test_stop_restores_current_weather_and_clears_timer_click(self):
        with patch("ellie_timer.subprocess.run") as run:
            run.return_value = Mock(stdout='{"icon":{"value":"☀"},"label":{"value":"12°C"}}')
            update_bar({"running": False})
        self.assertEqual(run.call_args_list[0].args[0], ["sketchybar", "--query", "weather_data"])
        command = run.call_args.args[0]
        self.assertEqual(command.count("label=12°C"), 2)
        self.assertEqual(command.count("click_script="), 2)
        self.assertEqual(command.count("icon.background.drawing=off"), 2)
        self.assertEqual(command.count("icon.color=0xffffffff"), 2)
        self.assertEqual(command.count("icon.padding_left=0"), 2)
        self.assertIn("label.padding_left=4", command)

    def test_running_timer_and_no_credentials_in_snapshot(self):
        state = snapshot(records())
        self.assertEqual(display(state, 1767225665)["label"], "01:15 Example task")
        self.assertNotIn("must-not-be-cached", str(state))
        self.assertNotIn("api_key", str(state))

    def test_pending_pause_and_stop_override_server_cache(self):
        for value in ({"active": False}, None):
            with self.subTest(value=value):
                data = records()
                data.append((4, {"overlayMutation": {
                    "update": {"name": "projects/p/databases/d/documents/users/user",
                               "fields": {"active_timer": typed(value)}},
                    "updateMask": {"fieldPaths": ["active_timer"]}}}))
                self.assertEqual(display(snapshot(data)), {"running": False})

    def test_nested_pause_patch_and_unrelated_account(self):
        data = records()
        data.append((4, {"overlayMutation": {
            "update": {"name": "projects/p/databases/d/documents/users/user",
                       "fields": {"active_timer": typed({"active": False})}},
            "updateMask": {"fieldPaths": ["active_timer.active"]}}}))
        self.assertEqual(snapshot(data), {})
        data[-1][1]["overlayMutation"]["update"]["name"] += "-other"
        self.assertTrue(display(snapshot(data))["running"])

    def test_no_signed_in_user_hides_old_timer(self):
        self.assertEqual(snapshot(records()[1:]), {})

    def test_countdown_and_pomodoro_do_not_go_negative(self):
        state = snapshot(records({"active": True, "type": "timer", "task_id": "task",
                                  "focus_time_left": 90, "last_start_time": "2026-01-01T00:00:00Z"}))
        self.assertEqual(display(state, 1767225665)["label"], "00:25 Example task")
        self.assertTrue(display(state, 1767225800)["label"].startswith("00:00"))
        state.update(kind="pomodoro", timer={"active": True, "phase": "short_break",
                                            "phase_started_at": "2026-01-01T00:00:00Z", "phase_time_left": 90})
        result = display(state, 1767225665)
        self.assertEqual(result["icon"], "☕")
        self.assertEqual(result["label"], "00:25 Example task")
        self.assertEqual(result["tick"]["direction"], -1)

    def test_native_tick_anchor_preserves_fractional_start(self):
        result = display(snapshot(records()), 1767225665.75)
        self.assertEqual(result["tick"]["seconds"], 75)
        self.assertEqual(result["tick"]["direction"], 1)
        self.assertEqual(result["tick"]["reference_time"], 1767225665)
        self.assertEqual(result["tick"]["sampled_at"], 1767225665.75)

    def test_tick_handoff_clears_on_stop(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch("ellie_timer.tempfile.gettempdir", return_value=directory):
            result = display(snapshot(records()), 1767225665.75)
            ellie_timer.publish_tick(result)
            path = ellie_timer.cache_directory() / "tick.json"
            self.assertEqual(json.loads(path.read_text()), result["tick"])
            ellie_timer.publish_tick({"running": False})
            self.assertEqual(json.loads(path.read_text()), {"running": False})

    def test_latest_document_wins_and_html_title_is_cleaned(self):
        data = records()
        newer = copy.deepcopy(data[1][1])
        newer["readTime"] = [101, 0]
        newer["document"]["fields"]["active_timer"] = typed(None)
        data.insert(0, (10, newer))
        self.assertEqual(snapshot(data), {})
        data = records()
        data[2][1]["document"]["fields"]["description"] = typed("<b>Study</b> &amp;\n practice")
        self.assertEqual(snapshot(data)["title"], "Study & practice")

    def test_cache_invalidates_when_database_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "db").mkdir()
            log_path = root / "db/000001.log"
            log_path.write_bytes(b"start")
            with patch("ellie_timer.tempfile.gettempdir", return_value=directory), \
                    patch("ellie_timer.firestore_records", return_value=records()) as read:
                first = cached_snapshot(root / "db")
                self.assertEqual(cached_snapshot(root / "db"), first)
                self.assertEqual(read.call_count, 1)
                log_path.write_bytes(b"stop")
                read.return_value = records()[1:]
                self.assertEqual(cached_snapshot(root / "db"), {})
                self.assertEqual(read.call_count, 2)


if __name__ == "__main__":
    unittest.main()
