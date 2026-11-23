"""Load actual generated personal files against a minimal neutral Common fixture.

Run: python3 -B test_personal_layers_runtime.py /path/to/opencode
Private servers/local mock only; no live config, notes, MCP or browser access.
This is not acceptance of the later HM wiring or the complete corporate Common.
"""

import base64
import io
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
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

from test_todo_scope_runtime import evaluate
from test_v2_runtime import MockResponses, SOURCE


class LayerResponses(MockResponses):
    """Script native tool choices; never claim this proves model obedience."""

    delegation = None
    lock = threading.Lock()

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        body = json.loads(raw)
        with type(self).lock:
            script = self.delegation
            if script and script["marker"] in json.dumps(body):
                names = {tool.get("name") for tool in body.get("tools", [])}
                if "subagent" in names and not script["launched"]:
                    script["launched"] = True
                    type(self).next_tool = ("subagent", {
                        "agent": script["agent"], "description": "Generated layer inheritance fixture",
                        "prompt": script["marker"] + ": read the supplied fixture/policies only.",
                    })
                elif "subagent" not in names and "read" in names and script["reads"]:
                    type(self).next_tool = ("read", {"path": str(script["reads"].pop(0))})
            self.rfile = io.BytesIO(raw)
            super().do_POST()


def materialize(directory, files):
    for name, entry in files.items():
        target = directory / name
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        target.parent.mkdir(parents=True, exist_ok=True)
        if "text" in entry:
            target.write_text(entry["text"])
        else:
            shutil.copyfile(entry["source"], target)
        assert not target.is_symlink()


def file_text(entry):
    return entry["text"] if "text" in entry else Path(entry["source"]).read_text()


def text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from text_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from text_values(child)


