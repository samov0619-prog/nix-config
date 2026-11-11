"""Check evaluated HM environment.d text with the installed systemd generator.

Pass the evaluated file on stdin. HOME/XDG and inherited variables are isolated;
the generator still reads the installed system-wide environment.d defaults.
"""

from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


GENERATOR = Path(
    "/run/current-system/systemd/lib/systemd/user-environment-generators/"
    "30-systemd-environment-d-generator"
)


class EnvironmentTest(unittest.TestCase):
    def generate(self, text, inherited=None):
        with tempfile.TemporaryDirectory(
            prefix="qt-environment-", dir="/tmp/opencode"
        ) as directory:
            root = Path(directory)
            config = root / "config"
            target = config / "environment.d"
            target.mkdir(parents=True)
            (target / "10-home-manager.conf").write_text(text)
            env = {
                "HOME": directory,
                "XDG_CONFIG_HOME": str(config),
                "PATH": "/run/current-system/sw/bin",
                "LC_ALL": "C",
            }
            if inherited is not None:
                env["QT_STYLE_OVERRIDE"] = inherited
            result = subprocess.run(
                [str(GENERATOR)],
                env=env,
                text=True,
                capture_output=True,
                check=True,
                timeout=5,
            )
            values = {}
            for assignment in shlex.split(result.stdout):
                key, value = assignment.split("=", 1)
                values[key] = value
            return values, result.stderr

    def test_old_literal_empty_is_rejected(self):
        values, errors = self.generate("QT_STYLE_OVERRIDE=\n")
        self.assertNotIn("QT_STYLE_OVERRIDE", values)
        self.assertIn('invalid syntax (around "QT_STYLE_OVERRIDE")', errors)

    def test_evaluated_configuration_clears_override(self):
        for inherited in (None, "Adwaita-Dark", "Adwaita"):
            with self.subTest(inherited=inherited):
                values, errors = self.generate(self.configuration, inherited)
                self.assertEqual(errors, "")
                self.assertIn("QT_STYLE_OVERRIDE", values)
                self.assertEqual(values["QT_STYLE_OVERRIDE"], "")
                self.assertEqual(values["QT_QPA_PLATFORMTHEME"], "qt5ct")


if __name__ == "__main__":
    if not GENERATOR.is_file():
        sys.exit(f"Installed systemd generator not found: {GENERATOR}")
    if sys.stdin.isatty():
        sys.exit("Pipe evaluated HM environment.d text into this test.")
    EnvironmentTest.configuration = sys.stdin.read()
    unittest.main()
