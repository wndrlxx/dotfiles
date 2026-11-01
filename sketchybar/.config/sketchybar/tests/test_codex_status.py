import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins"))
from codex_status import Renderer, groups, receive_events


def agent(pane, state, kind="codex", title="Task"):
    return {"pane_id": pane, "agent_status": state, "agent": kind, "terminal_title_stripped": title}


class CodexStatusTests(unittest.TestCase):
    def test_extra_usage_gap_follows_nearest_visible_status(self):
        with patch("codex_status.subprocess.run") as run:
            renderer = Renderer()
            for working, nearest in ((True, "working"), (False, "waiting")):
                data = [agent("p1", "working" if working else "idle"),
                        agent("p2", "blocked"), agent("p3", "done")]
                renderer.render(data)
                command = run.call_args.args[0]
                for state in ("working", "waiting", "done"):
                    index = command.index(f"codex_state.{state}")
                    self.assertEqual(command[index + 2], f"padding_right={10 if state == nearest else 6}")

    def test_split_event_frames_and_server_disconnect(self):
        connection = Mock()
        connection.recv.side_effect = [b'{"event":"pane.agent_', b'status_changed","data":{}}\n', b'']
        buffer, changed = receive_events(connection, b'')
        self.assertFalse(changed)
        buffer, changed = receive_events(connection, buffer)
        self.assertTrue(changed)
        self.assertEqual(buffer, b'')
        with self.assertRaises(ConnectionError):
            receive_events(connection, buffer)

    def test_only_codex_working_blocked_and_done_are_visible(self):
        data = [agent("p1", "working"), agent("p2", "blocked"), agent("p3", "done"),
                agent("p4", "idle"), agent("p5", "unknown"), agent("p6", "working", "claude")]
        self.assertEqual(groups(data), {"working": [("p1", "Task")],
                                       "waiting": [("p2", "Task")], "done": [("p3", "Task")]})

    def test_counts_and_popup_titles_follow_agent_state(self):
        with patch("codex_status.subprocess.run") as run:
            renderer = Renderer()
            renderer.render([agent("p1", "working", title='Study "$HOME"'), agent("p2", "working")])
            command = run.call_args.args[0]
            self.assertIn("label=Working: 2", command)
            self.assertIn('label=Study "$HOME"', command)
            self.assertIn("popup.codex_state.working", command)
            renderer.render([agent("p1", "idle"), agent("p2", "idle")])
            command = run.call_args.args[0]
            self.assertEqual(command.count("drawing=off"), 3)
            self.assertEqual(command.count("popup.drawing=off"), 3)

    def test_unchanged_status_does_not_update_bar_but_reload_does(self):
        with patch("codex_status.subprocess.run") as run:
            renderer = Renderer()
            renderer.render([agent("p1", "working")])
            renderer.render([agent("p1", "working")])
            self.assertEqual(run.call_count, 1)
            renderer.render([agent("p1", "working")], force=True)
            self.assertEqual(run.call_count, 2)

    def test_done_becomes_hidden_when_herdr_marks_it_idle(self):
        with patch("codex_status.subprocess.run") as run:
            renderer = Renderer()
            renderer.render([agent("p1", "done")])
            self.assertIn("label=Done: 1", run.call_args.args[0])
            renderer.render([agent("p1", "idle")])
            command = run.call_args.args[0]
            offset = command.index("codex_state.done")
            self.assertEqual(command[offset + 1], "drawing=off")


if __name__ == "__main__":
    unittest.main()
