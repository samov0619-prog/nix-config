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
        self.body = self.body.replace("${lib.boolToString config.voiceDictate.fastLocalInput}", "false")
        self.body = self.body.replace("${vulkanEnv}", "")
        self.body = self.body.replace("${gpuFlag}", "").replace("''${", "${")
        for name in ("cat", "rm", "mkdir", "tr", "sed", "flock"):
            (self.bin / name).symlink_to(shutil.which(name))
        self.command("pw-record", '''
            import json, os, signal, sys, time
            from pathlib import Path
            if os.environ.get("START_FAIL"):
                sys.exit(7)
            signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
            Path("recorder.argv").write_text(json.dumps(sys.argv[1:]))
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
        self.command("voice-input-ready", '''
            import os, sys, time
            from pathlib import Path
            if sys.argv[1] == "source":
                source = os.environ.get("LOCAL_SOURCE", "")
                if not source:
                    sys.exit(1)
                print(source)
            else:
                Path("local-wait.started").touch()
                while not Path("local-wait.release").exists():
                    time.sleep(0.005)
                sys.exit(1 if os.environ.get("LOCAL_WAIT_FAIL") else 0)
        ''')
        self.command("notify-send", '''
            import json, os, sys, time
            from pathlib import Path
            with Path("notices.jsonl").open("a") as log:
                log.write(json.dumps(sys.argv[1:]) + "\\n")
            if "--expire-time=0" in sys.argv and os.environ.get("NOTIFY_FAIL"):
                sys.exit(8)
            if "--action=default=Cancel" in sys.argv:
                recording = "--print-id" in sys.argv
                prefix = "recording-action" if recording else "action"
                if recording:
                    if os.environ.get("BLOCK_RECORDING_NOTICE"):
                        Path("publication.started").touch()
                        while not Path("publication.release").exists():
                            time.sleep(0.005)
                    print("123", flush=True)
                Path(prefix + ".ready").write_text(str(os.getpid()))
                if not recording and os.environ.get("TRANSCRIPTION_NOTIFY_FAIL"):
                    sys.exit(8)
                while not Path(prefix + ".release").exists():
                    time.sleep(0.005)
                print(os.environ.get("RECORDING_ACTION" if recording else "ACTION", ""))
        ''')
        self.command("notification-close", '''
            import json, sys
            from pathlib import Path
            with Path("closed.jsonl").open("a") as log:
                log.write(json.dumps(sys.argv[1:]) + "\\n")
        ''')
        self.command("whisper-cli", '''
            import os, signal, time
            from pathlib import Path
            Path("whisper.ready").write_text(str(os.getpid()))
            if os.environ.get("SLOW_WHISPER"):
                while not Path("whisper.release").exists():
                    time.sleep(0.005)
            print("fixture transcript")
        ''')
        for name in ("wl-copy", "wtype"):
            self.command(name, '''
                import sys
                from pathlib import Path
                Path(Path(sys.argv[0]).name + ".called").write_bytes(sys.stdin.buffer.read())
            ''')

    def command(self, name, body):
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(body))
        path.chmod(0o700)

    def launch(self, *, worker=False):
        body = self.body
        if self.env.get("FAST_LOCAL_INPUT"):
            body = body.replace("fast_local_input=false", "fast_local_input=true")
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
        recording = [call for call in calls if "recording." in call[-1]]
        self.assertTrue(recording)
        self.assertTrue(all(call == ["--app-name=Voice dictate", f"--category=voice-dictate.recording.{pid}"] for call in recording))

    def test_persistent_notice_then_normal_second_hotkey(self):
        worker, pid = self.start()
        self.release()
        self.until(lambda: len(self.notices()) == 1)
        notice = self.notices()[0]
        self.assertIn("--expire-time=0", notice)
        self.assertIn(f"--category=voice-dictate.recording.{pid}", notice)
        self.assertIn("--action=default=Cancel", notice)
        self.assertIn("Super+Shift+R", notice[-1])
        self.assertIn("Left-click", notice[-1])
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
        self.assertFalse(any(any("voice-dictate.recording." in arg for arg in notice) for notice in self.notices()))
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
        self.until(lambda: any("Transcribed and copied to clipboard" in notice for notice in self.notices()))
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

    def transcribing(self):
        self.env["SLOW_WHISPER"] = "1"
        worker, _ = self.start()
        self.release()
        self.until(lambda: len(self.notices()) == 1)
        stop = self.launch()
        self.until(lambda: (self.root / "whisper.ready").exists())
        self.until(lambda: (self.root / "action.ready").exists())
        return worker, stop

    def assert_transcription_cleaned(self):
        for name in ("recording.wav", "recording.pid", "transcript.txt", "transcription-action"):
            self.assertFalse((self.state / name).exists(), name)
        for name in ("whisper.ready", "action.ready"):
            with self.assertRaises(ProcessLookupError):
                os.kill(int((self.root / name).read_text()), 0)

    def test_notification_action_cancels_without_clipboard_or_insertion(self):
        self.env["ACTION"] = "default"
        worker, stop = self.transcribing()
        (self.root / "action.release").touch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assert_transcription_cleaned()
        self.assertFalse((self.root / "wl-copy.called").exists())
        self.assertFalse((self.root / "wtype.called").exists())
        self.assertEqual(self.notices()[-1], ["Voice dictate", "Transcription cancelled", "--expire-time=3000"])
        closed = (self.root / "closed.jsonl").read_text()
        self.assertIn(f"voice-dictate.transcribing.{stop.pid}", closed)

    def test_manual_dismissal_does_not_cancel_transcription(self):
        worker, stop = self.transcribing()
        (self.root / "action.release").touch()
        time.sleep(0.05)
        self.assertIsNone(stop.poll())
        (self.root / "whisper.release").touch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assert_transcription_cleaned()
        self.assertEqual((self.root / "wtype.called").read_bytes(), b"fixture transcript")

    def test_recognition_completion_reaps_pending_notification(self):
        worker, stop = self.transcribing()
        (self.root / "whisper.release").touch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assert_transcription_cleaned()
        self.assertEqual((self.root / "wl-copy.called").read_bytes(), b"fixture transcript")

    def test_notification_failure_does_not_discard_recognition(self):
        self.env["TRANSCRIPTION_NOTIFY_FAIL"] = "1"
        worker, stop = self.transcribing()
        (self.root / "whisper.release").touch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assert_transcription_cleaned()
        self.assertEqual((self.root / "wtype.called").read_bytes(), b"fixture transcript")

    def test_new_recording_after_cancellation(self):
        self.env["ACTION"] = "default"
        worker, stop = self.transcribing()
        (self.root / "action.release").touch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assert_transcription_cleaned()

        for name in ("recorder.ready", "whisper.ready", "action.ready", "action.release"):
            (self.root / name).unlink()
        del self.env["SLOW_WHISPER"]
        del self.env["ACTION"]
        next_worker, _ = self.start()
        next_stop = self.launch()
        self.assertEqual(next_stop.wait(timeout=4), 0)
        self.assertEqual(next_worker.wait(timeout=4), 0)
        self.assertEqual((self.root / "wtype.called").read_bytes(), b"fixture transcript")
        self.assertFalse((self.state / "recording.wav").exists())

    def test_recording_action_cancels_before_recognition(self):
        self.env["RECORDING_ACTION"] = "default"
        worker, pid = self.start()
        self.release()
        self.until(lambda: (self.root / "recording-action.ready").exists())
        (self.root / "recording-action.release").touch()
        self.assertEqual(worker.wait(timeout=4), 0)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        with self.assertRaises(ProcessLookupError):
            os.kill(int((self.root / "recording-action.ready").read_text()), 0)
        self.assertFalse((self.root / "whisper.ready").exists())
        self.assertFalse((self.root / "wl-copy.called").exists())
        self.assertFalse((self.root / "wtype.called").exists())
        self.assertFalse((self.state / "recording.pid").exists())
        self.assertFalse((self.state / "recording.wav").exists())
        self.assertEqual(self.notices()[-1], ["Voice dictate", "Recording cancelled", "--expire-time=3000"])
        self.assert_closed(pid)

    def test_detached_recording_action_targets_worker_not_exited_launcher(self):
        self.env["RECORDING_ACTION"] = "default"
        start = self.launch()
        self.assertEqual(start.wait(timeout=4), 0)
        self.until(lambda: (self.root / "recorder.ready").exists())
        pid = int((self.root / "recorder.ready").read_text())
        self.release()
        self.until(lambda: (self.root / "recording-action.ready").exists())
        (self.root / "recording-action.release").touch()
        self.until(lambda: any("Recording cancelled" in notice for notice in self.notices()))
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertFalse((self.root / "whisper.ready").exists())
        self.assertFalse((self.state / "recording.wav").exists())

    def test_recording_dismissal_keeps_microphone_and_hotkey(self):
        worker, pid = self.start()
        self.release()
        self.until(lambda: (self.root / "recording-action.ready").exists())
        (self.root / "recording-action.release").touch()
        time.sleep(0.05)
        self.assertIsNone(worker.poll())
        os.kill(pid, 0)
        stop = self.launch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assertEqual((self.root / "wtype.called").read_bytes(), b"fixture transcript")

    def test_late_recording_cancel_signal_does_not_cancel_recognition(self):
        worker, stop = self.transcribing()
        os.kill(worker.pid, signal.SIGUSR1)
        time.sleep(0.05)
        self.assertIsNone(stop.poll())
        (self.root / "whisper.release").touch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assertEqual((self.root / "wtype.called").read_bytes(), b"fixture transcript")
        self.assertFalse(any("Recording cancelled" in notice for notice in self.notices()))

    def test_new_recording_after_recording_cancellation(self):
        self.env["RECORDING_ACTION"] = "default"
        worker, _ = self.start()
        self.release()
        self.until(lambda: (self.root / "recording-action.ready").exists())
        (self.root / "recording-action.release").touch()
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assertFalse((self.state / "recording.wav").exists())
        for name in ("recorder.ready", "recording-action.ready", "recording-action.release"):
            (self.root / name).unlink()
        del self.env["RECORDING_ACTION"]
        next_worker, _ = self.start()
        self.until(lambda: (self.root / "recording-action.ready").exists())
        next_stop = self.launch()
        self.assertEqual(next_stop.wait(timeout=4), 0)
        self.assertEqual(next_worker.wait(timeout=4), 0)
        self.assertEqual((self.root / "wtype.called").read_bytes(), b"fixture transcript")

    def test_hotkey_waits_for_recording_notice_publication(self):
        self.env["BLOCK_RECORDING_NOTICE"] = "1"
        worker, _ = self.start()
        self.release()
        self.until(lambda: (self.root / "publication.started").exists())
        stop = self.launch()
        time.sleep(0.05)
        self.assertIsNone(stop.poll())
        self.assertTrue((self.state / "recording.pid").exists())
        (self.root / "publication.release").touch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assertFalse((self.state / "recording.wav").exists())

    def test_new_recording_clears_stale_transcript_after_interrupted_session(self):
        self.state.mkdir()
        (self.state / "recording.wav").write_bytes(b"stale audio")
        for name in ("transcript.txt", "transcription-action"):
            (self.state / name).write_text("stale private contents")
        worker, _ = self.start()
        for name in ("transcript.txt", "transcription-action"):
            self.assertFalse((self.state / name).exists())
        self.release()
        stop = self.launch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assertFalse((self.state / "recording.wav").exists())

    def test_local_input_waits_for_audio_not_bluetooth_allowance(self):
        self.env.update(FAST_LOCAL_INPUT="1", LOCAL_SOURCE="77")
        worker, _ = self.start()
        self.until(lambda: (self.root / "local-wait.started").exists())
        self.assertEqual(self.notices(), [])
        arguments = json.loads((self.root / "recorder.argv").read_text())
        self.assertEqual(arguments[:2], ["--target", "77"])
        properties = json.loads(arguments[2].split("=", 1)[1])
        self.assertEqual(properties, {"node.dont-fallback": True, "node.dont-reconnect": True})
        self.assertFalse((self.root / "allowance.started").exists())
        (self.root / "local-wait.release").touch()
        self.until(lambda: (self.root / "recording-action.ready").exists())
        stop = self.launch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)

    def test_manual_bluetooth_or_unknown_source_retains_allowance(self):
        self.env["FAST_LOCAL_INPUT"] = "1"
        worker, _ = self.start()
        self.until(lambda: (self.root / "allowance.started").exists())
        self.assertFalse((self.root / "local-wait.started").exists())
        self.assertNotIn("--target", json.loads((self.root / "recorder.argv").read_text()))
        self.release()
        stop = self.launch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)

    def test_failed_local_readiness_stops_recorder_and_cleans_audio(self):
        self.env.update(FAST_LOCAL_INPUT="1", LOCAL_SOURCE="77", LOCAL_WAIT_FAIL="1")
        worker, pid = self.start()
        self.until(lambda: (self.root / "local-wait.started").exists())
        (self.root / "local-wait.release").touch()
        self.assertEqual(worker.wait(timeout=4), 1)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertFalse((self.state / "recording.wav").exists())
        self.assertEqual(self.notices(), [["Voice dictate", "Could not start the microphone", "-u", "critical", "--expire-time=15000"]])

    def test_hotkey_during_local_readiness_does_not_publish_late_notice(self):
        self.env.update(FAST_LOCAL_INPUT="1", LOCAL_SOURCE="77")
        worker, _ = self.start()
        self.until(lambda: (self.root / "local-wait.started").exists())
        stop = self.launch()
        self.until(lambda: not (self.state / "recording.pid").exists())
        (self.root / "local-wait.release").touch()
        self.assertEqual(stop.wait(timeout=4), 0)
        self.assertEqual(worker.wait(timeout=4), 0)
        self.assertFalse(any(any("voice-dictate.recording." in arg for arg in notice) for notice in self.notices()))


if __name__ == "__main__":
    unittest.main()
