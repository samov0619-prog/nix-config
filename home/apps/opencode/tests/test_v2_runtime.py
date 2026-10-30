"""Opt-in isolated V2 smoke test: python3 .../test_v2_runtime.py /path/to/opencode.

No user credentials, database, config or background service are used.
"""

import base64
from collections import Counter
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SOURCE = Path(__file__).resolve().parents[1]


class MockResponses(BaseHTTPRequestHandler):
    requests = []
    paths = []
    fail_next = False
    fail_status = 400
    next_tool_command = None
    next_tool_skill = None
    next_tool = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.requests.append(body)
        self.paths.append(self.path)
        if self.fail_next:
            type(self).fail_next = False
            self.send_response(self.fail_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                b'{"error":{"type":"invalid_request_error","message":"fixture unavailable"}}'
            )
            return
        reply = "Mock response"
        if "You MUST use this format for your response" in json.dumps(body):
            reply = "\n\n".join(
                f"{heading}\n- Fixture"
                for heading in (
                    "## Objective",
                    "## Requirements",
                    "## Decisions",
                    "## Work State",
                    "### Completed",
                    "### Active",
                    "### Blocked",
                    "## Next Move",
                    "## Relevant Files",
                    "## Important Context",
                )
            )
        item = {
            "id": "msg_mock",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": reply, "annotations": []}],
        }
        checkpoint = any(
            item.get("type") == "compaction_trigger" for item in body.get("input", [])
        )
        if checkpoint:
            item = {
                "type": "compaction",
                "id": "cmp_mock",
                "encrypted_content": "fixture-checkpoint",
            }
        tool_call = self.next_tool_command or self.next_tool_skill or self.next_tool
        if tool_call:
            skill_call = self.next_tool_skill
            custom_call = self.next_tool
            type(self).next_tool_command = None
            type(self).next_tool_skill = None
            type(self).next_tool = None
            # Deliberately reuse the provider call ID across assistant messages.
            item = {
                "type": "function_call",
                "id": "fc_mock",
                "call_id": "call_mock",
                "name": custom_call[0]
                if custom_call
                else "skill"
                if skill_call
                else "shell",
                "arguments": json.dumps(
                    custom_call[1]
                    if custom_call
                    else {"id": skill_call}
                    if skill_call
                    else {"command": tool_call, "timeout": 1000}
                ),
            }
        response = {
            "id": "resp_mock",
            "object": "response",
            "created_at": int(time.time()),
            "model": body["model"],
            "status": "completed",
            "output": [item],
            "usage": {
                "input_tokens": 20,
                "output_tokens": 4,
                "total_tokens": 24,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens_details": {"reasoning_tokens": 0},
            },
        }
        if self.path.endswith("/compact"):
            encoded = json.dumps(
                {
                    "object": "response.compaction",
                    "output": [
                        {
                            "type": "compaction",
                            "id": "cmp_mock",
                            "encrypted_content": "fixture-checkpoint",
                        },
                    ],
                    "usage": response["usage"],
                }
            ).encode()
            content_type = "application/json"
        elif body.get("stream"):
            events = [
                {
                    "type": "response.created",
                    "response": {**response, "status": "in_progress", "output": []},
                },
                {
                    "type": "response.output_item.added",
                    "output_index": 0,
                    "item": {**item, "status": "in_progress", "content": []},
                },
                {
                    "type": "response.content_part.added",
                    "item_id": item["id"],
                    "output_index": 0,
                    "content_index": 0,
                    "part": {"type": "output_text", "text": "", "annotations": []},
                },
                {
                    "type": "response.output_text.delta",
                    "item_id": item["id"],
                    "output_index": 0,
                    "content_index": 0,
                    "delta": reply,
                },
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": response},
            ]
            if checkpoint:
                events = [
                    events[0],
                    {
                        "type": "response.output_item.done",
                        "output_index": 0,
                        "item": item,
                    },
                    events[-1],
                ]
            if tool_call:
                events = [
                    events[0],
                    {
                        "type": "response.output_item.added",
                        "output_index": 0,
                        "item": item,
                    },
                    {
                        "type": "response.output_item.done",
                        "output_index": 0,
                        "item": item,
                    },
                    events[-1],
                ]
            encoded = "".join(
                "data: " + json.dumps(event) + "\n\n" for event in events
            ).encode()
            content_type = "text/event-stream"
        else:
            encoded = json.dumps(response).encode()
            content_type = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main(binary, catalog_only=False, mac=False, native=False):
    settings = json.loads(
        subprocess.check_output(
            [
                "nix",
                "eval",
                "--json",
                "--file",
                str(SOURCE / "config/v2-settings.nix"),
                "--apply",
                "f: f { lib = {}; }",
            ]
        )
    )
    mock = ThreadingHTTPServer(("127.0.0.1", 0), MockResponses)
    threading.Thread(target=mock.serve_forever, daemon=True).start()
    mock_url = f"http://127.0.0.1:{mock.server_port}/v1"
    settings["providers"]["openai"].update(
        package="@opencode/ai/providers/openai/responses",
        settings={"baseURL": mock_url, "apiKey": "mock"},
    )
    # Only the fixture supplies a fake free catalog; production uses the real one.
    free_fixture = {
        "package": "@opencode/ai/providers/openai/responses",
        "settings": {"baseURL": mock_url, "apiKey": "mock"},
        "models": {"big-pickle": {"capabilities": {"tools": True}}},
    }
    if not catalog_only:
        settings["providers"]["opencode"] = free_fixture
    if native:
        for provider in settings["providers"].values():
            provider["settings"]["compaction"] = {"type": "native"}
            for model in provider.get("models", {}).values():
                model.setdefault("settings", {})["compaction"] = {"type": "native"}
    if mac:
        settings = json.loads((SOURCE / "macos/opencode/opencode.json").read_text())
        for server in settings["mcp"]["servers"].values():
            server["disabled"] = (
                True  # Never connect to corporate services in this test.
            )
    generation = os.environ.get("OPENCODE_TEST_HM_GENERATION")
    with tempfile.TemporaryDirectory(prefix="opencode-v2-", dir="/tmp/opencode") as tmp:
        root = Path(tmp)
        config = root / "config" / "opencode"
        config.mkdir(parents=True)
        (config / "opencode.json").write_text(json.dumps(settings))
        for name, entry in [
            ("git-offline", "git-offline.ts"),
            ("permission-stats", "permission-stats.ts"),
            ("model-calls", "model-calls.ts"),
            ("skill-stats", "skill-stats.ts"),
            ("agent-todo", "agent-todo.ts"),
        ]:
            plugin = config / "plugins" / name
            generation = os.environ.get("OPENCODE_TEST_HM_GENERATION")
            if generation:
                plugin.parent.mkdir(parents=True, exist_ok=True)
                plugin.symlink_to(
                    Path(generation)
                    / "home-files/.config/opencode/plugins"
                    / f"{name}-v2",
                    target_is_directory=True,
                )
            else:
                plugin.mkdir(parents=True)
                (plugin / "index.ts").write_text(
                    (SOURCE / "plugins" / entry).read_text()
                )
        for skill_id in ["discussion-map", "git-regression-rollback", "decision-check"]:
            skill = config / "skills" / skill_id / "SKILL.md"
            skill.parent.mkdir(parents=True)
            if generation:
                skill.symlink_to(
                    Path(generation)
                    / "home-files/.config/opencode/skills"
                    / skill_id
                    / "SKILL.md"
                )
            else:
                skill.write_text(
                    (SOURCE / "skills" / skill_id / "SKILL.md").read_text()
                )
        rules = config / "AGENTS.md"
        # Resolve the home-only configured instruction inside the isolated HOME.
        settings["instructions"] = [str(config / "decision-support.md")]
        (config / "opencode.json").write_text(json.dumps(settings))
        (config / "decision-support.md").write_text(
            (SOURCE / "config/decision-support.md").read_text()
        )
        if generation:
            rules.symlink_to(Path(generation) / "home-files/.config/opencode/AGENTS.md")
        else:
            rules.write_text((SOURCE / "config/AGENTS.md").read_text())
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("OPENCODE_", "OPENAI_", "ANTHROPIC_", "XDG_"))
        }
        env.update(
            HOME=tmp,
            XDG_CONFIG_HOME=str(root / "config"),
            XDG_DATA_HOME=str(root / "data"),
            XDG_STATE_HOME=str(root / "state"),
            XDG_CACHE_HOME=str(root / "cache"),
            XDG_RUNTIME_DIR=str(root / "runtime"),
            OPENCODE_CONFIG_DIR=str(config),
            OPENCODE_DISABLE_PROJECT_CONFIG="1",
            OPENCODE_DISABLE_MODELS_FETCH="1",
            OPENCODE_PASSWORD="isolated-smoke",
        )
        (root / "runtime").mkdir(mode=0o700)
        work = root
        if mac:
            personal = root / "config/opencode-local"
            personal.mkdir()
            for name in ["opencode.json", "AGENTS-personal.md"]:
                (personal / name).write_text(
                    (SOURCE / "macos/opencode-local" / name).read_text()
                )
            work = root / "project"
            work.mkdir()
            (work / "opencode.json").write_text(
                json.dumps(
                    {
                        "$schema": "https://opencode.ai/config.json",
                        "model": "copilot/x5-airun-small",
                    }
                )
            )
            env.update(
                OPENCODE_CONFIG=str(personal / "opencode.json"),
                OPENCODE_DISABLE_PROJECT_CONFIG="0",
                MCP_WIKI_URL="http://127.0.0.1:9/wiki",
                MCP_WIKI_AUTHORIZATION="Bearer fixture",
                MCP_KAITEN_URL="http://127.0.0.1:9/kaiten",
                MCP_KAITEN_AUTHORIZATION="Bearer fixture",
            )
        log_path = root / "server.log"
        with log_path.open("w+") as log:
            process = subprocess.Popen(
                [
                    binary,
                    "serve",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--log-level",
                    "debug",
                    "--print-logs",
                ],
                env=env,
                cwd=work,
                stdout=log,
                stderr=log,
            )

            def api(path, data=None, method=None):
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/{path}",
                    data=json.dumps(data).encode() if data is not None else None,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Basic "
                        + base64.b64encode(b"opencode:isolated-smoke").decode(),
                    },
                    method=method,
                )
                with urllib.request.urlopen(request, timeout=30) as response:
                    body = response.read()
                    return json.loads(body) if body else None

            try:
                deadline = time.monotonic() + 90
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(f"server exited {process.returncode}")
                    try:
                        resolved = api("config")
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() > deadline:
                            raise
                        time.sleep(0.25)
                if mac:
                    by_path = {
                        doc.get("path"): doc["info"]
                        for doc in resolved
                        if doc.get("type") == "document"
                    }
                    assert str(personal / "opencode.json") in by_path, by_path.keys()
                    assert str(work / "opencode.json") in by_path, by_path.keys()
                    team = by_path[str(config / "opencode.json")]
                    assert (
                        team["mcp"]["servers"]["MCP-WIKI"]["headers"]["Authorization"]
                        == "Bearer fixture"
                    )
                    assert (
                        team["providers"]["copilot"]["settings"]["baseURL"]
                        == "https://api-copilot.x5.ru/v1/"
                    )
                    print(
                        "PASS: Mac native schema, env substitution, team/personal/project config layers"
                    )
                    return
                assert any(
                    doc.get("info", {}).get("model", {}).get("model") == "gpt-6.1-sol"
                    for doc in resolved
                ), resolved
                print("PASS: native config parsed")
                deadline = time.monotonic() + 20
                while True:
                    agents = api("agent")
                    plugins = api("plugin")
                    skills = api("skill")
                    if (
                        agents.get("data")
                        and plugins.get("data")
                        and {"discussion-map", "git-regression-rollback"}
                        <= {s["id"] for s in skills.get("data", [])}
                    ):
                        break
                    if time.monotonic() > deadline:
                        raise AssertionError({"agents": agents, "plugins": plugins})
                    time.sleep(0.25)
                assert {"build", "plan", "explore", "research", "review"} <= {
                    a["id"] for a in agents["data"]
                }
                local = [
                    plugin
                    for plugin in plugins["data"]
                    if plugin["id"].startswith("local.")
                ]
                assert {p["id"] for p in local} == {
                    "local.git-offline",
                    "local.permission-stats",
                    "local.model-calls",
                    "local.skill-stats",
                    "local.agent-todo",
                }, local
                assert all(p["state"]["status"] == "active" for p in local), local
                print("PASS: configured agents and native local plugins active")
                by_skill = {skill["id"]: skill for skill in skills["data"]}
                assert {"opencode", "report"} <= by_skill.keys()
                for skill_id in [
                    "discussion-map",
                    "git-regression-rollback",
                    "decision-check",
                ]:
                    expected = next(
                        line.removeprefix("description: ")
                        for line in (SOURCE / "skills" / skill_id / "SKILL.md")
                        .read_text()
                        .splitlines()
                        if line.startswith("description: ")
                    )
                    assert by_skill[skill_id]["description"] == expected, by_skill[
                        skill_id
                    ]
                assert "For multi-turn planning or discussion" not in rules.read_text()
                print(
                    "PASS: native skill discovery advertises scoped descriptions; no blanket discussion-map rule"
                )
                if catalog_only:
                    catalog = api("model")
                    free = [
                        model
                        for model in catalog["data"]
                        if model["id"] == "big-pickle"
                    ]
                    print("Real Big Pickle catalog entries:", json.dumps(free))
                    assert any(model["providerID"] == "opencode" for model in free), (
                        "free model unavailable in native V2 catalog"
                    )
                    return
                session = api("session", {})
                session_id = session["data"]["id"]

                def assert_compacted():
                    with sqlite3.connect(
                        f"file:{root / 'data/opencode/opencode.db'}?mode=ro", uri=True
                    ) as db:
                        rows = [
                            json.loads(data)
                            for (data,) in db.execute(
                                "SELECT data FROM session_message WHERE type='compaction'"
                            )
                        ]
                    assert rows and all(row["status"] == "completed" for row in rows), (
                        rows
                    )

                def prompt(sid, expected_model, effort=None, title=False):
                    start = len(MockResponses.requests)
                    api(f"session/{sid}/prompt", {"text": "Reply briefly."})
                    api(f"experimental/session/{sid}/wait", {}, "POST")
                    requests = MockResponses.requests[start:]
                    assert requests, "no provider request"
                    title_model = "gpt-6-luna" if title is True else title
                    assert all(
                        req["model"]
                        in (
                            {expected_model, title_model} if title else {expected_model}
                        )
                        for req in requests
                    ), requests
                    if effort:
                        assert any(
                            req.get("reasoning", {}).get("effort") == effort
                            for req in requests
                        ), requests
                    if title:
                        deadline = time.monotonic() + 10
                        while len(MockResponses.requests[start:]) < 2 or not any(
                            req["model"] == title_model
                            for req in MockResponses.requests[start:]
                        ):
                            assert time.monotonic() < deadline, "no title request"
                            time.sleep(0.1)
                        if title is True:
                            assert any(
                                req.get("reasoning", {}).get("effort") == "low"
                                for req in MockResponses.requests[start:]
                            )
                        assert all(
                            req["model"] in {expected_model, title_model}
                            for req in MockResponses.requests[start:]
                        )
                    print(
                        f"PASS: {expected_model} {effort or ''}: {len(MockResponses.requests[start:])} actual mock requests"
                    )

                prompt(session_id, "gpt-6.1-sol", "high", title=True)
                key = "local.model-routing"
                api(
                    f"session/{session_id}",
                    {
                        "metadata": {
                            "foreign": 1,
                            key: {
                                "version": 1,
                                "mode": "free",
                                "models": {
                                    "*": {"providerID": "opencode", "id": "big-pickle"}
                                },
                            },
                        }
                    },
                    "PATCH",
                )
                prompt(session_id, "big-pickle")
                start = len(MockResponses.requests)
                api(f"session/{session_id}/generate", {"prompt": "Summarize briefly."})
                assert MockResponses.requests[start:] and all(
                    r["model"] == "big-pickle" for r in MockResponses.requests[start:]
                )
                print("PASS: free auxiliary generation uses Big Pickle")
                start = len(MockResponses.requests)
                api(f"session/{session_id}/compact", {})
                api(f"experimental/session/{session_id}/wait", {}, "POST")
                assert_compacted()
                assert MockResponses.requests[start:] and all(
                    r["model"] == "big-pickle" for r in MockResponses.requests[start:]
                )
                print("PASS: free manual compaction uses Big Pickle")
                if native:
                    assert any(
                        item.get("type") == "compaction_trigger"
                        for item in MockResponses.requests[start]["input"]
                    )
                child = api(
                    "session",
                    {"parentID": session_id, "agent": "explore", "title": "Child"},
                )["data"]["id"]
                prompt(child, "big-pickle")
                start = len(MockResponses.requests)
                MockResponses.fail_next = True
                api(f"session/{child}/prompt", {"text": "Error fixture"})
                try:
                    api(f"experimental/session/{child}/wait", {}, "POST")
                except urllib.error.HTTPError as error:
                    assert error.code == 503, error
                assert (
                    len(MockResponses.requests[start:]) == 1
                    and MockResponses.requests[-1]["model"] == "big-pickle"
                )
                print("PASS: provider error does not fall back to a paid provider")
                paid = json.loads(
                    (SOURCE / "plugins/model-routing/routing-models.json").read_text()
                )
                api(
                    f"session/{session_id}",
                    {
                        "metadata": {
                            "foreign": 1,
                            key: {
                                "version": 1,
                                "mode": "paid",
                                "models": paid,
                            },
                        }
                    },
                    "PATCH",
                )
                prompt(child, "gpt-6-luna", "max")
                api(f"session/{session_id}/agent", {"agent": "plan"})
                prompt(session_id, "gpt-6.1-sol", "xhigh")
                start = len(MockResponses.requests)
                api(f"session/{session_id}/generate", {"prompt": "Summarize briefly."})
                assert (
                    MockResponses.requests[start:]
                    and MockResponses.requests[-1]["model"] == "gpt-6.1-sol"
                )
                assert (
                    MockResponses.requests[-1].get("reasoning", {}).get("effort")
                    == "high"
                )
                print("PASS: paid auxiliary generation uses High after Plan XHigh")
                start = len(MockResponses.requests)
                api(f"session/{session_id}/compact", {})
                api(f"experimental/session/{session_id}/wait", {}, "POST")
                assert_compacted()
                compact_requests = MockResponses.requests[start:]
                assert (
                    compact_requests and compact_requests[0]["model"] == "gpt-6.1-sol"
                ), compact_requests
                assert (
                    compact_requests[0].get("reasoning", {}).get("effort") == "high"
                ), compact_requests
                print("PASS: paid compaction uses High after Plan XHigh")
                if native:
                    assert any(
                        item.get("type") == "compaction_trigger"
                        for item in compact_requests[0]["input"]
                    )
                    print("PASS: native streamed checkpoint compaction routing")
                assert api(f"session/{session_id}")["data"]["metadata"]["foreign"] == 1
                report = json.loads(
                    subprocess.check_output(
                        [
                            sys.executable,
                            str(SOURCE / "scripts/task-report.py"),
                            "--session",
                            session_id,
                            "--json",
                        ],
                        env=env,
                    )
                )
                assert report["storage"] == "v2", report
                assert (
                    report["totals"]["input"] == 140
                    and report["totals"]["output"] == 28
                ), report["totals"]
                assert (
                    report["processed_total_tokens"] == 168
                    and report["compactions"] == 2
                ), report
                calls = report["model_calls"]
                assert {row["kind"] for row in calls} == {
                    "primary",
                    "title",
                    "generate",
                    "compaction",
                }, calls
                assert any(
                    row["kind"] == "title"
                    and row["wireModel"] == "gpt-6-luna"
                    and row["effort"] == "low"
                    for row in calls
                ), calls
                assert any(
                    row["sessionID"] == child
                    and row["agent"] == "explore"
                    and row.get("http_status") == 400
                    for row in calls
                ), calls
                assert all(row.get("http_status") in (200, 400) for row in calls), calls
                assert any(
                    row["kind"] == "primary"
                    and row.get("variant") == "xhigh"
                    and row.get("effort") == "xhigh"
                    for row in calls
                ), calls
                recent = json.loads(
                    subprocess.check_output(
                        [
                            sys.executable,
                            str(SOURCE / "scripts/task-report.py"),
                            "--recent",
                            "10",
                            "--json",
                        ],
                        env=env,
                    )
                )
                assert {session_id, child} <= {row["id"] for row in recent}, recent
                print(
                    "PASS: real V2 SQLite read-only accounting, exact tokens, children and recent sessions"
                )
                print("PASS: live root routing affects existing children and Plan")
                free = api(
                    "session",
                    {
                        "metadata": {
                            key: {
                                "version": 1,
                                "mode": "free",
                                "models": {
                                    "*": {"providerID": "opencode", "id": "big-pickle"}
                                },
                            }
                        }
                    },
                )["data"]["id"]
                prompt(free, "big-pickle", title="big-pickle")
                print("PASS: new free session title also uses Big Pickle")
                free_report = json.loads(
                    subprocess.check_output(
                        [
                            sys.executable,
                            str(SOURCE / "scripts/task-report.py"),
                            "--session",
                            free,
                            "--json",
                        ],
                        env=env,
                    )
                )
                assert any(
                    row["kind"] == "title" and row["wireModel"] == "big-pickle"
                    for row in free_report["model_calls"]
                ), free_report["model_calls"]
                retry_session = api("session", {"title": "Retry fixture"})["data"]["id"]
                start = len(MockResponses.requests)
                MockResponses.fail_next, MockResponses.fail_status = True, 429
                prompt(retry_session, "gpt-6.1-sol", "high")
                MockResponses.fail_status = 400
                assert len(MockResponses.requests[start:]) >= 2, (
                    "retry was not exercised"
                )
                retry_report = json.loads(
                    subprocess.check_output(
                        [
                            sys.executable,
                            str(SOURCE / "scripts/task-report.py"),
                            "--session",
                            retry_session,
                            "--json",
                        ],
                        env=env,
                    )
                )
                assert [r.get("http_status") for r in retry_report["model_calls"]] == [
                    429,
                    200,
                ], retry_report["model_calls"]
                if not native:
                    sid = api(
                        "session",
                        {
                            "title": "Git policy fixture",
                            "permissions": [
                                {"action": "shell", "resource": "*", "effect": "ask"},
                            ],
                        },
                    )["data"]["id"]
                    # Persist an actual native Always grant, then exercise the real
                    # shell parser and policy evaluation through model tool calls.
                    grant = api(
                        f"session/{sid}/permission",
                        {
                            "action": "shell",
                            "resources": ["fixture-policy-grant"],
                            "save": ["*"],
                        },
                    )["data"]
                    assert grant["effect"] == "ask", grant
                    api(
                        f"session/{sid}/permission/{grant['id']}/reply",
                        {"decision": "always"},
                    )
                    assert any(
                        row["action"] == "shell" and row["resource"] == "*"
                        for row in api("permission/saved")["data"]
                    )
                    marker = root / "must-not-execute"
                    for command, denied in [
                        (f"touch {marker} && git fetch", True),
                        ("git -C . fetch", True),
                        ("git remote show origin", True),
                        ("git remote show -n origin", False),
                    ]:
                        MockResponses.next_tool_command = command
                        prompt(sid, "gpt-6.1-sol", "high")
                        with sqlite3.connect(
                            f"file:{root / 'data/opencode/opencode.db'}?mode=ro",
                            uri=True,
                        ) as db:
                            tools = [
                                part
                                for (data,) in db.execute(
                                    "SELECT data FROM session_message WHERE session_id=? AND type='assistant' ORDER BY seq",
                                    (sid,),
                                )
                                for part in json.loads(data).get("content", [])
                                if part["type"] == "tool"
                            ]
                        assert (
                            tools
                            and (tools[-1]["state"]["status"] == "error") == denied
                        ), tools[-1:]
                        assert not marker.exists(), (
                            "compound command executed before policy denial"
                        )
                    print(
                        "PASS: native shell parser enforces Git policies over saved Always, including compound/-C and cached show -n"
                    )
                    history = root / "state/opencode/permission-history.jsonl"
                    rows = [
                        json.loads(line) for line in history.read_text().splitlines()
                    ]
                    assert any(
                        row["requestID"] == grant["id"]
                        and row["sessionID"] == sid
                        and row["response"] == "always"
                        for row in rows
                    ), rows
                    assert history.stat().st_mode & 0o777 == 0o600
                    print(
                        "PASS: native permission stream recorded correlated Always decision privately"
                    )
                # Real native tool hooks and plugin KV storage; the mock emits a
                # skill call, not a synthetic plugin event. No paid inference.
                skill_session = api(
                    "session",
                    {
                        "title": "Skill stats fixture",
                        "permissions": [
                            {"action": "skill", "resource": "*", "effect": "allow"},
                        ],
                    },
                )["data"]["id"]
                for skill_id in ["discussion-map", "missing-fixture-skill"]:
                    MockResponses.next_tool_skill = skill_id
                    prompt(skill_session, "gpt-6.1-sol", "high")
                skill_report = json.loads(
                    subprocess.check_output(
                        [
                            sys.executable,
                            str(SOURCE / "scripts/skill-stats.py"),
                            "--json",
                            "--examples",
                            "10",
                        ],
                        env=env,
                    )
                )
                observed = {row["skill"]: row for row in skill_report["skills"]}
                assert observed["discussion-map"]["completed"] == 1, skill_report
                assert observed["missing-fixture-skill"]["error"] == 1, skill_report
                assert len(skill_report["examples"]) == 2, skill_report
                assert all(
                    row["lastQuery"] == "Reply briefly."
                    and row["queryID"]
                    and row["sessionID"] == skill_session
                    for row in skill_report["examples"]
                ), skill_report
                assert all(
                    row["model"]["id"] == "gpt-6.1-sol"
                    for row in skill_report["examples"]
                ), skill_report
                print(
                    "PASS: actual skill success/error recorded once in native plugin storage with preceding query and model"
                )
                # Exercise the actual Promise adapter -> native question executor,
                # form API and Git backend, not a replacement confirmation mock.
                todo_session = api(
                    "session",
                    {
                        "title": "Todo confirmation fixture",
                        "permissions": [
                            {"action": action, "resource": "*", "effect": "allow"}
                            for action in ("read", "edit", "question")
                        ],
                    },
                )["data"]["id"]

                def last_tool(sid):
                    with sqlite3.connect(
                        f"file:{root / 'data/opencode/opencode.db'}?mode=ro", uri=True
                    ) as db:
                        tools = [
                            part
                            for (data,) in db.execute(
                                "SELECT data FROM session_message WHERE session_id=? AND type='assistant' ORDER BY seq",
                                (sid,),
                            )
                            for part in json.loads(data).get("content", [])
                            if part["type"] == "tool"
                        ]
                    return tools[-1]["state"]

                def tool_result(sid):
                    state = last_tool(sid)
                    assert state["status"] == "completed", state
                    return json.loads(
                        "".join(
                            c["text"] for c in state["content"] if c["type"] == "text"
                        )
                    )

                MockResponses.next_tool = ("agent_todo_read", {})
                prompt(todo_session, "gpt-6.1-sol", "high")
                todo = tool_result(todo_session)
                assert not (root / "agent-todo").exists(), todo
                proposal = {
                    "base": todo["fingerprint"],
                    "content": "# Todo\n\n## Проверка устройства\n<!-- todo:device -->\n\n- Цель:\n  Проверить сон.\n",
                    "reason": "Сохранить проверку.",
                    "message": "add device test note",
                }
                for answer, expected in [
                    ("Нет, не сохранять", "declined"),
                    ("Уточни формулировку", "revise"),
                    ("Да, сохранить", "saved"),
                ]:
                    MockResponses.next_tool = ("agent_todo_propose", proposal)
                    api(f"session/{todo_session}/prompt", {"text": "Предложи заметку."})
                    deadline = time.monotonic() + 20
                    while True:
                        forms = api(f"session/{todo_session}/form")["data"]
                        if forms:
                            form = forms[0]
                            break
                        assert time.monotonic() < deadline, last_tool(todo_session)
                        time.sleep(0.1)
                    assert form["fields"][0]["custom"] is True, form
                    assert (
                        "Обращений: 1 · Приоритет: 1"
                        in form["fields"][0]["description"]
                    ), form
                    assert not (root / "agent-todo/todo.md").exists()
                    # Isolated identity only; never write the real user's Git config.
                    (root / ".gitconfig").write_text(
                        "[user]\n name = Todo Fixture\n email = todo@example.invalid\n"
                    )
                    api(
                        f"session/{todo_session}/form/{form['id']}/reply",
                        {"answer": {"q0": answer}},
                    )
                    api(f"experimental/session/{todo_session}/wait", {}, "POST")
                    result = tool_result(todo_session)
                    assert result["status"] == expected, result
                assert (
                    "Обращений: 1 · Приоритет: 1"
                    in (root / "agent-todo/todo.md").read_text()
                )
                assert ";last:" in (root / "agent-todo/todo.md").read_text(), (
                    "native in-flight user attribution missing"
                )
                assert (
                    subprocess.check_output(
                        ["git", "status", "--porcelain"],
                        cwd=root / "agent-todo",
                        env=env,
                    )
                    == b""
                )
                MockResponses.next_tool = ("agent_todo_read", {})
                prompt(todo_session, "gpt-6.1-sol", "high")
                proposal["base"] = tool_result(todo_session)["fingerprint"]
                proposal["revisited"] = ["device"]
                MockResponses.next_tool = ("agent_todo_propose", proposal)
                api(
                    f"session/{todo_session}/prompt",
                    {"text": "Вернёмся к проверке устройства."},
                )
                deadline = time.monotonic() + 20
                while True:
                    forms = api(f"session/{todo_session}/form")["data"]
                    if forms:
                        form = forms[0]
                        break
                    assert time.monotonic() < deadline, last_tool(todo_session)
                    time.sleep(0.1)
                assert (
                    "Обращений: 2 · Приоритет: 2" in form["fields"][0]["description"]
                ), form
                api(
                    f"session/{todo_session}/form/{form['id']}/reply",
                    {"answer": {"q0": "Да, сохранить"}},
                )
                api(f"experimental/session/{todo_session}/wait", {}, "POST")
                assert tool_result(todo_session)["status"] == "saved"
                assert (
                    "Обращений: 2 · Приоритет: 2"
                    in (root / "agent-todo/todo.md").read_text()
                )
                api(f"session/{todo_session}/agent", {"agent": "plan"})
                MockResponses.next_tool = ("agent_todo_read", {})
                prompt(todo_session, "gpt-6.1-sol", "xhigh")
                proposal["base"] = tool_result(todo_session)["fingerprint"]
                MockResponses.next_tool = ("agent_todo_propose", proposal)
                prompt(todo_session, "gpt-6.1-sol", "xhigh")
                assert last_tool(todo_session)["status"] == "error", last_tool(
                    todo_session
                )
                assert not api(f"session/{todo_session}/form")["data"]
                print(
                    "PASS: native todo read, exact diff form, no/revise/yes, real local commit, revisit attribution/priority and Plan edit denial"
                )
                attempts = []
                for path in (root / "state/opencode/model-calls").glob("*.jsonl"):
                    rows = [json.loads(line) for line in path.read_text().splitlines()]
                    attempts.extend(row for row in rows if row["event"] == "attempt")
                    assert path.stat().st_mode & 0o777 == 0o600
                    assert not any(
                        secret in path.read_text()
                        for secret in (
                            "Reply briefly",
                            "Summarize briefly",
                            "authorization",
                            "input_tokens",
                            "fixture unavailable",
                        )
                    )
                assert len(attempts) == len(MockResponses.requests), (
                    len(attempts),
                    len(MockResponses.requests),
                )
                assert Counter(
                    (r["wireModel"], r.get("effort")) for r in attempts
                ) == Counter(
                    (r["model"], r.get("reasoning", {}).get("effort"))
                    for r in MockResponses.requests
                )
                print(
                    "PASS: every real mock HTTP attempt, title/free title, generation, children, compaction and retry recorded privately without token double-counting"
                )
            except Exception:
                log.flush()
                text = log_path.read_text()
                print(text[-7000:], file=sys.stderr)
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                mock.shutdown()


if __name__ == "__main__":
    main(
        sys.argv[1],
        "--catalog" in sys.argv[2:],
        "--mac" in sys.argv[2:],
        "--native" in sys.argv[2:],
    )
