"""Local fixtures: no privilege elevation, network changes, real VPN or builds.

Optional --quick-source runs the pinned upstream quick script with fake commands.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer_vpn", ROOT / "installer-vpn.py")
vpn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpn)
QUICK_SOURCE = None
TEST_TMP = "/tmp/opencode" if Path("/tmp/opencode").is_dir() else None
PROFILE = """[Interface]
Address = 10.66.0.2/32, fd00:66::2/128
PrivateKey = PRIVATE_FIXTURE_NOT_A_REAL_KEY
DNS = 10.66.0.1
Jc = 4
Jmin = 10
Jmax = 50
S1 = 32
S2 = 32
S3 = 32
S4 = 32
H1 = 1
H2 = 2
H3 = 3
H4 = 4
HeaderProtectionKey = HEADER_FIXTURE_NOT_A_REAL_KEY
RandomTrailers = on
DisableCookies = on

[Peer]
PublicKey = PUBLIC_FIXTURE_NOT_A_REAL_KEY
Endpoint = 192.0.2.42:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""


class InstallerVpnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="installer-vpn-test-", dir=TEST_TMP)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.profile = self.root / "lenovo.conf"
        self.profile.write_text(PROFILE)
        self.profile.chmod(0o600)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in (("RUNTIME_DIR", str(self.root)),):
            self.stack.enter_context(patch.object(vpn, name, value))
        self.stack.enter_context(patch.dict(os.environ, {}, clear=True))
        self.stack.enter_context(patch.object(vpn.os, "geteuid", return_value=0))

    def main(self, action, run):
        output = io.StringIO()
        with patch.object(vpn, "run", side_effect=run), contextlib.redirect_stdout(output):
            code = vpn.main([action, str(self.profile)])
        return code, output.getvalue()

    def test_native_profile_is_forwarded_byte_for_byte_in_private_runtime_snapshot(self):
        def run(command):
            self.assertEqual(command[:2], [vpn.QUICK, "up"])
            snapshot = Path(command[2])
            self.assertEqual(snapshot.name, "lenovo.conf")
            self.assertEqual(snapshot.read_bytes(), self.profile.read_bytes())
            self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)
            self.assertEqual(snapshot.parent.stat().st_mode & 0o777, 0o700)
            self.assertNotEqual(snapshot, self.profile)
            return 0, b""

        original = self.profile.read_bytes()
        code, output = self.main("up", run)
        self.assertEqual(code, 0)
        self.assertIn("NOT yet verified", output)
        self.assertEqual(self.profile.read_bytes(), original)
        self.assertEqual(list(self.root.glob("installer-vpn-*")), [])

    def test_rejects_hooks_routing_overrides_unknown_and_duplicate_directives(self):
        for directive in ("PreUp = touch /tmp/never", "PostDown = true", "Table = off",
                          "SaveConfig = true", "Unknown = SECRET", "DNS = 1.1.1.1"):
            with self.subTest(directive=directive):
                self.profile.write_text(PROFILE.replace("Jc = 4", directive + "\nJc = 4"))
                with self.assertRaises(vpn.Failure), patch.object(vpn, "run") as run:
                    vpn.main(["up", str(self.profile)])
                run.assert_not_called()

    def test_rejects_nonprivate_profile_and_store_path_even_via_symlink(self):
        self.profile.chmod(0o644)
        with self.assertRaisesRegex(vpn.Failure, "chmod 600"):
            vpn.read_profile(self.profile)
        alias = self.root / "external.conf"
        alias.symlink_to("/nix/store/existing.conf")
        with patch.object(Path, "resolve", return_value=Path("/nix/store/existing.conf")):
            with self.assertRaisesRegex(vpn.Failure, "outside /nix/store"):
                vpn.profile_path(alias)

    def test_requires_native_awg31_full_tunnel_with_numeric_dns(self):
        cases = [
            PROFILE.replace("HeaderProtectionKey = HEADER_FIXTURE_NOT_A_REAL_KEY\n", ""),
            PROFILE.replace("0.0.0.0/0, ::/0", "0.0.0.0/0"),
            PROFILE.replace("DNS = 10.66.0.1", "DNS = dns.example.test"),
            PROFILE + "\n[Peer]\nPublicKey = ANOTHER\n",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.profile.write_text(text)
                with self.assertRaises(vpn.Failure):
                    vpn.read_profile(self.profile)

    def test_elevation_uses_absolute_runtime_paths_not_keys(self):
        class Elevated(Exception):
            pass

        os.environ["SSH_CONNECTION"] = "192.168.0.10 1234 192.168.0.100 22"
        with patch.object(vpn.os, "geteuid", return_value=1000):
            with patch.object(vpn.os, "execv", side_effect=Elevated) as execute:
                with self.assertRaises(Elevated):
                    vpn.main(["up", str(self.profile)])
        program, command = execute.call_args.args
        self.assertEqual(program, vpn.SUDO)
        self.assertEqual(command[:4], [vpn.SUDO, "--", vpn.PYTHON, "-I"])
        self.assertIn(str(self.profile), command)
        self.assertEqual(command[-2:], ["--ssh-peer", "192.168.0.10"])
        self.assertNotIn("PRIVATE_FIXTURE", " ".join(command))

    def test_lan_ssh_route_is_checked_before_and_after_up(self):
        os.environ["SSH_CONNECTION"] = "192.168.0.10 1234 192.168.0.100 22"
        calls = []

        def run(command):
            calls.append(command)
            if command[0] == vpn.IP:
                return 0, json.dumps([{"dst": "192.168.0.0/24", "dev": "wlan0"}]).encode()
            return 0, b""

        self.main("up", run)
        self.assertEqual(len(calls), 3)
        self.assertIn("fibmatch", calls[0])
        self.assertEqual(calls[1][1], "up")
        self.assertEqual(calls[2][-1], "192.168.0.10")

    def test_ssh_over_default_route_is_refused_without_network_changes(self):
        os.environ["SSH_CONNECTION"] = "198.51.100.10 1234 192.168.0.100 22"
        with patch.object(vpn, "run", return_value=(0, b'[{"dst":"default","dev":"wlan0"}]')) as run:
            with self.assertRaisesRegex(vpn.Failure, "default route"):
                vpn.main(["up", str(self.profile)])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], vpn.IP)

    def test_unexpected_ssh_route_change_rolls_back(self):
        os.environ["SSH_CONNECTION"] = "192.168.0.10 1234 192.168.0.100 22"
        calls = []

        def run(command):
            calls.append(command)
            if command[0] == vpn.IP:
                dev = "wlan0" if "fibmatch" in command else "lenovo"
                return 0, json.dumps([{"dst": "192.168.0.0/24", "dev": dev}]).encode()
            return 0, b""

        with self.assertRaisesRegex(vpn.Failure, "tunnel was disconnected"):
            self.main("up", run)
        self.assertEqual(calls[-1][1], "down")

    def test_failed_commands_never_relay_secret_output_and_remove_snapshot(self):
        with self.assertRaises(vpn.Failure) as error:
            self.main("up", lambda command: (1, b"PrivateKey = PRIVATE_FIXTURE_NOT_A_REAL_KEY"))
        self.assertNotIn("PRIVATE_FIXTURE", str(error.exception))
        self.assertEqual(list(self.root.glob("installer-vpn-*")), [])

    def test_actual_subprocess_failure_keeps_stdout_and_stderr_secret(self):
        quick = self.root / "fake-quick"
        quick.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            "print('PrivateKey = PRIVATE_FIXTURE_NOT_A_REAL_KEY')\n"
            "print('HeaderProtectionKey = HEADER_FIXTURE_NOT_A_REAL_KEY', file=sys.stderr)\n"
            "sys.exit(1)\n"
        )
        quick.chmod(0o755)
        output = io.StringIO()
        with patch.object(vpn, "QUICK", str(quick)), contextlib.redirect_stdout(output):
            with contextlib.redirect_stderr(output), self.assertRaises(vpn.Failure) as error:
                vpn.main(["up", str(self.profile)])
        self.assertNotIn("PRIVATE_FIXTURE", output.getvalue() + str(error.exception))
        self.assertNotIn("HEADER_FIXTURE", output.getvalue() + str(error.exception))

    def test_nonregular_profile_is_rejected_without_blocking(self):
        pipe = self.root / "pipe.conf"
        os.mkfifo(pipe, 0o600)
        with self.assertRaisesRegex(vpn.Failure, "regular file"):
            vpn.read_profile(pipe)

    def test_status_does_not_disclose_peer_keys_or_claim_https_works(self):
        code, output = self.main("status", lambda command: (0, b"SECRET_PUBLIC_KEY\t0\n"))
        self.assertEqual(code, 2)
        self.assertIn("NOT verified", output)
        self.assertNotIn("SECRET_PUBLIC_KEY", output)
        code, output = self.main("status", lambda command: (0, f"KEY\t{int(time.time())}\n".encode()))
        self.assertEqual(code, 0)
        self.assertIn("verify DNS/HTTPS", output)

    def test_down_uses_upstream_teardown_without_modifying_profile(self):
        calls = []
        self.main("down", lambda command: (calls.append(command) or 0, b""))
        self.assertEqual(calls[0][:2], [vpn.QUICK, "down"])
        self.assertEqual(self.profile.read_text(), PROFILE)

    def test_subprocess_environment_excludes_debug_and_startup_hooks(self):
        runner = self.root / "environment.py"
        runner.write_text("import json, os; print(json.dumps(dict(os.environ)))")
        os.environ.update(LOG_LEVEL="debug", BASH_ENV="/not-used", WG_PROCESS_FOREGROUND="1")
        with patch.object(vpn, "RUNTIME_PATH", os.defpath):
            code, output = vpn.run([sys.executable, str(runner)])
        self.assertEqual(code, 0)
        env = json.loads(output)
        self.assertEqual(env["LOG_LEVEL"], "silent")
        self.assertNotIn("BASH_ENV", env)
        self.assertNotIn("WG_PROCESS_FOREGROUND", env)


