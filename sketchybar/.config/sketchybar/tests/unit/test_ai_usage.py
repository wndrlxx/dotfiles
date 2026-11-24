"""Unified AI usage (Codex + Gemini + Claude/Antigravity) plugin and hook tests."""

import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, PLUGINS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ai_usage = _load_module("ai_usage", "ai_usage.py")
agy_hook = _load_module("agy_usage_hook", "agy_usage_hook.py")


def _decode_png(path):
    raw = Path(path).read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    offset = 8
    width = height = 0
    idat = bytearray()
    while offset < len(raw):
        length = struct.unpack("!I", raw[offset:offset + 4])[0]
        kind = raw[offset + 4:offset + 8]
        data = raw[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height = struct.unpack("!2I", data[:8])
        elif kind == b"IDAT":
            idat.extend(data)
    decompressed = zlib.decompress(bytes(idat))
    stride = width * 4 + 1
    pixels = bytearray()
    for y in range(height):
        row = decompressed[y * stride:(y + 1) * stride]
        assert row[0] == 0
        pixels.extend(row[1:])
    return width, height, bytes(pixels)


def _pixel_at(pixels, width, x, y):
    idx = (y * width + x) * 4
    return tuple(pixels[idx:idx + 4])


class AiUsageTests(unittest.TestCase):
    def test_codex_remaining_clamps_and_handles_invalid_values(self):
        self.assertEqual(ai_usage.codex_remaining({"usedPercent": 25}), 75.0)
        self.assertEqual(ai_usage.codex_remaining({"usedPercent": 150}), 0.0)
        self.assertEqual(ai_usage.codex_remaining({"usedPercent": -10}), 100.0)
        self.assertIsNone(ai_usage.codex_remaining({"usedPercent": float("nan")}))
        self.assertIsNone(ai_usage.codex_remaining(None))

    def test_bar_fill_color_applies_low_quota_thresholds(self):
        self.assertEqual(ai_usage.bar_fill_color(80.0, ai_usage.CODEX_COLOR), ai_usage.CODEX_COLOR)
        self.assertEqual(ai_usage.bar_fill_color(80.0, ai_usage.GEMINI_COLOR), ai_usage.GEMINI_COLOR)
        self.assertEqual(ai_usage.bar_fill_color(80.0, ai_usage.CLAUDE_COLOR), ai_usage.CLAUDE_COLOR)
        self.assertEqual(ai_usage.bar_fill_color(24.9, ai_usage.CODEX_COLOR), ai_usage.WARN_AMBER)
        self.assertEqual(ai_usage.bar_fill_color(10.0, ai_usage.CLAUDE_COLOR), ai_usage.WARN_AMBER)
        self.assertEqual(ai_usage.bar_fill_color(9.9, ai_usage.GEMINI_COLOR), ai_usage.WARN_CORAL)
        self.assertEqual(ai_usage.bar_fill_color(0.0, ai_usage.CODEX_COLOR), ai_usage.WARN_CORAL)

    def test_enabled_and_active_providers_auto_collapse(self):
        self.assertEqual(ai_usage.enabled_providers("auto"), ["codex", "gemini", "claude"])
        self.assertEqual(ai_usage.enabled_providers("gemini,claude"), ["gemini", "claude"])
        self.assertEqual(ai_usage.enabled_providers("gemini"), ["gemini"])

        g_buckets = [{"id": "gemini-weekly", "remaining": 80.0}]
        c_buckets = [{"id": "3p-weekly", "remaining": 100.0}]
        self.assertEqual(
            ai_usage.active_providers(["codex", "gemini", "claude"], [80.0, 90.0], g_buckets, c_buckets),
            ["codex", "gemini", "claude"],
        )
        self.assertEqual(
            ai_usage.active_providers(["codex", "gemini", "claude"], [None, None], g_buckets, c_buckets),
            ["gemini", "claude"],
        )
        self.assertEqual(
            ai_usage.active_providers(["codex", "gemini", "claude"], [None, None], g_buckets, []),
            ["gemini"],
        )
        self.assertEqual(
            ai_usage.active_providers(["codex", "gemini", "claude"], [80.0, None], [], []),
            ["codex"],
        )
        self.assertEqual(
            ai_usage.active_providers(["codex", "gemini", "claude"], [None, None], [], []),
            ["codex", "gemini"],
        )

    def test_parse_agy_snapshot_splits_gemini_and_claude_buckets(self):
        now = 1_700_000_000.0
        snapshot = {
            "plan_tier": "Google AI Pro",
            "captured_at": now - 30,
            "quota": {
                "3p-weekly": {
                    "remaining_fraction": 1.0,
                    "reset_time": "2023-11-20T00:00:00Z",
                },
                "3p-5h": {
                    "remaining_fraction": 0.95,
                    "reset_in_seconds": 18000,
                },
                "gemini-weekly": {
                    "remaining_fraction": 0.9378,
                    "reset_time": "2023-11-20T00:00:00Z",
                },
                "gemini-5h": {
                    "remaining_fraction": 0.62,
                    "reset_in_seconds": 7200,
                },
                "disabled-bucket": {
                    "remaining_fraction": 0.10,
                    "disabled": True,
                },
            },
        }
        parsed = ai_usage.parse_agy_snapshot(snapshot, now=now)
        self.assertEqual(parsed["plan_tier"], "Google AI Pro")
        self.assertEqual([b["id"] for b in parsed["gemini_buckets"]], ["gemini-5h", "gemini-weekly"])
        self.assertEqual([b["title"] for b in parsed["gemini_buckets"]], ["5-hour", "Weekly"])
        self.assertEqual([b["id"] for b in parsed["claude_buckets"]], ["3p-5h", "3p-weekly"])
        self.assertEqual([b["title"] for b in parsed["claude_buckets"]], ["5-hour", "Weekly"])
        self.assertAlmostEqual(parsed["gemini_buckets"][0]["remaining"], 62.0)
        self.assertAlmostEqual(parsed["claude_buckets"][0]["remaining"], 95.0)
        self.assertEqual(ai_usage.select_bar_values(parsed["gemini_buckets"]), [62.0, 93.78])
        self.assertEqual(ai_usage.select_bar_values(parsed["claude_buckets"]), [95.0, 100.0])

    def test_parse_agy_snapshot_marks_expired_windows(self):
        now = 1_800_000_000.0
        snapshot = {
            "captured_at": now - 3600,
            "quota": {
                "gemini-weekly": {
                    "remaining_fraction": 0.40,
                    "reset_time": "2026-01-01T00:00:00Z",
                }
            },
        }
        parsed = ai_usage.parse_agy_snapshot(snapshot, now=now)
        bucket = parsed["gemini_buckets"][0]
        self.assertTrue(bucket["expired"])
        self.assertIsNone(bucket["remaining"])
        self.assertEqual(
            ai_usage.describe_agy_bucket(bucket, now=now),
            "Weekly: reset · open agy to sync",
        )

    def test_draw_bars_renders_single_dual_and_triple_stacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            triple_path = Path(tmp) / "triple.png"
            width_pt = ai_usage.draw_bars(
                triple_path,
                {"codex": [80.0, 20.0], "gemini": [75.0, 90.0], "claude": [100.0, 8.0]},
                shown=["codex", "gemini", "claude"],
            )
            self.assertEqual(width_pt, 114)
            w, h, px = _decode_png(triple_path)
            self.assertEqual((w, h), (220, 32))
            self.assertEqual(_pixel_at(px, w, 4, 6), ai_usage.CODEX_COLOR)
            self.assertEqual(_pixel_at(px, w, 4, 22), ai_usage.WARN_AMBER)
            self.assertEqual(_pixel_at(px, w, 2 + 64 + 12 + 2, 6), ai_usage.GEMINI_COLOR)
            self.assertEqual(_pixel_at(px, w, 2 + 2 * (64 + 12) + 2, 6), ai_usage.CLAUDE_COLOR)
            self.assertEqual(_pixel_at(px, w, 2 + 2 * (64 + 12) + 2, 22), ai_usage.WARN_CORAL)

            dual_path = Path(tmp) / "dual.png"
            width_pt = ai_usage.draw_bars(
                dual_path,
                {"gemini": [75.0, 90.0], "claude": [100.0, 100.0]},
                shown=["gemini", "claude"],
            )
            self.assertEqual(width_pt, 88)
            w, h, px = _decode_png(dual_path)
            self.assertEqual((w, h), (168, 32))
            self.assertEqual(_pixel_at(px, w, 4, 6), ai_usage.GEMINI_COLOR)
            self.assertEqual(_pixel_at(px, w, 2 + 76 + 12 + 2, 6), ai_usage.CLAUDE_COLOR)

            single_path = Path(tmp) / "single.png"
            width_pt = ai_usage.draw_bars(
                single_path,
                {"gemini": [50.0]},
                shown=["gemini"],
            )
            self.assertEqual(width_pt, 48)
            w, h, px = _decode_png(single_path)
            self.assertEqual((w, h), (88, 32))
            self.assertEqual(_pixel_at(px, w, 4, 6), (0, 0, 0, 0))
            self.assertEqual(_pixel_at(px, w, 4, 15), ai_usage.GEMINI_COLOR)

    def test_update_auto_collapses_to_gemini_and_claude_when_codex_unavailable(self):
        now = 1_750_000_000.0
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            cache.mkdir(mode=0o700)
            ai_usage.write_json_atomic(cache / "gemini.json", {
                "plan_tier": "Google AI Pro",
                "captured_at": now - 5,
                "quota": {
                    "gemini-5h": {"remaining_fraction": 0.72, "reset_in_seconds": 3600},
                    "gemini-weekly": {"remaining_fraction": 0.91, "reset_in_seconds": 172800},
                    "3p-5h": {"remaining_fraction": 1.0, "reset_in_seconds": 18000},
                    "3p-weekly": {"remaining_fraction": 1.0, "reset_in_seconds": 604800},
                },
            })
            calls = []
            with patch.object(ai_usage, "read_codex_limits", side_effect=RuntimeError("No subscription")), \
                 patch.object(ai_usage, "run_sketchybar", side_effect=lambda *a, **kw: calls.append(a)):
                ai_usage.update(sender="routine", cache_dir=cache, now=now)

            self.assertEqual(len(calls), 1)
            joined = " ".join(calls[0])
            self.assertIn("width=88", joined)
            self.assertNotIn("label=Codex", joined)
            self.assertIn("label=Gemini · Google AI Pro", joined)
            self.assertIn("label=Claude · Google AI Pro", joined)
            self.assertIn("label.color=0xffd97757", joined)
            self.assertIn("label=5-hour: 72% left", joined)
            self.assertIn("label=5-hour: 100% left", joined)

    def test_update_gemini_event_uses_cached_codex_and_renders_three_stacks(self):
        now = 1_750_000_000.0
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            cache.mkdir(mode=0o700)
            ai_usage.write_json_atomic(cache / "codex.json", {
                "limits": {
                    "primary": {"usedPercent": 20, "resetsAt": now + 3600},
                    "secondary": {"usedPercent": 40, "resetsAt": now + 86400},
                },
                "error": None,
                "updated_at": now - 60,
            })
            ai_usage.write_json_atomic(cache / "gemini.json", {
                "plan_tier": "Google AI Pro",
                "captured_at": now - 5,
                "quota": {
                    "gemini-weekly": {"remaining_fraction": 0.85, "reset_in_seconds": 172800},
                    "3p-5h": {"remaining_fraction": 0.90, "reset_in_seconds": 10000},
                },
            })
            calls = []
            with patch.object(ai_usage, "read_codex_limits", side_effect=AssertionError("should not poll codex")), \
                 patch.object(ai_usage, "run_sketchybar", side_effect=lambda *a, **kw: calls.append(a)):
                ai_usage.update(sender="gemini_usage_updated", cache_dir=cache, now=now)

            joined = " ".join(calls[0])
            self.assertIn("width=114", joined)
            self.assertIn("label=Codex", joined)
            self.assertIn("label=Gemini · Google AI Pro", joined)
            self.assertIn("label=Claude · Google AI Pro", joined)

    def test_mouse_events_toggle_popup_only(self):
        calls = []
        with patch.object(ai_usage, "run_sketchybar", side_effect=lambda *a, **kw: calls.append(a)):
            ai_usage.update(sender="mouse.entered")
            ai_usage.update(sender="mouse.exited.global")
            ai_usage.update(sender="mouse.clicked")
        self.assertEqual(calls[0], ("--set", "ai_usage", "popup.drawing=on"))
        self.assertEqual(calls[1], ("--set", "ai_usage", "popup.drawing=off"))
        self.assertEqual(calls[2], ("--set", "ai_usage", "popup.drawing=toggle"))

    def test_subsequent_render_updates_popup_rows_in_place(self):
        now = 1_750_000_000.0
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            cache.mkdir(mode=0o700)
            ai_usage.write_json_atomic(cache / "gemini.json", {
                "plan_tier": "Google AI Pro",
                "captured_at": now - 5,
                "quota": {"gemini-5h": {"remaining_fraction": 0.80, "reset_in_seconds": 3600}},
            })
            calls = []
            with patch.object(ai_usage, "run_sketchybar", side_effect=lambda *a, **kw: calls.append(a)):
                ai_usage.update(sender="routine", cache_dir=cache, now=now, providers="gemini")
                ai_usage.update(sender="gemini_usage_updated", cache_dir=cache, now=now + 10, providers="gemini")

            self.assertIn("--remove", calls[0])
            self.assertIn("--add", calls[0])
            self.assertNotIn("--remove", calls[1])
            self.assertNotIn("--add", calls[1])
            self.assertNotIn("width=48", calls[1])


class AgyUsageHookTests(unittest.TestCase):
    def test_hook_caches_quota_and_deduplicates_triggers(self):
        payload = json.dumps({
            "plan_tier": "Pro",
            "quota": {
                "gemini-weekly": {
                    "remaining_fraction": 0.9378,
                    "reset_time": "2026-07-06T07:50:32Z",
                    "reset_in_seconds": 560580,
                }
            },
        })
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            with patch.object(agy_hook.subprocess, "run") as run_mock:
                triggered1 = agy_hook.process_payload(payload, cache_dir=cache, executable="/fake/sketchybar", now=1000.0)
                triggered2 = agy_hook.process_payload(payload, cache_dir=cache, executable="/fake/sketchybar", now=1005.0)
                triggered3 = agy_hook.process_payload(payload, cache_dir=cache, executable="/fake/sketchybar", now=1070.0)

            self.assertTrue(triggered1)
            self.assertFalse(triggered2)
            self.assertTrue(triggered3)
            self.assertEqual(run_mock.call_count, 2)
            cached = json.loads((cache / "gemini.json").read_text(encoding="utf-8"))
            self.assertEqual(cached["plan_tier"], "Pro")
            self.assertAlmostEqual(cached["quota"]["gemini-weekly"]["remaining_fraction"], 0.9378)

    def test_hook_does_not_starve_periodic_trigger_on_frequent_unchanged_updates(self):
        payload = json.dumps({
            "plan_tier": "Pro",
            "quota": {
                "gemini-weekly": {
                    "remaining_fraction": 0.9378,
                    "reset_time": "2026-07-06T07:50:32Z",
                }
            },
        })
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            with patch.object(agy_hook.subprocess, "run") as run_mock:
                results = [
                    agy_hook.process_payload(payload, cache_dir=cache, executable="/fake/sketchybar", now=ts)
                    for ts in (1000.0, 1020.0, 1040.0, 1060.0)
                ]
            self.assertEqual(results, [True, False, False, True])
            self.assertEqual(run_mock.call_count, 2)

    def test_write_json_atomic_handles_concurrent_writes(self):
        import concurrent.futures

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "gemini.json"

            def writer(idx):
                for step in range(10):
                    agy_hook.write_json_atomic(target, {"writer": idx, "step": step})

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(writer, i) for i in range(4)]
                for future in futures:
                    future.result()

            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn("writer", data)
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_hook_ignores_invalid_or_quota_free_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            self.assertFalse(agy_hook.process_payload("not-json", cache_dir=cache, executable="/fake/sketchybar"))
            self.assertFalse(agy_hook.process_payload('{"model": {}}', cache_dir=cache, executable="/fake/sketchybar"))
            self.assertFalse((cache / "gemini.json").exists())


if __name__ == "__main__":
    unittest.main()
