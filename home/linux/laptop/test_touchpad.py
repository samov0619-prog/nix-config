"""Actual helper subprocesses with mocked hyprctl, never the live input device."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
DEVICE = "gxtp5100:00-27c6:01e7-touchpad"


class TouchpadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir="/tmp/opencode")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.log = self.root / "calls.jsonl"
        self.hyprctl = self.root / "hyprctl"
        self.hyprctl.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys, time\n"
            "with open(os.environ['CALL_LOG'], 'a') as log:\n"
            "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if os.environ.get('SLOW'):\n"
            "    time.sleep(5)\n"
            "print(os.environ.get('REPLY', 'ok'))\n"
            "sys.exit(int(os.environ.get('EXIT', '0')))\n"
        )
        self.hyprctl.chmod(0o700)
        self.env = {
            **os.environ,
            "HYPRLAND_INSTANCE_SIGNATURE": "test-session-a",
            "XDG_RUNTIME_DIR": str(self.root),
            "CALL_LOG": str(self.log),
        }

    def start(self, action="toggle", **env):
        return subprocess.Popen(
            [sys.executable, "-B", str(ROOT / "touchpad.py"), "--hyprctl", str(self.hyprctl), action],
            env={**self.env, **env},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def run_helper(self, action="toggle", success=True, **env):
        process = self.start(action, **env)
        stdout, stderr = process.communicate(timeout=8)
        self.assertEqual(process.returncode == 0, success, stdout + stderr)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def targets(self):
        calls = self.calls()
        for call in calls:
            self.assertEqual(call[:2], ["keyword", f"device[{DEVICE}]:enabled"])
        return [call[2] for call in calls]

    def test_toggle_disables_only_touchpad_then_enables_it(self):
        self.run_helper()
        self.run_helper()
        self.assertEqual(self.targets(), ["false", "true"])

    def test_reload_reset_and_next_toggle_agree(self):
        for action in ("enable", "toggle", "enable", "toggle"):
            self.run_helper(action)
        self.assertEqual(self.targets(), ["true", "false", "true", "false"])

    def test_new_session_does_not_inherit_disabled_state(self):
        self.run_helper()
        self.run_helper(HYPRLAND_INSTANCE_SIGNATURE="test-session-b")
        self.assertEqual(self.targets(), ["false", "false"])

    def test_keyword_error_does_not_advance_state(self):
        self.run_helper()
        self.run_helper(success=False, REPLY="no such option")
        self.run_helper()
        self.assertEqual(self.targets(), ["false", "true", "true"])

    def test_command_failure_does_not_advance_state(self):
        self.run_helper(success=False, EXIT="1")
        self.run_helper()
        self.assertEqual(self.targets(), ["false", "false"])

    def test_timeout_does_not_advance_state(self):
        self.run_helper(success=False, SLOW="1")
        self.run_helper()
        self.assertEqual(self.targets(), ["false", "false"])

    def test_parallel_toggles_are_serialized(self):
        processes = [self.start() for _ in range(6)]
        for process in processes:
            stdout, stderr = process.communicate(timeout=8)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertEqual(self.targets(), ["false", "true"] * 3)

    def test_missing_session_never_calls_hyprctl(self):
        self.run_helper(success=False, HYPRLAND_INSTANCE_SIGNATURE="")
        self.assertFalse(self.log.exists())

    def test_invalid_state_requires_explicit_reset(self):
        self.run_helper()
        state = next(self.root.glob("lenovo-touchpad-*/state"))
        state.write_text("invalid")
        self.run_helper(success=False)
        self.assertEqual(len(self.calls()), 1)
        self.run_helper("enable")
        self.assertEqual(state.read_text(), "enabled\n")
        self.assertEqual(state.stat().st_mode & 0o777, 0o600)
        self.assertEqual(state.parent.stat().st_mode & 0o777, 0o700)

    def test_bindings_and_reset_match_agreed_keys(self):
        config = (ROOT / "hyprland.conf").read_text()
        for line in (
            "exec = lenovo-touchpad enable",
            "bind = , F1, exec, hypr-controls",
            "bind = , F11, exec, ~/.config/hypr/scripts/toggle-theme.sh",
            "bind = , XF86Favorites, exec, agent-todo-open",
            "bind = , XF86TouchpadToggle, exec, lenovo-touchpad toggle",
            "bind = , PRINT, exec, hypr-screenshot-region",
            "bind = $mainMod, P, pseudo,",
        ):
            self.assertIn(line, config.splitlines())
        for fragment in (", F3,", "$mainMod, F11,", "code:248", "XF86LinkPhone"):
            self.assertNotIn(fragment, config)
        self.assertIn(f"name = {DEVICE}\n    enabled = true", config)
        self.assertNotIn("name = gxtp5100:00-27c6:01e7-mouse", config)


if __name__ == "__main__":
    unittest.main()
