"""Network widget sampling and macOS counter parsing tests."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "network", Path(__file__).resolve().parents[2] / "plugins/network.py"
)
network = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(network)


class NetworkTests(unittest.TestCase):
    def baseline(self):
        return network.sample(None, "en0", 0, 0, 0)[0]

    def test_requires_three_seconds_and_formats_decimal_megabytes(self):
        state = self.baseline()
        for second in (1, 2, 3):
            state, label = network.sample(
                state, "en0", second * 2_000_000, second * 500_000, second
            )
            if second < 3:
                self.assertIsNone(label)
        self.assertEqual(label, "↓ 2.00 MB/s")

    def test_upload_alone_qualifies(self):
        state = self.baseline()
        for second in (1, 2, 3):
            state, label = network.sample(state, "en0", 0, second * 2_000_000, second)
        self.assertEqual(label, "↑ 2.00 MB/s")

    def test_background_traffic_never_qualifies(self):
        state = self.baseline()
        for second in range(1, 10):
            state, label = network.sample(
                state, "en0", second * 1_000_000, second * 999_999, second
            )
            self.assertIsNone(label)
            self.assertIsNone(state["down_since"])
            self.assertIsNone(state["up_since"])

    def test_idle_hides_and_restarts_sustained_window(self):
        state = self.baseline()
        for second in (1, 2, 3):
            state, _ = network.sample(state, "en0", second * 2_000_000, 0, second)
        state, label = network.sample(state, "en0", 6_000_000, 0, 4)
        self.assertEqual(label, "↓ 0.00 MB/s")
        state, label = network.sample(state, "en0", 8_000_000, 0, 5)
        self.assertEqual(label, "↓ 2.00 MB/s")
        self.assertEqual(state["down_since"], 4)

    def test_stays_visible_for_five_seconds_with_live_rates(self):
        state = self.baseline()
        for second in (1, 2, 3):
            state, label = network.sample(state, "en0", second * 2_000_000, 0, second)
        self.assertEqual(state["visible_since"], 3)
        for second in (4, 5, 6, 7):
            state, label = network.sample(state, "en0", 6_000_000, 0, second)
            self.assertEqual(label, "↓ 0.00 MB/s")
        state, label = network.sample(state, "en0", 6_000_000, 0, 8)
        self.assertIsNone(label)
        self.assertIsNone(state["visible_since"])
        for second in (9, 10, 11):
            state, label = network.sample(
                state, "en0", 6_000_000 + (second - 8) * 2_000_000, 0, second
            )
            if second < 11:
                self.assertIsNone(label)
        self.assertEqual(state["visible_since"], 11)
        self.assertEqual(label, "↓ 2.00 MB/s")

    def test_activity_after_minimum_does_not_extend_hold(self):
        state = self.baseline()
        for second in range(1, 10):
            state, label = network.sample(state, "en0", second * 2_000_000, 0, second)
        self.assertEqual(label, "↓ 2.00 MB/s")
        state, label = network.sample(state, "en0", 18_000_000, 0, 10)
        self.assertIsNone(label)

    def test_interface_changes_counter_resets_and_gaps_reset(self):
        state, _ = network.sample(self.baseline(), "en0", 1_000_000, 0, 1)
        for interface, received, now in (
            ("en1", 10_000_000, 2),
            ("en0", 0, 2),
            ("en0", 10_000_000, 10),
            ("en0", 10_000_000, 1),
        ):
            with self.subTest(interface=interface, received=received, now=now):
                new, label = network.sample(state, interface, received, 0, now)
                self.assertIsNone(label)
                self.assertIsNone(new["down_since"])
                self.assertIsNone(new["up_since"])

    def test_uses_elapsed_time_not_sample_count(self):
        state = self.baseline()
        for now in (0.8, 1.6, 2.4, 3.2):
            state, label = network.sample(state, "en0", int(now * 2_000_000), 0, now)
            if now < 3:
                self.assertIsNone(label)
        self.assertEqual(label, "↓ 2.00 MB/s")

    def test_directions_qualify_independently_and_hide_independently(self):
        state = self.baseline()
        for second in range(1, 6):
            state, label = network.sample(
                state, "en0", second * 2_000_000,
                max(0, second - 2) * 3_000_000, second
            )
            if second in (3, 4):
                self.assertEqual(label, "↓ 2.00 MB/s")
        self.assertEqual(label, "↓ 2.00 MB/s  ↑ 3.00 MB/s")
        state, label = network.sample(state, "en0", 10_000_000, 12_000_000, 6)
        self.assertEqual(label, "↑ 3.00 MB/s")
        state, label = network.sample(state, "en0", 12_000_000, 15_000_000, 7)
        self.assertEqual(label, "↑ 3.00 MB/s")

    def test_link_rows_with_and_without_mac_address(self):
        for interface, address in (("en0", "aa:bb:cc:dd:ee:ff"), ("utun0", "")):
            with self.subTest(interface=interface), patch.object(
                network.subprocess, "check_output",
                side_effect=[
                    f"   interface: {interface}\n",
                    f"{interface} 1500 <Link#1> {address} 10 0 123456 20 0 654321 0\n"
                    f"{interface} 1500 192.168.1 192.168.1.2 10 - 123456 20 - 654321 -\n",
                ],
            ):
                self.assertEqual(network.read_counters(), (interface, 123456, 654321))


if __name__ == "__main__":
    unittest.main()
