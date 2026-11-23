"""Opt-in private PTY: native manual skill and limits compaction marks.

python3 -B tests/test_personal_limits_tui.py /path/to/opencode
OPENCODE_TEST_HM_GENERATION optionally selects the built limits plugin closure.
No real credentials, model, MCP, browser, live service or config are used.
"""

import base64
import fcntl
import json
import os
from pathlib import Path
import pty
import select
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

from test_personal_layers_runtime import materialize, text_values
from test_todo_scope_runtime import evaluate
from test_v2_runtime import MockResponses, SOURCE


class HeldResponses(MockResponses):
    hold = False
    entered = threading.Event()
    release = threading.Event()

    def do_POST(self):
        if type(self).hold:
            type(self).hold = False
            type(self).entered.set()
            if not type(self).release.wait(timeout=20):
                self.send_error(504, "fixture hold timed out")
                return
        super().do_POST()


def scenario(binary, root, label, layer):
    root.mkdir(mode=0o700)
    config = root / ".config/opencode"
    personal = root / ".config/opencode-local"
    for directory in [config, root / "state", root / "runtime"]:
        directory.mkdir(parents=True, mode=0o700)
    materialize(personal, layer["files"])
    plugin = config / "plugins/limits"
    plugin.parent.mkdir()
    generation = os.environ.get("OPENCODE_TEST_HM_GENERATION")
    if generation:
        plugin.symlink_to(Path(generation) / "home-files/.config/opencode/plugins/limits-v2",
                          target_is_directory=True)
    else:
        source = SOURCE / "plugins/limits"
        plugin.mkdir()
        for name in ["index.ts", "policy.ts", "rpc.ts", "writer.ts", "tui.tsx"]:
            (plugin / name).write_bytes((source / name).read_bytes())
    probe = config / "plugins/personal-limits-probe"
    probe.mkdir()
    (probe / "tui.ts").write_bytes((SOURCE / "tests/personal-limits-probe.ts").read_bytes())
    provider = ThreadingHTTPServer(("127.0.0.1", 0), HeldResponses)
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    settings = {
        "update": "disable", "share": "disabled", "formatter": False,
        "model": "openai/gpt-6.1-sol", "compaction": {"auto": True},
        "policies": [{"action": "provider.use", "resource": "openai", "effect": "allow"}],
        "providers": {"openai": {
            "package": "@opencode/ai/providers/openai/responses",
            "settings": {"baseURL": f"http://127.0.0.1:{provider.server_port}/v1", "apiKey": "fixture"},
            "models": {"gpt-6.1-sol": {"capabilities": {"tools": True}}},
        }},
    }
    common = config / "opencode.json"
    common.write_text(json.dumps(settings))
    preferences = {"attention": {"sound": False}, "theme": {"name": "flexoki", "mode": "dark"}}
    (config / "cli.json").write_text(json.dumps(preferences))
    env = {key: value for key, value in os.environ.items() if not key.startswith(
        ("OPENCODE_", "OPENAI_", "ANTHROPIC_", "XDG_", "KITTY_", "OTUI_"))}
    env.update(
        HOME=str(root), XDG_CONFIG_HOME=str(root / ".config"), XDG_STATE_HOME=str(root / "state"),
        XDG_DATA_HOME=str(root / "data"), XDG_CACHE_HOME=str(root / "cache"),
        XDG_RUNTIME_DIR=str(root / "runtime"), OPENCODE_DISABLE_PROJECT_CONFIG="1",
        OPENCODE_DISABLE_MODELS_FETCH="1", OPENCODE_CONFIG_DIR=str(config),
        OPENCODE_CONFIG=str(personal / "opencode.jsonc"),
        OPENCODE_PASSWORD="personal-limits-fixture", TERM="xterm-256color",
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    auth = "Basic " + base64.b64encode(b"opencode:personal-limits-fixture").decode()
    server = client = None
    master = None
    output = bytearray()
    snapshots = {}

    def api(path, data=None, method=None):
        request = urllib.request.Request(url + "/api/" + path, method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Authorization": auth, "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = response.read()
            return json.loads(payload) if payload else None

    def state():
        try:
            return json.loads((root / "state/personal-limits.state").read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def drain():
        if master is None:
            return
        while select.select([master], [], [], 0)[0]:
            try:
                chunk = os.read(master, 65536)
            except OSError:
                break
            if not chunk:
                break
            output.extend(chunk)

    def wait(predicate, message, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            drain()
            if client is not None:
                assert client.poll() is None, "private TUI exited"
            try:
                if predicate():
                    return
            except (OSError, ValueError, urllib.error.URLError):
                pass
            time.sleep(0.03)
        raise AssertionError((message, state()))

    def frame():
        return "\n".join("".join(span["text"] for span in row) for row in state().get("frame", []))

    def icons():
        return [span for row in state().get("frame", []) for span in row if "≋" in span["text"]]

    def icon(color):
        return len(icons()) == 1 and icons()[0]["fg"] == state().get(color)

    def save(name):
        snapshots[name] = state()

    def navigate(sid):
        (root / "state/personal-limits.route").write_text(sid)
        wait(lambda: state().get("route", {}).get("sessionID") == sid, "route not ready")

    def set_auto(value):
        settings["compaction"]["auto"] = value
        common.write_text(json.dumps(settings))
        wait(lambda: (icon("muted") if value else not icons()), "config auto change not rendered")

    with (root / "server.log").open("w+") as log:
        try:
            server = subprocess.Popen([binary, "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                                      cwd=root, env=env, stdout=log, stderr=log)
            wait(lambda: api("info"), "server not ready", timeout=25)
            wait(lambda: "discussion-map" in {s["id"] for s in api("skill")["data"]}, "skill not registered")
            selected = {"providerID": "openai", "id": "gpt-6.1-sol", "variant": "low"}
            sid = api("session", {"title": "Personal PTY " + label, "agent": "build", "model": selected})["data"]["id"]
            other = api("session", {"title": "Other idle session", "agent": "build", "model": selected})["data"]["id"]
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))

            def controlling_terminal():
                os.setsid()
                fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

            client = subprocess.Popen([binary, "--server", url, "--session", sid],
                cwd=root, env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=controlling_terminal)
            os.close(slave)
            wait(lambda: state().get("route", {}).get("sessionID") == sid and icon("muted"), "idle auto icon")
            wait(lambda: "Active: 0" in frame() and "+" in frame(), "base limits/handoff marks")
            save("auto-enabled-idle")
            start = len(HeldResponses.requests)
            os.write(master, b"@discussion-map")
            wait(lambda: "@discussion-map" in frame() and "Use when two" in frame(), "manual skill autocomplete")
            os.write(master, b"\t")
            os.write(master, b" Show the two fixture discussion threads.\r")
            wait(lambda: len(HeldResponses.requests) > start, "manual skill prompt not submitted")
            api(f"experimental/session/{sid}/wait", {})
            items = api(f"session/{sid}/message?limit=100&order=asc")["data"]
            attachments = [skill for message in items if message["type"] == "user"
                           for skill in message.get("skills", [])]
            assert len(attachments) == 1 and attachments[0]["id"] == "discussion-map", attachments
            skill_body = (personal / "skills/discussion-map/SKILL.md").read_text().split("---", 2)[2].strip()
            assert skill_body in attachments[0]["text"], "stored native skill attachment missing body"
            assert any(skill_body in text for request in HeldResponses.requests[start:] for text in text_values(request)), "manual skill body absent from wire"
            assert not any(tool.get("name") == "skill" for message in items for tool in message.get("content", [])), "fixture must test manual injection, not a scripted model skill call"
            save("manual-skill")
            print(f"PASS: {label}: native @discussion-map autocomplete/selection/submission injects actual generated body without model tool call", flush=True)

            api(f"session/{sid}", {"metadata": {"local.checkpoint": {"ready": True}}}, method="PATCH")
            wait(lambda: "✓" in frame(), "ready handoff cache rendering")
            save("handoff-ready")
            set_auto(False)
            save("auto-disabled-idle")
            HeldResponses.entered.clear()
            HeldResponses.release.clear()
            HeldResponses.hold = True
            api(f"session/{sid}/compact", {})
            wait(lambda: HeldResponses.entered.is_set() and icon("info"), "native compaction blue icon")
            assert any(message["type"] == "compaction" and message["status"] == "running" for message in state()["messages"])
            save("auto-disabled-running")
            navigate(other)
            wait(lambda: not icons(), "other idle session must not inherit running icon")
            save("other-idle-during-compaction")
            navigate(sid)
            wait(lambda: icon("info"), "running session icon after return")
            HeldResponses.release.set()
            api(f"experimental/session/{sid}/wait", {})
            wait(lambda: not icons() and any(message["type"] == "compaction" and message["status"] == "completed" for message in state()["messages"]), "completed compaction must clear icon when auto off")
            save("auto-disabled-completed")
            set_auto(True)
            save("auto-enabled-completed")
            (root / "state/personal-limits.route").write_text("home")
            wait(lambda: state().get("route", {}).get("type") == "home" and icon("muted"), "home auto icon must not be blue")
            save("home-footer")
            assert json.loads((config / "cli.json").read_text()) == preferences
            assert not (root / "agent-todo").exists()
            print(f"PASS: {label}: rendered limits +/✓, Active:0, auto off/on, native running blue/completed/other-session/home-muted states", flush=True)
        finally:
            HeldResponses.release.set()
            HeldResponses.hold = False
            for process in [client, server]:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)
            if master is not None:
                os.close(master)
            provider.shutdown()
            provider.server_close()
            (root / "snapshots.json").write_text(json.dumps(snapshots, ensure_ascii=False, indent=2))
            (root / "pty-output.bin").write_bytes(output)


def main():
    binary = str(Path(sys.argv[1]).resolve(strict=True))
    layers = evaluate(SOURCE / "config/personal-layers.nix", "f: f { todoEnabled = false; }")
    root = Path(tempfile.mkdtemp(prefix="personal-limits-pty-", dir="/tmp/opencode"))
    print("Private fixture artifacts:", root, flush=True)
    for label in ["home", "corporate"]:
        scenario(binary, root / label, label, layers[label])
    print("PASS: generated layers + native PTY/cache + mock HTTP; quota percentages, real models and integrations are not covered")


if __name__ == "__main__":
    main()
