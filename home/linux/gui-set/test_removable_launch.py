"""Generated folder entry and installed udiskie code, without devices or real TUIs."""

import argparse
import ast
import configparser
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


DECLARATIONS = None
UDISKIE_PACKAGE = None
XDG_OPEN = None


class RemovableLaunchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = json.loads(DECLARATIONS.read_text())
        cls.profile = cls.profiles["samov-laptop"]
        sources = list(UDISKIE_PACKAGE.glob("lib/python*/site-packages/udiskie"))
        if len(sources) != 1:
            raise AssertionError("Expected one installed udiskie source directory")
        cls.source = sources[0]
        config_node = next(
            node for node in ast.parse((cls.source / "config.py").read_text()).body
            if isinstance(node, ast.ClassDef) and node.name == "Config"
        )
        namespace = {}
        exec(compile(ast.Module(body=[config_node], type_ignores=[]),
                     "<installed udiskie Config>", "exec"), namespace)
        cls.Config = namespace["Config"]
        cls.browser_node = next(
            node for node in ast.parse((cls.source / "prompt.py").read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name == "browser"
        )
        functions = []
        source = XDG_OPEN.read_text()
        for name in ("first_word", "last_word", "get_key", "exit_success",
                     "search_desktop_file"):
            matches = re.findall(
                r"^" + name + r"\(\)\n\{\n.*?^\}", source, re.M | re.S
            )
            if len(matches) != 1:
                raise AssertionError(f"Review changed xdg-open function: {name}")
            functions.append(matches[0])
        cls.launcher = "\n".join(functions)
        cls.launcher += '\nsearch_desktop_file yazi-xdg.desktop "$1" "$2" "$2"\n'

    def test_installed_udiskie_recognizes_smart_menu(self):
        config = self.Config(self.profile["udiskieSettings"])
        self.assertEqual(config.program_options, {"menu": "smart"})

    def test_original_root_menu_is_ignored(self):
        self.assertEqual(self.Config({"menu": "nested"}).program_options, {})

    def test_gui_profiles_share_the_entry_and_settings(self):
        for name in ("samov-laptop", "samov-desktop", "samov-laptop-next"):
            with self.subTest(profile=name):
                self.assertEqual(self.profiles[name]["directoryDesktopText"],
                                 self.profile["directoryDesktopText"])
                self.assertEqual(self.profiles[name]["udiskieSettings"],
                                 self.profile["udiskieSettings"])
        for name in ("samov-mac", "samov-server"):
            self.assertIsNone(self.profiles[name]["directoryDesktopText"])
            self.assertIsNone(self.profiles[name]["udiskieSettings"])

    def test_generated_entry_owns_its_terminal(self):
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(self.profile["directoryDesktopText"])
        entry = parser["Desktop Entry"]
        self.assertEqual(entry["Exec"], "kitty -- yazi %f")
        self.assertFalse(entry.getboolean("Terminal"))
        self.assertIn("inode/directory", entry["MimeType"].split(";"))

    def run_browse(self, name):
        with tempfile.TemporaryDirectory(
            prefix="removable-launch-test-", dir="/tmp/opencode"
        ) as temporary:
            root = Path(temporary)
            directory = root / name
            directory.mkdir()
            (root / "yazi-xdg.desktop").write_text(
                self.profile["directoryDesktopText"]
            )
            binaries = root / "bin"
            binaries.mkdir()
            scripts = {
                "kitty": (
                    "import json, os, sys\nfrom pathlib import Path\n"
                    "Path('kitty.json').write_text(json.dumps(sys.argv[1:]))\n"
                    "assert sys.argv[1] == '--'\n"
                    "os.execvp(sys.argv[2], sys.argv[2:])\n"
                ),
                "yazi": (
                    "import json, os, sys\nfrom pathlib import Path\n"
                    "data = dict(argv=sys.argv[1:], uid=os.getuid(), "
                    "euid=os.geteuid(), cwd=os.getcwd())\n"
                    "Path('yazi.json').write_text(json.dumps(data))\n"
                ),
            }
            for command, body in scripts.items():
                binary = binaries / command
                binary.write_text(f"#!{sys.executable}\n" + body)
                binary.chmod(0o700)
            # Real browser function, but a fake Popen captures the launch only.
            calls = []
            namespace = {
                "shlex": shlex,
                "which": lambda command: str(binaries / command),
                "subprocess": SimpleNamespace(Popen=lambda argv: calls.append(argv)),
            }
            exec(compile(ast.Module(body=[self.browser_node], type_ignores=[]),
                         "<installed udiskie browser>", "exec"), namespace)
            namespace["browser"]()(str(directory))
            self.assertEqual(calls, [["xdg-open", str(directory)]])
            # Exercise the actual desktop-launch path only, not MIME discovery,
            # a graphical session, sudo, D-Bus or UDisks mounting.
            result = subprocess.run(
                [shutil.which("bash"), "-c", self.launcher, "fixture", str(root),
                 calls[0][1]],
                cwd=root,
                env={"HOME": str(root), "PATH": str(binaries)},
                capture_output=True,
                timeout=5,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((root / "kitty.json").read_text()),
                             ["--", "yazi", str(directory)])
            yazi = json.loads((root / "yazi.json").read_text())
            self.assertEqual(yazi["argv"], [str(directory)])
            self.assertEqual(yazi["uid"], os.getuid())
            self.assertEqual(yazi["euid"], os.geteuid())
            self.assertEqual(yazi["cwd"], str(root))

    def test_browse_directory_with_spaces_and_unicode(self):
        self.run_browse("USB с пробелами")

    def test_browse_directory_with_literal_shell_characters(self):
        self.run_browse("O'Brien \"quoted\" $(exit 77) [*];")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--declarations", type=Path, required=True)
    parser.add_argument("--udiskie-package", type=Path, required=True)
    parser.add_argument("--xdg-open", type=Path,
                        default=Path("/run/current-system/sw/bin/xdg-open"))
    args, remaining = parser.parse_known_args()
    DECLARATIONS = args.declarations
    UDISKIE_PACKAGE = args.udiskie_package
    XDG_OPEN = args.xdg_open
    unittest.main(argv=[sys.argv[0], *remaining])
