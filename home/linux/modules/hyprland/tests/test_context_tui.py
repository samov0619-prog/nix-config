"""Isolated PTY smoke tests: real app APIs, no compositor or user storage.

Run: python3 home/linux/modules/hyprland/tests/test_context_tui.py
"""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
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
            "HOME": "home", "XDG_RUNTIME_DIR": "runtime", "XDG_CONFIG_HOME": "config",
            "XDG_DATA_HOME": "data", "XDG_STATE_HOME": "state", "XDG_CACHE_HOME": "cache",
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
            command, stdin=slave, stdout=slave, stderr=slave, cwd=self.root,
            env=self.env, preexec_fn=controlling_terminal,
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
        self.fail(f"No matching app context (exit={self.process.poll()}); PTY tail: {self.output[-1500:]!r}")

    @unittest.skipUnless(shutil.which("yazi"), "requires Yazi")
    def test_yazi_directory_and_tab_switch(self):
        config = self.root / "config/yazi"
        config.mkdir()
        (config / "init.lua").write_text(
            (MODULE / "yazi-context.lua").read_text().replace("@publisher@", str(MODULE / "app-context.lua"))
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

    @unittest.skipUnless(shutil.which("opencode"), "requires OpenCode")
    def test_opencode_real_tui_plugin(self):
        config = self.root / "config/opencode"
        config.mkdir()
        self.env["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
        self.env["OPENCODE_DISABLE_DEFAULT_PLUGINS"] = "1"
        (config / "opencode.json").write_text(json.dumps({"$schema": "https://opencode.ai/config.json"}))
        (config / "tui.json").write_text(json.dumps({
            "plugin": [str(ROOT / "home/apps/opencode/workspace-context.ts")],
        }))
        self.launch(["opencode"])
        record = self.wait_record(lambda r: r["app"] == "opencode", timeout=30)
        self.assertEqual(record["pane"], "42")
        self.assertEqual(record["cwd"], str(self.root))
        self.assertEqual(record["title"], "")

    @unittest.skipUnless(shutil.which("nvim"), "requires Neovim")
    def test_nvim_real_tui_local_directories(self):
        plugin = self.root / "nvim-context.lua"
        plugin.write_text((MODULE / "nvim-context.lua").read_text().replace(
            "@publisher@", str(MODULE / "app-context.lua")))
        local = self.root / "window-local"
        local.mkdir()
        self.launch(["nvim", "-u", "NONE", "-i", "NONE", "--cmd", f"lua dofile('{plugin}')"])
        self.wait_record(lambda r: r["app"] == "nvim" and r["cwd"] == str(self.root))
        os.write(self.master, f":lcd {local}\r".encode())
        self.wait_record(lambda r: r["cwd"] == str(local))
        os.write(self.master, b":tabnew\r:tcd /tmp\r")
        self.wait_record(lambda r: r["cwd"] == "/tmp")
        os.write(self.master, b":tabprevious\r")
        self.wait_record(lambda r: r["cwd"] == str(local))


if __name__ == "__main__":
    unittest.main()
