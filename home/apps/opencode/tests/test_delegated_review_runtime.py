"""Opt-in native subagent/HTTP recovery fixture, not a real-model policy test.

Usage: python3 -B .../test_delegated_review_runtime.py /absolute/path/to/opencode
Runs only after separate approval. No builds, real providers or shared service.
"""

import argparse
import base64
import io
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
import urllib.error
import urllib.parse
import urllib.request

from test_v2_runtime import MockResponses, SOURCE


class RecoveryMock(MockResponses):
    """Scripted tool decisions exercise native execution, not LLM obedience."""

    mode = None
    parent_step = 0
    child_started = False
    failures = 0
    child_id = None
    terminal_seen_at = None
    fixture = None
    violation = None
    lock = threading.Lock()

    @classmethod
    def reset(cls, mode, fixture):
        cls.mode = mode
        cls.fixture = str(fixture)
        cls.parent_step = 0
        cls.child_started = False
        cls.failures = 0
        cls.child_id = None
        cls.terminal_seen_at = None
        cls.violation = None
        cls.requests = []

    @classmethod
    def decide(cls, body):
        cls.next_tool = None
        cls.next_tool_command = None
        cls.next_tool_skill = None
        cls.fail_next = False
        cls.reply = "Mock recovery fixture"
        text = json.dumps(body, ensure_ascii=False)
        names = {tool.get("name") for tool in body.get("tools", [])}
        if "subagent" in names and "Orchestrate an independent review of" in text:
            assert "$ARGUMENTS" not in text
            step = cls.parent_step
            cls.parent_step += 1
            if step == 0:
                cls.next_tool = (
                    "subagent",
                    {
                        "agent": "review",
                        "description": "Native recovery fixture",
                        "prompt": "DR_CHILD_SCOPE_V1: read only " + cls.fixture,
                    },
                )
            elif cls.mode == "terminal" and step == 1:
                assert cls.failures == 11, "parent woke before native retries exhausted"
                assert "Subagent failed" in text, "expected an actual native tool error"
                ids = set(re.findall(r"sessionID[:=\s\"\\]+(ses_[A-Za-z0-9]+)", text))
                assert len(ids) == 1, ids
                cls.child_id = ids.pop()
                cls.terminal_seen_at = time.monotonic()
                cls.next_tool = ("shell", {"command": "sleep 20", "timeout": 25000})
            elif cls.mode == "terminal" and step == 2:
                assert time.monotonic() - cls.terminal_seen_at >= 20
                cls.next_tool = (
                    "subagent",
                    {
                        "agent": "review",
                        "sessionID": cls.child_id,
                        "description": "Continue native recovery fixture",
                        "prompt": "Continue DR_CHILD_SCOPE_V1; reuse the prior read result.",
                    },
                )
            else:
                assert step == (3 if cls.mode == "terminal" else 1)
                assert "DR_CHILD_COMPLETE" in text
                cls.reply = "DR_PARENT_COMPLETE (scripted mock, not a real review verdict)"
        elif "DR_CHILD_SCOPE_V1" in text and "read" in names:
            if not cls.child_started:
                cls.child_started = True
                cls.next_tool = ("read", {"path": cls.fixture})
            elif cls.failures < (11 if cls.mode == "terminal" else 1):
                cls.failures += 1
                cls.fail_next = True
                cls.fail_status = 429
            else:
                # The evidence comes from an actual native read tool result.
                # It is preserved reading, NOT proof of a completed review unit.
                assert "DR_PRESERVED_READ_EVIDENCE" in text
                cls.reply = "DR_CHILD_COMPLETE; prior read evidence is preserved."

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        with type(self).lock:
            try:
                type(self).decide(json.loads(raw))
            except Exception as error:
                type(self).violation = repr(error)
                self.send_error(400, "mock fixture assertion failed")
                return
            # Reuse the existing Responses/SSE emitter, including its real HTTP 429.
            self.rfile = io.BytesIO(raw)
            super().do_POST()


