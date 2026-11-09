"""Exercise the actual Nix-declared hook in isolated Fish processes, with fake keys."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


class FishLocalEnvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fish = shutil.which("fish")
        if not cls.fish or not shutil.which("nix"):
            raise RuntimeError("Tests require already-installed Fish and Nix")
        repository = Path(__file__).resolve().parents[2]
        expression = (
            "(import ./home/core-set/shell.nix "
            "{ pkgsUnstable = {}; lib = {}; config = {}; })"
            ".programs.fish.interactiveShellInit"
        )
        cls.hook = subprocess.check_output(
            ["nix", "eval", "--impure", "--offline", "--raw", "--expr", expression],
            cwd=repository,
            text=True,
        )

    def setUp(self):
        directory = tempfile.TemporaryDirectory(
            prefix="fish-local-env-", dir="/tmp/opencode"
        )
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.config = self.root / ".config"
        self.path = self.config / "fish/local-env.fish"

    def write_local(self, text):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(text)
        self.path.chmod(0o600)

    def run_hook(self, keys, inherited=None):
        hook = self.root / "hook.fish"
        hook.write_text(self.hook)
        report = (
            "import json,os; print(json.dumps("
            + "{key:os.environ.get(key) for key in "
            + repr(keys)
            + "}))"
        )
        # Only these artificial variables are reported, never the inherited env.
        env = os.environ | {
            "HOME": str(self.root),
            "XDG_CONFIG_HOME": str(self.config),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
        }
        for key in keys:
            env.pop(key, None)
        env.update(inherited or {})
        command = (
            f"source {shlex.quote(str(hook))}\n"
            f"command {shlex.quote(sys.executable)} -c {shlex.quote(report)}"
        )
        result = subprocess.run(
            [self.fish, "--no-config", "-c", command],
            cwd=self.root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_missing_file_is_optional_and_not_created(self):
        self.assertEqual(self.run_hook(["AUDIT_LOCAL_KEY"]), {"AUDIT_LOCAL_KEY": None})
        self.assertFalse(self.path.exists())

    def test_native_values_are_exported_exactly(self):
        expected = {
            "AUDIT_PADDED": "abc==",
            "AUDIT_URL": "https://example.invalid/api?x=1&y=2",
            "AUDIT_SPACES": "  two words  ",
            "AUDIT_EMPTY": "",
            "AUDIT_LITERAL": "$HOME $(touch injected); (touch injected)",
            "AUDIT_UNICODE": "пример=значение",
            "AUDIT_QUOTE": "it's a fixture",
        }
        self.write_local(
            "# Only fake values. Single quotes prevent variable/command expansion.\n\n"
            + "".join(
                f"set -gx {key} '{value}'\n"
                for key, value in expected.items()
                if key != "AUDIT_QUOTE"
            )
            + "set -gx AUDIT_QUOTE 'it\\'s a fixture'\n"
        )
        self.assertEqual(self.run_hook(list(expected)), expected)
        self.assertFalse((self.root / "injected").exists())

    def test_global_export_overrides_inherited_value(self):
        self.write_local("set -gx AUDIT_LOCAL_KEY 'local-value'\n")
        self.assertEqual(
            self.run_hook(["AUDIT_LOCAL_KEY"], {"AUDIT_LOCAL_KEY": "inherited"}),
            {"AUDIT_LOCAL_KEY": "local-value"},
        )

    def test_file_contents_permissions_and_identity_are_preserved(self):
        text = "# Hand-maintained\nset -gx AUDIT_LOCAL_KEY 'keep=='\n"
        self.write_local(text)
        before = self.path.stat()
        for _ in range(2):
            self.assertEqual(
                self.run_hook(["AUDIT_LOCAL_KEY"]), {"AUDIT_LOCAL_KEY": "keep=="}
            )
        after = self.path.stat()
        self.assertEqual(self.path.read_text(), text)
        self.assertEqual(after.st_mode & 0o777, 0o600)
        self.assertEqual(after.st_ino, before.st_ino)
        self.assertEqual(after.st_mtime_ns, before.st_mtime_ns)

    def test_new_session_reads_updated_file(self):
        self.write_local("set -gx AUDIT_LOCAL_KEY 'first'\n")
        self.assertEqual(
            self.run_hook(["AUDIT_LOCAL_KEY"]), {"AUDIT_LOCAL_KEY": "first"}
        )
        self.write_local("set -gx AUDIT_LOCAL_KEY 'second'\n")
        self.assertEqual(
            self.run_hook(["AUDIT_LOCAL_KEY"]), {"AUDIT_LOCAL_KEY": "second"}
        )

    def test_old_dotenv_is_not_read_or_changed(self):
        old = self.root / ".config/llm-secrets/env"
        old.parent.mkdir(parents=True)
        text = "AUDIT_OLD_KEY=old==\n"
        old.write_text(text)
        self.assertEqual(self.run_hook(["AUDIT_OLD_KEY"]), {"AUDIT_OLD_KEY": None})
        self.assertEqual(old.read_text(), text)
        self.assertFalse(self.path.exists())

    def test_custom_xdg_config_home_with_spaces(self):
        self.config = self.root / "custom config"
        self.path = self.config / "fish/local-env.fish"
        self.write_local("set -gx AUDIT_LOCAL_KEY 'custom'\n")
        self.assertEqual(
            self.run_hook(["AUDIT_LOCAL_KEY"]), {"AUDIT_LOCAL_KEY": "custom"}
        )


if __name__ == "__main__":
    unittest.main()
