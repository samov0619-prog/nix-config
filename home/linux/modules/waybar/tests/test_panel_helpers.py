"""Isolated panel/menu checks: fake Nix, journal, GPU and power commands only."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


MODULE = Path(__file__).resolve().parents[1]
SCRIPTS = MODULE / "scripts"
TOFI = MODULE.parent / "tofi/module.nix"


class PanelHelpersTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="panel-helpers-", dir="/tmp/opencode"
        )
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.flake = self.root / "flake"
        self.flake.mkdir()
        self.lock = self.flake / "flake.lock"
        self.lock.write_text('{"fixture": "old"}\n')
        self.cache = self.root / "cache/waybar-nix-updates"
        self.cache.parent.mkdir()
        self.environment = os.environ.copy()
        self.environment.update(
            HOME=str(self.root), XDG_CACHE_HOME=str(self.cache.parent),
            NIX_FLAKE=str(self.flake), PATH=f"{self.bin}:{os.environ['PATH']}",
            FIXTURE_ROOT=str(self.root),
        )
        self.fake("nix", r"""
import json, os, pathlib, sys
root = pathlib.Path(os.environ['FIXTURE_ROOT'])
args = sys.argv[1:]
assert args[:3] == ['flake', 'update', '--flake']
assert args[3] == os.environ['NIX_FLAKE']
assert args[4] == '--output-lock-file' and len(args) == 6
(root / 'nix-call.json').write_text(json.dumps(args))
mode = os.environ.get('NIX_MODE', 'clean')
if mode == 'fail': sys.exit(1)
lock = root / 'flake/flake.lock'
pathlib.Path(args[5]).write_text(lock.read_text() if mode == 'clean' else '{}\n')
""")

    def fake(self, name, source):
        path = self.bin / name
        path.write_text(f"#!{os.sys.executable}\n" + source)
        path.chmod(0o755)

    def run_script(self, name):
        return subprocess.run(
            ["/bin/sh", str(SCRIPTS / name)], cwd=self.root,
            env=self.environment, capture_output=True, text=True, timeout=5,
        )

    def view(self, state):
        self.cache.write_text(state)
        result = self.run_script("nix-updates-view.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_view_matches_lock_and_detects_changed_lock(self):
        digest = hashlib.sha256(self.lock.read_bytes()).hexdigest()
        for state, expected in ((f"clean:{digest}", "updated"),
                                (f"pending:{digest}", "pending-updates"),
                                ("clean:old", "unknown"), ("pending:", "unknown")):
            with self.subTest(state=state):
                self.assertEqual(self.view(state)["class"], expected)

    def test_view_cannot_claim_freshness_without_workspace_or_lock(self):
        for flake in ("", str(self.root / "missing"), str(self.flake)):
            self.environment["NIX_FLAKE"] = flake
            if flake == str(self.flake):
                self.lock.unlink()
            for state in ("clean:old", "pending:old"):
                with self.subTest(flake=flake, state=state):
                    self.assertEqual(self.view(state)["class"], "unknown")

    def test_view_loading_error_and_empty_cache(self):
        self.assertEqual(json.loads(self.run_script("nix-updates-view.sh").stdout)["class"],
                         "unknown")
        for state, expected in (("loading", "loading"), ("error:nix", "update-error"),
                                ("", "unknown"), ("other", "unknown")):
            with self.subTest(state=state):
                self.assertEqual(self.view(state)["class"], expected)

    def test_update_check_only_writes_temporary_lock(self):
        original = self.lock.read_bytes()
        temporary = self.root / "temporary"
        temporary.mkdir()
        self.environment["TMPDIR"] = str(temporary)
        for mode, expected in (("clean", "clean:"), ("pending", "pending:"),
                               ("fail", "error:nix")):
            with self.subTest(mode=mode):
                (self.root / "nix-call.json").unlink(missing_ok=True)
                self.environment["NIX_MODE"] = mode
                result = self.run_script("check-nix-updates.sh")
                self.assertEqual(result.returncode, 0, result.stderr)
                state = ("error:nix\n" if mode == "fail" else
                         f"{expected}{hashlib.sha256(original).hexdigest()}\n")
                self.assertEqual(self.cache.read_text(), state)
                self.assertEqual(self.lock.read_bytes(), original)
                self.assertTrue((self.root / "nix-call.json").is_file())
                self.assertEqual(list(temporary.iterdir()), [])

    def test_update_preflight_never_calls_nix(self):
        for flake, expected in (("", "no_env"), (str(self.root / "missing"), "not_dir"),
                                (str(self.flake), "no_lock")):
            with self.subTest(flake=flake):
                self.environment["NIX_FLAKE"] = flake
                if expected == "no_lock":
                    self.lock.unlink()
                result = self.run_script("check-nix-updates.sh")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.cache.read_text(), f"error:{expected}\n")
                self.assertFalse((self.root / "nix-call.json").exists())

    def test_session_menu_exact_actions_and_cancel(self):
        match = re.search(r'writeShellScriptBin "tofi-sessionmenu" \'\'(.*?)\'\'',
                          TOFI.read_text(), re.S)
        self.assertIsNotNone(match)
        script = self.root / "session.sh"
        script.write_text(match.group(1).replace("${pkgs.runtimeShell}", "/bin/sh"))
        self.fake("tofi", """
