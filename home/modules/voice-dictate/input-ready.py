"""Select a local PipeWire input and await PCM, without inspecting speech content."""

import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time


def local_source(graph):
    name = None
    for obj in graph:
        if obj.get("props", {}).get("metadata.name") != "default":
            continue
        for item in obj.get("metadata", []):
            if item.get("subject") == 0 and item.get("key") == "default.audio.source":
                value = item.get("value", {})
                if isinstance(value, str):
                    value = json.loads(value)
                name = value.get("name")
    if not name:
        return None
    for obj in graph:
        props = obj.get("info", {}).get("props", {})
        if (
            obj.get("type") == "PipeWire:Interface:Node"
            and props.get("node.name") == name
            and props.get("media.class") == "Audio/Source"
            and props.get("device.api") == "alsa"
            and name.startswith("alsa_input.")
        ):
            serial = props.get("object.serial")
            if isinstance(serial, int) and not isinstance(serial, bool) and serial > 0:
                return str(serial)
    return None


def has_pcm(path):
    try:
        with path.open("rb") as audio:
            header = audio.read(12)
            if header[:4] not in (b"RIFF", b"RF64") or header[8:12] != b"WAVE":
                return False
            size = os.fstat(audio.fileno()).st_size
            offset = 12
            while offset + 8 <= size:
                audio.seek(offset)
                chunk = audio.read(8)
                if len(chunk) != 8:
                    return False
                offset += 8
                if chunk[:4] == b"data":
                    # libsndfile finalizes chunk lengths on close. Actual bytes
                    # beyond the header prove one mono s16 frame has arrived;
                    # silent frames count too, without testing speech amplitude.
                    return size >= offset + 2
                offset += struct.unpack("<I", chunk[4:])[0]
                offset += offset % 2
    except OSError:
        return False
    return False


def wait_for_pcm(path, pid, timeout=2.0):
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        if has_pcm(path):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)


def main(argv):
    if argv == ["source"]:
        result = subprocess.run(
            ["pw-dump"], capture_output=True, text=True, check=True, timeout=2
        )
        source = local_source(json.loads(result.stdout))
        if source is not None:
            print(source)
            return 0
        return 1
    if len(argv) == 3 and argv[0] == "wait":
        pid = int(argv[2])
        if pid > 0:
            return 0 if wait_for_pcm(Path(argv[1]), pid) else 1
    raise ValueError("Expected: source | wait AUDIO PID")


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"voice-input-ready: {error}", file=sys.stderr)
        sys.exit(1)