class ActualQuickTests(unittest.TestCase):
    def test_userspace_override_and_native_dns_routes_teardown(self):
        if QUICK_SOURCE is None:
            self.skipTest("pass --quick-source for actual pinned upstream script coverage")
        self.assertEqual(
            hashlib.sha256(QUICK_SOURCE.read_bytes()).hexdigest(),
            "f4bb0f5d63665ade87f0cb9f2185c43515cff09868637eb311f98f65a318722c",
        )
        source = QUICK_SOURCE.read_text()
        marker = "# ~~ function override insertion point ~~"
        self.assertEqual(source.count(marker), 1)
        # Bypass only the root check in the fixture, never invoke host sudo.
        source = source.replace(
            marker,
            (ROOT / "userspace-only.bash").read_text() + "\nauto_su() { :; }\n",
        )
        with tempfile.TemporaryDirectory(prefix="installer-quick-test-", dir=TEST_TMP) as temporary:
            root = Path(temporary)
            # Do not consult the host's resolvconf prefix policy in this fixture.
            source = source.replace("/etc/resolvconf/interface-order", str(root / "interface-order"))
            quick = root / "quick"
            quick.write_text(source)
            subprocess.run(["bash", "-n", str(quick)], check=True)
            config = root / "lenovo.conf"
            config.write_text(PROFILE)
            config.chmod(0o600)
            fixture = root / "fake-command"
            fixture.write_text(f"""#!{sys.executable}
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open({str(root / 'calls.jsonl')!r}, 'a') as log:
    log.write(json.dumps([name, *args]) + '\\n')
if name == 'ip':
    if args[:3] == ['link', 'show', 'dev']: sys.exit(1)
    if args[:3] == ['link', 'add', 'lenovo']: sys.exit(99)
    if args[:3] == ['route', 'show', 'default']: print('default via 192.168.0.1 dev wlan0 mtu 1500')
    if args[:2] == ['route', 'get']: print('192.0.2.42 via 192.168.0.1 dev wlan0 mtu 1500')
    if len(args) >= 3 and args[1] == 'rule':
        state = pathlib.Path({str(root)!r}) / ('rules' + args[0])
        rules = state.read_text().splitlines() if state.exists() else []
        rule = 'from all lookup 51820' if '51820' in args else 'from all lookup main suppress_prefixlength 0'
        if args[2] == 'show': print('\\n'.join(rules))
        elif args[2] == 'add': rules.append(rule)
        elif args[2] == 'delete': rules.remove(rule)
        state.write_text('\\n'.join(rules))
elif name == 'awg':
    if args == ['show', 'lenovo', 'fwmark']: print('51820')
    elif args == ['show', 'lenovo', 'allowed-ips']: print('KEY 0.0.0.0/0 ::/0')
    elif args == ['show', 'lenovo', 'endpoints']: print('KEY 192.0.2.42:51820')
    elif args == ['show', 'interfaces']: print('lenovo')
    elif args[:2] == ['setconf', 'lenovo']:
        assert pathlib.Path(args[2]).read_text().find('HeaderProtectionKey') >= 0
elif name == 'resolvconf':
    state = pathlib.Path({str(root / 'dns-override')!r})
    if args[0] == '-a':
        assert sys.stdin.read() == 'nameserver 10.66.0.1\\n'
        state.touch()
    elif args[0] == '-d': state.unlink(missing_ok=True)
""")
            fixture.chmod(0o755)
            for name in ("ip", "awg", "resolvconf", "iptables", "ip6tables", "iptables-save",
                         "ip6tables-save", "iptables-restore", "ip6tables-restore", "sysctl", "backend"):
                (root / name).symlink_to(fixture)
            # Avoid the host's nft/ip/awg and network state entirely.
            for name in ("readlink", "stat", "sort"):
                executable = shutil.which(name)
                self.assertIsNotNone(executable)
                (root / name).symlink_to(executable)
            env = {"PATH": str(root), "WG_QUICK_USERSPACE_IMPLEMENTATION": str(root / "backend")}
            for action in ("up", "down"):
                result = subprocess.run(
                    [shutil.which("bash"), str(quick), action, str(config)],
                    env=env, capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
            self.assertIn(["backend", "lenovo"], calls)
            self.assertFalse(any(call[:3] == ["ip", "link", "add"] for call in calls))
            self.assertIn(["ip", "-4", "address", "add", "10.66.0.2/32", "dev", "lenovo"], calls)
            self.assertIn(["ip", "-6", "address", "add", "fd00:66::2/128", "dev", "lenovo"], calls)
            self.assertIn(["ip", "-4", "route", "add", "0.0.0.0/0", "dev", "lenovo", "table", "51820"], calls)
            self.assertIn(["ip", "-6", "route", "add", "::/0", "dev", "lenovo", "table", "51820"], calls)
            self.assertTrue(any(call[:2] == ["resolvconf", "-a"] for call in calls))
            self.assertTrue(any(call[:2] == ["resolvconf", "-d"] for call in calls))
            self.assertIn(["ip", "link", "delete", "dev", "lenovo"], calls)
            for family in ("-4", "-6"):
                self.assertIn(["ip", family, "rule", "delete", "table", "51820"], calls)
                self.assertIn(["ip", family, "rule", "delete", "table", "main", "suppress_prefixlength", "0"], calls)
                self.assertEqual((root / ("rules" + family)).read_text(), "")
            self.assertFalse((root / "dns-override").exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick-source", type=Path)
    args, rest = parser.parse_known_args()
    QUICK_SOURCE = args.quick_source
    unittest.main(argv=[sys.argv[0], *rest])
