"""Validate an external AWG profile, then use pinned userspace awg-quick.

No credentials, upstream command output or profiles are written to the Nix store.
Only a private temporary /run snapshot is passed to the privileged quick script.
"""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time


QUICK = "@quick@/bin/installer-vpn-quick"
AWG = "@tools@/bin/awg"
IP = "@iproute2@/bin/ip"
PYTHON = "@python3@/bin/python3"
RUNTIME_PATH = "@runtimePath@"
SUDO = "/run/wrappers/bin/sudo"
RUNTIME_DIR = "/run"
INTERFACE_KEYS = {
    "address", "privatekey", "dns", "mtu", "jc", "jmin", "jmax",
    "s1", "s2", "s3", "s4", "h1", "h2", "h3", "h4",
    "headerprotectionkey", "randomtrailers", "disablecookies",
}
PEER_KEYS = {"publickey", "presharedkey", "endpoint", "allowedips", "persistentkeepalive"}


class Failure(Exception):
    pass


def profile_path(value):
    try:
        path = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise Failure("profile is not an accessible file") from None
    if path.is_relative_to("/nix/store"):
        raise Failure("profiles must stay outside /nix/store")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,14}\.conf", path.name):
        raise Failure("use a short profile name such as lenovo.conf (interface name <=15 characters)")
    return path


def read_profile(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            owners = {0, os.getuid(), int(os.environ.get("SUDO_UID", os.getuid()))}
            if not stat.S_ISREG(info.st_mode) or info.st_uid not in owners:
                raise Failure("profile must be a regular file owned by you or root")
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise Failure("profile is not private; run chmod 600 on it")
            data = source.read(65537)
    except OSError:
        raise Failure("cannot read profile") from None
    if len(data) > 65536:
        raise Failure("profile is too large")
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise Failure("profile must be a native UTF-8 .conf export") from None
    sections = {}
    current = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.lower() in ("[interface]", "[peer]"):
            current = line.lower()
            if current in sections:
                raise Failure("only one Interface and one Peer are supported")
            sections[current] = {}
            continue
        key, separator, value = line.partition("=")
        key = key.strip().lower()
        allowed = INTERFACE_KEYS if current == "[interface]" else PEER_KEYS
        if current is None or not separator or key not in allowed:
            raise Failure("unsupported profile directive; hooks, Table and SaveConfig are not allowed")
        if key in sections[current] or not value.strip():
            raise Failure("empty or duplicate profile directive")
        sections[current][key] = value.strip()
    interface = sections.get("[interface]", {})
    peer = sections.get("[peer]", {})
    if not {"address", "dns", "privatekey", "headerprotectionkey"} <= interface.keys():
        raise Failure("expected a native AWG 3.1 profile with Address, DNS and HeaderProtectionKey")
    if not {"publickey", "endpoint", "allowedips"} <= peer.keys():
        raise Failure("profile is missing peer settings")
    if {v.strip() for v in peer["allowedips"].split(",")} != {"0.0.0.0/0", "::/0"}:
        raise Failure("installer-vpn requires a full tunnel: AllowedIPs = 0.0.0.0/0, ::/0")
    try:
        for address in interface["address"].split(","):
            ipaddress.ip_interface(address.strip())
        for dns in interface["dns"].split(","):
            ipaddress.ip_address(dns.strip())
    except ValueError:
        raise Failure("invalid Address or DNS; DNS must contain numeric IP addresses") from None
    return data


def run(command):
    # Do not inherit Bash startup hooks, Go fd/foreground overrides or debug logs.
    env = {"PATH": RUNTIME_PATH, "LC_ALL": "C", "LOG_LEVEL": "silent"}
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, start_new_session=True,
    ) as process:
        try:
            stdout, _ = process.communicate(timeout=60)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            raise Failure("operation interrupted or timed out; check status and use down if needed") from None
    # awg-quick's parser can quote a bad config line, including secret values.
    # Never relay its raw output, even on errors.
    return process.returncode, stdout


