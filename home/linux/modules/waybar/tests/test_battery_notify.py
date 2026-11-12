"""Actual event helper with fake notification/player commands; no battery or audio access."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/battery-notify.sh"
MOCK = """import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
with open(os.environ['CALL_LOG'], 'a') as log:
    log.write(json.dumps([name, *sys.argv[1:]]) + '\\n')
sys.exit(int(os.environ.get(name.upper() + '_STATUS', '0')))
"""


class BatteryNotifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="battery-notify-", dir="/tmp/opencode"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "calls.jsonl"
        self.commands = []
        for name in ("notify", "player", "close"):
            path = self.root / name
            path.write_text(f"#!{sys.executable}\n" + MOCK)
            path.chmod(0o700)
            self.commands.append(str(path))
        self.sound = str(self.root / "standard warning.oga")

    def invoke(self, *levels, **statuses):
        env = os.environ.copy()
        env.update(CALL_LOG=str(self.log), **statuses)
        result = subprocess.run(
            ["bash", str(SCRIPT), *self.commands[:2], self.sound, self.commands[2], *levels],
            env=env, capture_output=True, text=True, timeout=5,
        )
        calls = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return result, calls

    def check_event(self, level, urgency, title, body_fragment):
        result, calls = self.invoke(level)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "notify")
        self.assertIn("--app-name=Battery", calls[0])
        self.assertIn(f"--urgency={urgency}", calls[0])
        self.assertIn("--hint=boolean:suppress-sound:true", calls[0])
        self.assertIn("--expire-time=0" if level != "test" else "--expire-time=15000", calls[0])
        category = "device.power.test" if level == "test" else "device.power.low"
        self.assertIn(f"--category={category}", calls[0])
        self.assertIn(f"--hint=string:x-canonical-private-synchronous:{category}", calls[0])
        self.assertEqual(calls[0][-2], title)
        self.assertIn(body_fragment, calls[0][-1])
        self.assertEqual(calls[1], ["player", self.sound])

    def test_warning_popup_and_one_standard_sound(self):
        self.check_event("warning", "normal", "Low Battery", "Battery is low")

    def test_critical_popup_does_not_invoke_power_action(self):
        self.check_event("critical", "critical", "Very Low Battery", "immediately")

    def test_charging_only_closes_the_low_battery_category(self):
        result, calls = self.invoke("clear")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, [["close", "--app-name=Battery", "--category=device.power.low"]])

    def test_full_closes_warning_then_notifies_for_three_seconds_without_sound(self):
        result, calls = self.invoke("full")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls[0], ["close", "--app-name=Battery", "--category=device.power.low"])
        self.assertEqual(calls[1][0], "notify")
        self.assertIn("--expire-time=3000", calls[1])
        self.assertIn("--category=device.power.full", calls[1])
        self.assertEqual(len(calls), 2)

    def test_close_failure_is_not_hidden(self):
        result, calls = self.invoke("clear", CLOSE_STATUS="9")
        self.assertEqual(result.returncode, 9)
        self.assertEqual(len(calls), 1)

    def test_explicit_test_never_needs_fake_battery_state(self):
        self.check_event("test", "normal", "Battery notification test", "unchanged")

    def test_unknown_event_has_no_side_effects(self):
        result, calls = self.invoke("hibernate")
        self.assertEqual(result.returncode, 64)
        self.assertEqual(calls, [])

    def test_missing_event_has_no_side_effects(self):
        result, calls = self.invoke()
        self.assertEqual(result.returncode, 64)
        self.assertEqual(calls, [])

    def test_notification_failure_still_plays_sound_and_remains_an_error(self):
        result, calls = self.invoke("warning", NOTIFY_STATUS="7")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(calls[-1], ["player", self.sound])

    def test_audio_failure_is_not_hidden(self):
        result, calls = self.invoke("warning", PLAYER_STATUS="8")
        self.assertEqual(result.returncode, 8)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
