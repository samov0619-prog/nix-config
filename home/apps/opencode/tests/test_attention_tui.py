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
    with tempfile.TemporaryDirectory(
        prefix="attention-tui-", dir="/tmp/opencode"
    ) as temporary:
        root = Path(temporary)
        config = root / "config/opencode"
        config.mkdir(parents=True)
        (root / "state").mkdir()
        (root / "runtime").mkdir(mode=0o700)
        mock = ThreadingHTTPServer(("127.0.0.1", 0), MockResponses)
        threading.Thread(target=mock.serve_forever, daemon=True).start()
        settings = json.loads(
            subprocess.check_output(
                [
                    "nix",
                    "eval",
                    "--offline",
                    "--json",
                    "--file",
                    str(SOURCE / "config/v2-settings.nix"),
                    "--apply",
                    "f: f { lib = {}; }",
                ]
            )
        )
        settings["providers"]["openai"].update(
            package="@opencode/ai/providers/openai/responses",
            settings={
                "apiKey": "mock",
                "baseURL": f"http://127.0.0.1:{mock.server_port}/v1",
            },
        )
        settings["permissions"] = [
            {
                "action": "read",
                "resource": str(root / "agent-todo/*"),
                "effect": "allow",
            }
        ]
        (config / "opencode.json").write_text(json.dumps(settings))
        (config / "cli.json").write_text(
            json.dumps({"attention": {"sound": True}, "tabs": {"scope": "global"}})
        )
        todo_plugin = config / "plugins/agent-todo"
        generation = os.environ.get("OPENCODE_TEST_HM_GENERATION")
        todo_plugin.parent.mkdir(parents=True)
        if generation:
            todo_plugin.symlink_to(
                Path(generation) / "home-files/.config/opencode/plugins/agent-todo-v2",
                target_is_directory=True,
            )
        else:
            todo_plugin.mkdir()
            (todo_plugin / "index.ts").write_text(
                (SOURCE / "plugins/agent-todo.ts").read_text()
            )
            for source, target in [
                ("agent-todo-review.ts", "agent-todo-review.ts"),
                ("agent-todo-tui.tsx", "tui.tsx"),
            ]:
                (todo_plugin / target).write_text(
                    (SOURCE / "plugins" / source).read_text()
                )
        for name in ["quiet-urgency", "attention-probe"]:
            directory = config / "plugins" / name
            directory.mkdir(parents=True)
            urgency_package = os.environ.get("OPENCODE_TEST_QUIET_URGENCY_PLUGIN")
            if name == "quiet-urgency" and urgency_package:
                (directory / "tui.ts").symlink_to(Path(urgency_package) / "tui.ts")
            elif name == "quiet-urgency" and generation:
                (directory / "tui.ts").symlink_to(
                    Path(generation)
                    / "home-files/.config/opencode/plugins/quiet-urgency/tui.ts"
                )
            else:
                source = SOURCE / (
                    "tests/attention-probe.ts"
                    if name == "attention-probe"
                    else "plugins/quiet-urgency.ts"
                )
                (directory / "tui.ts").write_text(source.read_text())
                if name == "quiet-urgency":
                    for target, relative in [
                        ("session-attention.ts", "patches/session-attention.ts"),
                        ("silent-attention.py", "scripts/silent-attention.py"),
                    ]:
                        (directory / target).write_text((SOURCE / relative).read_text())
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(
                ("OPENCODE_", "OPENAI_", "ANTHROPIC_", "XDG_", "KITTY_")
            )
        }
        env.update(
            HOME=temporary,
            XDG_CONFIG_HOME=str(root / "config"),
            XDG_STATE_HOME=str(root / "state"),
            XDG_DATA_HOME=str(root / "data"),
            XDG_CACHE_HOME=str(root / "cache"),
            XDG_RUNTIME_DIR=str(root / "runtime"),
            OPENCODE_DISABLE_PROJECT_CONFIG="1",
            OPENCODE_DISABLE_MODELS_FETCH="1",
            OPENCODE_CONFIG_DIR=str(config),
            OPENCODE_PASSWORD="attention-fixture",
            TERM="xterm-256color",
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        clients = {}
        outputs = {"101": bytearray(), "202": bytearray()}
        with (root / "server.log").open("w+") as log:
            server = subprocess.Popen(
                [binary, "serve", "--hostname", "127.0.0.1", "--port", str(port)],
                cwd=root,
                env=env,
                stdout=log,
                stderr=log,
            )

            def api(path, data=None):
                request = urllib.request.Request(
                    url + "/api/" + path,
                    data=json.dumps(data).encode() if data is not None else None,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Basic "
                        + base64.b64encode(b"opencode:attention-fixture").decode(),
                    },
                )
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
                return json.loads((root / f"state/attention-{pane}.state").read_text())[
                    "route"
                ]

            def records(pane):
                path = root / f"state/attention-{pane}.jsonl"
                return (
                    [json.loads(line) for line in path.read_text().splitlines()]
                    if path.exists()
                    else []
                )

            def sounds(pane):
                return [
                    row["sound"] for row in records(pane) if row["type"] == "attention"
                ]

            def launch(pane, sid):
                master, slave = pty.openpty()
                fcntl.ioctl(
                    slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0)
                )

                def controlling_terminal():
                    os.setsid()
                    fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

                process = subprocess.Popen(
                    [binary, "--server", url, "--session", sid],
                    stdin=slave,
                    stdout=slave,
                    stderr=slave,
                    cwd=root,
                    env={**env, "KITTY_WINDOW_ID": pane},
                    preexec_fn=controlling_terminal,
                )
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
                event = (
                    "session.execution.failed"
                    if error
                    else "session.execution.succeeded"
                )
                wait(
                    lambda: all(
                        any(
                            row.get("event") == event and row.get("sessionID") == sid
                            for row in records(pane)
                        )
                        for pane in clients
                    ),
                    "Both clients must receive the event to exercise isolation",
                )
                # Let all handlers/native attention tasks and PTY output settle.
                until = time.monotonic() + 0.5
                while time.monotonic() < until:
                    drain()
                    time.sleep(0.02)

            def urgency(pane):
                return outputs[pane].count(b"\x1bP@kitty-cmd")

            try:
                wait(lambda: api("info"), "private server did not start", timeout=90)
                a = api(
                    "session",
                    {
                        "title": "Window A",
                        "permissions": [
                            {"action": "shell", "resource": "*", "effect": "ask"},
                        ],
                    },
                )["data"]["id"]
                b = api("session", {"title": "Window B"})["data"]["id"]
                launch("101", a)
                launch("202", b)
                wait(
                    lambda: (
                        route("101").get("sessionID") == a
                        and route("202").get("sessionID") == b
                    ),
                    "TUI probes did not attach",
                )
                prompt(a)
                assert sounds("101") == ["done"] and sounds("202") == [], (
                    sounds("101"),
                    sounds("202"),
                )
                assert urgency("101") > 0 and urgency("202") == 0, (
                    urgency("101"),
                    urgency("202"),
                )
                before_a = urgency("101")
                prompt(b)
                assert sounds("101") == ["done"] and sounds("202") == ["done"]
                assert urgency("101") == before_a and urgency("202") > 0
                print(
                    "PASS: two real TUI clients/global tabs receive both sessions' events; only the owning window requests native sound and Kitty urgency"
                )
                background = api("session", {"title": "Background A"})["data"]["id"]
                for target in [background, a]:
                    (root / "state/attention-101.route").write_text(target)
                    wait(
                        lambda: route("101").get("sessionID") == target,
                        "Did not select background tab and return",
                    )
                before_a = urgency("101")
                before_b = urgency("202")
                prompt(background)
                assert sounds("101") == ["done", "done"]
                assert sounds("202") == ["done"]
                assert urgency("101") > before_a and urgency("202") == before_b
                print("PASS: inactive internal tab notifies its owner, not the other global-tab client")
                before_b = urgency("202")
                permission = api(
                    f"session/{a}/permission",
                    {"action": "shell", "resources": ["attention-fixture"], "save": []},
                )["data"]
                assert permission["effect"] == "ask", permission
                wait(
                    lambda: (
                        sounds("101")[-1] == "permission"
                        and all(
                            any(
                                row.get("event") == "permission.asked"
                                and row.get("sessionID") == a
                                for row in records(pane)
                            )
                            for pane in clients
                        )
                    ),
                    "permission event did not reach both TUI clients",
                )
                assert sounds("202") == ["done"] and urgency("202") == before_b
                api(
                    f"session/{a}/permission/{permission['id']}/reply",
                    {"decision": "once"},
                )
                print(
                    "PASS: permission attention is also isolated, without changing the underlying permission decision flow"
                )
                outputs["101"].clear()

                def frame():
                    return "\n".join(
                        json.loads((root / "state/attention-101.state").read_text())[
                            "frame"
                        ]
                    )

                (root / "agent-todo").mkdir()
                MockResponses.next_tool = ("agent_todo_read", {})
                prompt(a)
                messages = api(f"session/{a}/message?limit=5")["data"]
                read_result = next(
                    part["state"]
                    for message in messages
                    for part in message.get("content", [])
                    if part.get("name") == "agent_todo_read"
                )
                assert read_result["status"] == "completed", read_result
                todo = json.loads(
                    "".join(
                        part["text"]
                        for part in read_result["content"]
                        if part["type"] == "text"
                    )
                )
                MockResponses.next_tool = (
                    "agent_todo_propose",
                    {
                        "base": todo["fingerprint"],
                        "content": "# Todo\n\n## Разобраться с /tmp/opencode\n<!-- todo:investigate-opencode-tmp -->\n\n- Цель:\n  Проверить временные файлы.\n",
                        "reason": "Сохранить задачу разобраться с /tmp/opencode.",
                        "message": "add temporary files note",
                    },
                )
                api(f"session/{a}/prompt", {"text": "Предложи заметку."})
                try:
                    wait(
                        lambda: api(f"session/{a}/form")["data"],
                        "Todo form not created",
                    )
                except AssertionError:
                    print(
                        "Todo pending permissions:",
                        api(f"session/{a}/permission"),
                        file=sys.stderr,
                    )
                    print(
                        "Todo recent messages:",
                        json.dumps(
                            api(f"session/{a}/message?limit=5"), ensure_ascii=False
                        )[-7000:],
                        file=sys.stderr,
                    )
                    raise
                form = api(f"session/{a}/form")["data"][0]
                wait(
                    lambda: b"this note only" in outputs["101"],
                    "Todo options absent in actual TUI",
                )
                wait(lambda: "this note only" in frame(), "Todo framebuffer not ready")
                assert "Questions" not in frame(), (
                    f"Native form visible behind todo dialog at 140x40:\n{frame()}"
                )
                assert frame().count("Type your own answer") == 1, frame()
                os.write(clients["101"][1], b"\x1b[C")
                wait(
                    lambda: "[Submit]" in frame() and "Reject" in frame(),
                    "Final todo decision not visible",
                )
                fcntl.ioctl(
                    clients["101"][1],
                    termios.TIOCSWINSZ,
                    struct.pack("HHHH", 48, 160, 0, 0),
                )
                wait(
                    lambda: (
                        len(
                            json.loads(
                                (root / "state/attention-101.state").read_text()
                            )["frame"]
                        )
                        == 48
                        and "Reject" in frame()
                    ),
                    "Wide dialog resize not rendered",
                )
                assert (
                    "Questions" not in frame()
                    and "Разобраться с /tmp/opencode" not in frame()
                ), frame()
                assert (
                    frame().count("Type your own answer") == 1
                    and frame().count("enter confirm") == 1
                ), frame()
                fcntl.ioctl(
                    clients["101"][1],
                    termios.TIOCSWINSZ,
                    struct.pack("HHHH", 40, 140, 0, 0),
                )
                api(
                    f"session/{a}/form/{form['id']}/reply",
                    {"answer": {form["fields"][-1]["key"]: "Reject"}},
                )
                api(f"experimental/session/{a}/wait", {})
                assert not (root / "agent-todo/todo.md").exists()
                assert not (root / "agent-todo/.git").exists()
                print(
                    "PASS: one visible todo dialog at 140x40 and 160x48; native Questions stays covered; declining writes nothing"
                )
                # Exercise real keyboard dismissal, not just API cancel/reply.
                MockResponses.next_tool = (
                    "agent_todo_propose",
                    {
                        "base": todo["fingerprint"],
                        "content": "# Todo\n\n## Разобраться с /tmp/opencode\n<!-- todo:investigate-opencode-tmp -->\n\n- Цель:\n  Проверить временные файлы.\n",
                        "reason": "Проверка отмены: Escape test.",
                        "message": "add temporary files note",
                    },
                )
                outputs["101"].clear()
                api(
                    f"session/{a}/prompt",
                    {"text": "Предложи ещё раз для проверки Esc."},
                )
                wait(
                    lambda: api(f"session/{a}/form")["data"],
                    "Second todo form not created",
                )
                wait(lambda: "this note only" in frame(), "Second form not visible")
                description = api(f"session/{a}/form")["data"][0]["fields"][0][
                    "description"
                ]
                assert "@@" not in description and "last:" not in description, (
                    description
                )
                os.write(clients["101"][1], b"\x1b")
                wait(
                    lambda: not api(f"session/{a}/form")["data"],
                    "Esc did not dismiss todo form",
                )
                api(f"experimental/session/{a}/wait", {})
                state = next(
                    part["state"]
                    for message in api(f"session/{a}/message?limit=5")["data"]
                    for part in message.get("content", [])
                    if part.get("name") == "agent_todo_propose"
                )
                assert state["status"] == "completed", state
                wait(
                    lambda: (
                        (
                            cached := json.loads(
                                (root / "state/attention-101.state").read_text()
                            )["todo"]
                        )
                        and all(tool["status"] == "completed" for tool in cached)
                    ),
                    "TUI still considers the dismissed todo tool running",
                )
                result = json.loads(
                    "".join(
                        part["text"]
                        for part in state["content"]
                        if part["type"] == "text"
                    )
                )
                assert result["status"] == "declined" and result["dismissed"] is True, (
                    result
                )
                assert not (root / "agent-todo/todo.md").exists()
                assert not (root / "agent-todo/.git").exists()
                prompt(a)
                print(
                    "PASS: real Escape completes todo as declined without writes; next prompt succeeds"
                )
                # The original overflow was not detectable through the form API:
                # verify actual rendered cells in a small real terminal, not just
                # text that appeared somewhere in accumulated ANSI output.
                master = clients["101"][1]
                fcntl.ioctl(
                    master, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0)
                )

                batch = {
                    "base": todo["fingerprint"],
                    "changes": {
                        "add": [
                            {
                                "id": f"batch-{i}",
                                "title": f"Task {i}",
                                "summary": f"Review task {i} before importing.",
                                "goal": f"Goal {i}.",
                                "returnWhen": "During configuration review.",
                                "notes": "Long path /"
                                + "путь" * 40
                                + " 👩🏽‍💻\n"
                                + "Long review line.\n" * 20
                                + "TAIL OF TASK ONE\n"
                                if i == 1
                                else "",
                            }
                            for i in range(3)
                        ]
                    },
                    "reason": "Проверить страницы пакетного импорта.",
                    "message": "import batch of todo notes",
                }
                for mode in [
                    "cancel",
                    "feedback",
                    "reject",
                    "route",
                    "replace",
                    "save",
                ]:
                    MockResponses.next_tool = ("agent_todo_propose", batch)
                    api(f"session/{a}/prompt", {"text": "Проверь пакетный импорт."})
                    wait(
                        lambda: api(f"session/{a}/form")["data"],
                        "Native multi-question form not created",
                    )
                    form = api(f"session/{a}/form")["data"][0]
                    fields = form["fields"]
                    assert len(fields) == 4, form
                    descriptor = json.loads(fields[-1]["description"].split("\n", 1)[1])
                    assert [note["id"] for note in descriptor["notes"]] == [
                        "batch-0",
                        "batch-1",
                        "batch-2",
                    ]
                    request_count = len(MockResponses.requests)

                    def page_visible(
                        index, fields=fields, form=form, request_count=request_count
                    ):
                        final = index == len(fields) - 1
                        visible = (
                            ["Reject", "Type your own answer"]
                            if final
                            else [f"[ ] {index + 1}. Task {index}", "this note only"]
                        )
                        visible += [
                            "tab",
                            "select" if final else "scroll",
                            "confirm",
                            "dismiss",
                        ]
                        wait(
                            lambda: all(text in frame() for text in visible),
                            f"80x24 todo {index} or controls clipped: {frame()}",
                        )
                        assert not (root / "agent-todo/todo.md").exists()
                        assert not (root / "agent-todo/.git").exists()
                        # Nested structured arguments stay out of the native
                        # generic-tool summary behind the form.
                        assert "changes=" not in frame()
                        assert "content=# Todo" not in frame()
                        assert (
                            "Questions" not in frame()
                            and frame().count("enter confirm") == 1
                        ), frame()
                        assert "<details>" not in frame() and "<summary>" not in frame()
                        assert (
                            "Proposal" not in frame()
                            and "Review 1/" not in frame()
                            and "Change 1/" not in frame()
                        )
                        assert api(f"session/{a}/form")["data"][0]["id"] == form["id"]
                        assert len(MockResponses.requests) == request_count

                    for index in range(len(fields) - 1):
                        page_visible(index)
                        if index == 1:
                            os.write(master, b"\x1b[D")  # Native left.
                            page_visible(0)
                            os.write(master, b"\t")  # Native Tab, forwards.
                            page_visible(1)
                            os.write(master, b"\x1b[Z")  # Native Shift+Tab.
                            page_visible(0)
                            os.write(master, b"\x1b[C")  # Native right.
                            page_visible(1)
                            os.write(master, b"\x1b[F")
                            wait(
                                lambda: "TAIL OF TASK ONE" in frame(),
                                "Long todo tail not scrollable",
                            )
                            os.write(master, b"\x1b[H")
                            wait(
                                lambda: "Review task 1 before importing." in frame(),
                                "Home did not return to note start",
                            )
                        if mode == "cancel" and index == 1:
                            os.write(master, b"\x1b")
                            break
                        if mode == "replace" and index == 1:
                            os.write(master, b"\x07")
                            wait(
                                lambda: not api(f"session/{a}/form")["data"],
                                "Dialog replacement did not cancel",
                            )
                            wait(
                                lambda: "Replacement dialog" in frame(),
                                "Replacement dialog was closed by todo cleanup",
                            )
                            os.write(master, b"\x1b")
                            break
                        if mode == "route" and index == 1:
                            (root / "state/attention-101.route").write_text("home")
                            wait(
                                lambda: (
                                    route("101")["type"] == "home"
                                    and not api(f"session/{a}/form")["data"]
                                ),
                                "Route change did not cancel review",
                            )
                            (root / "state/attention-101.route").write_text(a)
                            wait(
                                lambda: route("101").get("sessionID") == a,
                                "Did not return to session",
                            )
                            break
                        if mode == "feedback" and index in [0, 1]:
                            os.write(master, b"a")
                            wait(
                                lambda: "Feedback for this note only" in frame(),
                                "Scoped editor did not open",
                            )
                            os.write(master, f"Comment for task {index}".encode())
                            wait(
                                lambda index=index: (
                                    f"Comment for task {index}" in frame()
                                ),
                                "Feedback not typed",
                            )
                            os.write(master, b"\r")
                            wait(
                                lambda: "Comment saved for this note" in frame(),
                                "Feedback not retained",
                            )
                        os.write(master, b"\x1b[C")
                    if mode not in ["cancel", "route", "replace"]:
                        page_visible(len(fields) - 1)
                        os.write(master, b"\t")  # Final decision cycles to first todo.
                        page_visible(0)
                        if mode == "feedback":
                            os.write(master, b"a")
                            wait(
                                lambda: "Comment for task 0" in frame(),
                                "Wrong note feedback restored",
                            )
                            assert "Comment for task 1" not in frame()
                            os.write(master, b"\t")
                            page_visible(1)
                            os.write(master, b"a")
                            wait(
                                lambda: "Comment for task 1" in frame(),
                                "Second note feedback lost",
                            )
                            assert "Comment for task 0" not in frame()
                            os.write(master, b"\r")
                            wait(
                                lambda: "Comment saved for this note" in frame(),
                                "Editor did not close",
                            )
                            os.write(master, b"\x1b[D")
                            page_visible(0)
                        os.write(master, b"\x1b[D")  # First cycles to final decision.
                        page_visible(len(fields) - 1)
                        (root / ".gitconfig").write_text(
                            "[user]\n name = Todo Fixture\n email = todo@example.invalid\n"
                        )
                        if mode == "reject":
                            os.write(master, b"\x1b[B")
                            wait(lambda: "› Reject" in frame(), "Reject not selected")
                        assert not (root / "agent-todo/todo.md").exists()
                        assert not (root / "agent-todo/.git").exists()
                        os.write(master, b"\r")  # One final decision, no second screen.
                    api(f"experimental/session/{a}/wait", {})
                    if mode != "save":
                        assert not (root / "agent-todo/todo.md").exists()
                        assert not (root / "agent-todo/.git").exists()
                        if mode == "feedback":
                            messages = api(f"session/{a}/message?limit=5")["data"]
                            state = next(
                                part["state"]
                                for message in messages
                                for part in message.get("content", [])
                                if part.get("name") == "agent_todo_propose"
                            )
                            result = json.loads(
                                next(
                                    part["text"]
                                    for part in state["content"]
                                    if part["type"] == "text"
                                )
                            )
                            assert result["status"] == "revise", result
                            assert result["feedback"] == [
                                {
                                    "id": f"batch-{i}",
                                    "title": f"[ ] {i + 1}. Task {i}",
                                    "feedback": f"Comment for task {i}",
                                }
                                for i in [0, 1]
                            ], result
                            assert result["draft"]["changes"] == batch["changes"]
                    else:
                        saved = (root / "agent-todo/todo.md").read_text()
                        assert all(
                            f"## [ ] {i + 1}. Task {i}" in saved for i in range(3)
                        )
                        assert (
                            subprocess.check_output(
                                ["git", "rev-list", "--count", "HEAD"],
                                cwd=root / "agent-todo",
                                env=env,
                            ).strip()
                            == b"1"
                        )
                fcntl.ioctl(
                    master, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0)
                )
                print(
                    "PASS: real 80x24 one-note tabs, long-note scrolling, left/right/Tab/Shift+Tab, isolated feedback/drafts, Escape/Reject/route/replacement/reload cancellation and one Submit/commit"
                )
                child = api("session", {"parentID": a, "title": "Child A"})["data"][
                    "id"
                ]
                before_b = urgency("202")
                prompt(child)
                # Lifecycle records precede the asynchronous ancestry lookup used
                # by native attention. Wait for the notification, not just the event.
                wait(
                    lambda: sounds("101")[-1] == "subagent_done",
                    "Child completion attention not delivered",
                )
                assert sounds("101")[-1] == "subagent_done" and sounds("202") == [
                    "done"
                ], (sounds("101"), sounds("202"))
                assert urgency("202") == before_b
                print("PASS: child completion remains scoped to its own parent window")
                prompt(a, error=True)
                wait(
                    lambda: sounds("101")[-1] == "error",
                    "Error attention not delivered",
                )
                assert sounds("101")[-1] == "error" and sounds("202") == ["done"]
                (root / "state/attention-101.route").write_text("home")
                wait(
                    lambda: route("101")["type"] == "home",
                    "route did not change to home",
                )
                before_a = urgency("101")
                # Generate another lifecycle for A; old receipts are not enough.
                for pane in clients:
                    (root / f"state/attention-{pane}.jsonl").write_text("")
                prompt(a)
                assert sounds("101") == ["done"] and sounds("202") == []
                assert urgency("101") > before_a
                print(
                    "PASS: failed session is isolated; home navigation retains open background-tab ownership"
                )
                (root / "state/attention-202.route").write_text(a)
                wait(
                    lambda: route("202").get("sessionID") == a,
                    "Did not transfer session to the second client",
                )
                prompt(a)
                assert sounds("101") == ["done"] and sounds("202") == ["done"]
                (root / "state/attention-202.route").write_text(b)
                wait(
                    lambda: route("202").get("sessionID") == b,
                    "Did not make the transferred session a background tab",
                )
                prompt(a)
                assert sounds("101") == ["done"] and sounds("202") == ["done", "done"]
                print("PASS: last explicit selection transfers ownership, which survives switching away")
                # Reload disposes the test attention monkeypatch too, so run it
                # only after attention assertions; it must still cancel consent.
                (root / "state/attention-101.route").write_text(a)
                wait(
                    lambda: route("101").get("sessionID") == a,
                    "Did not return for reload test",
                )
                MockResponses.next_tool = ("agent_todo_read", {})
                prompt(a)
                messages = api(f"session/{a}/message?limit=5")["data"]
                state = next(
                    part["state"]
                    for message in messages
                    for part in message.get("content", [])
                    if part.get("name") == "agent_todo_read"
                )
                current = json.loads(
                    next(
                        part["text"]
                        for part in state["content"]
                        if part["type"] == "text"
                    )
                )
                extra = {
                    **batch,
                    "base": current["fingerprint"],
                    "changes": {
                        "add": [
                            {
                                **batch["changes"]["add"][0],
                                "id": "reload-task",
                                "title": "Reload task",
                            }
                        ]
                    },
                }
                original = (root / "agent-todo/todo.md").read_text()
                MockResponses.next_tool = ("agent_todo_propose", extra)
                api(f"session/{a}/prompt", {"text": "Проверь отмену при reload."})
                wait(
                    lambda: (
                        "[ ] 4. Reload task" in frame() and "this note only" in frame()
                    ),
                    "Reload review did not open",
                )
                pending_id = api(f"session/{a}/form")["data"][0]["id"]
                process, previous_master = clients["101"]
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                os.close(previous_master)
                launch("101", a)
                master = clients["101"][1]
                wait(
                    lambda: (
                        json.loads(
                            (root / "state/attention-101.state").read_text()
                        ).get("pid")
                        == clients["101"][0].pid
                    ),
                    "New TUI probe did not connect",
                )
                wait(
                    lambda: (
                        "[ ] 4. Reload task" in frame() and "this note only" in frame()
                    ),
                    "Pending review did not recover after disconnect",
                )
                assert api(f"session/{a}/form")["data"][0]["id"] == pending_id
                assert (root / "agent-todo/todo.md").read_text() == original
                os.write(master, b"\x19")
                wait(
                    lambda: not api(f"session/{a}/form")["data"],
                    "Reload did not cancel form",
                )
                wait(
                    lambda: "Configuration reloaded" in frame(),
                    "Reload did not complete",
                )
                api(f"experimental/session/{a}/wait", {})
                assert (root / "agent-todo/todo.md").read_text() == original
                assert "this note only" not in frame()
                print(
                    "PASS: abrupt TUI disconnect never saves; reconnect restores pending review; reload cancels without writing or reopening dismissed consent"
                )
            except Exception:
                drain()
                for pane, output in outputs.items():
                    Path(f"/tmp/opencode/attention-tui-{pane}-failure.log").write_bytes(
                        output
                    )
                print(
                    log_path.read_text()[-2000:]
                    if (log_path := root / "server.log").exists()
                    else "",
                    file=sys.stderr,
                )
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