def ssh_route(peer, fibmatch=False):
    command = [IP, "-j", "route", "get"]
    if fibmatch:
        command.append("fibmatch")
    code, output = run([*command, peer])
    try:
        routes = json.loads(output) if code == 0 else []
        route = routes[0]
        if not route.get("dev"):
            raise ValueError
        return route
    except (ValueError, IndexError, KeyError, TypeError):
        raise Failure("cannot verify the SSH client's route") from None


def status(interface):
    code, output = run([AWG, "show", interface, "latest-handshakes"])
    if code:
        print(f"{interface}: interface unavailable")
        return 1
    try:
        timestamps = [int(line.split()[1]) for line in output.decode().splitlines()]
        latest = max(timestamps, default=0)
    except (ValueError, IndexError, UnicodeError):
        raise Failure("cannot read handshake status") from None
    if latest == 0:
        print(f"{interface}: no handshake yet; connectivity is NOT verified")
        return 2
    age = max(0, int(time.time()) - latest)
    print(f"{interface}: latest handshake {age}s ago; verify DNS/HTTPS before downloading")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "status", "down"))
    parser.add_argument("profile", help="external private .conf; keep unchanged until down")
    parser.add_argument("--ssh-peer", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    path = profile_path(args.profile)
    # Validate before elevation, and again afterwards; no secrets enter argv.
    data = read_profile(path)
    peer = args.ssh_peer
    if peer is None and os.environ.get("SSH_CONNECTION"):
        connection = os.environ["SSH_CONNECTION"].split()
        if len(connection) != 4:
            raise Failure("invalid SSH connection metadata")
        peer = connection[0]
    if peer:
        try:
            peer = str(ipaddress.ip_address(peer))
        except ValueError:
            raise Failure("invalid SSH peer address") from None
    if os.geteuid() != 0:
        command = [SUDO, "--", PYTHON, "-I", str(Path(__file__).resolve()), args.action, str(path)]
        if peer:
            command += ["--ssh-peer", peer]
        os.execv(SUDO, command)
    interface = path.stem
    if args.action == "status":
        return status(interface)
    before = None
    if args.action == "up" and peer:
        before = ssh_route(peer, fibmatch=True)
        if before.get("dst", "default") in ("default", "0.0.0.0/0", "::/0"):
            raise Failure("SSH uses a default route; connect locally or through a directly routed LAN first")
        if before["dev"] == interface:
            raise Failure("SSH already uses this VPN interface")
    with tempfile.TemporaryDirectory(prefix="installer-vpn-", dir=RUNTIME_DIR) as temporary:
        snapshot = Path(temporary) / path.name
        snapshot.touch(mode=0o600)
        snapshot.write_bytes(data)
        code, _ = run([QUICK, args.action, str(snapshot)])
        if code:
            raise Failure(f"{args.action} failed (exit {code}); secret-bearing upstream output suppressed; see README diagnostics")
        if before is not None:
            try:
                if ssh_route(peer)["dev"] != before["dev"]:
                    raise Failure("SSH route changed unexpectedly")
            except Failure:
                cleanup, _ = run([QUICK, "down", str(snapshot)])
                if cleanup:
                    raise Failure("SSH route check failed and rollback failed; use the local console to disconnect") from None
                raise Failure("SSH route check failed; tunnel was disconnected") from None
    if args.action == "up":
        print(f"{interface}: configured with userspace AWG 3.1; connectivity NOT yet verified")
        print("Run status, then check DNS/HTTPS. Keep this profile unchanged until down.")
    else:
        print(f"{interface}: native teardown completed; verify ordinary routing and DNS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Failure as error:
        print(f"installer-vpn: {error}", file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError):
        print("installer-vpn: local operation failed; no profile or upstream output is displayed", file=sys.stderr)
        sys.exit(1)
