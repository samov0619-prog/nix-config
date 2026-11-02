"""Isolated PTY smoke tests: real app APIs, no compositor or user storage.

Run: python3 home/linux/modules/hyprland/tests/test_context_tui.py
"""

import fcntl
from contextlib import closing
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import sqlite3
import struct
import subprocess
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[5]
MODULE = ROOT / "home/linux/modules/hyprland"


class ContextTui(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hypr-context-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith(("OPENCODE_", "YAZI_")):
                self.env.pop(key)
        for key, directory in {
            "HOME": "home",
            "XDG_RUNTIME_DIR": "runtime",
            "XDG_CONFIG_HOME": "config",
            "XDG_DATA_HOME": "data",
            "XDG_STATE_HOME": "state",
            "XDG_CACHE_HOME": "cache",
        }.items():
            path = self.root / directory
            path.mkdir(mode=0o700)
            self.env[key] = str(path)
        self.env.update(TERM="xterm-256color", KITTY_WINDOW_ID="42")
        self.output = bytearray()

    def launch(self, command):
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))

        def controlling_terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        self.process = subprocess.Popen(
            command,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=self.root,
            env=self.env,
            preexec_fn=controlling_terminal,
        )
        os.close(slave)
        self.addCleanup(self.stop)

    def stop(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=3)
        os.close(self.master)

    def wait_record(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if select.select([self.master], [], [], 0.05)[0]:
                try:
                    self.output.extend(os.read(self.master, 65536))
                except OSError:
                    break
            for path in (self.root / "runtime/hypr-spaces/apps").glob("*.json"):
                try:
                    record = json.loads(path.read_text())
                    if predicate(record):
                        return record
                except (OSError, ValueError):
                    pass
            if self.process.poll() is not None:
                break
        Path("/tmp/opencode/v2-pty-failure.log").write_bytes(self.output)
        selection = self.root / "model-selection.json"
        self.fail(
            f"No matching app context (exit={self.process.poll()}, model={selection.read_text() if selection.exists() else 'not loaded'}); PTY output: /tmp/opencode/v2-pty-failure.log"
        )

    @unittest.skipUnless(shutil.which("yazi"), "requires Yazi")
    def test_yazi_directory_and_tab_switch(self):
        config = self.root / "config/yazi"
        config.mkdir()
        (config / "init.lua").write_text(
            (MODULE / "yazi-context.lua")
            .read_text()
            .replace("@publisher@", str(MODULE / "app-context.lua"))
        )
        initial = self.root / "files"
        child = initial / "child"
        child.mkdir(parents=True)
        self.env["YAZI_CONFIG_HOME"] = str(config)
        self.launch(["yazi", str(initial)])
        self.wait_record(lambda r: r["app"] == "yazi" and r["cwd"] == str(initial))
        os.write(self.master, b"tt")
        time.sleep(0.2)
        os.write(self.master, b"l")
        self.wait_record(lambda r: r["cwd"] == str(child))
        os.write(self.master, b"1")
        self.wait_record(lambda r: r["cwd"] == str(initial))
        os.write(self.master, b"2")
        self.wait_record(lambda r: r["cwd"] == str(child))

    @unittest.skipUnless(
        os.environ.get("OPENCODE_TEST_BINARY") or shutil.which("opencode"),
        "requires OpenCode",
    )
    def test_opencode_real_tui_plugin(self):
        config = self.root / "config/opencode"
        config.mkdir()
        self.env["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
        self.env["OPENCODE_DISABLE_MODELS_FETCH"] = "1"
        (config / "cli.json").write_text(json.dumps({"attention": {"sound": False}}))
        source = ROOT / "home/apps/opencode"
        settings = json.loads(
            subprocess.check_output(
                [
                    "nix",
                    "eval",
                    "--json",
                    "--file",
                    str(source / "config/v2-settings.nix"),
                    "--apply",
                    "f: f { lib = {}; }",
                ]
            )
        )
        settings["providers"]["openai"]["settings"] = {
            "apiKey": "isolated-no-inference"
        }
        (config / "opencode.json").write_text(json.dumps(settings))
        for name, filename in [
            ("workspace-context", "workspace-context.ts"),
            ("model-routing", "model-routing/tui.ts"),
            ("quiet-urgency", "quiet-urgency.ts"),
        ]:
            plugin = config / "plugins" / name
            plugin.mkdir(parents=True)
            (plugin / "tui.ts").write_text((source / "plugins" / filename).read_text())
            if name == "quiet-urgency":
                for part, relative in [
                    ("session-attention.ts", "patches/session-attention.ts"),
                    ("silent-attention.py", "scripts/silent-attention.py"),
                ]:
                    (plugin / part).write_text((source / relative).read_text())
        for filename in ["model-routing.ts", "routing-models.json"]:
            (config / "plugins/model-routing" / filename).write_text(
                (source / "plugins/model-routing" / filename).read_text()
            )
        generation = os.environ.get("OPENCODE_TEST_HM_GENERATION")
        if generation:
            # Exercise Home Manager's actual symlink/store layout, not copies
            # that hide relative-import failures in separately stored files.
            plugin = config / "plugins/model-routing"
            for file in plugin.iterdir():
                file.unlink()
            plugin.rmdir()
            plugin.symlink_to(
                Path(generation) / "home-files/.config/opencode/plugins/model-routing",
                target_is_directory=True,
            )
            resolved = (plugin / "tui.ts").resolve(strict=True).parent
            for filename in ["model-routing.ts", "routing-models.json"]:
                self.assertTrue(
                    (resolved / filename).is_file(),
                    f"Missing import beside real tui.ts: {filename}",
                )
            urgency = config / "plugins/quiet-urgency/tui.ts"
            urgency.unlink()
            urgency.symlink_to(
                Path(generation)
                / "home-files/.config/opencode/plugins/quiet-urgency/tui.ts"
            )
            for filename in ["session-attention.ts", "silent-attention.py"]:
                self.assertTrue(
                    (urgency.resolve(strict=True).parent / filename).is_file()
                )
        urgency_package = os.environ.get("OPENCODE_TEST_QUIET_URGENCY_PLUGIN")
        if urgency_package:
            urgency = config / "plugins/quiet-urgency/tui.ts"
            urgency.unlink()
            urgency.symlink_to(Path(urgency_package) / "tui.ts")
            for filename in ["session-attention.ts", "silent-attention.py"]:
                self.assertTrue(
                    (urgency.resolve(strict=True).parent / filename).is_file()
                )
        selection_file = self.root / "model-selection.json"
        probe = config / "plugins/model-probe"
        probe.mkdir()
        (probe / "tui.tsx").write_text(
            'import { Plugin } from "@opencode/plugin/tui";\n'
            'import { writeFileSync, renameSync } from "node:fs";\n'
            'export default Plugin.define({ id: "test.model-probe", setup(context) {\n'
            f"const file = {json.dumps(str(selection_file))};\n"
            "let frame = [];\n"
            "const capture = buffer => { frame = buffer.getSpanLines()\n"
            ".map(line => line.spans.map(span => span.text).join('')); };\n"
            "context.renderer.addPostProcessFn(capture);\n"
            "const timer = setInterval(() => {\n"
            "writeFileSync(file + '.tmp', JSON.stringify({model: context.ui.model.current(),\n"
            "frame}));\n"
            "renameSync(file + '.tmp', file);\n"
            "}, 50); return () => { clearInterval(timer); context.renderer.removePostProcessFn(capture); }; }});\n"
        )

        def frame():
            return "\n".join(json.loads(selection_file.read_text())["frame"])

        voice = config / "plugins/voice"
        voice.mkdir()
        for filename in ["tui.ts", "voice-runtime.ts"]:
            (voice / filename).write_text(
                (source / "macos/opencode/plugins/voice" / filename).read_text()
            )
        self.launch(
            [
                os.environ.get("OPENCODE_TEST_BINARY", "opencode"),
                "--standalone",
                "--log-level",
                "debug",
                "--print-logs",
            ]
        )
        record = self.wait_record(lambda r: r["app"] == "opencode", timeout=60)
        self.assertEqual(record["pane"], "42")
        self.assertEqual(record["cwd"], str(self.root))
        self.assertEqual(record["title"], "")
        # The Mac recorder must load through the real V2 API, but never open a
        # microphone on this Linux runner. Ctrl+R reaches its platform guard.
        os.write(self.master, b"\x12")
        deadline = time.monotonic() + 5
        while b"macOS AVFoundation" not in self.output and time.monotonic() < deadline:
            if select.select([self.master], [], [], 0.1)[0]:
                self.output.extend(os.read(self.master, 65536))
        self.assertIn(b"macOS AVFoundation", self.output)
        # Also cover plain defaults, before any free/paid policy is enabled.
        self.wait_record(
            lambda _: (
                json.loads(selection_file.read_text()).get("model", {}).get("variant")
                == "high"
            )
        )
        os.write(self.master, b"\x1b[Z")
        self.wait_record(
            lambda _: any(
                "Plan" in line and "xhigh" in line.lower()
                for line in frame().splitlines()
            )
        )
        self.assertNotIn("(plan)", frame())
        os.write(self.master, b"\x1b[Z")
        self.wait_record(
            lambda _: (
                json.loads(selection_file.read_text()).get("model", {}).get("variant")
                == "high"
            )
        )
        os.write(self.master, b"/switch-free")
        time.sleep(0.3)
        os.write(self.master, b"\r")
        database = self.root / "data/opencode/opencode.db"

        def routing_ready(mode):
            with closing(sqlite3.connect(f"file:{database}?mode=ro", uri=True)) as db:
                rows = db.execute("SELECT metadata FROM session_v2").fetchall()
                return (
                    len(rows) == 1
                    and json.loads(rows[0][0])
                    .get("local.model-routing", {})
                    .get("mode")
                    == mode
                )

        self.wait_record(lambda _: routing_ready("free"))
        self.wait_record(
            lambda _: (
                json.loads(selection_file.read_text()).get("model", {}).get("modelID")
                == "big-pickle"
            )
        )
        # DB creation precedes TUI navigation/model sync. Wait until the command
        # has finished and painted its toast before typing into the new prompt.
        self.wait_record(lambda _: b"Model routing" in self.output)
        # Empty native V2 sessions have no title until explicitly renamed.
        title = "Проверка V2 — рабочая сессия"
        os.write(self.master, f"/rename {title}".encode())
        time.sleep(0.3)
        os.write(self.master, b"\r")
        self.wait_record(lambda r: r["title"] == title)
        os.write(self.master, b"/switch-paid")
        time.sleep(0.3)
        os.write(self.master, b"\r")
        self.wait_record(lambda _: routing_ready("paid"))
        self.wait_record(
            lambda _: (
                json.loads(selection_file.read_text()).get("model", {}).get("modelID")
                == "gpt-6.1-sol"
            )
        )
        self.wait_record(
            lambda _: (
                json.loads(selection_file.read_text())["model"].get("variant") == "high"
            )
        )
        # Real Build/Plan switching must expose effort separately from model name.
        os.write(self.master, b"\x1b[Z")
        self.wait_record(
            lambda _: (
                json.loads(selection_file.read_text())["model"].get("variant")
                == "xhigh"
            )
        )
        self.wait_record(
            lambda _: any(
                "Plan" in line and "xhigh" in line.lower()
                for line in frame().splitlines()
            )
        )
        self.assertNotIn("(plan)", frame())
        os.write(self.master, b"\x1b[Z")
        self.wait_record(
            lambda _: (
                json.loads(selection_file.read_text())["model"].get("variant") == "high"
            )
        )
        for mode in ["paid", "free"]:
            if mode == "free":
                os.write(self.master, b"/switch-free")
                self.wait_record(lambda _: "Switch to free models" in frame())
                os.write(self.master, b"\r")
                self.wait_record(lambda _: routing_ready("free"))
                self.wait_record(
                    lambda _: (
                        json.loads(selection_file.read_text())
                        .get("model", {})
                        .get("modelID")
                        == "big-pickle"
                    )
                )
            # Real picker, not a model-probe command: selection must clear the
            # root policy and the public TUI model must reflect the real model.
            os.write(self.master, b"/models")
            self.wait_record(
                lambda _: any(
                    "/models" in line and "Switch model" in line
                    for line in frame().splitlines()
                )
            )
            os.write(self.master, b"\r")
            self.wait_record(lambda _: "Select model" in frame())
            for alias in ["(plan)", "(summary)", "(explore)"]:
                self.assertNotIn(alias, frame())
            time.sleep(0.3)
            os.write(self.master, b"GPT-6 Luna")
            self.wait_record(lambda _: frame().count("GPT-6 Luna") >= 2)
            os.write(self.master, b"\r")
            self.wait_record(lambda _: routing_ready(None))
            self.wait_record(
                lambda _: (
                    json.loads(selection_file.read_text())
                    .get("model", {})
                    .get("modelID")
                    == "gpt-6-luna"
                )
            )
            # The model can open its native variant picker. Dismiss it without
            # sending a prompt before testing the next slash command.
            time.sleep(0.3)
            os.write(self.master, b"\x1b")
            self.wait_record(
                lambda _: (
                    "Select variant" not in frame() and "Select model" not in frame()
                )
            )
            # Escape has a native ambiguity timeout; do not fuse the following
            # slash command into an escape sequence or submit before its menu paints.
            time.sleep(0.7)
        os.write(self.master, b"/switch-paid")
        self.wait_record(lambda _: "Switch to paid models" in frame())
        os.write(self.master, b"\r")
        self.wait_record(lambda _: routing_ready("paid"))
        with closing(sqlite3.connect(f"file:{database}?mode=ro", uri=True)) as db:
            rows = db.execute("SELECT metadata FROM session_v2").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(
                json.loads(rows[0][0])["local.model-routing"]["mode"], "paid"
            )
            self.assertEqual(
                db.execute("SELECT count(*) FROM session_message").fetchone()[0], 0
            )

    @unittest.skipUnless(shutil.which("nvim"), "requires Neovim")
    def test_nvim_real_tui_local_directories(self):
        plugin = self.root / "nvim-context.lua"
        plugin.write_text(
            (MODULE / "nvim-context.lua")
            .read_text()
            .replace("@publisher@", str(MODULE / "app-context.lua"))
        )
        local = self.root / "window-local"
        local.mkdir()
        self.launch(
            ["nvim", "-u", "NONE", "-i", "NONE", "--cmd", f"lua dofile('{plugin}')"]
        )
        self.wait_record(lambda r: r["app"] == "nvim" and r["cwd"] == str(self.root))
        os.write(self.master, f":lcd {local}\r".encode())
        self.wait_record(lambda r: r["cwd"] == str(local))
        os.write(self.master, b":tabnew\r:tcd /tmp\r")
        self.wait_record(lambda r: r["cwd"] == "/tmp")
        os.write(self.master, b":tabprevious\r")
        self.wait_record(lambda r: r["cwd"] == str(local))


if __name__ == "__main__":
    unittest.main()
