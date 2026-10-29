"""Opt-in: two real TUI clients, one private server, mock provider, no actual audio.

python3 .../test_attention_tui.py /path/to/opencode
Optional OPENCODE_TEST_HM_GENERATION exercises the built urgency plugin.
"""
import base64
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from test_v2_runtime import MockResponses, SOURCE


def main(binary):
    with tempfile.TemporaryDirectory(prefix="attention-tui-", dir="/tmp/opencode") as temporary:
        root = Path(temporary)
        config = root / "config/opencode"
        config.mkdir(parents=True)
        (root / "state").mkdir()
        (root / "runtime").mkdir(mode=0o700)
        mock = ThreadingHTTPServer(("127.0.0.1", 0), MockResponses)
        threading.Thread(target=mock.serve_forever, daemon=True).start()
        settings = json.loads(subprocess.check_output([
            "nix", "eval", "--offline", "--json", "--file", str(SOURCE / "config/v2-settings.nix"), "--apply", "f: f { lib = {}; }",
        ]))
        settings["providers"]["openai"].update(package="@opencode/ai/providers/openai/responses", settings={
            "apiKey": "mock", "baseURL": f"http://127.0.0.1:{mock.server_port}/v1"})
        (config / "opencode.json").write_text(json.dumps(settings))
        (config / "cli.json").write_text(json.dumps({"attention": {"sound": True}, "tabs": {"scope": "global"}}))
        for name in ["quiet-urgency", "attention-probe"]:
            directory = config / "plugins" / name
            directory.mkdir(parents=True)
            generation = os.environ.get("OPENCODE_TEST_HM_GENERATION")
            if name == "quiet-urgency" and generation:
                (directory / "tui.ts").symlink_to(Path(generation) / "home-files/.config/opencode/plugins/quiet-urgency/tui.ts")
            else:
                source = SOURCE / ("tests/attention-probe.ts" if name == "attention-probe" else "plugins/quiet-urgency.ts")
                (directory / "tui.ts").write_text(source.read_text().replace(
                    "@sessionAttention@", str(SOURCE / "patches/session-attention.ts")).replace("@silentAttention@", str(SOURCE / "scripts/silent-attention.py")))
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("OPENCODE_", "OPENAI_", "ANTHROPIC_", "XDG_", "KITTY_"))}
        env.update(HOME=temporary, XDG_CONFIG_HOME=str(root / "config"), XDG_STATE_HOME=str(root / "state"),
                   XDG_DATA_HOME=str(root / "data"), XDG_CACHE_HOME=str(root / "cache"), XDG_RUNTIME_DIR=str(root / "runtime"),
                   OPENCODE_DISABLE_PROJECT_CONFIG="1", OPENCODE_DISABLE_MODELS_FETCH="1", OPENCODE_CONFIG_DIR=str(config),
                   OPENCODE_PASSWORD="attention-fixture", TERM="xterm-256color")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        clients = {}
        outputs = {"101": bytearray(), "202": bytearray()}
        with (root / "server.log").open("w+") as log:
            server = subprocess.Popen([binary, "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                                      cwd=root, env=env, stdout=log, stderr=log)

            def api(path, data=None):
                request = urllib.request.Request(url + "/api/" + path, data=json.dumps(data).encode() if data is not None else None,
                    headers={"Content-Type": "application/json", "Authorization": "Basic " + base64.b64encode(b"opencode:attention-fixture").decode()})
                with urllib.request.urlopen(request, timeout=30) as response:
                    body = response.read()
                    return json.loads(body) if body else None

            def drain():
                for pane, (process, master) in clients.items():
                    while select.select([master], [], [], 0)[0]:
                        try:
                            chunk = os.read(master, 65536)
                            if not chunk:
                                break
                            outputs[pane].extend(chunk)
                        except OSError:
                            break

            def wait(predicate, message, timeout=30):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    drain()
                    try:
                        if predicate():
                            return
                    except (OSError, ValueError, urllib.error.URLError):
                        pass
                    time.sleep(0.05)
                raise AssertionError(message)

            def route(pane):
                return json.loads((root / f"state/attention-{pane}.state").read_text())["route"]

            def records(pane):
                path = root / f"state/attention-{pane}.jsonl"
                return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

            def sounds(pane):
                return [row["sound"] for row in records(pane) if row["type"] == "attention"]

            def launch(pane, sid):
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))
                def controlling_terminal():
                    os.setsid()
                    fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
                process = subprocess.Popen([binary, "--server", url, "--session", sid], stdin=slave, stdout=slave, stderr=slave,
                    cwd=root, env={**env, "KITTY_WINDOW_ID": pane}, preexec_fn=controlling_terminal)
                os.close(slave)
                clients[pane] = (process, master)

            def prompt(sid, error=False):
                if error:
                    MockResponses.fail_next = True
                api(f"session/{sid}/prompt", {"text": "Reply briefly."})
                try:
                    api(f"experimental/session/{sid}/wait", {})
                except urllib.error.HTTPError as failure:
                    assert error and failure.code == 503, failure
                event = "session.execution.failed" if error else "session.execution.succeeded"
                wait(lambda: all(any(row.get("event") == event and row.get("sessionID") == sid for row in records(pane))
                                 for pane in clients), "Both clients must receive the event to exercise isolation")
                # Let all handlers/native attention tasks and PTY output settle.
                until = time.monotonic() + 0.5
                while time.monotonic() < until:
                    drain()
                    time.sleep(0.02)

            def urgency(pane):
                return outputs[pane].count(b"\x1bP@kitty-cmd")

            try:
                wait(lambda: api("info"), "private server did not start", timeout=90)
                a = api("session", {"title": "Window A", "permissions": [
                    {"action": "shell", "resource": "*", "effect": "ask"},
                ]})["data"]["id"]
                b = api("session", {"title": "Window B"})["data"]["id"]
                launch("101", a)
                launch("202", b)
                wait(lambda: route("101").get("sessionID") == a and route("202").get("sessionID") == b, "TUI probes did not attach")
                prompt(a)
                assert sounds("101") == ["done"] and sounds("202") == [], (sounds("101"), sounds("202"))
                assert urgency("101") > 0 and urgency("202") == 0, (urgency("101"), urgency("202"))
                before_a = urgency("101")
                prompt(b)
                assert sounds("101") == ["done"] and sounds("202") == ["done"]
                assert urgency("101") == before_a and urgency("202") > 0
                print("PASS: two real TUI clients/global tabs receive both sessions' events; only the owning window requests native sound and Kitty urgency")
                before_b = urgency("202")
                permission = api(f"session/{a}/permission", {"action": "shell", "resources": ["attention-fixture"], "save": []})["data"]
                assert permission["effect"] == "ask", permission
                wait(lambda: sounds("101")[-1] == "permission" and all(
                    any(row.get("event") == "permission.asked" and row.get("sessionID") == a for row in records(pane))
                    for pane in clients), "permission event did not reach both TUI clients")
                assert sounds("202") == ["done"] and urgency("202") == before_b
                api(f"session/{a}/permission/{permission['id']}/reply", {"decision": "once"})
                print("PASS: permission attention is also isolated, without changing the underlying permission decision flow")
                child = api("session", {"parentID": a, "title": "Child A"})["data"]["id"]
                before_b = urgency("202")
                prompt(child)
                assert sounds("101")[-1] == "subagent_done" and sounds("202") == ["done"], (sounds("101"), sounds("202"))
                assert urgency("202") == before_b
                print("PASS: child completion remains scoped to its own parent window")
                prompt(a, error=True)
                assert sounds("101")[-1] == "error" and sounds("202") == ["done"]
                (root / "state/attention-101.route").write_text("home")
                wait(lambda: route("101")["type"] == "home", "route did not change to home")
                before_a = urgency("101")
                # Generate another lifecycle for A; old receipts are not enough.
                for pane in clients:
                    (root / f"state/attention-{pane}.jsonl").write_text("")
                prompt(a)
                assert sounds("101") == [] and sounds("202") == []
                assert urgency("101") == before_a
                print("PASS: failed session does not affect the other window; home/global navigation revokes prior ownership")
            except Exception:
                drain()
                for pane, output in outputs.items():
                    Path(f"/tmp/opencode/attention-tui-{pane}-failure.log").write_bytes(output)
                print(log_path.read_text()[-2000:] if (log_path := root / "server.log").exists() else "", file=sys.stderr)
                raise
            finally:
                for process, master in clients.values():
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                    os.close(master)
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
                mock.shutdown()


if __name__ == "__main__":
    main(sys.argv[1])
