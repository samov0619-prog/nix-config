"""Exact notification selection with mocked native Mako CLI replies."""

import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "notification_close", Path(__file__).resolve().parents[1] / "close.py"
)
close = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(close)


class CloseTests(unittest.TestCase):
    def invoke(self, notifications):
        with patch.object(close.subprocess, "run") as run:
            run.return_value.stdout = json.dumps(notifications)
            close.close("/fixture/makoctl", "Battery", "device.power.low")
            return [call.args[0] for call in run.call_args_list]

    def test_only_exact_app_and_category_are_closed(self):
        calls = self.invoke([
            {"id": 1, "app_name": "Battery", "category": "device.power.low"},
            {"id": 2, "app_name": "Battery", "category": "device.power.full"},
            {"id": 3, "app_name": "Other", "category": "device.power.low"},
            {"id": 4, "app_name": "Voice dictate", "category": "voice-dictate.recording.42"},
            {"id": 5, "app_name": "Battery", "category": "device.power.low"},
        ])
        self.assertEqual(calls, [
            ["/fixture/makoctl", "list", "-j"],
            ["/fixture/makoctl", "dismiss", "-n", "1"],
            ["/fixture/makoctl", "dismiss", "-n", "5"],
        ])

    def test_manual_dismissal_or_daemon_restart_needs_no_cached_ids(self):
        self.assertEqual(self.invoke([]), [["/fixture/makoctl", "list", "-j"]])

    def test_malformed_list_is_not_treated_as_a_match(self):
        for value in ({}, [None]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.invoke(value)

    def test_invalid_ids_are_never_passed_to_dismiss(self):
        for identifier in (None, True, 0, -1, "1", 0x100000000):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                self.invoke([{"id": identifier, "app_name": "Battery", "category": "device.power.low"}])

    def test_list_failure_is_not_hidden(self):
        with patch.object(close.subprocess, "run", side_effect=subprocess.TimeoutExpired("makoctl", 5)):
            with self.assertRaises(subprocess.TimeoutExpired):
                close.close("makoctl", "Battery", "device.power.low")

    def test_dismiss_failure_is_not_hidden(self):
        listed = subprocess.CompletedProcess([], 0, json.dumps([
            {"id": 1, "app_name": "Battery", "category": "device.power.low"}
        ]))
        with patch.object(close.subprocess, "run", side_effect=[listed, subprocess.CalledProcessError(1, "makoctl")]):
            with self.assertRaises(subprocess.CalledProcessError):
                close.close("makoctl", "Battery", "device.power.low")


if __name__ == "__main__":
    unittest.main()