import os, sys
sys.stdin.read()
print(os.environ['CHOICE'])
sys.exit(int(os.environ.get('CANCEL', '0')))
""")
        self.fake("systemctl", """
import json, os, pathlib, sys
assert sys.argv[1:] in (['poweroff'], ['reboot'])
(pathlib.Path(os.environ['FIXTURE_ROOT']) / 'power.json').write_text(json.dumps(sys.argv[1:]))
""")
        output = self.root / "power.json"
        for choice, cancel, expected in (("Poweroff", "0", ["poweroff"]),
                                         ("Reboot", "0", ["reboot"]),
                                         ("Poweroff", "1", None), ("custom", "0", None)):
            with self.subTest(choice=choice, cancel=cancel):
                output.unlink(missing_ok=True)
                self.environment.update(CHOICE=choice, CANCEL=cancel)
                result = subprocess.run(
                    ["/bin/sh", str(script)], cwd=self.root, env=self.environment,
                    capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = json.loads(output.read_text()) if output.exists() else None
                self.assertEqual(actual, expected)

    def test_gpu_helper_with_fake_single_gpu_and_failure(self):
        linux = MODULE.parent.parent
        for profile in ("laptop-old", "desktop"):
            self.assertIn("gp.sh", (linux / profile / "waybar-config.jsonc").read_text())
        self.assertNotIn("gp.sh", (linux / "laptop/waybar-config.jsonc").read_text())
        self.fake("nvidia-smi", """
import os, sys
print('12, 345')
sys.exit(int(os.environ.get('GPU_FAIL', '0')))
""")
        result = self.run_script("gp.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "gpu:12%|0.3GB ")
        self.environment["GPU_FAIL"] = "1"
        self.assertNotEqual(self.run_script("gp.sh").returncode, 0)

    def test_startup_helper_with_fake_journal(self):
        self.fake("journalctl", "import os\nprint(os.environ.get('JOURNAL', ''))\n")
        for duration in (None, "18.2s", "1min 3.5s", "1h 2min 3.5s"):
            with self.subTest(duration=duration):
                self.environment["JOURNAL"] = (
                    f"fixture systemd[1]: Startup finished in 1s (kernel) = {duration}."
                    if duration else ""
                )
                result = self.run_script("startup-time.sh")
                self.assertEqual(result.returncode, 0, result.stderr)
                value = json.loads(result.stdout)
                self.assertEqual(value["text"], duration or "N/A")
                if duration is None:
                    self.assertEqual(value["class"], "startup_gray")
                elif "min" in duration:
                    self.assertEqual(value["class"], "startup_red")


if __name__ == "__main__":
    unittest.main()
