import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins"))
from agent_status import Renderer, groups, list_agents, receive_events, receive_rex


def agent(pane, state, kind="codex", title="Task"):
    return {"pane_id": pane, "agent_status": state, "agent": kind, "terminal_title_stripped": title}


class AgentStatusTests(unittest.TestCase):
    def test_extra_usage_gap_follows_nearest_visible_status(self):
        with patch("agent_status.subprocess.run") as run:
            renderer = Renderer()
            for working, nearest in ((True, "working"), (False, "waiting")):
                data = [agent("p1", "working" if working else "idle"),
                        agent("p2", "blocked"), agent("p3", "done")]
                renderer.render(data)
                command = run.call_args.args[0]
                for state in ("working", "waiting", "done"):
                    index = command.index(f"agent_state.{state}")
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

    def test_only_supported_agents_and_active_states_are_visible(self):
        data = [agent("p1", "working"), agent("p2", "blocked"), agent("p3", "done"),
                agent("p4", "idle"), agent("p5", "unknown"), agent("p6", "working", "claude"),
                agent("p7", "working", "pi"), agent("p8", "blocked", "pi"),
                agent("p9", "done", "pi"), agent("p10", "idle", "pi"), agent("p11", "unknown", "pi"),
                agent("p12", "working", "antigravity"), agent("p13", "blocked", "antigravity"),
                agent("p14", "done", "antigravity"), agent("p15", "error", "antigravity"),
                agent("p16", "idle", "antigravity")]
        self.assertEqual(groups(data), {"working": [("p1", "Task"), ("p12", "Task"), ("p7", "Task")],
                                       "waiting": [("p13", "Task"), ("p2", "Task"), ("p8", "Task")],
                                       "done": [("p14", "Task"), ("p3", "Task"), ("p9", "Task")],
                                       "error": [("p15", "Task")]})

    def test_rex_snapshots_replace_rows_after_complete_frames(self):
        row = dict(agent("rex:p1", "error", "pi"), source="Rex")
        agy_row = dict(agent("rex:p2", "working", "antigravity", title="sketchybar · Extend"), source="Rex")
        frame = json.dumps({"rex:p1": row, "rex:p2": agy_row}).encode()
        with patch("agent_status.os.read", side_effect=[frame[:10], frame[10:] + b"\n", b"{}\n", b""]):
            buffer, rows = receive_rex(3, b"", [])
            self.assertEqual(rows, [])
            buffer, rows = receive_rex(3, buffer, rows)
            grouped = groups(rows)
            self.assertEqual(grouped["error"], [("rex:p1", "Rex · Task")])
            self.assertEqual(grouped["working"], [("rex:p2", "Rex · sketchybar · Extend")])
            buffer, rows = receive_rex(3, buffer, rows)
            self.assertEqual((buffer, rows), (b"", []))
            with self.assertRaises(ConnectionError):
                receive_rex(3, buffer, rows)

    def test_snapshot_keeps_pi_panes_for_status_subscriptions(self):
        data = [agent("p1", "working"), agent("p2", "blocked", "pi"),
                agent("p3", "idle", "pi"), agent("p4", "working", "claude")]
        with patch("agent_status.request") as request:
            stream = request.return_value.__enter__.return_value.makefile.return_value.__enter__.return_value
            stream.readline.return_value = json.dumps({"result": {"agents": data}}).encode()
            self.assertEqual(list_agents("test.sock"), data[:3])
            request.assert_called_once_with("test.sock", "agent.list", {})

    def test_counts_and_popup_titles_follow_agent_state(self):
        with patch("agent_status.subprocess.run") as run:
            renderer = Renderer()
            renderer.render([agent("p1", "working", title='Study "$HOME"'),
                             agent("p2", "working", "pi", title="Pi task")])
            command = run.call_args.args[0]
            self.assertIn("label=Working: 2", command)
            self.assertIn('label=Study "$HOME"', command)
            self.assertIn("label=Pi task", command)
            self.assertIn("popup.agent_state.working", command)
            renderer.render([agent("p1", "idle"), agent("p2", "idle")])
            command = run.call_args.args[0]
            self.assertEqual(command.count("drawing=off"), 4)
            self.assertEqual(command.count("popup.drawing=off"), 4)

    def test_unchanged_status_does_not_update_bar_but_reload_does(self):
        with patch("agent_status.subprocess.run") as run:
            renderer = Renderer()
            renderer.render([agent("p1", "working")])
            renderer.render([agent("p1", "working")])
            self.assertEqual(run.call_count, 1)
            renderer.render([agent("p1", "working")], force=True)
            self.assertEqual(run.call_count, 2)

    def test_done_becomes_hidden_when_herdr_marks_it_idle(self):
        with patch("agent_status.subprocess.run") as run:
            renderer = Renderer()
            renderer.render([agent("p1", "done")])
            self.assertIn("label=Done: 1", run.call_args.args[0])
            renderer.render([agent("p1", "idle")])
            command = run.call_args.args[0]
            offset = command.index("agent_state.done")
            self.assertEqual(command[offset + 1], "drawing=off")


if __name__ == "__main__":
    unittest.main()
