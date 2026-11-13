"""Production Bash event handler with a fake hyprctl; no live layout changes."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/focus-layout-en.sh"
SWITCH = ["switchxkblayout", "all", "0"]


class LayoutTests(unittest.TestCase):
    def test_shared_installation_and_all_host_launchers_use_new_name(self):
        module = (ROOT / "default.nix").read_text()
        self.assertIn('xdg.configFile."hypr/scripts/focus-layout-en.sh"', module)
        self.assertIn("source = ./scripts/focus-layout-en.sh;", module)
        self.assertNotIn("terminal-layout-en.sh", module)
        for host in ("laptop", "laptop-old", "desktop"):
            with self.subTest(host=host):
                config = (ROOT.parents[1] / host / "hyprland.conf").read_text()
                self.assertEqual(
                    config.count(
                        "exec-once = ~/.config/hypr/scripts/focus-layout-en.sh --focus-watcher"
                    ),
                    1,
                )
                self.assertNotIn("terminal-layout-en.sh", config)

    def run_streams(self, *streams, hyprctl_exit=0):
        with tempfile.TemporaryDirectory(
            prefix="layout-en-test-", dir="/tmp/opencode"
        ) as directory:
            root = Path(directory)
            binary = root / "hyprctl"
            binary.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "with open(os.environ['CALLS'], 'a') as log:\n"
                "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "sys.exit(int(os.environ['HYPRCTL_EXIT']))\n"
            )
            binary.chmod(0o700)
            paths = []
            for index, stream in enumerate(streams):
                path = root / f"stream-{index}"
                path.write_text(stream)
                paths.append(str(path))
            log = root / "calls"
            result = subprocess.run(
                [
                    shutil.which("bash"),
                    "-c",
                    'source "$1"; shift; for stream in "$@"; do '
                    '_focus_events < "$stream"; done',
                    "fixture",
                    str(SCRIPT),
                    *paths,
                ],
                env={
                    "PATH": str(root),
                    "CALLS": str(log),
                    "HYPRCTL_EXIT": str(hyprctl_exit),
                },
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            if log.exists():
                return [json.loads(line) for line in log.read_text().splitlines()]
            return []

    def test_pinentry_exact_wayland_and_xwayland_classes(self):
        for name in ("org.gnupg.pinentry-qt", "pinentry-qt", "Pinentry", "PINENTRY-QT"):
            with self.subTest(name=name):
                self.assertEqual(self.run_streams(f"activewindow>>{name},GPG\n"), [SWITCH])

    def test_each_pinentry_focus_resets_including_same_class(self):
        self.assertEqual(
            self.run_streams(
                "activewindow>>org.gnupg.pinentry-qt,First\n"
                "activewindow>>org.gnupg.pinentry-qt,Second\n"
                "activewindow>>firefox,Browser\n"
                "activewindow>>org.gnupg.pinentry-qt,First\n"
            ),
            [SWITCH] * 3,
        )

    def test_terminal_group_entry_behavior_is_preserved(self):
        self.assertEqual(
            self.run_streams(
                "activewindow>>firefox,Browser\n"
                "activewindow>>kitty,One\n"
                "activewindow>>Alacritty,Two\n"
                "activewindow>>foot,Three\n"
                "activewindow>>org.wezfurlong.wezterm,Four\n"
                "activewindow>>,\n"
                "activewindow>>kitty,Again\n"
            ),
            [SWITCH] * 2,
        )

    def test_pinentry_between_terminals_is_not_a_terminal(self):
        self.assertEqual(
            self.run_streams(
                "activewindow>>kitty,Shell\n"
                "activewindow>>pinentry-qt,GPG\n"
                "activewindow>>kitty,Shell\n"
            ),
            [SWITCH] * 3,
        )

    def test_title_and_similar_class_do_not_match(self):
        self.assertEqual(
            self.run_streams(
                "activewindow>>firefox,pinentry-qt,Password\n"
                "activewindow>>not-pinentry-qt,Password\n"
                "activewindow>>org.gnupg.pinentry-qt.fake,Password\n"
                "activewindow>>,\n"
            ),
            [],
        )

    def test_layout_and_title_events_do_not_lock_or_reset_layout(self):
        self.assertEqual(
            self.run_streams(
                "activewindow>>pinentry-qt,Title,with,commas\n"
                "activelayout>>keyboard,Russian\n"
                "windowtitle>>123\n"
                "windowtitlev2>>123,New title\n"
                "activewindowv2>>123\n"
            ),
            [SWITCH],
        )

    def test_leaving_pinentry_does_not_restore_previous_russian_layout(self):
        self.assertEqual(
            self.run_streams(
                "activewindow>>firefox,Browser\n"
                "activelayout>>keyboard,Russian\n"
                "activewindow>>pinentry-qt,GPG\n"
                "activelayout>>keyboard,English (US)\n"
                "activewindow>>firefox,Browser\n"
            ),
            [SWITCH],
        )

    def test_new_stream_resets_terminal_state_after_disconnect(self):
        self.assertEqual(
            self.run_streams(
                "activewindow>>kitty,Before disconnect\n",
                "activewindow>>kitty,After reconnect\n"
                "activewindow>>pinentry-qt,GPG\n",
            ),
            [SWITCH] * 3,
        )

    def test_switch_failure_does_not_stop_event_processing(self):
        self.assertEqual(
            self.run_streams(
                "activewindow>>pinentry-qt,First\n"
                "activewindow>>pinentry-qt,Second\n",
                hyprctl_exit=1,
            ),
            [SWITCH] * 2,
        )


if __name__ == "__main__":
    unittest.main()
