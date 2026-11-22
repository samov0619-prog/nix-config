"""Exercise the Nix-rendered AWG scripts without builds, SSH or real VPN changes.

Run: python3 -B hosts/server/tests/test_awg_state.py
Requires nix-instantiate, Bash, awk and standard coreutils/util-linux commands.
AWG, OpenSSL and chown are test doubles; this is not kernel/systemd integration.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
PRIVATE_KEY = "fixture-server-private"
HEADER_KEY = "fixture-header-protection"
INTERFACE = f"""[Interface]
Address = 10.66.0.1/24
ListenPort = 51820
PrivateKey = {PRIVATE_KEY}
HeaderProtectionKey = {HEADER_KEY}"""
PHONE = """[Peer]
# phone
PublicKey = fixture-phone-public
PresharedKey = fixture-phone-preshared
AllowedIPs = 10.66.0.2/32, fd42:1234:5678:1::2/128"""
LAPTOP = """[Peer]
# laptop
PublicKey = fixture-laptop-public
AllowedIPs = 10.66.0.3/32, fd42:1234:5678:1::3/128"""


class AwgStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        expression = f"""let
          module = import {ROOT}/hosts/server/vpn.nix {{
            lib = {{
              mkIf = condition: value: if condition then value else {{}};
              optionalString = condition: value: if condition then value else "";
            }};
            pkgs = {{
              writeText = name: text: {{
                inherit text;
                __toString = _: "/fixture/" + name;
              }};
              writeShellApplication = value: value;
            }};
            serverSettings = {{
              publicEndpoint = "192.0.2.42";
              awgPort = 51820;
              network.ipv4.interface = "fixture0";
              network.ipv6 = null;
            }};
          }};
        in {{
          bootstrap = module.config.systemd.services.amneziawg-bootstrap.script;
          schema = (builtins.head module.config.systemd.services.wg-quick-awg0.restartTriggers).text;
          list = (builtins.elemAt module.config.environment.systemPackages 2).text;
          remove = (builtins.elemAt module.config.environment.systemPackages 1).text;
        }}"""
        result = subprocess.run(
            ["nix-instantiate", "--eval", "--strict", "--json", "--expr", expression],
            check=True,
            capture_output=True,
            text=True,
        )
        cls.source = json.loads(result.stdout)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="awg-state-")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.state = self.work / "state"
        self.profiles = self.work / "profiles"
        self.state.mkdir(mode=0o700)
        self.profiles.mkdir(mode=0o700)
        self.config = self.state / "awg0.conf"
        schema = self.work / "schema"
        schema.write_text(self.source["schema"])
        self.scripts = {
            name: text.replace("/var/lib/amneziawg", str(self.state))
            .replace("/srv/vpn-download/files", str(self.profiles))
            .replace("/fixture/amneziawg-3.1-profile-schema", str(schema))
            for name, text in self.source.items()
            if name != "schema"
        }
        bin_dir = self.work / "bin"
        bin_dir.mkdir()
        commands = {
            "chown": "#!/bin/sh\nexit 0\n",
            "openssl": "#!/bin/sh\nprintf 'fixture-generated-header\\n'\n",
            "awg": """#!/bin/sh
printf '%s\n' "$*" >> "$AWG_TEST_CALLS"
case "$*" in
  genkey) printf 'fixture-generated-private\n' ;;
  'show awg0' | 'show awg0 transfer') exit 0 ;;
  'set awg0 peer fixture-phone-public remove') exit 0 ;;
  *) exit 99 ;;
