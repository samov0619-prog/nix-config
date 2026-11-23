"""Exercise actual interactive Fish events without rebuilding or notifying."""

import errno
import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import signal
import sys
import tempfile
import time
import subprocess
import unittest


class NixosSwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(
            prefix="nixos-switch-", dir="/tmp/opencode"
        )
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        cls.bin = cls.root / "bin"
        cls.bin.mkdir()
        cls.fish = shutil.which("fish")
        if not cls.fish:
            raise RuntimeError("Tests require already-installed Fish and Nix")
        mock = (
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "name = Path(sys.argv[0]).name\n"
            "with open(os.environ['SWITCH_TEST_LOG'], 'a') as log:\n"
            "    log.write(json.dumps([name, *sys.argv[1:]]) + '\\n')\n"
            "if name != 'notify-send':\n"
            "    print('fixture rebuild output')\n"
            "    print('fixture rebuild diagnostic', file=sys.stderr)\n"
            "key = 'SWITCH_TEST_NOTIFY' if name == 'notify-send' else 'SWITCH_TEST_REBUILD'\n"
            "sys.exit(int(os.environ[key]))\n"
        )
        for name in ("sudo", "nixos-rebuild", "notify-send"):
            path = cls.bin / name
            path.write_text(mock)
            path.chmod(0o700)
        module = Path(__file__).resolve().parents[1] / "default.nix"
        expression = (
            f"(import {module} "
            f"{{ pkgs.libnotify = {json.dumps(str(cls.root))}; }})"
            ".programs.fish.interactiveShellInit"
        )
        hook = subprocess.check_output(
            ["nix", "eval", "--impure", "--offline", "--raw", "--expr", expression],
            text=True,
        )
        cls.hook = cls.root / "hook.fish"
        cls.hook.write_text(hook)

    def run_command(self, command, rebuild_status=0, notify_status=0):
        log = self.root / "calls.jsonl"
        log.write_text("")
        env = os.environ | {
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "TERM": "dumb",
            "SWITCH_TEST_LOG": str(log),
            "SWITCH_TEST_REBUILD": str(rebuild_status),
            "SWITCH_TEST_NOTIFY": str(notify_status),
        }
        # A real PTY is needed: Fish does not emit fish_postexec for -c or piped
        # stdin. Skip user config/secrets and disable history only in this child.
        init = (
            "set -g fish_history ''; "
            "function fish_prompt; echo SWITCH_TEST_READY; end; "
            f"source {shlex.quote(str(self.hook))}"
        )
        pid, master = pty.fork()
        if pid == 0:
            os.execvpe(
                self.fish,
                [self.fish, "--no-config", "--interactive", "--init-command", init],
                env,
            )
        output = b""
        deadline = time.monotonic() + 5

        def read_until(marker):
            nonlocal output
            while marker not in output:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([master], [], [], remaining)[0]:
                    self.fail(f"Fish timed out: {output!r}")
                try:
                    chunk = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    chunk = b""
                if not chunk:
                    self.fail(f"Fish exited before {marker!r}: {output!r}")
                output += chunk

        try:
            read_until(b"SWITCH_TEST_READY")
            os.write(
                master,
                (
                    command
                    + "\nset -l test_command_status $status\nwait\n"
                    + "printf '\\nSWITCH_TEST_STATUS=%s_END\\n' $test_command_status\n"
                ).encode(),
            )
            read_until(b"_END\r\n")
        finally:
            # Only the isolated shell from this test; all its commands are mocks.
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            os.close(master)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        notifications = [call for call in calls if call[0] == "notify-send"]
        return output.decode(errors="replace"), calls, notifications

    def test_ordinary_sudo_command_success(self):
        output, calls, notifications = self.run_command(
            "sudo nixos-rebuild switch --flake ~/nix-config/.#laptop -L"
        )
        self.assertEqual(
            calls[0],
            [
                "sudo", "nixos-rebuild", "switch", "--flake",
                str(Path.home() / "nix-config/.#laptop"), "-L",
            ],
        )
        self.assertEqual(
            notifications,
            [["notify-send", "--app-name=NixOS", "NixOS",
              "System configuration built and activated"]],
        )
        self.assertEqual(len(calls), 2)
        self.assertIn("SWITCH_TEST_STATUS=0_END", output)
        self.assertIn("fixture rebuild output", output)
        self.assertIn("fixture rebuild diagnostic", output)

    def test_direct_command_with_whitespace_and_quoted_path(self):
        _, calls, notifications = self.run_command(
            '  nixos-rebuild switch --flake "/fixture/path with spaces#laptop" -L'
        )
        self.assertEqual(calls[0][3], "/fixture/path with spaces#laptop")
        self.assertEqual(len(notifications), 1)

    def test_errors_preserve_exit_status(self):
        for status in (1, 4, 130):
            with self.subTest(status=status):
                output, _, notifications = self.run_command(
                    "sudo nixos-rebuild switch -L", rebuild_status=status
                )
                self.assertEqual(len(notifications), 1)
                self.assertIn("--urgency=critical", notifications[0])
                self.assertIn(f"exit code {status}", notifications[0][-1])
                self.assertIn(f"SWITCH_TEST_STATUS={status}_END", output)

    def test_notification_failure_preserves_rebuild_status(self):
        for status in (0, 1):
            with self.subTest(status=status):
                output, _, notifications = self.run_command(
                    "sudo nixos-rebuild switch", status, notify_status=1
                )
                self.assertEqual(len(notifications), 1)
                self.assertIn("could not send desktop notification", output)
                self.assertIn(f"SWITCH_TEST_STATUS={status}_END", output)

    def test_unrelated_and_ambiguous_commands_are_ignored(self):
        for command in (
            "sudo nixos-rebuild build -L",
            "sudo nixos-rebuild test",
            "sudo nixos-rebuild switch --help",
            "sudo nixos-rebuild switch -h",
            "nixos-rebuild switch --dry-run",
            "sudo -E nixos-rebuild switch",
            "sudo nixos-rebuild switcher",
            "echo sudo nixos-rebuild switch",
            "sudo nixos-rebuild switch; true",
            "sudo nixos-rebuild switch | cat",
            "sudo nixos-rebuild switch &",
        ):
            with self.subTest(command=command):
                _, _, notifications = self.run_command(command)
                self.assertEqual(notifications, [])


if __name__ == "__main__":
    unittest.main()
