"""Execute the evaluated HM activation snippet, never a real home/service."""

import json
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest


FIXTURE = json.loads(Path(sys.argv.pop(1)).read_text())["activationFixture"]


class InitialSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="handy-seed-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data with spaces"
        self.target = self.data / "com.pais.handy/settings_store.json"
        source = self.root / "initial settings.json"
        source.write_text(json.dumps(FIXTURE["settings"]))
        # Substitute complete shell-escaped paths, matching lib.escapeShellArg;
        # replacing just the home substring would insert unquoted whitespace.
        old_dir = FIXTURE["dataHome"] + "/com.pais.handy"
        self.script = FIXTURE["script"].replace(
            shlex.quote(old_dir + "/settings_store.json"),
            shlex.quote(str(self.target)),
        ).replace(
            shlex.quote(old_dir), shlex.quote(str(self.target.parent))
        ).replace(FIXTURE["source"], shlex.quote(str(source)))

    def activate(self, dry_run=False):
        run = 'run() { "$@"; }\n' if not dry_run else 'run() { :; }\n'
        subprocess.run(["bash", "-euc", run + self.script], check=True)

    def test_new_store_is_native_json_private_and_not_a_symlink(self):
        self.activate()
        self.assertEqual(json.loads(self.target.read_text()), FIXTURE["settings"])
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o600)

    def test_existing_gui_preferences_and_unknown_fields_are_untouched(self):
        self.target.parent.mkdir(parents=True)
        existing = '{"settings":{"audio_feedback":false,"future_field":"keep"}}\n'
        self.target.write_text(existing)
        self.activate()
        self.assertEqual(self.target.read_text(), existing)

    def test_even_malformed_existing_store_is_not_overwritten(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text("not JSON; preserve for recovery")
        self.activate()
        self.assertEqual(self.target.read_text(), "not JSON; preserve for recovery")

    def test_dangling_symlink_is_not_followed_or_replaced(self):
        self.target.parent.mkdir(parents=True)
        missing = self.root / "missing.json"
        self.target.symlink_to(missing)
        self.activate()
        self.assertTrue(self.target.is_symlink())
        self.assertFalse(missing.exists())

    def test_existing_symlink_target_is_not_changed(self):
        self.target.parent.mkdir(parents=True)
        other = self.root / "other.json"
        other.write_text("keep this file")
        self.target.symlink_to(other)
        self.activate()
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(other.read_text(), "keep this file")

    def test_second_activation_does_not_reset_gui_changes(self):
        self.activate()
        changed = {"settings": {"audio_feedback": False}}
        self.target.write_text(json.dumps(changed))
        self.activate()
        self.assertEqual(json.loads(self.target.read_text()), changed)

    def test_dry_run_does_not_create_a_store(self):
        self.activate(dry_run=True)
        self.assertFalse(self.data.exists())


if __name__ == "__main__":
    unittest.main()
