"""Run the production screenshot shell body with mocks, never a real display."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = b"\x89PNG\r\n\x1a\nsynthetic pipeline bytes, not a screenshot"


class ScreenshotTests(unittest.TestCase):
    def run_helper(self, geometry="10,20 300x200\n", selection_exit=0):
        source = (ROOT / "default.nix").read_text()
        opening = 'name = "hypr-screenshot-region";'
        self.assertEqual(source.count(opening), 1)
        definition = source.split(opening, 1)[1].split("\n  };", 1)[0]
        body = definition.split("text = ''\n", 1)[1].split("\n    '';", 1)[0]
        self.assertNotIn("${", body)
        for dependency in ("pkgs.grim", "pkgs.slurp", "pkgs.swappy"):
            self.assertIn(dependency, definition)

        with tempfile.TemporaryDirectory(
            prefix="screenshot-test-", dir="/tmp/opencode"
        ) as directory:
            root = Path(directory)
            binaries = root / "bin"
            binaries.mkdir()
            (root / "geometry.txt").write_text(geometry)
            (root / "fixture.bin").write_bytes(FIXTURE)
            scripts = {
                "slurp": """
                    import os
                    import sys
                    from pathlib import Path
                    Path("slurp.called").touch()
                    sys.stdout.write(Path("geometry.txt").read_text())
                    sys.exit(int(os.environ["SELECTION_EXIT"]))
                """,
                "grim": """
                    import json
                    import sys
                    from pathlib import Path
                    Path("grim-argv.json").write_text(json.dumps(sys.argv[1:]))
                    sys.stdout.buffer.write(Path("fixture.bin").read_bytes())
                """,
                "swappy": """
                    import json
                    import sys
                    from pathlib import Path
                    Path("swappy-argv.json").write_text(json.dumps(sys.argv[1:]))
                    Path("received.bin").write_bytes(sys.stdin.buffer.read())
                """,
            }
            for name, script in scripts.items():
                executable = binaries / name
                executable.write_text(
                    f"#!{sys.executable}\n" + textwrap.dedent(script)
                )
                executable.chmod(0o700)
            # Match writeShellApplication's Bash strict mode. PATH contains only
            # mocks; no Wayland/PipeWire/session variables reach the child.
            result = subprocess.run(
                [shutil.which("bash"), "-euo", "pipefail", "-c", body],
                cwd=root,
                env={
                    "PATH": str(binaries),
                    "HOME": str(root),
                    "SELECTION_EXIT": str(selection_exit),
                },
                capture_output=True,
                timeout=5,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "slurp.called").exists())
            arguments = {}
            for name in ("grim", "swappy"):
                path = root / f"{name}-argv.json"
                if path.exists():
                    arguments[name] = json.loads(path.read_text())
            received = root / "received.bin"
            return arguments, received.read_bytes() if received.exists() else None

    def test_cancel_does_not_start_capture_or_editor(self):
        self.assertEqual(self.run_helper("", selection_exit=1), ({}, None))

    def test_failed_selection_with_output_does_not_capture(self):
        self.assertEqual(
            self.run_helper("10,20 300x200\n", selection_exit=1), ({}, None)
        )

    def test_empty_success_does_not_start_capture_or_editor(self):
        self.assertEqual(self.run_helper(""), ({}, None))

    def test_selected_region_streams_unchanged_to_editor(self):
        arguments, received = self.run_helper()
        self.assertEqual(arguments["grim"], ["-g", "10,20 300x200", "-"])
        self.assertEqual(arguments["swappy"], ["-f", "-"])
        self.assertEqual(received, FIXTURE)

    def test_negative_coordinates_and_no_final_newline(self):
        arguments, received = self.run_helper("-1920,0 1920x1080")
        self.assertEqual(arguments["grim"], ["-g", "-1920,0 1920x1080", "-"])
        self.assertEqual(received, FIXTURE)

    def test_geometry_is_one_literal_argument_not_shell_code(self):
        geometry = '10,20 300x200; $(exit 77) " *'
        arguments, _ = self.run_helper(geometry)
        self.assertEqual(arguments["grim"], ["-g", geometry, "-"])

    def test_all_bindings_and_help_use_the_shared_workflow(self):
        linux = ROOT.parents[1]
        for host in ("laptop-old", "desktop", "laptop"):
            config = (linux / host / "hyprland.conf").read_text()
            bindings = re.findall(r"^bind = , PRINT, exec, (.+)$", config, re.M)
            self.assertEqual(bindings, ["hypr-screenshot-region"])
        help_source = (ROOT.parent / "tofi/module.nix").read_text()
        self.assertIn("Print               select screenshot region, edit in Swappy", help_source)


if __name__ == "__main__":
    unittest.main()
