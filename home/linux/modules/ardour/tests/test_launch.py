"""Isolated startup-wrapper tests; never start Ardour or access personal settings."""

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


SCRIPT = Path(__file__).resolve().parents[1] / "launch.py"
spec = importlib.util.spec_from_file_location("ardour_theme", SCRIPT)
theme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(theme)
FIXTURE = b'''<?xml version="1.0" encoding="UTF-8"?>
<Ardour><UI>
<!-- Keep the user's preferences -->
<Option name="font-scale" value="102400"/>
<Option name="color-file" value="onedark"/>
</UI><Canvas><Option name="custom" value="keep &amp; this"/></Canvas></Ardour>
'''


class StartupThemeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="ardour-theme-", dir="/tmp/opencode")
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        self.config = self.home / "config with spaces"
        self.path = self.config / "ardour9/ui_config"
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(FIXTURE)
        self.path.chmod(0o600)
        self.dconf = self.home / "dconf"
        self.set_mode("prefer-light")
        self.fake = self.home / "fake-ardour"
        # The actual launcher execs this harmless stand-in, with all arguments.
        self.fake.write_text(
            f"#!{sys.executable}\n"
            "import fcntl,json,os,pathlib,sys\n"
            "p=pathlib.Path(os.environ['XDG_CACHE_HOME'])/'ardour-system-theme/launch.lock'\n"
            "with p.open('a') as lock:\n"
            " try:\n"
            "  fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "  held=False\n"
            " except BlockingIOError:\n"
            "  held=True\n"
            "print(json.dumps({'args':sys.argv[1:], 'lockHeld':held}))\n"
            "sys.exit(int(os.environ.get('FIXTURE_EXIT', '0')))\n"
        )
        self.fake.chmod(0o700)

    def set_mode(self, mode):
        self.dconf.write_text(f"#!/bin/sh\nprintf \"'{mode}'\\n\"\n")
        self.dconf.chmod(0o700)

    def launch(self, args=(), extra_env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--major", "9", "--dconf", str(self.dconf),
             "--", str(self.fake), *args],
            env=os.environ | {
                "HOME": str(self.home),
                "XDG_CONFIG_HOME": str(self.config),
                "XDG_CACHE_HOME": str(self.home / "cache"),
            } | (extra_env or {}),
            capture_output=True,
            text=True,
            timeout=5,
        )

    def palette(self):
        return ET.parse(self.path).find("UI/Option[@name='color-file']").get("value")

    def test_actual_launch_light_dark_arguments_exit_and_inherited_lock(self):
        for mode, expected in (("prefer-light", "captain_light"), ("prefer-dark", "dark")):
            with self.subTest(mode=mode):
                self.set_mode(mode)
                result = self.launch(["--new", "a session; no shell"], {"FIXTURE_EXIT": "7"})
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout), {
                    "args": ["--new", "a session; no shell"], "lockHeld": True,
                })
                self.assertEqual(self.palette(), expected)

    def test_only_palette_changes_semantically_and_original_backup_survives(self):
        before = ET.fromstring(FIXTURE)
        for selected in ("captain_light", "dark"):
            theme.apply_theme(self.path, selected)
            after = ET.parse(self.path).getroot()
            before.find("UI/Option[@name='color-file']").set("value", selected)
            self.assertEqual(ET.tostring(after), ET.tostring(before))
            self.assertIn(b"<!-- Keep the user's preferences -->", self.path.read_bytes())
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.path.with_name("ui_config.before-system-theme").read_bytes(), FIXTURE)

    def test_default_option_can_be_absent(self):
        self.path.write_text('<Ardour><UI/><Canvas/></Ardour>')
        theme.apply_theme(self.path, "captain_light")
        self.assertEqual(self.palette(), "captain_light")

    def test_no_rewrite_when_theme_already_matches(self):
        theme.apply_theme(self.path, "dark")
        before = self.path.stat()
        theme.apply_theme(self.path, "dark")
        after = self.path.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))

    def test_first_run_does_not_create_config_or_touch_legacy(self):
        self.path.unlink()
        self.path.parent.rmdir()
        old = self.config / "ardour8/ui_config"
        old.parent.mkdir()
        old.write_bytes(FIXTURE)
        self.assertEqual(self.launch().returncode, 0)
        self.assertFalse(self.path.parent.exists())
        self.assertEqual(old.read_bytes(), FIXTURE)

    def test_bad_or_ambiguous_xml_is_preserved_and_does_not_block_launch(self):
        for content in (b"not xml", b"<Other/>", b"<Ardour><UI/><UI/></Ardour>",
                        b'<Ardour><UI><Option name="color-file"/><Option name="color-file"/></UI></Ardour>'):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                result = self.launch()
                self.assertEqual(result.returncode, 0)
                self.assertIn("startup theme skipped", result.stderr)
                self.assertEqual(self.path.read_bytes(), content)

    def test_unknown_or_failed_desktop_read_leaves_settings_alone(self):
        self.set_mode("unknown")
        self.assertEqual(self.launch().returncode, 0)
        self.assertEqual(self.path.read_bytes(), FIXTURE)
        self.dconf.write_text("#!/bin/sh\nexit 1\n")
        self.assertEqual(self.launch().returncode, 0)
        self.assertEqual(self.path.read_bytes(), FIXTURE)

    def test_default_and_unset_desktop_modes_select_light(self):
        for value in ("'default'", ""):
            with self.subTest(value=value):
                self.dconf.write_text(f"#!/bin/sh\nprintf '%s' \"{value}\"\n")
                self.assertEqual(theme.system_theme(str(self.dconf)), "captain_light")

    def test_help_and_version_do_not_change_settings(self):
        for flag in ("--help", "--version", "-h", "-v"):
            with self.subTest(flag=flag):
                # Fake executable needs its lock parent for its reporting only.
                (self.home / "cache/ardour-system-theme").mkdir(parents=True, exist_ok=True)
                self.assertEqual(self.launch([flag]).returncode, 0)
                self.assertEqual(self.path.read_bytes(), FIXTURE)

    def test_symlink_is_not_replaced_or_followed_for_writes(self):
        target = self.home / "keep.xml"
        self.path.rename(target)
        self.path.symlink_to(target)
        result = self.launch()
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.path.is_symlink())
        self.assertEqual(target.read_bytes(), FIXTURE)

    def test_second_launcher_does_not_edit_a_running_instances_settings(self):
        directory = self.home / "cache/ardour-system-theme"
        directory.mkdir(parents=True)
        with (directory / "launch.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.launch()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.path.read_bytes(), FIXTURE)

    def test_process_guard_recognizes_upstream_binary_not_just_wrappers(self):
        proc = self.home / "proc"
        entry = proc / "1234"
        entry.mkdir(parents=True)
        (entry / "exe").symlink_to("/nix/store/fixture/lib/ardour9/ardour-9.7.0")
        self.assertTrue(theme.running_ardour(proc))
        (entry / "exe").unlink()
        (entry / "exe").symlink_to("/bin/not-ardour")
        self.assertFalse(theme.running_ardour(proc))

    def test_protected_process_falls_back_to_linux_command_name(self):
        proc = self.home / "proc"
        entry = proc / "1234"
        entry.mkdir(parents=True)
        command = entry / "comm"
        with patch.object(Path, "readlink", side_effect=PermissionError):
            command.write_text("unrelated\n")
            self.assertFalse(theme.running_ardour(proc))
            command.write_text("ardour-9.7.0\n")
            self.assertTrue(theme.running_ardour(proc))

    def test_generated_nix_launcher_uses_the_helper_without_starting_ardour(self):
        repository = SCRIPT.resolve().parents[4]
        expression = '''let
          f = builtins.getFlake (toString ./.);
          p = f.inputs.nixpkgs.legacyPackages.x86_64-linux;
          w = p.callPackage ./home/linux/modules/ardour/package.nix {};
        in { script = w.launcher.text; python = "${p.python3}/bin/python3";
          dconf = "${p.dconf}/bin/dconf";
          ardour = "${p.ardour}/bin/${p.ardour.meta.mainProgram}"; }'''
        generated = json.loads(subprocess.check_output(
            ["nix", "eval", "--impure", "--offline", "--json",
             "--option", "allow-import-from-derivation", "false", "--expr", expression],
            cwd=repository, text=True,
        ))
        # Substitute only executables: run the real Nix-generated shell and
        # store copy of launch.py, but never the real dconf or Ardour commands.
        script = generated["script"].replace(generated["python"], sys.executable)
        script = script.replace(generated["dconf"], str(self.dconf))
        script = script.replace(generated["ardour"], str(self.fake))
        launcher = self.home / "generated-launcher"
        launcher.write_text(script)
        launcher.chmod(0o700)
        result = subprocess.run([str(launcher), "project with spaces"], capture_output=True,
            text=True, check=True, env=os.environ | {
                "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.config),
                "XDG_CACHE_HOME": str(self.home / "cache"),
            })
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.palette(), "captain_light")
        self.assertEqual(json.loads(result.stdout), {
            "args": ["project with spaces"], "lockHeld": True,
        })

    def test_actual_f11_leaves_all_ardour_configs_untouched(self):
        legacy = self.config / "ardour8/ui_config"
        legacy.parent.mkdir()
        legacy.write_bytes(FIXTURE)
        commands = self.home / "bin"
        commands.mkdir()
        for name, body in {
            "dconf": "case \"$1\" in read) printf \"'prefer-dark'\\n\" ;; write) exit 0 ;; esac",
            "qt-theme-apply": "exit 0",
            "hyprctl": "exit 0",
        }.items():
            command = commands / name
            command.write_text("#!/bin/sh\n" + body + "\n")
            command.chmod(0o700)
        script = SCRIPT.parent.parent / "hyprland/scripts/toggle-theme.sh"
        subprocess.run(["sh", str(script)], check=True, capture_output=True, env=os.environ | {
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.config),
            "PATH": str(commands) + os.pathsep + os.environ["PATH"],
        })
        self.assertEqual(self.path.read_bytes(), FIXTURE)
        self.assertEqual(legacy.read_bytes(), FIXTURE)


if __name__ == "__main__":
    unittest.main()
