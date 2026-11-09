"""Production stop/transcription branch with no real signals, audio or display."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parent


class VoiceDictateTests(unittest.TestCase):
    def run_dictation(self, text="Пример диктовки.", *, whisper_exit=0, empty_audio=False):
        source = (ROOT / "default.nix").read_text()
        self.assertEqual(source.count("    text = ''\n"), 1)
        body = source.split("    text = ''\n", 1)[1].split("\n    '';", 1)[0]
        body = textwrap.dedent(body)
        self.assertIn("${whisperSmallQ51}", body)
        self.assertIn("${gpuFlag}", body)
        body = body.replace("${whisperSmallQ51}", "/fixture/model.bin")
        body = body.replace("${gpuFlag}", "").replace("''${", "${")
        # kill is a shell function in this child, never the real builtin.
        # First probe: recording exists; subsequent probe: mock recorder stopped.
        prefix = '''
            checks=0
            kill() {
                printf '%s\\n' "$*" >> "$HOME/signals.txt"
                case "$1" in
                    -0) checks=$((checks + 1)); [ "$checks" -eq 1 ] ;;
                    -INT) return 0 ;;
                    *) return 99 ;;
                esac
            }
        '''
        with tempfile.TemporaryDirectory(
            prefix="voice-dictate-test-", dir="/tmp/opencode"
        ) as directory:
            root = Path(directory)
            binaries = root / "bin"
            binaries.mkdir()
            state = root / "voice-dictate"
            state.mkdir()
            (state / "recording.pid").write_text("424242\n")
            (state / "recording.wav").write_bytes(
                b"" if empty_audio else b"synthetic fixture, not recorded audio"
            )
            (root / "transcript.txt").write_text(text)
            # Limit PATH to mocks and explicit local text/file utilities.
            for name in ("cat", "rm", "mkdir", "tr", "sed", "sleep"):
                (binaries / name).symlink_to(shutil.which(name))
            scripts = {
                "whisper-cli": """
                    import json
                    import os
                    import sys
                    from pathlib import Path
                    Path("whisper-argv.json").write_text(json.dumps(sys.argv[1:]))
                    sys.stdout.write(Path("transcript.txt").read_text())
                    sys.exit(int(os.environ["WHISPER_EXIT"]))
                """,
                "wl-copy": """
                    import json
                    import sys
                    from pathlib import Path
                    Path("clipboard-argv.json").write_text(json.dumps(sys.argv[1:]))
                    Path("copied.bin").write_bytes(sys.stdin.buffer.read())
                """,
                "wtype": """
                    import json
                    import sys
                    from pathlib import Path
                    Path("wtype-argv.json").write_text(json.dumps(sys.argv[1:]))
                    Path("typed.bin").write_bytes(sys.stdin.buffer.read())
                """,
                "notify-send": """
                    import json
                    import sys
                    from pathlib import Path
                    with Path("notifications.jsonl").open("a") as stream:
                        stream.write(json.dumps(sys.argv[1:]) + "\\n")
                """,
                "pw-record": """
                    from pathlib import Path
                    Path("unexpected-recording.called").touch()
                    raise SystemExit(99)
                """,
            }
            for name, script in scripts.items():
                executable = binaries / name
                executable.write_text(
                    f"#!{sys.executable}\n" + textwrap.dedent(script)
                )
                executable.chmod(0o700)
            result = subprocess.run(
                [shutil.which("bash"), "-euo", "pipefail", "-c", prefix + body],
                cwd=root,
                env={
                    "PATH": str(binaries),
                    "HOME": str(root),
                    "XDG_RUNTIME_DIR": str(root),
                    "WHISPER_EXIT": str(whisper_exit),
                    "LC_ALL": "C.UTF-8",
                },
                capture_output=True,
                timeout=5,
            )
            self.assertFalse((root / "unexpected-recording.called").exists())
            self.assertFalse((state / "recording.pid").exists())
            self.assertEqual(
                (root / "signals.txt").read_text().splitlines(),
                ["-0 424242", "-INT 424242", "-0 424242"],
            )
            notification_path = root / "notifications.jsonl"
            output = {
                "exit": result.returncode,
                "stderr": result.stderr,
                "audio_remains": (state / "recording.wav").exists(),
                "notifications": (
                    [json.loads(line) for line in notification_path.read_text().splitlines()]
                    if notification_path.exists() else []
                ),
            }
            for name in ("copied.bin", "typed.bin"):
                path = root / name
                output[name] = path.read_bytes() if path.exists() else None
            for name in ("wtype-argv.json", "clipboard-argv.json", "whisper-argv.json"):
                path = root / name
                output[name] = json.loads(path.read_text()) if path.exists() else None
            return output

    def assert_failure(self, output, message):
        self.assertNotEqual(output["exit"], 0)
        self.assertFalse(output["audio_remains"])
        self.assertIsNone(output["copied.bin"])
        self.assertIsNone(output["typed.bin"])
        self.assertEqual(
            output["notifications"], [["Voice dictate", message, "-u", "critical"]]
        )

    def test_whisper_failure_removes_audio_and_notifies(self):
        self.assert_failure(
            self.run_dictation("", whisper_exit=7), "Transcription failed"
        )

    def test_failed_partial_transcript_is_not_copied_or_typed(self):
        self.assert_failure(
            self.run_dictation("partial output", whisper_exit=7),
            "Transcription failed",
        )

    def test_leading_dash_uses_stdin_without_final_newline(self):
        output = self.run_dictation("- пример диктовки")
        self.assertEqual(output["exit"], 0, output["stderr"])
        self.assertEqual(output["wtype-argv.json"], ["-"])
        self.assertEqual(output["typed.bin"], "- пример диктовки".encode())
        self.assertEqual(output["copied.bin"], output["typed.bin"])
        self.assertFalse(output["audio_remains"])
        self.assertEqual(
            output["notifications"],
            [["Voice dictate", "Transcribed and copied to clipboard"]],
        )

    def test_literal_unicode_quotes_and_shell_characters(self):
        text = "Кавычки 'слово' $HOME * \\ $(exit 77)"
        output = self.run_dictation(text)
        self.assertEqual(output["exit"], 0, output["stderr"])
        self.assertEqual(output["typed.bin"], text.encode())
        self.assertEqual(output["wtype-argv.json"], ["-"])
        self.assertEqual(output["clipboard-argv.json"], [])

    def test_existing_whitespace_normalization_is_preserved(self):
        output = self.run_dictation("  первая\nвторая\t строка  \n")
        self.assertEqual(output["exit"], 0, output["stderr"])
        self.assertEqual(output["typed.bin"], "первая вторая строка".encode())

    def test_empty_transcript_removes_audio_and_notifies(self):
        self.assert_failure(self.run_dictation(" \n \t"), "No speech recognized")

    def test_empty_audio_does_not_run_recognizer(self):
        output = self.run_dictation(empty_audio=True)
        self.assertNotEqual(output["exit"], 0)
        self.assertIsNone(output["whisper-argv.json"])
        self.assertIsNone(output["typed.bin"])
        self.assertIsNone(output["copied.bin"])
        self.assertEqual(
            output["notifications"],
            [["Voice dictate", "No audio was recorded", "-u", "critical"]],
        )

    def test_recognizer_options_are_unchanged(self):
        output = self.run_dictation()
        arguments = output["whisper-argv.json"]
        self.assertEqual(arguments[:2], ["-m", "/fixture/model.bin"])
        self.assertEqual(arguments[2], "-f")
        self.assertTrue(arguments[3].endswith("/voice-dictate/recording.wav"))
        self.assertEqual(arguments[4:], ["-l", "ru", "-nt", "-np"])


if __name__ == "__main__":
    unittest.main()
