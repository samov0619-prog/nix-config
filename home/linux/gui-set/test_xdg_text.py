"""Actual xdg-open desktop-launch functions with generated desktop text and fake TUIs."""

import argparse
import configparser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


DESKTOP = None
XDG_OPEN = None


class TextHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desktop = DESKTOP.read_text()
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(cls.desktop)
        cls.entry = parser["Desktop Entry"]
        source = XDG_OPEN.read_text()
        functions = []
        for name in (
            "first_word",
            "last_word",
            "get_key",
            "exit_success",
            "search_desktop_file",
        ):
            matches = re.findall(
                r"^" + name + r"\(\)\n\{\n.*?^\}", source, re.M | re.S
            )
            if len(matches) != 1:
                raise AssertionError(f"Review changed xdg-open function: {name}")
            functions.append(matches[0])
        cls.launcher = "\n".join(functions)
        cls.launcher += '\nsearch_desktop_file nvim-xdg.desktop "$1" "$2" "$2"\n'

    def run_handler(self, filename, original=False):
        with tempfile.TemporaryDirectory(
            prefix="xdg-text-test-", dir="/tmp/opencode"
        ) as temporary:
            root = Path(temporary)
            binaries = root / "bin"
            binaries.mkdir()
            target = root / filename
            target.touch()
            desktop = root / "nvim-xdg.desktop"
            desktop.write_text(
                # The previous upstream entry's relevant launch contract.
                "[Desktop Entry]\nName=Neovim\nExec=nvim %F\nTerminal=true\n"
                if original
                else self.desktop
            )
            scripts = {
                "kitty": (
                    "import json, os, sys\n"
                    "from pathlib import Path\n"
                    "Path('kitty.json').write_text(json.dumps(sys.argv[1:]))\n"
                    "assert sys.argv[1] == '--'\n"
                    "os.execvp(sys.argv[2], sys.argv[2:])\n"
                ),
                "nvim": (
                    "import json, os, sys\n"
                    "from pathlib import Path\n"
                    "data = dict(argv=sys.argv[1:], uid=os.getuid(), "
                    "euid=os.geteuid(), cwd=os.getcwd(), "
                    "sentinel=os.environ.get('FIXTURE_ENV'))\n"
                    "Path('nvim.json').write_text(json.dumps(data))\n"
                ),
            }
            for name, body in scripts.items():
                binary = binaries / name
                binary.write_text(f"#!{sys.executable}\n" + body)
                binary.chmod(0o700)
            result = subprocess.run(
                [shutil.which("bash"), "-c", self.launcher, "fixture", str(root),
                 str(target)],
                cwd=root,
                env={"HOME": str(root), "PATH": str(binaries),
                     "FIXTURE_ENV": "inherited-not-secret"},
                capture_output=True,
                timeout=5,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            nvim = json.loads((root / "nvim.json").read_text())
            kitty = root / "kitty.json"
            if original:
                self.assertFalse(kitty.exists())
                self.assertEqual(nvim["argv"], [str(target)])
            else:
                self.assertEqual(
                    json.loads(kitty.read_text()), ["--", "nvim", "--", str(target)]
                )
                self.assertEqual(nvim["argv"], ["--", str(target)])
            self.assertEqual(nvim["uid"], os.getuid())
            self.assertEqual(nvim["euid"], os.geteuid())
            self.assertEqual(nvim["cwd"], str(root))
            self.assertEqual(nvim["sentinel"], "inherited-not-secret")

    def test_generated_entry_owns_the_terminal_and_is_hidden(self):
        self.assertEqual(self.entry["Exec"], "kitty -- nvim -- %F")
        self.assertFalse(self.entry.getboolean("Terminal"))
        self.assertTrue(self.entry.getboolean("NoDisplay"))
        self.assertEqual(self.entry["MimeType"].rstrip(";"), "text/plain")

    def test_old_entry_control_reproduces_missing_terminal(self):
        self.run_handler("control.txt", original=True)

    def test_plain_file_keeps_identity_cwd_and_environment(self):
        self.run_handler("test.txt")

    def test_spaces_and_unicode(self):
        self.run_handler("текст с пробелами.txt")

    def test_quotes_and_shell_characters_are_literal(self):
        self.run_handler("O'Brien \"quoted\" $(exit 77) [*];.txt")

    def test_option_like_filename_is_after_nvim_separator(self):
        self.run_handler("-u init.lua.txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop-file", type=Path, required=True)
    parser.add_argument("--xdg-open", type=Path,
                        default=Path("/run/current-system/sw/bin/xdg-open"))
    args, remaining = parser.parse_known_args()
    DESKTOP = args.desktop_file
    XDG_OPEN = args.xdg_open
    unittest.main(argv=[sys.argv[0], *remaining])
