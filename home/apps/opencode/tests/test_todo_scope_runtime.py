"""Focused isolated V2 todo tool/context scoping; local mock provider only.

Run: python3 -B test_todo_scope_runtime.py /path/to/opencode
No real model, MCP, credentials, user DB, note writes or live service are used.
"""

import base64
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from test_v2_runtime import MockResponses

SOURCE = Path(__file__).resolve().parents[1]


def evaluate(path, apply):
    return json.loads(subprocess.check_output(
        ["nix", "eval", "--offline", "--json", "--file", str(path), "--apply", apply],
        text=True, timeout=10,
    ))


def main():
    binary = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "opencode")
    if not binary:
        raise SystemExit("OpenCode binary unavailable")
    print(subprocess.check_output([binary, "--version"], text=True).strip())
    mock = ThreadingHTTPServer(("127.0.0.1", 0), MockResponses)
    threading.Thread(target=mock.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix="todo-scope-runtime-", dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            config = root / "config/opencode"
            plugin = config / "plugins/agent-todo"
            plugin.mkdir(parents=True)
            work = root / "project"
            work.mkdir()
            (root / "runtime").mkdir(mode=0o700)
            for name, target in [
                ("agent-todo.ts", "index.ts"),
                ("agent-todo-instructions.ts", "agent-todo-instructions.ts"),
                ("agent-todo-review.ts", "agent-todo-review.ts"),
            ]:
                shutil.copyfile(SOURCE / "plugins" / name, plugin / target)
            settings = evaluate(SOURCE / "config/v2-settings.nix", "f: f { lib = {}; }")
            scope = evaluate(SOURCE / "config/todo-settings.nix", "f: f { todoDirectory = " + json.dumps(str(root / "agent-todo")) + "; }")
            settings["model"] = "openai/gpt-6.1-sol"
            settings["providers"] = {"openai": {
                "package": "@opencode/ai/providers/openai/responses",
                "settings": {"baseURL": f"http://127.0.0.1:{mock.server_port}/v1", "apiKey": "fixture"},
                "models": {"gpt-6.1-sol": {"capabilities": {"tools": True}}},
            }}
            settings.setdefault("permissions", []).extend(scope["permissions"])
            for name, agent in scope["agents"].items():
                settings["agents"].setdefault(name, {}).setdefault("permissions", []).extend(agent["permissions"])
            for agent in settings["agents"].values():
                agent["model"] = "openai/gpt-6.1-sol"
            settings["compaction"]["auto"] = False
            assert not settings.get("instructions") and not settings.get("mcp")
            (config / "opencode.json").write_text(json.dumps(settings))
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("OPENCODE_", "OPENAI_", "ANTHROPIC_", "XDG_"))}
            env.update(
                HOME=tmp, XDG_CONFIG_HOME=str(root / "config"),
                XDG_DATA_HOME=str(root / "data"), XDG_STATE_HOME=str(root / "state"),
                XDG_CACHE_HOME=str(root / "cache"), XDG_RUNTIME_DIR=str(root / "runtime"),
                OPENCODE_CONFIG_DIR=str(config), OPENCODE_DISABLE_PROJECT_CONFIG="1",
                OPENCODE_DISABLE_MODELS_FETCH="1", OPENCODE_PASSWORD="todo-scope-fixture",
            )
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            auth = "Basic " + base64.b64encode(b"opencode:todo-scope-fixture").decode()

            def api(path, data=None):
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/{path}",
                    data=json.dumps(data).encode() if data is not None else None,
                    headers={"Authorization": auth, "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=25) as response:
                    payload = response.read()
                    return json.loads(payload) if payload else None

            with (root / "server.log").open("w+") as log:
                process = subprocess.Popen(
                    [binary, "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                    cwd=work, env=env, stdout=log, stderr=log,
                )
                try:
                    deadline = time.monotonic() + 25
                    while True:
                        assert process.poll() is None, "private server exited"
                        try:
                            agents = api("agent")["data"]
                            if {"review", "research"} <= {agent["id"] for agent in agents}:
                                break
                        except (urllib.error.URLError, TimeoutError):
                            pass
                        assert time.monotonic() < deadline, "private server not ready"
                        time.sleep(0.1)
                    for name in ["build", "plan", "general", "explore", "research", "review"]:
                        sid = api("session", {"title": f"Todo scope {name}", "agent": name})["data"]["id"]
                        start = len(MockResponses.requests)
                        api(f"session/{sid}/prompt", {"text": "Reply briefly with no tools."})
                        api(f"experimental/session/{sid}/wait", {})
                        requests = MockResponses.requests[start:]
                        assert requests, f"no local mock request for {name}"
                        # Explicit session titles avoid separate naming requests.
                        names = {tool.get("name") for request in requests for tool in request.get("tools", [])}
                        note_tools = {"agent_todo_read", "agent_todo_propose"}
                        if name in {"build", "plan"}:
                            assert note_tools <= names, (name, names)
                            assert any("# Todo notes" in json.dumps(request) for request in requests), name
                        else:
                            assert not note_tools & names, (name, names)
                            assert all("# Todo notes" not in json.dumps(request) for request in requests), name
                        assert all("# Decision support" not in json.dumps(request) for request in requests), name
                        print(f"PASS: {name}: todo tools/instructions {'present' if name in {'build', 'plan'} else 'absent'}")
                    assert "decision-check" not in json.dumps(api("skill"))
                    assert not (root / "agent-todo").exists(), "scoping check created notes"
                except BaseException:
                    log.flush()
                    log.seek(0)
                    print(log.read()[-3000:], file=sys.stderr)
                    raise
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
    finally:
        mock.shutdown()
        mock.server_close()
    print("PASS: local mock only; no notes, tool execution, live service changes or real model/MCP calls")


if __name__ == "__main__":
    main()