def main(binary):
    binary = str(Path(binary).resolve(strict=True))
    # Closing the context also releases the socket if preparation fails before
    # the serving thread starts. Never call shutdown on an unstarted server.
    with ThreadingHTTPServer(("127.0.0.1", 0), RecoveryMock) as provider:
        run_fixture(binary, provider)


def run_fixture(binary, provider):
    root = Path(tempfile.mkdtemp(prefix="delegated-review-runtime-", dir="/tmp/opencode"))
    print("Private fixture artifacts:", root, flush=True)
    config = root / "config/opencode"
    config.mkdir(parents=True)
    work = root / "project"
    work.mkdir()
    fixture = work / "fixture.txt"
    fixture.write_text("DR_PRESERVED_READ_EVIDENCE\n")
    runtime = root / "runtime"
    runtime.mkdir(mode=0o700)
    settings = json.loads(
        subprocess.check_output(
            [
                "nix", "eval", "--offline", "--json", "--file",
                str(SOURCE / "config/v2-settings.nix"), "--apply", "f: f { lib = {}; }",
            ],
            text=True,
            timeout=10,
        )
    )
    thread = threading.Thread(target=provider.serve_forever, daemon=True)
    mock_url = f"http://127.0.0.1:{provider.server_port}/v1"
    # Both provider identities are local fixtures. Every actual request must
    # still use Big Pickle; keeping the paid catalog permits native resolution
    # before the installed routing patch applies the root's free policy.
    settings["providers"]["openai"].update(
        package="@opencode/ai/providers/openai/responses",
        settings={"baseURL": mock_url, "apiKey": "fixture"},
    )
    settings["providers"]["opencode"] = {
        "package": "@opencode/ai/providers/openai/responses",
        "settings": {"baseURL": mock_url, "apiKey": "fixture"},
        "models": {"big-pickle": {"capabilities": {"tools": True}}},
    }
    settings["instructions"] = []
    settings["plugins"] = []
    for server in settings.get("mcp", {}).get("servers", {}).values():
        server["disabled"] = True
    (config / "opencode.json").write_text(json.dumps(settings))
    commands = config / "commands"
    commands.mkdir()
    (commands / "delegated-review.md").write_bytes(
        (SOURCE / "commands/delegated-review.md").read_bytes()
    )
    plugin = config / "plugins/model-calls"
    plugin.mkdir(parents=True)
    (plugin / "index.ts").write_bytes((SOURCE / "plugins/model-calls.ts").read_bytes())
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("OPENCODE_", "OPENAI_", "ANTHROPIC_", "XDG_"))
        and not key.lower().endswith("_proxy")
    }
    env.update(
        HOME=str(root),
        XDG_CONFIG_HOME=str(root / "config"),
        XDG_DATA_HOME=str(root / "data"),
        XDG_STATE_HOME=str(root / "state"),
        XDG_CACHE_HOME=str(root / "cache"),
        XDG_RUNTIME_DIR=str(runtime),
        OPENCODE_CONFIG_DIR=str(config),
        OPENCODE_DISABLE_PROJECT_CONFIG="1",
        OPENCODE_DISABLE_MODELS_FETCH="1",
        OPENCODE_PASSWORD="isolated-recovery-fixture",
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = None

    def api(path, data=None):
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/{path}",
            data=json.dumps(data).encode() if data is not None else None,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Basic "
                + base64.b64encode(b"opencode:isolated-recovery-fixture").decode(),
            },
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read()
            return json.loads(body) if body else None

    def messages(sid):
        result = []
        path = f"session/{sid}/message?limit=100&order=asc"
        while True:
            page = api(path)
            result.extend(page["data"])
            cursor = page.get("cursor", {}).get("next")
            if not page["data"] or not cursor:
                return result
            path = f"session/{sid}/message?limit=100&cursor=" + urllib.parse.quote(cursor, safe="")

    def tool_parts(items):
        return [
            part
            for message in items
            for part in message.get("content", [])
            if isinstance(part, dict) and part.get("type") == "tool"
        ]

    def run_case(mode):
        RecoveryMock.reset(mode, fixture)
        sid = api(
            "session",
            {
                "title": "Native recovery fixture " + mode,
                "metadata": {
                    "local.model-routing": {
                        "version": 1, "mode": "free",
                        "models": {"*": {"providerID": "opencode", "id": "big-pickle"}},
                    }
                },
            },
        )["data"]["id"]
        api(f"session/{sid}/command", {"name": "delegated-review", "text": "fixture.txt"})
        api(f"experimental/session/{sid}/wait", {})
        assert RecoveryMock.violation is None, RecoveryMock.violation
        parent = messages(sid)
        children = api(f"session?parentID={sid}&limit=50")["data"]
        assert len(children) == 1, children
        child_id = children[0]["id"]
        child = messages(child_id)
        tools = tool_parts(parent)
        calls = [part for part in tools if part.get("name") == "subagent"]
        assert len(calls) == (2 if mode == "terminal" else 1), calls
        assert calls[0]["state"]["metadata"]["sessionID"] == child_id
        assert calls[-1]["state"]["status"] == "completed"
        if mode == "terminal":
            assert calls[0]["state"]["status"] == "error", calls[0]
            assert calls[1]["state"]["input"]["sessionID"] == child_id
            assert RecoveryMock.child_id == child_id
            sleeps = [part for part in tools if part.get("name") == "shell"]
            assert len(sleeps) == 1 and sleeps[0]["state"]["status"] == "completed"
            assert calls[1]["time"]["created"] - calls[0]["time"]["completed"] >= 20000
        reads = [part for part in tool_parts(child) if part.get("name") == "read"]
        assert len(reads) == 1 and reads[0]["state"]["status"] == "completed"
        assert "DR_PARENT_COMPLETE" in json.dumps(parent)
        assert "DR_CHILD_COMPLETE" in json.dumps(child)
        assert RecoveryMock.failures == (11 if mode == "terminal" else 1)
        assert all(request["model"] == "big-pickle" for request in RecoveryMock.requests)
        for name, value in [("parent", parent), ("child", child), ("requests", RecoveryMock.requests)]:
            path = root / f"{mode}-{name}.json"
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
            path.chmod(0o600)
        print("PASS:", mode, "parent", sid, "child", child_id, flush=True)

    def deadline(_signum, _frame):
        raise TimeoutError("fixture exceeded the approved 240-second wall limit")

    previous_alarm = signal.signal(signal.SIGALRM, deadline)
    signal.alarm(240)
    thread.start()
    try:
        with (root / "server.log").open("w") as log:
            process = subprocess.Popen(
                [binary, "serve", "--hostname", "127.0.0.1", "--port", str(port),
                 "--log-level", "debug", "--print-logs"],
                env=env, cwd=work, stdout=log, stderr=log,
            )
            ready_by = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    raise RuntimeError("private server exited; see fixture server.log")
                try:
                    api("info")
                    break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() >= ready_by:
                        raise
                    time.sleep(0.25)
            # The list endpoint does not await asynchronous plugin activation.
            # Wait for actual discovery, not a fixed startup sleep.
            discovery_by = time.monotonic() + 20
            while True:
                available = api("command")["data"]
                if any(command["name"] == "delegated-review" for command in available):
                    break
                if time.monotonic() >= discovery_by:
                    raise AssertionError({"commands": available, "plugins": api("plugin")})
                time.sleep(0.25)
            run_case("native")
            run_case("terminal")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_alarm)
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        provider.shutdown()
        thread.join(timeout=5)
        debug = root / "last-mock-state.json"
        debug.write_text(json.dumps({
            "mode": RecoveryMock.mode,
            "parent_step": RecoveryMock.parent_step,
            "child_id": RecoveryMock.child_id,
            "failures": RecoveryMock.failures,
            "violation": RecoveryMock.violation,
            "requests": RecoveryMock.requests,
        }, ensure_ascii=False, indent=2))
        debug.chmod(0o600)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", help="installed binary; never builds it")
    main(parser.parse_args().binary)
