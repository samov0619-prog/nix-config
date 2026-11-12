"""Actual recording worker/toggle, isolated fake recorder; no PipeWire or display."""

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RecordingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dictation-worker-", dir="/tmp/opencode")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.state = self.root / "voice-dictate"
        self.env = {
            "PATH": str(self.bin),
            "HOME": str(self.root),
            "XDG_RUNTIME_DIR": str(self.root),
        }
        source = (ROOT / "default.nix").read_text()
        self.body = textwrap.dedent(source.split("    text = ''\n", 1)[1].split("\n    '';", 1)[0])
        self.body = self.body.replace("${whisperSmallQ51}", "/fixture/model.bin")
        self.body = self.body.replace("${gpuFlag}", "").replace("''${", "${")
        for name in ("cat", "rm", "mkdir", "tr", "sed", "flock"):
            (self.bin / name).symlink_to(shutil.which(name))
        self.command("pw-record", '''
            import os, signal, sys, time
            from pathlib import Path
            if os.environ.get("START_FAIL"):
                sys.exit(7)
            signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
            Path(sys.argv[-1]).write_bytes(b"synthetic audio")
            Path("recorder.ready").write_text(str(os.getpid()))
            while True:
                signal.pause()
        ''')
        self.command("sleep", '''
            import os, sys, time
            from pathlib import Path
            if sys.argv[1] == "2":
                Path("allowance.started").touch()
                deadline = time.monotonic() + 5
                while not Path("allowance.release").exists():
                    if time.monotonic() > deadline:
                        sys.exit(9)
                    time.sleep(0.005)
            else:
                time.sleep(0.005)
        ''')
        self.command("notify-send", '''
            import json, os, sys
            from pathlib import Path
            with Path("notices.jsonl").open("a") as log:
                log.write(json.dumps(sys.argv[1:]) + "\\n")
            if "--expire-time=0" in sys.argv and os.environ.get("NOTIFY_FAIL"):
                sys.exit(8)
        ''')
        self.command("notification-close", '''
            import json, sys
            from pathlib import Path
            with Path("closed.jsonl").open("a") as log:
                log.write(json.dumps(sys.argv[1:]) + "\\n")
        ''')
        self.command("whisper-cli", 'print("fixture transcript")')
        for name in ("wl-copy", "wtype"):
            self.command(name, 'import sys; sys.stdin.buffer.read()')

    def command(self, name, body):
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(body))
        path.chmod(0o700)

    def launch(self, *, worker=False):
        body = self.body
        if worker:
            # Keep the actual worker in the foreground to observe its result.
            body = body.replace("record_microphone >/dev/null 2>&1 &", "record_microphone")
        process = subprocess.Popen(
            [shutil.which("bash"), "-euo", "pipefail", "-c", body],
            cwd=self.root, env=self.env, start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        def cleanup():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)
        self.addCleanup(cleanup)
        return process

    def until(self, predicate):
        deadline = time.monotonic() + 4
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("Timed out waiting for isolated fixture state")
            time.sleep(0.01)

    def notices(self):
        path = self.root / "notices.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def start(self):
        worker = self.launch(worker=True)
        self.until(lambda: (self.root / "recorder.ready").exists())
        pid = int((self.root / "recorder.ready").read_text())
        return worker, pid

    def release(self):
        (self.root / "allowance.release").touch()

    def assert_closed(self, pid):
        calls = [json.loads(line) for line in (self.root / "closed.jsonl").read_text().splitlines()]
        self.assertTrue(calls)
        self.assertTrue(all(call == ["--app-name=Voice dictate", f"--category=voice-dictate.recording.{pid}"] for call in calls))

    def test_persistent_notice_then_normal_second_hotkey(self):
        worker, pid = self.start()
        self.release()
        self.until(lambda: len(self.notices()) == 1)
        notice = self.notices()[0]
        self.assertIn("--expire-time=0", notice)
        self.assertIn(f"--category=voice-dictate.recording.{pid}", notice)
        self.assertIsNone(worker.poll())
        stop = self.launch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assert_closed(pid)
        self.assertEqual(self.notices()[-1], ["Voice dictate", "Transcribed and copied to clipboard", "--expire-time=3000"])
        self.assertFalse((self.state / "recording.pid").exists())
        self.assertFalse((self.state / "recording.wav").exists())

    def test_stop_during_bluetooth_allowance_never_publishes_recording_notice(self):
        worker, pid = self.start()
        stop = self.launch()
        self.until(lambda: not (self.state / "recording.pid").exists())
        self.release()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assertFalse(any("--expire-time=0" in notice for notice in self.notices()))
        self.assert_closed(pid)

    def test_actual_detached_launch_keeps_worker_and_lock_lifecycle(self):
        start = self.launch()
        self.assertEqual(start.wait(timeout=4), 0)
        self.until(lambda: (self.root / "recorder.ready").exists())
        pid = int((self.root / "recorder.ready").read_text())
        self.assertEqual((self.state / "recording.pid").read_text(), f"{pid}\n")
        self.release()
        self.until(lambda: len(self.notices()) == 1)
        stop = self.launch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.until(lambda: len(self.notices()) == 2)
        self.assert_closed(pid)
        self.assertFalse((self.state / "recording.pid").exists())
        self.assertFalse((self.state / "recording.wav").exists())

    def test_start_failure_reports_error_without_persistent_notice(self):
        self.env["START_FAIL"] = "1"
        worker = self.launch(worker=True)
        self.until(lambda: (self.root / "allowance.started").exists())
        self.release()
        self.assertEqual(worker.wait(timeout=4), 1)
        self.assertEqual(self.notices(), [["Voice dictate", "Could not start the microphone", "-u", "critical", "--expire-time=15000"]])
        self.assertFalse((self.state / "recording.pid").exists())

    def test_unexpected_exit_closes_notice_and_reports_error(self):
        worker, pid = self.start()
        self.release()
        self.until(lambda: len(self.notices()) == 1)
        os.kill(pid, signal.SIGTERM)
        self.assertEqual(worker.wait(timeout=4), 1)
        self.assert_closed(pid)
        self.assertEqual(self.notices()[-1], ["Voice dictate", "Microphone stopped unexpectedly", "-u", "critical", "--expire-time=15000"])
        self.assertFalse((self.state / "recording.wav").exists())

    def test_notification_failure_stops_recorder_and_cleans_state(self):
        self.env["NOTIFY_FAIL"] = "1"
        worker, pid = self.start()
        self.release()
        self.assertEqual(worker.wait(timeout=4), 1)
        self.assert_closed(pid)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertFalse((self.state / "recording.pid").exists())
        self.assertFalse((self.state / "recording.wav").exists())

    def test_old_worker_does_not_delete_new_session_state(self):
        worker, pid = self.start()
        self.release()
        self.until(lambda: len(self.notices()) == 1)
        (self.state / "recording.pid").write_text("424242\n")
        (self.state / "recording.wav").write_bytes(b"new session fixture")
        os.kill(pid, signal.SIGTERM)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assert_closed(pid)
        self.assertEqual((self.state / "recording.pid").read_text(), "424242\n")
        self.assertEqual((self.state / "recording.wav").read_bytes(), b"new session fixture")


if __name__ == "__main__":
    unittest.main()
