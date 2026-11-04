"""Small local tests: fake Nix builds, real shell scripts and lazy flake wiring.

Run from the repository root: python3 hosts/server/tests/test_settings.py
Requires nix-instantiate; put jq on PATH to include preflight tests.
No project builds, SSH, or external settings are used.
"""

import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]


def evaluate(expression):
    return subprocess.run(
        ["nix-instantiate", "--eval", "--strict", "--json", "--expr", expression],
        capture_output=True,
        text=True,
    )


class SettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = evaluate(
            f"""let m = import {ROOT}/home/core-set/nix-flake-update-verify.nix {{
              pkgs = {{ coreutils = null; git = null; nix = null; python3 = null;
                writeShellApplication = x: x; }};
            }}; in (builtins.head m.home.packages).text"""
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        cls.script = json.loads(result.stdout)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="server-settings-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.log = self.work / "nix-calls.jsonl"
        self.env = dict(os.environ)
        self.env.update(
            HOME=str(self.work),
            XDG_CONFIG_HOME=str(self.work / "config"),
            PATH=f"{self.bin}:{os.environ['PATH']}",
        )
        self.env.pop("SERVER_SETTINGS_DIR", None)
        self.env.pop("SERVER_SETTINGS_FILE", None)
        self.default = self.work / "config/nix-config/server"
        self.command("git", f"#!/bin/sh\nprintf '%s\\n' '{self.work}'\n")
        self.command("uname", "#!/bin/sh\nprintf 'Linux\\n'\n")
        self.command(
            "nix",
            f"""#!{os.sys.executable}
import json, os, sys
with open({str(self.log)!r}, 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1] == 'build':
    sys.exit(int(os.environ.get('MOCK_BUILD_EXIT', '0')))
""",
        )

    def command(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o755)

    def settings(self, directory):
        directory.mkdir(parents=True)
        (directory / "settings.nix").write_text('{ publicEndpoint = "192.0.2.42"; }')

    def verify(self, *arguments):
        return subprocess.run(
            ["bash", "-c", self.script, "verify", *arguments],
            env=self.env,
            cwd=self.work,
            capture_output=True,
            text=True,
        )

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_laptop_does_not_require_or_override_server_settings(self):
        result = self.verify("--hosts", "laptop", "--no-update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls()), 2)
        self.assertTrue(all("--override-input" not in call for call in self.calls()))

    def test_server_override_is_not_used_for_lock_update_or_home_manager(self):
        self.settings(self.default)
        result = self.verify("--hosts", "server", "--input", "nixpkgs")
        self.assertEqual(result.returncode, 0, result.stderr)
        update, system, home = self.calls()
        self.assertEqual(update, ["flake", "update", "nixpkgs"])
        self.assertIn(f"path:{self.default}", system)
        self.assertIn("--no-write-lock-file", system)
        self.assertNotIn("--override-input", home)

    def test_missing_settings_stop_all_before_update_or_build(self):
        result = self.verify("--hosts", "all", "--input", "all")
        self.assertEqual(result.returncode, 2)
        self.assertIn("phase=settings", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_installer_accepts_explicit_path_with_spaces(self):
        directory = self.work / "custom settings"
        self.settings(directory)
        result = self.verify(
            "--hosts", "server-installer", "--no-update",
            "--server-settings", str(directory),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_settings_reference(self.calls()[0], directory)

    def assert_settings_reference(self, call, directory):
        reference = call[call.index("--override-input") + 2]
        # Parse the generated reference with real Nix, not the build mock.
        parsed = evaluate(f"builtins.parseFlakeRef {json.dumps(reference, ensure_ascii=False)}")
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertEqual(
            json.loads(parsed.stdout),
            {"type": "path", "path": str(directory.resolve())},
        )

    def test_settings_path_preserves_uri_delimiters_percent_and_unicode(self):
        directory = self.work / "settings #?%+é"
        self.settings(directory)
        result = self.verify(
            "--hosts", "server", "--no-update", "--server-settings", str(directory)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_settings_reference(self.calls()[0], directory)

    def test_environment_override_and_build_failure(self):
        directory = self.work / "external"
        self.settings(directory)
        self.env["SERVER_SETTINGS_DIR"] = str(directory)
        self.env["MOCK_BUILD_EXIT"] = "7"
        result = self.verify("--hosts", "server", "--no-update")
        self.assertEqual(result.returncode, 7)
        self.assertIn("phase=build", result.stderr)
        self.assertEqual(len(self.calls()), 1)

    def wiring(self, settings, selection):
        # Use actual outputs/module composition without evaluating nixpkgs or derivations.
        return evaluate(
            f"""let f = import {ROOT}/flake.nix; outputs = f.outputs {{
              self = {{}};
              nixpkgs.lib.nixosSystem = x: x;
              nixpkgs-unstable = null; home-manager = null;
              browser-previews = null; disko = null; freesm = null;
              nix-gc-env = null; xremap-flake = null; hermes-agent = null;
              opencode = null; server-settings = {json.dumps(str(settings))};
            }}; in {selection}"""
        )

    def test_both_server_outputs_receive_the_same_input(self):
        self.settings(self.default)
        result = self.wiring(
            self.default,
            "builtins.map (name: outputs.nixosConfigurations.${name}.specialArgs.serverSettings.publicEndpoint) [\"server\" \"server-installer\"]",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ["192.0.2.42", "192.0.2.42"])

    def test_default_fails_for_server_but_does_not_force_laptop(self):
        settings = ROOT / "hosts/server/settings-template"
        server = self.wiring(
            settings, "outputs.nixosConfigurations.server.specialArgs.serverSettings"
        )
        self.assertNotEqual(server.returncode, 0)
        self.assertIn("Server settings were not selected", server.stderr)
        laptop = self.wiring(settings, "outputs.nixosConfigurations.laptop.system")
        self.assertEqual(laptop.returncode, 0, laptop.stderr)
        self.assertEqual(json.loads(laptop.stdout), "x86_64-linux")

    def preflight(self, ipv6_answer, save_answer):
        if not shutil.which("jq"):
            self.skipTest("jq is required for the real preflight parser")
        inventory = [
            {"blockdevices": [{"path": "/dev/vda", "size": "40G", "type": "disk", "ro": False}]},
            [{"ifname": "ens3", "addr_info": [{"family": "inet", "scope": "global", "local": "198.51.100.4", "prefixlen": 24}]}],
            [{"dev": "ens3", "gateway": "198.51.100.1"}],
            [], [], [], {"id": "debian", "variantId": ""},
        ]
        probe = "\n".join(json.dumps(item) for item in inventory)
        self.command("ssh", f"#!/bin/sh\ncat <<'PROBE'\n{probe}\nPROBE\n")
        answers = [""] * 6 + ["ssh-ed25519 AAAA fixture", "", "", ipv6_answer, save_answer]
        return subprocess.run(
            ["sh", str(ROOT / "hosts/server/preflight.sh"), "fixture-host"],
            input="\n".join(answers) + "\n",
            cwd=self.work,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_preflight_writes_only_confirmed_external_settings(self):
        result = self.preflight("y", "y")
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.default / "settings.nix"
        self.assertTrue(path.exists())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        parsed = evaluate(f"(import {path}).network.ipv4.address")
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertEqual(json.loads(parsed.stdout), "198.51.100.4")
        self.assertIn("--store-paths", result.stdout)
        self.assertFalse((self.work / "hosts/server/settings.nix").exists())

    def test_preflight_decline_does_not_create_settings_directory(self):
        result = self.preflight("y", "n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.default.exists())

    def test_preflight_ipv6_decline_preserves_existing_settings(self):
        self.settings(self.default)
        path = self.default / "settings.nix"
        before = path.read_bytes()
        result = self.preflight("n", "y")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
