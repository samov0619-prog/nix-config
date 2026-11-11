"""Unit/IPC/subprocess tests with a fake nvidia-smi; no GPU or real Waybar."""

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("gpu_status", HERE / "gpu-status.py")
gpu = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gpu)


class GpuTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gpu-", dir="/tmp/opencode")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_default_window_and_idle_render(self):
        self.assertEqual(gpu.WINDOW, 60)
        self.assertEqual(gpu.INTERVAL, 2)
        result = gpu.render(None, None)
        self.assertEqual(result["text"], "GPU")
        self.assertEqual(result["class"], "idle")
        self.assertNotIn("--", result["text"])

    def test_metrics_are_hidden_when_monitoring_is_off(self):
        sample = gpu.parse_metrics("12, 512, 8192\n")
        sample.update(time="12:34:56", at=100)
        idle = gpu.render(sample, None)
        self.assertEqual(idle["text"], "GPU")
        self.assertEqual(idle["class"], "idle")
        self.assertNotIn("VRAM", idle["tooltip"])
        self.assertNotIn("12:34:56", idle["tooltip"])
        with patch.object(gpu, "clock", return_value=100):
            active = gpu.render(sample, 160)
            failure = gpu.render(sample, 160, error=True)
        self.assertEqual(active["class"], "active")
        self.assertEqual(active["text"], "GPU:12%|0.5GiB")
        self.assertIn("8.0 GiB", active["tooltip"])
        self.assertIn("12:34:56", active["tooltip"])
        self.assertEqual(failure["class"], "unavailable")
        self.assertIn("прежние показания не текущие", failure["tooltip"])

    def test_invalid_or_unsupported_metrics_are_not_zero(self):
        for value in ("N/A, 512, 8192", "101, 1, 10", "-1, 1, 10", "0, -1, 10",
                      "0, 11, 10", "0, 0, 0", "nan, 1, 10", "0, inf, inf",
                      "1, 2", "1, 2, 3\n4, 5, 6"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                gpu.parse_metrics(value)

    def test_deadline_and_lock_contention_never_launch_a_query(self):
        with patch.object(gpu, "clock", return_value=100), \
                patch.object(gpu.subprocess, "run") as run:
            self.assertIsNone(gpu.collect(self.root, 100, "must-not-run"))
            with (self.root / "sample.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertIsNone(gpu.collect(self.root, 200, "must-not-run"))
            run.assert_not_called()

    def test_shared_cache_and_bounded_single_pci_query(self):
        (self.root / "sample.json").write_text("broken cache")
        result = subprocess.CompletedProcess([], 0, stdout="12, 512, 8192\n")
        with patch.object(gpu, "clock", return_value=100), \
                patch.object(gpu.subprocess, "run", return_value=result) as run:
            first = gpu.collect(self.root, 100.25, "fake-smi")
            second = gpu.collect(self.root, 101, "fake-smi")
            self.assertEqual(first, second)
            run.assert_called_once()
            args, kwargs = run.call_args
            self.assertEqual(args[0][0], "fake-smi")
            self.assertIn("--id=0000:02:00.0", args[0])
            self.assertEqual(kwargs["timeout"], 0.25)
            self.assertNotIn("shell", kwargs)

    def test_suspend_expiry_discards_late_result(self):
        result = subprocess.CompletedProcess([], 0, stdout="12, 512, 8192\n")
        with patch.object(gpu, "clock", side_effect=[100, 100, 200]), \
                patch.object(gpu.subprocess, "run", return_value=result):
            self.assertIsNone(gpu.collect(self.root, 160, "fake-smi"))
        self.assertFalse((self.root / "sample.json").exists())

    def test_failed_queries_share_the_backoff_without_fabricating_metrics(self):
        failure = subprocess.CalledProcessError(1, "fake-smi")
        with patch.object(gpu, "clock", return_value=100), \
                patch.object(gpu.subprocess, "run", side_effect=failure) as run:
            with self.assertRaises(subprocess.SubprocessError):
                gpu.collect(self.root, 160, "fake-smi")
            with self.assertRaises(subprocess.SubprocessError):
                gpu.collect(self.root, 160, "fake-smi")
            run.assert_called_once()
        self.assertEqual(json.loads((self.root / "sample.json").read_text()),
                         {"at": 100, "error": True})

    def test_expiry_during_cache_read_never_starts_a_query(self):
        with patch.object(gpu, "clock", side_effect=[100, 200]), \
                patch.object(gpu.subprocess, "run") as run:
            self.assertIsNone(gpu.collect(self.root, 160, "must-not-run"))
            run.assert_not_called()

    def test_boot_clock_includes_suspend(self):
        with patch.object(gpu.time, "clock_gettime", return_value=123) as get:
            self.assertEqual(gpu.clock(), 123)
        get.assert_called_once_with(time.CLOCK_BOOTTIME)

    def test_click_timestamp_does_not_extend_a_queued_or_expired_request(self):
        self.assertEqual(gpu.request_deadline(b"activate:100", 102), 160)
        self.assertIsNone(gpu.request_deadline(b"activate:100", 200))
        for message in (b"activate", b"activate:nan", b"activate:inf", b"other:100"):
            self.assertIsNone(gpu.request_deadline(message, 100))
        self.assertEqual(gpu.request_deadline(b"activate:1000", 100), 160)

    def test_private_runtime_and_stale_socket_cleanup(self):
        with patch.dict(os.environ, XDG_RUNTIME_DIR=str(self.root), WAYLAND_DISPLAY="test"):
            directory = gpu.runtime_directory()
            stale = directory / "999999.sock"
            with gpu.socket.socket(gpu.socket.AF_UNIX, gpu.socket.SOCK_DGRAM) as sock:
                sock.bind(str(stale))
            gpu.activate(directory)
            self.assertFalse(stale.exists())
            directory.chmod(0o755)
            with self.assertRaises(ValueError):
                gpu.runtime_directory()

    def test_lenovo_configuration_and_theme(self):
        linux = HERE.parents[1]
        source = (linux / "laptop/waybar-config.jsonc").read_text()
        # The raw file's only JSON extensions are line comments/trailing commas.
        import re
        config = json.loads(re.sub(r",\s*([}\]])", r"\1", re.sub(r"//[^\n]*", "", source)))
        modules = config["modules-center"]
        self.assertEqual(modules[modules.index("custom/disk") + 1], "custom/gpu-manual")
        module = config["custom/gpu-manual"]
        self.assertFalse(module["exec-on-event"])
        self.assertNotIn("interval", module)
        self.assertTrue(module["on-click"].endswith(" --activate"))
        for host in ("laptop-old", "desktop"):
            other = (linux / host / "waybar-config.jsonc").read_text()
            self.assertIn("gp.sh", other)
            self.assertNotIn("gpu-manual", other)
        css = (linux / "modules/waybar/style.css").read_text()
        self.assertIn("#custom-gpu-manual:hover", css)
        self.assertIn("#power-profiles-daemon:hover", css)
        self.assertNotRegex(css, r"#power-profiles-daemon\.(performance|balanced|power-saver)")
        for mode in ("dark", "light"):
            theme = (linux / f"modules/waybar/style-{mode}.css").read_text()
            self.assertIn('@import url("./style.css")', theme)
            self.assertIn("#custom-gpu-manual,", theme)


class StreamTests(unittest.TestCase):
    def setUp(self):
        GpuTests.setUp(self)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "calls.jsonl"
        self.mode = self.root / "mode"
        self.mode.write_text("ok")
        fake = self.bin / "nvidia-smi"
        fake.write_text(f"#!{sys.executable}\n" + """
import json, os, pathlib, sys, time
with open(os.environ['TEST_LOG'], 'a') as log:
    log.write(json.dumps({'at': time.monotonic(), 'pid': os.getpid(), 'args': sys.argv[1:]}) + '\\n')
mode = pathlib.Path(os.environ['TEST_MODE']).read_text()
if mode == 'slow':
    time.sleep(10)
if mode == 'fail':
    sys.exit(1)
print('12, 512, 8192')
""")
        fake.chmod(0o755)
        self.runner = self.root / "runner.py"
        self.runner.write_text(f"""
import importlib.util
s = importlib.util.spec_from_file_location('gpu', {str(HERE / 'gpu-status.py')!r})
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
m.WINDOW = 0.6
m.INTERVAL = 0.12
m.QUERY_TIMEOUT = 0.15
m.main()
""")
        self.env = dict(os.environ, XDG_RUNTIME_DIR=str(self.root), WAYLAND_DISPLAY="test",
                        TEST_LOG=str(self.log), TEST_MODE=str(self.mode),
                        PATH=f"{self.bin}:{os.environ['PATH']}")
        self.buffers = {}

    def start(self):
        process = subprocess.Popen([sys.executable, "-B", str(self.runner)], env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop, process)
        self.buffers[process.pid] = b""
        self.assertEqual(self.event(process)["class"], "idle")
        return process

    def stop(self, process):
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=2)
        process.stdout.close()
        process.stderr.close()

    def event(self, process, timeout=3):
        end = time.monotonic() + timeout
        while b"\n" not in self.buffers[process.pid]:
            ready, _, _ = select.select([process.stdout], [], [], max(0, end - time.monotonic()))
            self.assertTrue(ready, "no JSON event before timeout")
            data = os.read(process.stdout.fileno(), 65536)
            if not data:
                self.fail(process.stderr.read().decode())
            self.buffers[process.pid] += data
        line, self.buffers[process.pid] = self.buffers[process.pid].split(b"\n", 1)
        return json.loads(line)

    def click(self):
        subprocess.run([sys.executable, "-B", str(self.runner), "--activate"],
                       env=self.env, check=True, timeout=2)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def until(self, process, state):
        for _ in range(100):
            event = self.event(process)
            if event["class"] == state:
                return event
        self.fail(f"no {state} event")

    def test_real_ipc_idle_click_expiry_and_restart(self):
        process = self.start()
        with patch.dict(os.environ, self.env):
            directory = gpu.runtime_directory()
        with gpu.socket.socket(gpu.socket.AF_UNIX, gpu.socket.SOCK_DGRAM) as client:
            stale = f"activate:{gpu.clock() - 1000}".encode()
            client.sendto(stale, str(directory / f"{process.pid}.sock"))
        time.sleep(0.16)
        self.assertEqual(self.calls(), [])
        self.click()
        self.assertEqual(self.until(process, "active")["text"], "GPU:12%|0.5GiB")
        self.assertEqual(self.until(process, "idle")["text"], "GPU")
        count = len(self.calls())
        self.assertGreater(count, 1)
        time.sleep(0.2)
        self.assertEqual(len(self.calls()), count)
        self.stop(process)
        restarted = self.start()
        time.sleep(0.16)
        self.assertEqual(len(self.calls()), count)
        self.assertIsNone(restarted.poll())

    def test_repeated_click_renews_one_window(self):
        process = self.start()
        first = time.monotonic()
        self.click()
        self.until(process, "active")
        time.sleep(0.3)
        renewed = time.monotonic()
        self.click()
        self.until(process, "idle")
        elapsed = time.monotonic()
        self.assertGreater(elapsed - first, 0.85)
        self.assertGreater(elapsed - renewed, 0.55)
        self.assertLess(elapsed - renewed, 1.2)

    def test_multi_output_shares_queries_and_click(self):
        first, second = self.start(), self.start()
        self.click()
        self.until(first, "idle")
        self.until(second, "idle")
        calls = self.calls()
        self.assertGreater(len(calls), 1)
        for previous, current in zip(calls, calls[1:]):
            self.assertGreaterEqual(current["at"] - previous["at"], 0.11)

    def test_multi_output_failures_share_backoff(self):
        self.mode.write_text("fail")
        first, second = self.start(), self.start()
        self.click()
        self.until(first, "idle")
        self.until(second, "idle")
        calls = self.calls()
        self.assertGreater(len(calls), 1)
        for previous, current in zip(calls, calls[1:]):
            self.assertGreaterEqual(current["at"] - previous["at"], 0.11)

    def test_errors_preserve_honestly_stale_data_and_still_stop(self):
        process = self.start()
        self.click()
        self.until(process, "active")
        self.mode.write_text("fail")
        error = self.until(process, "unavailable")
        self.assertEqual(error["text"], "GPU:12%|0.5GiB")
        self.assertIn("не текущие", error["tooltip"])
        self.assertEqual(self.until(process, "idle")["text"], "GPU")
        count = len(self.calls())
        time.sleep(0.2)
        self.assertEqual(len(self.calls()), count)

        # A new window must not resurrect the previous window's stale figures.
        self.click()
        self.assertEqual(self.until(process, "unavailable")["text"], "GPU")
        self.until(process, "idle")

    def test_timeout_reaps_fake_query_and_window_expires(self):
        self.mode.write_text("slow")
        process = self.start()
        self.click()
        self.until(process, "unavailable")
        # No successful sample means the expired button returns to plain GPU.
        self.until(process, "idle")
        for call in self.calls():
            with self.assertRaises(ProcessLookupError):
                os.kill(call["pid"], 0)
        count = len(self.calls())
        time.sleep(0.2)
        self.assertEqual(len(self.calls()), count)

    def test_termination_during_query_reaps_child_and_removes_socket(self):
        self.mode.write_text("slow")
        process = self.start()
        self.click()
        end = time.monotonic() + 2
        while not self.calls() and time.monotonic() < end:
            time.sleep(0.01)
        self.assertTrue(self.calls())
        self.stop(process)
        with self.assertRaises(ProcessLookupError):
            os.kill(self.calls()[0]["pid"], 0)
        self.assertEqual(list(self.root.glob("waybar-gpu-*/*.sock")), [])


if __name__ == "__main__":
    unittest.main()
