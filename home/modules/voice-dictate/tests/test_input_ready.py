"""PipeWire JSON selection and WAV readiness; no real microphone or daemon."""

import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "input_ready", Path(__file__).resolve().parents[1] / "input-ready.py"
)
READY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READY)


def graph(name="alsa_input.fixture", api="alsa", media_class="Audio/Source"):
    return [
        {
            "type": "PipeWire:Interface:Metadata",
            "props": {"metadata.name": "default"},
            "metadata": [
                {"subject": 0, "key": "default.audio.source", "value": {"name": name}}
            ],
        },
        {
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "node.name": name,
                    "device.api": api,
                    "media.class": media_class,
                    "object.serial": 77,
                }
            },
        },
    ]


def wav(data=b"", *, junk=b"", finalized=False):
    fmt = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if junk:
        chunks += b"JUNK" + struct.pack("<I", len(junk)) + junk
        chunks += b"\0" * (len(junk) % 2)
    chunks += b"data" + struct.pack("<I", len(data) if finalized else 0) + data
    return b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks


class SourceTests(unittest.TestCase):
    def test_local_default_returns_pinned_serial(self):
        self.assertEqual(READY.local_source(graph()), "77")

    def test_string_metadata_is_supported(self):
        objects = graph()
        objects[0]["metadata"][0]["value"] = json.dumps({"name": "alsa_input.fixture"})
        self.assertEqual(READY.local_source(objects), "77")

    def test_bluetooth_unknown_and_monitor_do_not_take_fast_path(self):
        for objects in (
            graph("bluez_input.fixture", "bluez5"),
            graph(api="unknown"),
            graph(media_class="Audio/Sink"),
            graph(name="alsa_output.fixture"),
            [],
        ):
            with self.subTest(objects=objects):
                self.assertIsNone(READY.local_source(objects))

    def test_no_default_or_invalid_serial_fails_closed(self):
        objects = graph()
        objects[0]["metadata"][0]["key"] = "default.configured.audio.source"
        self.assertIsNone(READY.local_source(objects))
        for serial in (None, True, -1, "77"):
            objects = graph()
            objects[1]["info"]["props"]["object.serial"] = serial
            self.assertIsNone(READY.local_source(objects))


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="input-ready-", dir="/tmp/opencode")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "recording.wav"

    def test_header_and_partial_frame_are_not_ready(self):
        for data in (b"", b"\0"):
            self.path.write_bytes(wav(data))
            self.assertFalse(READY.has_pcm(self.path))

    def test_silence_counts_before_header_sizes_are_finalized(self):
        self.path.write_bytes(wav(b"\0\0"))
        self.assertTrue(READY.has_pcm(self.path))
        self.assertTrue(READY.wait_for_pcm(self.path, os.getpid(), timeout=0))

    def test_odd_metadata_chunk_is_skipped(self):
        self.path.write_bytes(wav(b"\0\0", junk=b"x"))
        self.assertTrue(READY.has_pcm(self.path))

    def test_missing_truncated_or_non_wav_is_not_ready(self):
        self.assertFalse(READY.has_pcm(self.path))
        for data in (b"RIFF", b"not a WAV", wav()[:20]):
            self.path.write_bytes(data)
            self.assertFalse(READY.has_pcm(self.path))

    def test_timeout_does_not_claim_readiness(self):
        self.path.write_bytes(wav())
        self.assertFalse(READY.wait_for_pcm(self.path, os.getpid(), timeout=0.02))


if __name__ == "__main__":
    unittest.main()