esac
""",
        }
        for name, text in commands.items():
            command = bin_dir / name
            command.write_text(text)
            command.chmod(0o700)
        self.calls = self.work / "awg-calls"
        self.env = dict(
            os.environ,
            PATH=f"{bin_dir}:{os.environ['PATH']}",
            AWG_TEST_CALLS=str(self.calls),
        )
        self.profile_names = {
            f"{name}{suffix}"
            for name in ("phone", "laptop")
            for suffix in (".conf", ".vpn", ".txt", ".vpn.txt")
        }
        for name in self.profile_names:
            (self.profiles / name).write_text("fixture profile\n")

    def run_script(self, name, *arguments):
        return subprocess.run(
            ["bash", "-euo", "pipefail", "-c", self.scripts[name], name, *arguments],
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
            umask=0o077,
        ).stdout

    def assert_retained(self):
        config = self.config.read_text()
        self.assertIn(f"PrivateKey = {PRIVATE_KEY}\n", config)
        self.assertIn(f"HeaderProtectionKey = {HEADER_KEY}\n", config)
        for peer in (PHONE, LAPTOP):
            for line in peer.splitlines()[1:]:
                self.assertEqual(config.splitlines().count(line), 1, line)
        self.assertEqual(config.count("[Peer]"), 2)
        self.assertEqual(
            {profile.name for profile in self.profiles.iterdir()}, self.profile_names
        )
        for profile in self.profiles.iterdir():
            self.assertEqual(profile.read_text(), "fixture profile\n")
        if self.calls.exists():
            self.assertNotIn("genkey", self.calls.read_text())

    def test_section_separators_do_not_drop_peers_or_break_listing(self):
        for separator in ("\n\n", "\n", "\n   \n", "\n\t\n", "\r\n"):
            with self.subTest(separator=repr(separator)):
                self.config.write_text(separator.join((INTERFACE, PHONE, LAPTOP)) + "\n")
                self.run_script("bootstrap")
                self.assert_retained()
                listing = self.run_script("list")
                self.assertIn("phone", listing)
                self.assertIn("laptop", listing)

    def test_indented_commented_headers_and_crlf_keep_peers(self):
        original = "\n".join((INTERFACE, PHONE, LAPTOP)) + "\n"
        original = original.replace("[Peer]", "  [Peer]  # existing client")
        self.config.write_bytes(original.replace("\n", "\r\n").encode())
        self.run_script("bootstrap")
        self.assert_retained()
        self.assertIn("phone", self.run_script("list"))
        self.assertIn("laptop", self.run_script("list"))

    def test_repeated_bootstrap_is_idempotent(self):
        self.config.write_text("\n".join((INTERFACE, PHONE, LAPTOP)) + "\n")
        self.run_script("bootstrap")
        normalized = self.config.read_bytes()
        for _ in range(3):
            self.run_script("bootstrap")
            self.assertEqual(self.config.read_bytes(), normalized)
            self.assert_retained()

    def test_unnamed_peers_are_retained(self):
        peer = PHONE.replace("# phone\n", "")
        self.config.write_text(INTERFACE + "\n" + peer + "\n")
        self.run_script("bootstrap")
        self.assertIn(peer + "\n", self.config.read_text())
        self.assertIn(f"PrivateKey = {PRIVATE_KEY}\n", self.config.read_text())

    def test_removal_after_reconciliation_keeps_other_client(self):
        self.config.write_text("\n".join((INTERFACE, PHONE, LAPTOP)) + "\n")
        self.run_script("bootstrap")
        self.run_script("remove", "phone")
        config = self.config.read_text()
        self.assertNotIn("fixture-phone-public", config)
        self.assertIn("fixture-laptop-public", config)
        self.assertIn(f"PrivateKey = {PRIVATE_KEY}\n", config)
        for suffix in (".conf", ".vpn", ".txt", ".vpn.txt"):
            self.assertFalse((self.profiles / f"phone{suffix}").exists())
            self.assertTrue((self.profiles / f"laptop{suffix}").exists())

    def test_fresh_bootstrap_still_initializes(self):
        self.run_script("bootstrap")
        config = self.config.read_text()
        self.assertIn("PrivateKey = fixture-generated-private\n", config)
        self.assertIn("HeaderProtectionKey = fixture-generated-header\n", config)
        self.assertNotIn("[Peer]", config)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)

    def test_existing_interface_without_peers_keeps_keys(self):
        self.config.write_text(INTERFACE + "\n")
        self.run_script("bootstrap")
        config = self.config.read_text()
        self.assertIn(f"PrivateKey = {PRIVATE_KEY}\n", config)
        self.assertIn(f"HeaderProtectionKey = {HEADER_KEY}\n", config)
        self.assertNotIn("[Peer]", config)
        self.assertFalse(self.calls.exists())


if __name__ == "__main__":
    unittest.main()
