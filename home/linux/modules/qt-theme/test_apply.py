import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import shlex
import shutil
import subprocess
import sys

import apply as appearance


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="theme-test-", dir="/tmp/opencode")
        self.addCleanup(self.directory.cleanup)
        self.config = Path(self.directory.name)

    def test_declared_styles_and_nomacs_proxy(self):
        self.assertEqual(appearance.apply(self.config, "dark", True), 3)
        for version in ("qt5ct", "qt6ct"):
            text = (self.config / version / f"{version}.conf").read_text()
            self.assertIn("style=Adwaita-Dark\n", text)
            self.assertIn("custom_palette=false\n", text)
            self.assertIn("standard_dialogs=xdgdesktopportal\n", text)
        text = (self.config / "nomacs" / "Image Lounge.conf").read_text()
        self.assertIn("themeName312=System.css\n", text)
        self.assertIn("stylePlugin=qt6ct-style\n", text)

    def test_preserves_unrelated_qsettings_and_backs_up_once(self):
        path = self.config / "nomacs" / "Image Lounge.conf"
        path.parent.mkdir()
        original = (
            b"; user comment\r\n[General]\r\nwindowState=@ByteArray(\\0\\xff)\r\n"
            b"[DisplaySettings]\r\nstylePlugin=fusion\r\n"
            b"themeName312=Light-Theme.css\r\nfontSize=14\r\n"
            b"[RecentFiles]\r\nfilePath=/keep/original.png\r\n"
        )
        path.write_bytes(original)
        path.chmod(0o640)
        appearance.apply(self.config, "dark", True)
        current = path.read_bytes()
        self.assertEqual(
            current,
            original.replace(b"stylePlugin=fusion", b"stylePlugin=qt6ct-style").replace(
                b"themeName312=Light-Theme.css", b"themeName312=System.css"
            ),
        )
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        backup = path.with_name(path.name + ".before-qt-theme")
        self.assertEqual(backup.read_bytes(), original)
        appearance.apply(self.config, "light", True)
        self.assertEqual(backup.read_bytes(), original)

    def test_idempotence_does_not_rewrite_files(self):
        appearance.apply(self.config, "light", True)
        path = self.config / "qt6ct" / "qt6ct.conf"
        before = path.stat()
        self.assertEqual(appearance.apply(self.config, "light", True), 0)
        after = path.stat()
        self.assertEqual(before.st_ino, after.st_ino)
        self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)

    def test_f11_changes_style_without_touching_app_preferences(self):
        appearance.apply(self.config, "light", True)
        path = self.config / "nomacs" / "Image Lounge.conf"
        before = path.read_bytes()
        appearance.apply(self.config, "dark")
        self.assertEqual(path.read_bytes(), before)
        appearance.apply(self.config, "light")
        self.assertIn("style=Adwaita\n", (self.config / "qt6ct" / "qt6ct.conf").read_text())

    def test_validation_happens_before_any_write(self):
        path = self.config / "qt6ct" / "qt6ct.conf"
        path.parent.mkdir()
        target = self.config / "user-file"
        target.write_text("untouched")
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            appearance.apply(self.config, "dark", True)
        self.assertEqual(target.read_text(), "untouched")
        self.assertFalse((self.config / "qt5ct").exists())
        self.assertFalse((self.config / "nomacs").exists())

    def test_duplicate_sections_and_keys_are_rejected(self):
        for text in (
            "[Appearance]\nstyle=a\n[Appearance]\nstyle=b\n",
            "[Appearance]\nstyle=a\nstyle=b\n",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                appearance.update_section(text, "Appearance", {"style": "Adwaita"})

    def test_existing_qtct_fonts_and_icons_are_preserved(self):
        path = self.config / "qt6ct" / "qt6ct.conf"
        path.parent.mkdir()
        text = '[Appearance]\nstyle=Fusion\nicon_theme=existing\n[Fonts]\ngeneral="Keep font,14"\n'
        path.write_text(text)
        appearance.apply(self.config, "light")
        result = path.read_text()
        self.assertIn("icon_theme=existing\n", result)
        self.assertIn('[Fonts]\ngeneral="Keep font,14"\n', result)
        self.assertIn("style=Adwaita\n", result)

    def test_missing_section_and_missing_final_newline(self):
        text = "[Other]\nkeep=original"
        result = appearance.update_section(text, "Appearance", {"style": "Adwaita"})
        self.assertEqual(result, "[Other]\nkeep=original\n\n[Appearance]\nstyle=Adwaita\n")

    def test_system_mode_uses_dconf(self):
        for setting, expected in (("'prefer-dark'", "dark"), ("'prefer-light'", "light"), ("", "light")):
            with self.subTest(setting=setting), patch.object(appearance.subprocess, "run") as run:
                run.return_value.stdout = setting
                self.assertEqual(appearance.system_mode(), expected)
        with patch.object(appearance.subprocess, "run") as run:
            run.return_value.stdout = "'unexpected'"
            with self.assertRaises(ValueError):
                appearance.system_mode()

    def test_new_files_are_private(self):
        appearance.apply(self.config, "dark", True)
        for path in (
            self.config / "qt5ct" / "qt5ct.conf",
            self.config / "qt6ct" / "qt6ct.conf",
            self.config / "nomacs" / "Image Lounge.conf",
        ):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_actual_f11_script_updates_gtk_and_both_qt_versions(self):
        commands = self.config / "bin"
        commands.mkdir()
        script = Path(__file__).resolve().parents[1] / "hyprland/scripts/toggle-theme.sh"
        helper = Path(appearance.__file__).resolve()
        cases = (
            ("'prefer-light'", "dark", "Adwaita-Dark", "Adwaita-dark"),
            ("'prefer-dark'", "light", "Adwaita", "Adwaita"),
            ("", "dark", "Adwaita-Dark", "Adwaita-dark"),
            ("'default'", "dark", "Adwaita-Dark", "Adwaita-dark"),
            ("'unexpected'", "dark", "Adwaita-Dark", "Adwaita-dark"),
        )
        for current, mode, expected, gtk_theme in cases:
            with self.subTest(current=current):
                programs = {
                    "dconf": (
                        'case "$1" in\n'
                        'read) printf "%s\\n" "$F11_CURRENT_SCHEME" ;;\n'
                        'write) printf "%s\\t%s\\n" "$2" "$3" >> "$F11_DCONF_LOG" ;;\n'
                        '*) exit 1 ;;\nesac\n'
                    ),
                    "qt-theme-apply": f"exec {shlex.quote(sys.executable)} {shlex.quote(str(helper))} \"$@\"\n",
                    "hyprctl": "exit 0\n",
                    "systemctl": "exit 99\n",
                    "uwsm": "exit 99\n",
                }
                for name, body in programs.items():
                    path = commands / name
                    path.write_text("#!/bin/sh\n" + body)
                    path.chmod(0o700)
                env = os.environ | {
                    "HOME": str(self.config),
                    "XDG_CONFIG_HOME": str(self.config),
                    "PATH": str(commands) + os.pathsep + os.environ["PATH"],
                    "F11_CURRENT_SCHEME": current,
                    "F11_DCONF_LOG": str(self.config / "dconf-writes"),
                }
                writes = self.config / "dconf-writes"
                writes.write_text("")
                subprocess.run(["sh", str(script)], env=env, check=True, capture_output=True)
                self.assertEqual(writes.read_text().splitlines(), [
                    f"/org/gnome/desktop/interface/color-scheme\t'prefer-{mode}'",
                    f"/org/gnome/desktop/interface/gtk-theme\t'{gtk_theme}'",
                ])
                for version in ("qt5ct", "qt6ct"):
                    text = (self.config / version / f"{version}.conf").read_text()
                    self.assertIn(f"style={expected}\n", text)
                self.assertFalse((self.config / "uwsm/env-toggle").exists())
                self.assertEqual((self.config / "theme/current_theme").read_text(), mode)

    @unittest.skipUnless(shutil.which("dconf") and shutil.which("dbus-run-session"),
                         "Native dconf check requires installed dconf and dbus-run-session")
    def test_actual_f11_with_real_dconf_on_a_private_bus(self):
        commands = self.config / "bin"
        commands.mkdir()
        helper = Path(appearance.__file__).resolve()
        for name, body in {
            "qt-theme-apply": f"exec {shlex.quote(sys.executable)} {shlex.quote(str(helper))} \"$@\"",
            "hyprctl": "exit 0",
        }.items():
            path = commands / name
            path.write_text("#!/bin/sh\n" + body + "\n")
            path.chmod(0o700)
        script = Path(__file__).resolve().parents[1] / "hyprland/scripts/toggle-theme.sh"
        scenario = '''
import subprocess
import sys

def read(key):
    return subprocess.check_output(["dconf", "read", key], text=True).strip()

def write(key, value):
    subprocess.run(["dconf", "write", key, value], check=True)

base = "/org/gnome/desktop/interface/"
write(base + "font-name", "'Fixture font 13'")
for current, mode, gtk in (
    ("'prefer-light'", "dark", "Adwaita-dark"),
    ("'prefer-dark'", "light", "Adwaita"),
    ("'default'", "dark", "Adwaita-dark"),
):
    write(base + "color-scheme", current)
    subprocess.run(["sh", sys.argv[1]], check=True, capture_output=True)
    assert read(base + "color-scheme") == "'prefer-" + mode + "'"
    assert read(base + "gtk-theme") == "'" + gtk + "'"
    assert read(base + "font-name") == "'Fixture font 13'"
'''
        result = subprocess.run(
            ["dbus-run-session", "--", sys.executable, "-c", scenario, str(script)],
            env=os.environ | {
                "HOME": str(self.config),
                "XDG_CONFIG_HOME": str(self.config),
                "XDG_CACHE_HOME": str(self.config / "cache"),
                "PATH": str(commands) + os.pathsep + os.environ["PATH"],
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
