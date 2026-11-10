"""Real GLib parsing and launcher process, fake Tofi/UWSM, no GUI or app launch."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parent
GLIB = None


class LauncherTests(unittest.TestCase):
    def run_launcher(self, command, status=0, legacy=False):
        with tempfile.TemporaryDirectory(
            prefix="tofi-launch-", dir="/tmp/opencode"
        ) as temporary:
            root = Path(temporary)
            binaries = root / "bin"
            binaries.mkdir()
            (root / "selection").write_bytes(command)
            (root / "fixture.txt").touch()
            scripts = {
                "touch": """
                    from pathlib import Path
                    Path('marker').touch()
                """,
                "tofi-drun": """
                    from pathlib import Path
                    import os, sys
                    assert sys.argv[1:] == ([] if os.environ['LEGACY'] == '1' else ['--drun-launch=false'])
                    sys.stdout.buffer.write(Path('selection').read_bytes())
                    sys.exit(int(os.environ['TOFI_STATUS']))
                """,
                "uwsm": """
                    from pathlib import Path
                    import json, os, sys
                    assert sys.argv[1:3] == ['app', '--']
                    Path('uwsm.json').write_text(json.dumps({
                        'args': sys.argv[1:], 'uid': os.getuid(), 'euid': os.geteuid(),
                        'cwd': os.getcwd(), 'environment': os.environ['LAUNCH_FIXTURE'],
                    }))
                """,
            }
            for name, source in scripts.items():
                path = binaries / name
                path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(source))
                path.chmod(0o700)
            environment = {
                **os.environ,
                "HOME": str(root),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_RUNTIME_DIR": str(root / "runtime"),
                "PATH": str(binaries),
                "TOFI_STATUS": str(status),
                "LEGACY": "1" if legacy else "0",
                "LAUNCH_FIXTURE": "synthetic-exported-value",
            }
            invocation = (
                ["/bin/sh", "-c", "uwsm app -- $(tofi-drun)"]
                if legacy else
                [sys.executable, str(ROOT / "launch.py"), "--glib", str(GLIB),
                 "--tofi", str(binaries / "tofi-drun"), "--uwsm", str(binaries / "uwsm")]
            )
            result = subprocess.run(
                invocation, cwd=root, env=environment,
                capture_output=True, timeout=5,
            )
            log = root / "uwsm.json"
            actual = json.loads(log.read_text()) if log.exists() else None
            self.assertFalse((root / "marker").exists(), "Shell substitution executed")
            if actual is not None:
                self.assertEqual(actual["uid"], os.getuid())
                self.assertEqual(actual["euid"], os.geteuid())
                self.assertEqual(actual["cwd"], str(root))
                self.assertEqual(actual["environment"], "synthetic-exported-value")
            return result, actual

    def assert_arguments(self, command, expected):
        result, actual = self.run_launcher(command.encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(actual)
        self.assertEqual(actual["args"], ["app", "--", *expected])

    def test_plain_terminal_command_is_not_wrapped_twice(self):
        self.assert_arguments("kitty -- nvim\n", ["kitty", "--", "nvim"])

    def test_quoted_arguments_and_empty_argument(self):
        self.assert_arguments(
            'fixture-app --label "two words" ""\n',
            ["fixture-app", "--label", "two words", ""],
        )

    def test_executable_path_and_unicode(self):
        self.assert_arguments(
            '"/fixture/app with spaces" "тест с пробелами"\n',
            ["/fixture/app with spaces", "тест с пробелами"],
        )

    def test_escaped_quotes_backslashes_and_apostrophe(self):
        self.assert_arguments(
            r'''fixture-app "say \"hi\"" "C:\\temp\\file" "O'Reilly"''',
            ["fixture-app", 'say "hi"', "C:\\temp\\file", "O'Reilly"],
        )

    def test_shell_characters_stay_literal(self):
        self.assert_arguments(
            r'''fixture-app "\$HOME" "\$(touch marker)" "*.txt" "semi; pipe| amp&" "\`touch marker\`"''',
            ["fixture-app", "$HOME", "$(touch marker)", "*.txt", "semi; pipe| amp&",
             "`touch marker`"],
        )
        self.assert_arguments(
            'fixture-app "$HOME" "$(touch marker)" "*.txt" "`touch marker`" ";" "|" "&"',
            ["fixture-app", "$HOME", "$(touch marker)", "*.txt", "`touch marker`", ";", "|", "&"],
        )

    def test_cancel_empty_and_whitespace_never_call_uwsm(self):
        for command, status in ((b"", 1), (b"fixture-app\n", 1), (b"", 0), (b" \n\t", 0)):
            with self.subTest(command=command, status=status):
                result, actual = self.run_launcher(command, status)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsNone(actual)

    def test_malformed_nul_and_empty_executable_never_call_uwsm(self):
        for command in (b'fixture-app "unterminated', b"fixture-app \\",
                        b'"" --label value', b"fixture-app\0unexpected"):
            with self.subTest(command=command):
                result, actual = self.run_launcher(command)
                self.assertEqual(result.returncode, 1)
                self.assertIn(b"tofi-launch:", result.stderr)
                self.assertIsNone(actual)

    def test_original_shell_expression_breaks_the_quote_fixture(self):
        result, actual = self.run_launcher(b'fixture-app --label "two words"\n', legacy=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(actual["args"], ["app", "--", "fixture-app", "--label", '"two', 'words"'])

    def test_missing_library_or_binary_reports_error_without_launch(self):
        for missing in ("--glib", "--tofi", "--uwsm"):
            with self.subTest(missing=missing):
                # The process fixture never starts a real binary for these paths.
                with tempfile.TemporaryDirectory(dir="/tmp/opencode") as temporary:
                    root = Path(temporary)
                    tofi = root / "tofi"
                    tofi.write_text(f"#!{sys.executable}\nprint('fixture-app')\n")
                    tofi.chmod(0o700)
                    uwsm = root / "uwsm"
                    uwsm.write_text(f"#!{sys.executable}\nraise SystemExit(99)\n")
                    uwsm.chmod(0o700)
                    paths = {"--glib": str(GLIB), "--tofi": str(tofi), "--uwsm": str(uwsm)}
                    paths[missing] = str(root / "missing")
                    arguments = [sys.executable, str(ROOT / "launch.py")]
                    for option, value in paths.items():
                        arguments.extend([option, value])
                    result = subprocess.run(arguments, capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(b"tofi-launch:", result.stderr)

    def test_three_gui_profiles_use_the_shared_launcher(self):
        linux = ROOT.parent.parent
        for profile in ("laptop", "desktop", "laptop-next"):
            with self.subTest(profile=profile):
                config = (linux / profile / "hyprland.conf").read_text()
                self.assertIn("$menu = tofi-launch\n", config)
                self.assertNotIn("$(tofi-drun)", config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glib", required=True, type=Path)
    options, remaining = parser.parse_known_args()
    GLIB = options.glib.resolve()
    unittest.main(argv=[__file__, *remaining])
