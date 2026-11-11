"""Lenovo-only Hyprland toggle; no daemon, sudo or persistent device policy."""

import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import subprocess
import sys


DEVICE = "gxtp5100:00-27c6:01e7-touchpad"


def run(action, hyprctl):
    signature = os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
    runtime = Path(os.environ["XDG_RUNTIME_DIR"])
    if not signature or runtime.stat().st_uid != os.getuid():
        raise ValueError("A current, user-owned Hyprland session is required")
    key = hashlib.sha256(signature.encode()).hexdigest()[:16]
    directory = runtime / f"lenovo-touchpad-{key}"
    directory.mkdir(mode=0o700, exist_ok=True)
    with (directory / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = directory / "state"
        enabled = True
        if action == "toggle" and state.exists():
            previous = state.read_text().strip()
            if previous not in ("enabled", "disabled"):
                raise ValueError("Invalid touchpad state; run lenovo-touchpad enable")
            enabled = previous == "enabled"
        target = action == "enable" or not enabled
        reply = subprocess.run(
            [hyprctl, "keyword", f"device[{DEVICE}]:enabled", "true" if target else "false"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
        # hyprctl may return zero even when the compositor rejects a keyword.
        if reply.stdout.strip() != "ok":
            raise ValueError(f"Hyprland rejected touchpad change: {reply.stdout.strip()}")
        state.write_text("enabled\n" if target else "disabled\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hyprctl", default="hyprctl")
    parser.add_argument("action", choices=("toggle", "enable"))
    args = parser.parse_args()
    os.umask(0o077)
    try:
        run(args.action, args.hyprctl)
    except (KeyError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"lenovo-touchpad: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