def run(binary, root, label, layer, enabled, mock_url):
    root.mkdir(mode=0o700)
    home = root / "home"
    config_home = home / ("custom-config" if label == "home-hm-layout" else ".config")
    config = config_home / "opencode"
    personal = config_home / "opencode-local"
    work = root / "unrelated-project"
    for directory in [config, work, root / "runtime"]:
        directory.mkdir(parents=True, mode=0o700)
    # Keep the adjacent personal files even in Common-only: prove they are not
    # discovered without OPENCODE_CONFIG. Never alter the generated JSONC.
    if label == "home-hm-layout":
        layer = evaluate(SOURCE / "config/personal-layers.nix", "f: f { personalDirectory = "
                         + json.dumps(str(personal)) + "; todoDirectory = "
                         + json.dumps(str(home / "agent-todo")) + "; }")["home"]
    materialize(personal, layer["files"])
    if label == "home-hm-layout":
        # HM's combined plugin is one store-directory link, not escaping leaf
        # index.ts links. Exercise this layout without building a derivation.
        bundle = root / "store-like-todo"
        shutil.move(personal / "plugins/agent-todo", bundle)
        (personal / "plugins/agent-todo").symlink_to(bundle, target_is_directory=True)
    git_plugin = config / "plugins/git-offline"
    git_plugin.mkdir(parents=True)
    shutil.copyfile(SOURCE / "plugins/git-offline.ts", git_plugin / "index.ts")
    common = {
        "$schema": "https://opencode.ai/config.json",
        "update": "disable", "share": "disabled", "formatter": False,
        "model": "openai/gpt-6.1-sol", "compaction": {"auto": False},
        "permissions": [{"action": "shell", "resource": "fixture-deny *", "effect": "deny"}],
        "policies": [{"action": "provider.use", "resource": "openai", "effect": "allow"}],
        "providers": {"openai": {
            "package": "@opencode/ai/providers/openai/responses",
            "settings": {"baseURL": mock_url, "apiKey": "fixture"},
            "models": {"gpt-6.1-sol": {"capabilities": {"tools": True}}},
        }},
    }
    instruction_layers = json.loads(subprocess.check_output(
        ["nix", "eval", "--offline", "--json", "--file", str(SOURCE / "config/instructions.nix")],
        text=True, timeout=10,
    ))
    base_instructions = instruction_layers["corporate" if label == "corporate" else "homeBase"]
    (config / "AGENTS.md").write_text(base_instructions)
    assert not any(marker in base_instructions for marker in ["## Goals and Approach", "discussion-map", "opencode-local", "`research`"])
    (config / "opencode.jsonc").write_text(json.dumps(common))
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("OPENCODE_", "OPENAI_", "ANTHROPIC_", "XDG_"))}
    # Isolation is intentional: protect real credentials, sessions and config.
    env.update(
        HOME=str(home), XDG_CONFIG_HOME=str(config_home),
        XDG_DATA_HOME=str(root / "data"), XDG_STATE_HOME=str(root / "state"),
        XDG_CACHE_HOME=str(root / "cache"), XDG_RUNTIME_DIR=str(root / "runtime"),
        OPENCODE_CONFIG_DIR=str(config), OPENCODE_DISABLE_PROJECT_CONFIG="1",
        OPENCODE_DISABLE_MODELS_FETCH="1", OPENCODE_PASSWORD="personal-layer-fixture",
    )
    if enabled:
        env["OPENCODE_CONFIG"] = str(personal / "opencode.jsonc")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    auth = "Basic " + base64.b64encode(b"opencode:personal-layer-fixture").decode()

    def api(path, data=None):
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/{path}",
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Authorization": auth, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = response.read()
            return json.loads(payload) if payload else None

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

    def children(sid):
        result = []
        path = f"session?parentID={sid}&limit=100"
        while True:
            page = api(path)
            result.extend(page["data"])
            cursor = page.get("cursor", {}).get("next")
            if not page["data"] or not cursor:
                return result
            path = f"session?parentID={sid}&limit=100&cursor=" + urllib.parse.quote(cursor, safe="")

    def wait_idle(sid):
        api(f"experimental/session/{sid}/wait", {})

    selected_model = {"providerID": "openai", "id": "gpt-6.1-sol", "variant": "low"}

    def assert_identity(sid, name):
        session = api(f"session/{sid}")["data"]
        assert session["agent"] == name and session["model"] == selected_model, session
        replies = [message for message in messages(sid) if message["type"] == "assistant"]
        assert replies and all(message["agent"] == name and message["model"] == selected_model
                               for message in replies), (name, replies)

    def assert_wire_identity(requests):
        assert requests and all(request["model"] == selected_model["id"]
                                and request.get("reasoning", {}).get("effort") == "low"
                                for request in requests), requests

    def command_cases():
        # Includes an active subagent-mode role: subagent:false must still keep
        # the command in this session, not create a child or select agent defaults.
        for name in ["build", "plan", "review"]:
            sid = api("session", {"title": f"Commands {label} {name}", "agent": name,
                                  "model": selected_model})["data"]["id"]
            for command in sorted(expected_commands):
                for arguments in ['src/fixture.ts "two words" --scope=тест', ""]:
                    template = file_text(layer["files"][f"commands/{command}.md"]).strip()
                    assert "$ARGUMENTS" in template
                    expanded = template.replace("$ARGUMENTS", arguments)
                    start = len(LayerResponses.requests)
                    api(f"session/{sid}/command", {"name": command, "text": arguments})
                    wait_idle(sid)
                    prompts = [message for message in messages(sid) if message["type"] == "user"]
                    assert prompts[-1]["text"] == expanded, (label, name, command, prompts[-1])
                    assert any(expanded in text for request in LayerResponses.requests[start:]
                               for text in text_values(request)), (label, name, command, "wire prompt")
                    assert_wire_identity(LayerResponses.requests[start:])
                    assert_identity(sid, name)
                    assert children(sid) == [], (label, name, command, "unintended child")
        print(f"PASS: {label}: all {len(expected_commands)} commands × Build/Plan/Review × exact/empty arguments; agent/model/variant retained, no child")

    def corporate_inheritance():
        evidence = work / "evidence.txt"
        evidence.write_text("CORPORATE_NATIVE_READ_EVIDENCE\n")
        for name in ["review", "research"]:
            paths = [personal / "review-analysis.md", personal / "review-system.md"] if name == "review" else [evidence]
            sid = api("session", {"title": f"Native corporate {name}", "agent": "build",
                                  "model": selected_model})["data"]["id"]
            marker = f"CORPORATE_INHERITANCE_{name}"
            LayerResponses.delegation = {"marker": marker, "agent": name,
                                         "reads": list(paths), "launched": False}
            start = len(LayerResponses.requests)
            try:
                api(f"session/{sid}/prompt", {"text": marker})
                # Native 2.4 children report to/resume the parent. Wait for the
                # whole execution tree before arming another scripted request.
                wait_idle(sid)
                spawned = children(sid)
                assert len(spawned) == 1, spawned
                child_id = spawned[0]["id"]
                wait_idle(child_id)
                wait_idle(sid)
                assert_identity(sid, "build")
                assert_identity(child_id, name)
                assert_wire_identity(LayerResponses.requests[start:])
                parent_tools = [part for message in messages(sid) for part in message.get("content", [])
                                if part.get("type") == "tool" and part.get("name") == "subagent"]
                assert len(parent_tools) == 1 and parent_tools[0]["state"]["status"] == "completed", parent_tools
                assert "model" not in parent_tools[0]["state"]["input"], parent_tools
                reads = [part for message in messages(child_id) for part in message.get("content", [])
                         if part.get("type") == "tool" and part.get("name") == "read"]
                assert [part["state"]["input"]["path"] for part in reads] == list(map(str, paths)), reads
                assert all(part["state"]["status"] == "completed" for part in reads), reads
                returned = "\n".join(text_values(reads))
                for path in paths:
                    assert path.read_text().strip().splitlines()[-1] in returned, (name, path, "missing actual read evidence")
                system = file_text(layer["files"][f"agents/{name}.md"]).strip()
                assert any(system in text for request in LayerResponses.requests[start:]
                           for text in text_values(request)), (name, "missing child system")
                assert children(child_id) == []
                assert not LayerResponses.delegation["reads"]
            finally:
                LayerResponses.delegation = None
        print("PASS: corporate: native review/research inherit parent provider/model/low variant without override; actual policy/evidence reads")

    expected_commands = set(layer["settings"]["commands"]) if enabled else set()
    expected_agents = set(layer["settings"]["agents"]) if enabled else set()
    todo = enabled and "plugins" in layer["settings"]
    expected_plugins = {"local.git-offline"} | ({"local.agent-todo"} if todo else set())
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
                    docs = {doc.get("path"): doc["info"] for doc in api("config")
                            if doc.get("type") == "document"}
                    agents = {agent["id"]: agent for agent in api("agent")["data"]}
                    commands = {command["name"]: command for command in api("command")["data"]}
                    plugins = {plugin["id"]: plugin for plugin in api("plugin")["data"]}
                    skills = {skill["id"]: skill for skill in api("skill")["data"]}
                    if (expected_commands <= commands.keys()
                            and expected_agents <= agents.keys()
                            and expected_plugins <= plugins.keys()
                            and (not enabled or "discussion-map" in skills)):
                        break
                except (urllib.error.URLError, TimeoutError):
                    pass
                assert time.monotonic() < deadline, (label, "registry readiness timed out")
                time.sleep(0.1)
            assert str(config / "opencode.jsonc") in docs
            assert (str(personal / "opencode.jsonc") in docs) == enabled
            assert {"build", "plan", "general", "explore"} <= agents.keys()
            assert {key for key in plugins if key.startswith("local.")} == expected_plugins
            assert all(plugins[key]["state"]["status"] == "active" for key in expected_plugins)
            shared = docs[str(config / "opencode.jsonc")]
            assert shared["permissions"] == common["permissions"]
            assert shared["policies"] == common["policies"]
            assert shared["providers"]["openai"]["settings"]["baseURL"] == mock_url
            if enabled:
                info = docs[str(personal / "opencode.jsonc")]
                assert info["instructions"] == layer["settings"]["instructions"], info["instructions"]
                for name, metadata in layer["settings"]["commands"].items():
                    # Native {file:...} interpolation trims surrounding whitespace.
                    expected = file_text(layer["files"][f"commands/{name}.md"]).strip()
                    assert info["commands"][name]["template"] == expected, name
                    assert info["commands"][name]["subagent"] is False
                    assert not {"model", "agent"} & info["commands"][name].keys()
                    assert commands[name]["description"] == metadata["description"]
                for name, metadata in layer["settings"]["agents"].items():
                    actual = agents[name]
                    if "system" in metadata:
                        assert actual["system"] == file_text(layer["files"][f"agents/{name}.md"]).strip(), name
                    assert actual["mode"] == metadata.get("mode", actual["mode"])
                    for permission in metadata.get("permissions", []):
                        resolved = dict(permission)
                        if resolved["resource"].startswith("~/"):
                            resolved["resource"] = str(home / resolved["resource"][2:])
                        assert resolved in actual["permissions"], (name, resolved, actual["permissions"])
                    if "model" not in metadata:
                        assert "model" not in info["agents"][name], name
                    else:
                        provider, model = metadata["model"].split("/", 1)
                        model_id, _, variant = model.partition("#")
                        expected_model = {"providerID": provider, "id": model_id}
                        if variant:
                            expected_model["variant"] = variant
                        assert actual["model"] == expected_model, (name, actual["model"])
                for name in ["review", "research"]:
                    assert all(any(rule["action"] == action and rule["effect"] == "deny"
                                   for rule in agents[name]["permissions"])
                               for action in ["edit", "subagent", "todowrite"])
                assert skills["discussion-map"]["autoinvoke"] is False
                assert skills["discussion-map"]["path"] == str(personal / "skills/discussion-map/SKILL.md")
            else:
                assert not set(layer["settings"]["commands"]) & commands.keys()
                assert not {"review", "research"} & agents.keys()
                assert "discussion-map" not in skills
            assert "decision-check" not in skills
            # Explicit model selection routes all six agents only to the local
            # mock without changing any generated role definitions or JSONC.
            roles = ["build", "plan", "general", "explore", "research", "review"] if enabled else ["build"]
            for name in roles:
                sid = api("session", {"title": f"Layer {label} {name}", "agent": name,
                                     "model": {"providerID": "openai", "id": "gpt-6.1-sol"}})["data"]["id"]
                start = len(LayerResponses.requests)
                api(f"session/{sid}/prompt", {"text": "Reply briefly with no tools."})
                api(f"experimental/session/{sid}/wait", {})
                requests = LayerResponses.requests[start:]
                assert requests, (label, name, "no local model request")
                assert any(base_instructions.strip() in text for request in requests for text in text_values(request)), (label, name, "base instructions missing")
                tools = {tool.get("name") for request in requests for tool in request.get("tools", [])}
                note_tools = {"agent_todo_read", "agent_todo_propose"}
                expected_todo = todo and name in {"build", "plan"}
                assert (note_tools <= tools) == expected_todo, (label, name, tools)
                assert (any("# Todo notes" in json.dumps(request) for request in requests)) == expected_todo
                if not expected_todo:
                    assert not note_tools & tools, (label, name, tools)
                if enabled:
                    instructions = file_text(layer["files"]["AGENTS-personal.md"]).strip()
                    assert any(instructions in text for request in requests for text in text_values(request)), (label, name, "personal instructions missing")
                    assert all(skills["discussion-map"]["description"] not in text
                               for request in requests for text in text_values(request)), (label, name, "manual skill advertised")
                else:
                    assert all("## Goals and Approach" not in text for request in requests for text in text_values(request))
                assert all("# Decision support" not in json.dumps(request) for request in requests)
            if enabled and label in {"home", "corporate"}:
                command_cases()
            if enabled and label == "corporate":
                corporate_inheritance()
            assert not (home / "agent-todo").exists(), "test created notes"
            print(f"PASS: {label}: native files/commands/roles/skills/plugins and mock context; unrelated CWD, no discovery links")
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


def main():
    binary = shutil.which(sys.argv[1] if len(sys.argv) > 1 else "opencode")
    if not binary:
        raise SystemExit("OpenCode binary unavailable")
    print(subprocess.check_output([binary, "--version"], text=True).strip())
    layers = evaluate(SOURCE / "config/personal-layers.nix", "f: f {}")
    disabled = evaluate(SOURCE / "config/personal-layers.nix", "f: f { todoEnabled = false; }")
    mock = ThreadingHTTPServer(("127.0.0.1", 0), LayerResponses)
    threading.Thread(target=mock.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix="personal-layers-runtime-", dir="/tmp/opencode") as tmp:
            for label, layer, enabled in [
                ("common-only", layers["home"], False),
                ("home", layers["home"], True),
                ("corporate", layers["corporate"], True),
                ("home-no-todo", disabled["home"], True),
                ("home-hm-layout", layers["home"], True),
            ]:
                run(binary, Path(tmp) / label, label, layer, enabled,
                    f"http://127.0.0.1:{mock.server_port}/v1")
    finally:
        mock.shutdown()
        mock.server_close()
    print("PASS: no real model/MCP/browser, note writes, live service mutation or activation; scripted tools do not prove policy reasoning")


if __name__ == "__main__":
    main()
