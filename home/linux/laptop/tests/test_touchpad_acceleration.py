"""Check saved curve declarations and math, not hardware or application gestures."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEVICE = "gxtp5100:00-27c6:01e7-touchpad"
DPI = int(31 * 25.4)
BASELINE = 0.9 * 0.2968 * 1000 / DPI


def expected_gain(speed):
    if speed <= 16:
        physical_speed = speed * 31 * 25.4 / DPI
        factor = min(0.9, 0.1 * physical_speed + 0.3)
        return factor * 0.2968 * 1000 / DPI
    t = min(1.0, (speed - 16) / 74)
    return BASELINE + (1.4 - BASELINE) * t * t * (3 - 2 * t)


class TouchpadAccelerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = (ROOT / "hyprland.conf").read_text()
        blocks = re.findall(r"(?m)^device\s*\{([^{}]*)\}", cls.config)
        matches = [
            block
            for block in blocks
            if re.search(rf"(?m)^\s*name\s*=\s*{re.escape(DEVICE)}\s*$", block)
        ]
        if len(matches) != 1:
            raise AssertionError("Expected exactly one Lenovo touchpad block")
        cls.block = matches[0]
        motion = re.search(
            r"(?m)^\s*accel_profile\s*=\s*custom\s+([^\n]+)$", cls.block
        )
        cls.step, *cls.points = map(float, motion[1].split())

    def test_scope_is_only_lenovo_touchpad(self):
        self.assertEqual(self.config.count("accel_profile = custom"), 1)
        self.assertIn("accel_profile = adaptive", self.config)
        self.assertIn("enabled = true", self.block)
        for host in ("laptop-old", "desktop"):
            other = (ROOT.parent / host / "hyprland.conf").read_text()
            self.assertNotIn("accel_profile = custom", other)

    def test_samples_match_accepted_physical_speed_contract(self):
        self.assertEqual(self.step, 0.062)
        self.assertEqual(len(self.points), 64)
        for i, point in enumerate(self.points):
            self.assertAlmostEqual(point, i * self.step * expected_gain(i * 2), places=7)
        self.assertEqual(self.points[0], 0)
        self.assertTrue(all(a < b for a, b in zip(self.points, self.points[1:])))

    def test_fast_motion_and_extrapolation_keep_constant_gain(self):
        for i in range(45, len(self.points)):
            self.assertAlmostEqual(self.points[i] / (i * self.step), 1.4, places=7)
        slope = (self.points[-1] - self.points[-2]) / self.step
        intercept = self.points[-1] - slope * (len(self.points) - 1) * self.step
        self.assertAlmostEqual(slope, 1.4, places=7)
        self.assertAlmostEqual(intercept, 0, places=7)

    def test_two_finger_scroll_preserves_stock_constant_gain(self):
        scroll = re.search(r"(?m)^\s*scroll_points\s*=\s*([^\n]+)$", self.block)
        step, zero, output = map(float, scroll[1].split())
        self.assertEqual(zero, 0)
        self.assertGreater(step, 0)
        self.assertAlmostEqual(output / step, BASELINE, places=7)


if __name__ == "__main__":
    unittest.main()
