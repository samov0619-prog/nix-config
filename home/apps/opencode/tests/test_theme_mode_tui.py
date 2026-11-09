"""Opt-in installed-binary PTY theme regression; no model requests or real config.

python3 -B tests/test_theme_mode_tui.py /path/to/opencode
Use --expect-stale-cache-bug only to reproduce the old binary's negative control.
"""

import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import socket
import struct
import subprocess
import tempfile
import termios
import time
import urllib.request


def scenario(binary, cached_mode, expect_bug):
    with tempfile.TemporaryDirectory(prefix="theme-pty-", dir="/tmp/opencode") as temporary:
        root = Path(temporary)
        config = root / "config/opencode"
        plugin = config / "plugins/theme-probe"
        plugin.mkdir(parents=True)
        (plugin / "tui.ts").write_text(Path(__file__).with_name("theme-mode-probe.ts").read_text())
        (config / "opencode.json").write_text(json.dumps({"providers": {}}))
        preferences = {"theme": {"name": "flexoki", "mode": "system"}, "attention": {"sound": False}}
        (config / "cli.json").write_text(json.dumps(preferences))
        (root / "state").mkdir()
        (root / "runtime").mkdir(mode=0o700)
        if cached_mode:
            cached = root / "state/opencode/prod/tui/system-theme.json"
            cached.parent.mkdir(parents=True)
            cached.write_text(json.dumps({"colors": {
                "defaultForeground": "#dddddd", "defaultBackground": "#2c2e34",
                "palette": ["#000000"] * 16,
            }}))
        env = {k: v for k, v in os.environ.items() if not k.startswith(
            ("OPENCODE_", "OPENAI_", "ANTHROPIC_", "XDG_", "KITTY_", "OTUI_"))}
        env.update(
            HOME=temporary, XDG_CONFIG_HOME=str(root / "config"),
            XDG_STATE_HOME=str(root / "state"), XDG_DATA_HOME=str(root / "data"),
            XDG_CACHE_HOME=str(root / "cache"), XDG_RUNTIME_DIR=str(root / "runtime"),
            OPENCODE_DISABLE_PROJECT_CONFIG="1", OPENCODE_DISABLE_MODELS_FETCH="1",
            OPENCODE_CONFIG_DIR=str(config), OPENCODE_PASSWORD="theme-fixture",
            TERM="xterm-kitty",
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        server = client = None
        master = None
        mode = "light"
        query_counts = {"10": 0, "11": 0}
        buffer = bytearray()
        position = 0
        output = bytearray()
        queries = re.compile(rb"\x1b\](10|11);\?(?:\x07|\x1b\\)|\x1b\[\?([0-9]+)\$p|\x1b\[6n|\x1b\[c|\x1b\[>q|\x1b\[\?u")

        def drain():
            nonlocal position
            while select.select([master], [], [], 0)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    return
                if not chunk:
                    return
                output.extend(chunk)
                buffer.extend(chunk)
            for match in queries.finditer(buffer, position):
                position = match.end()
                request = match.group()
                if match.group(1):
                    code = match.group(1).decode()
                    query_counts[code] += 1
                    color = ({"10": "3838/3a3a/4242", "11": "fafa/fafa/fafa"}
                             if mode == "light" else
                             {"10": "dddd/dddd/dddd", "11": "2c2c/2e2e/3434"})[code]
                    response = f"\x1b]{code};rgb:{color}\x1b\\".encode()
                elif match.group(2):
                    response = b"\x1b[?" + match.group(2) + b";1$y"
                else:
                    response = {
                        b"\x1b[6n": b"\x1b[1;1R", b"\x1b[c": b"\x1b[?62;c",
                        b"\x1b[>q": b"\x1bP>|kitty(0.47.0)\x1b\\",
                        b"\x1b[?u": b"\x1b[?0u",
                    }[request]
                os.write(master, response)

        def state():
            try:
                return json.loads((root / "state/theme.state").read_text())
            except (FileNotFoundError, ValueError):
                return {}

        def wait(predicate, timeout=15):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                drain()
                if predicate():
                    return True
                if client.poll() is not None:
                    break
                time.sleep(0.02)
            return False

        def check(expected):
            snapshot = state()
            assert snapshot.get("rendererMode") == mode, snapshot
            assert snapshot.get("themeMode") == expected, snapshot
            # Native Flexoki text tokens distinguish dark and light, not just a flag.
            expected_text = ("rgba(0.06, 0.06, 0.06, 1.00)" if expected == "light"
                             else "rgba(0.81, 0.80, 0.76, 1.00)")
            assert snapshot.get("text") == expected_text, snapshot

        with (root / "server.log").open("w+") as log:
            try:
                server = subprocess.Popen(
                    [binary, "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                    cwd=root, env=env, stdout=log, stderr=log, start_new_session=True,
                )
                request = urllib.request.Request(url + "/api/info", headers={
                    "Authorization": "Basic " + base64.b64encode(b"opencode:theme-fixture").decode(),
                })
                deadline = time.monotonic() + 20
                while True:
                    try:
                        with urllib.request.urlopen(request, timeout=1):
                            break
                    except OSError:
                        if time.monotonic() > deadline:
                            raise RuntimeError("Private server did not start")
                        time.sleep(0.1)
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))

                def controlling_terminal():
                    os.setsid()
                    fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

                client = subprocess.Popen(
                    [binary, "--server", url], stdin=slave, stdout=slave, stderr=slave,
                    cwd=root, env=env, preexec_fn=controlling_terminal,
                )
                os.close(slave)
                assert wait(lambda: bool(state())), "Theme probe did not attach"
                stale = bool(cached_mode and expect_bug)
                check("dark" if stale else "light")
                for next_mode in ("light", "dark", "light"):
                    mode = next_mode
                    before = query_counts["11"]
                    os.write(master, b"\x1b[?997;1n" if mode == "dark" else b"\x1b[?997;2n")
                    assert wait(lambda: query_counts["11"] > before and state().get("rendererMode") == mode, 3), state()
                    until = time.monotonic() + 0.15
                    while time.monotonic() < until:
                        drain()
                        time.sleep(0.02)
                    check("dark" if stale else mode)
                    stale = False
                assert b"\x1b[?2031h" in output, "OpenTUI must subscribe to notifications"
                assert json.loads((config / "cli.json").read_text()) == preferences
                print("PASS:", "stale-cache negative control" if cached_mode and expect_bug else
                      "stale-cache regression" if cached_mode else "fresh-cache control")
            finally:
                for process in (client, server):
                    if process is not None and process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=4)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait(timeout=2)
                if master is not None:
                    os.close(master)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary")
    parser.add_argument("--expect-stale-cache-bug", action="store_true")
    args = parser.parse_args()
    for cached_mode in (False, True):
        scenario(args.binary, cached_mode, args.expect_stale_cache_bug)
