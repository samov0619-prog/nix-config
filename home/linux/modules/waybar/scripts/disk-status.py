"""Waybar-owned JSON stream: home filesystem capacity and backing disk activity."""

import argparse
from dataclasses import dataclass
import html
import json
import math
import os
from pathlib import Path
import time


GIB = 1024**3
MIB = 1024**2


@dataclass(frozen=True)
class Counters:
    device: str
    identity: tuple
    timestamp: float
    read_sectors: int
    written_sectors: int
    busy_ms: int


def read_counters(device_number, timestamp, sysfs=Path("/sys")):
    device = (sysfs / "dev/block" / (
        f"{os.major(device_number)}:{os.minor(device_number)}"
    )).resolve(strict=True)
    if (device / "partition").exists():
        device = device.parent
    # Do not guess physical utilization or double count device-mapper/RAID layers.
    if any((device / "slaves").iterdir()):
        raise ValueError("stacked block devices are not supported")
    values = [int(value) for value in (device / "stat").read_text().split()]
    if len(values) < 11 or any(value < 0 for value in values):
        raise ValueError("invalid block statistics")
    # diskseq distinguishes a replaced/rebound device even if its name is reused.
    identity = (str(device), (device / "diskseq").read_text().strip())
    return Counters(
        device.name, identity, timestamp, values[2], values[6], values[9]
    )


def rates(previous, current):
    if previous is None or previous.identity != current.identity:
        return None
    elapsed = current.timestamp - previous.timestamp
    deltas = (
        current.read_sectors - previous.read_sectors,
        current.written_sectors - previous.written_sectors,
        current.busy_ms - previous.busy_ms,
    )
    if elapsed <= 0 or min(deltas) < 0:
        return None
    # Linux block statistics always use 512-byte sectors, not logical sector size.
    return (
        min(100.0, deltas[2] / (elapsed * 1000) * 100),
        deltas[0] * 512 / elapsed / MIB,
        deltas[1] * 512 / elapsed / MIB,
    )


def collect(path, previous=None, *, sysfs=Path("/sys"), clock=time.monotonic):
    try:
        device_number = os.stat(path).st_dev
        space = os.statvfs(path)
        total = space.f_blocks * space.f_frsize
        available = max(0, space.f_bavail) * space.f_frsize
        if total <= 0:
            raise ValueError("filesystem capacity is unavailable")
    except (OSError, ValueError):
        return {
            "text": "disk:—",
            "tooltip": "Home filesystem capacity and I/O are unavailable.",
            "class": "unavailable",
        }, None

    current = None
    activity = None
    try:
        current = read_counters(device_number, clock(), sysfs)
        activity = rates(previous, current)
        io_note = "Collecting the first I/O interval."
    except (OSError, ValueError):
        io_note = "I/O unavailable: no supported single backing block device."

    busy_text = "—" if activity is None else f"{activity[0]:.0f}%"
    lines = [
        "Home filesystem — available / total",
        f"{available / GIB:.1f} / {total / GIB:.1f} GiB",
        "Available excludes blocks reserved for the administrator.",
    ]
    if current is not None:
        lines.append(f"Whole backing disk: {html.escape(current.device)}")
    if activity is not None:
        busy, read, written = activity
        lines.extend([
            f"I/O busy: {busy:.0f}% of the sampling interval",
            f"Read: {read:.1f} MiB/s · Write: {written:.1f} MiB/s",
        ])
    else:
        lines.append(io_note)
    lines.append("Busy time is not a percentage of maximum speed (especially NVMe).")
    return {
        "text": f"disk:{busy_text} · {available / GIB:.0f}/{total / GIB:.0f} GiB",
        "tooltip": "\n".join(lines),
        "class": "ready" if activity is not None else "io-unavailable",
    }, current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path.home())
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--samples", type=int, help="Stop after N samples (diagnostics).")
    args = parser.parse_args()
    if not math.isfinite(args.interval) or args.interval < 0.05:
        parser.error("--interval must be finite and at least 0.05 seconds")
    if args.samples is not None and args.samples < 1:
        parser.error("--samples must be positive")
    previous = None
    count = 0
    while True:
        started = time.monotonic()
        output, previous = collect(args.path, previous)
        print(json.dumps(output, ensure_ascii=False), flush=True)
        count += 1
        if args.samples is not None and count >= args.samples:
            break
        time.sleep(max(0, args.interval - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
