"""Explicit NVIDIA/PPD terminal monitor; no service, cache or power-policy writes."""

import argparse
import csv
from dataclasses import dataclass
import io
import math
import signal
import subprocess
import sys
import time


FIELDS = "name,temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total"
PROFILES = {"power-saver", "balanced", "performance"}
HEADER = "Time     Profile       Temp   Power W   GPU %     VRAM MiB    VRAM %"


@dataclass(frozen=True)
class Metrics:
    name: str
    temperature: float | None
    watts: float | None
    utilization: float | None
    used: float | None
    total: float | None

    @property
    def memory_percent(self):
        if self.used is None or self.total is None:
            return None
        return 100 * self.used / self.total


@dataclass(frozen=True)
class Sample:
    timestamp: str
    profile: str
    metrics: Metrics | None
    error: str = ""


def number(value):
    value = value.strip()
    if value in {"N/A", "[N/A]", "[Not Supported]", "Not Supported"}:
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("invalid numeric GPU metric")
    return result


def parse_metrics(text):
    rows = list(csv.reader(io.StringIO(text.strip())))
    if len(rows) != 1 or len(rows[0]) != 6:
        raise ValueError("expected one GPU and six fields")
    name, *values = rows[0]
    metrics = Metrics(name.strip(), *(number(value) for value in values))
    if not metrics.name:
        raise ValueError("missing GPU name")
    if metrics.utilization is not None and metrics.utilization > 100:
        raise ValueError("GPU utilization exceeds 100%")
    if metrics.total is not None and metrics.total <= 0:
        raise ValueError("invalid VRAM capacity")
    if metrics.used is not None and metrics.total is not None and metrics.used > metrics.total:
        raise ValueError("used VRAM exceeds capacity")
    return metrics


def collect(gpu):
    profile = "?"
    errors = []
    try:
        result = subprocess.run(
            ["powerprofilesctl", "get"], stdin=subprocess.DEVNULL,
            capture_output=True, text=True, check=True, timeout=1,
        )
        if result.stdout.strip() not in PROFILES:
            raise ValueError("unknown PPD profile")
        profile = result.stdout.strip()
    except (OSError, ValueError, subprocess.SubprocessError):
        errors.append("PPD profile unavailable")
    try:
        result = subprocess.run(
            ["nvidia-smi", f"--id={gpu}", f"--query-gpu={FIELDS}",
             "--format=csv,noheader,nounits"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            check=True, timeout=2,
        )
        metrics = parse_metrics(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        metrics = None
        errors.append("NVIDIA query failed (missing command, timeout or invalid response)")
    return Sample(time.strftime("%H:%M:%S"), profile, metrics, "; ".join(errors))


def formatted(value, precision=0):
    return "n/a" if value is None else f"{value:.{precision}f}"


def row(sample):
    prefix = f"{sample.timestamp} {sample.profile:<12}"
    metric = sample.metrics
    if metric is None:
        return prefix + "  -- query failed --"
    memory = f"{formatted(metric.used)}/{formatted(metric.total)}"
    return (
        f"{prefix} {formatted(metric.temperature):>4} C"
        f" {formatted(metric.watts, 2):>8} {formatted(metric.utilization):>7}"
        f" {memory:>12} {formatted(metric.memory_percent, 1):>9}"
    )


def safe_text(text):
    # External GPU names/error strings must not inject terminal control codes.
    return "".join(character if character.isprintable() else "?" for character in text)


def stream(args):
    print(f"NVIDIA GPU {safe_text(args.gpu)} | every {args.interval:g}s | Ctrl+C to stop", flush=True)
    print("Manual polling can wake/keep GPU awake. Power W = GPU board, not laptop.", flush=True)
    print("Profile = PPD; change it in Waybar. VRAM = used/total MiB and capacity %.", flush=True)
    previous_name = None
    count = 0
    while True:
        started = time.monotonic()
        sample = collect(args.gpu)
        if sample.metrics and sample.metrics.name != previous_name:
            previous_name = sample.metrics.name
            print(f"GPU: {safe_text(previous_name)}", flush=True)
        if count % 20 == 0:
            print(HEADER, flush=True)
        print(safe_text(row(sample)), flush=True)
        if sample.error:
            print(f"  {sample.error}", flush=True)
        count += 1
        # Append forever without keeping a growing in-memory history. The
        # terminal owns scrollback; repeat only the heading, never truncate rows.
        remaining = args.interval - (time.monotonic() - started)
        # Never burst/catch up after a slow query or resume.
        time.sleep(remaining if remaining > 0 else args.interval)


def interrupt(_signal, _frame):
    raise KeyboardInterrupt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=5, help="Seconds between queries (default: 5)")
    parser.add_argument("--gpu", default="0000:02:00.0", help="NVIDIA PCI ID or index")
    parser.add_argument("--once", action="store_true", help="Print just one snapshot")
    args = parser.parse_args(argv)
    if not math.isfinite(args.interval) or args.interval < 1:
        parser.error("--interval must be finite and at least 1 second")
    signal.signal(signal.SIGTERM, interrupt)
    try:
        if args.once:
            sample = collect(args.gpu)
            print(HEADER)
            print(safe_text(row(sample)))
            if sample.error:
                print(sample.error, file=sys.stderr)
            return 1 if sample.error else 0
        stream(args)
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
