"""Click-only NVIDIA sampling; Waybar owns the idle IPC listener, not NVML.

No NVIDIA command or cached metric read before a click. Each click grants 60s
of sampling, which may wake the GPU. No window survives a helper restart. A
session-local lock/cache shares samples between bars on multiple outputs.
"""

import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import time


WINDOW = 60.0
INTERVAL = 2.0
QUERY_TIMEOUT = 2.0
PCI_ID = "0000:02:00.0"


def clock():
    # Count time in suspend too: resuming must not grant another minute.
    return time.clock_gettime(time.CLOCK_BOOTTIME)


def runtime_directory():
    base = Path(os.environ["XDG_RUNTIME_DIR"])
    if base.stat().st_uid != os.getuid():
        raise ValueError("XDG_RUNTIME_DIR is not owned by the current user")
    session = os.environ.get("WAYLAND_DISPLAY", "")
    key = hashlib.sha256(session.encode()).hexdigest()[:12]
    directory = base / f"waybar-gpu-{key}"
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if directory.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("GPU runtime directory is not private")
    return directory


def activate(directory):
    message = f"activate:{clock()}".encode()
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
        client.setblocking(False)
        for path in directory.glob("*.sock"):
            try:
                client.sendto(message, str(path))
            except (FileNotFoundError, ConnectionRefusedError):
                path.unlink(missing_ok=True)
            except BlockingIOError:
                # A queued click already wakes this listener.
                pass


def request_deadline(message, now):
    if not message.startswith(b"activate:"):
        return None
    try:
        requested = float(message[len(b"activate:"):])
    except ValueError:
        return None
    if not math.isfinite(requested):
        return None
    deadline = min(requested, now) + WINDOW
    return deadline if deadline > now else None


def parse_metrics(output):
    fields = output.strip().split(",")
    if len(fields) != 3:
        raise ValueError("expected one GPU with utilization and VRAM used/total")
    utilization, used, total = (float(value.strip()) for value in fields)
    if not all(math.isfinite(value) for value in (utilization, used, total)):
        raise ValueError("non-finite GPU metrics")
    if not (0 <= utilization <= 100 and 0 <= used <= total and total > 0):
        raise ValueError("invalid GPU metrics")
    return {"utilization": utilization, "used": used, "total": total}


def save_sample(directory, sample):
    temporary = directory / f"sample.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(sample))
    temporary.replace(directory / "sample.json")


def collect(directory, deadline, command):
    """Return a fresh shared sample, or None while another bar is collecting.

    Only called inside an explicitly enabled window. Each invocation closes all
    driver handles on exit; timeout kills/reaps the child, not a persistent NVML
    session. Userspace cannot forcibly cancel an uninterruptible kernel ioctl.
    """
    with (directory / "sample.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return None
        remaining = deadline - clock()
        if remaining <= 0:
            return None
        cache = directory / "sample.json"
        try:
            sample = json.loads(cache.read_text())
            if 0 <= clock() - sample["at"] < INTERVAL:
                if sample.get("error") is True:
                    raise subprocess.SubprocessError("shared NVIDIA query failed")
                if not isinstance(sample["time"], str):
                    raise ValueError("invalid sample time")
                sample.update(parse_metrics(",".join(
                    str(sample[key]) for key in ("utilization", "used", "total")
                )))
                return sample
        except (OSError, ValueError, KeyError, TypeError):
            pass
        # Reading the shared cache is not permission to start a late query.
        remaining = deadline - clock()
        if remaining <= 0:
            return None
        try:
            result = subprocess.run(
                [command, f"--id={PCI_ID}",
                 "--query-gpu=utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, check=True,
                timeout=min(QUERY_TIMEOUT, remaining),
            )
            sample = parse_metrics(result.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            # Share failed attempts too, rather than hammering a broken driver
            # once per output. This marker never replaces displayed good data.
            save_sample(directory, {"at": clock(), "error": True})
            raise
        sample.update(at=clock(), time=time.strftime("%H:%M:%S"))
        if sample["at"] >= deadline:
            return None
        save_sample(directory, sample)
        return sample


def render(sample, deadline, error=False):
    text = "GPU"
    lines = []
    if sample is not None and deadline is not None:
        text += f":{sample['utilization']:.0f}%|{sample['used'] / 1024:.1f}GiB"
        lines.extend([
            f"Загрузка NVIDIA: {sample['utilization']:.0f}%",
            f"VRAM: {sample['used'] / 1024:.1f} / {sample['total'] / 1024:.1f} GiB",
            f"Последний замер: {sample['time']}",
        ])
    if deadline is None:
        state = "idle"
        lines.append("Автоматический опрос NVIDIA выключен.")
    else:
        state = "unavailable" if error else "active"
        lines.append(f"Опрос включён: ещё {max(0, math.ceil(deadline - clock()))} с.")
        if error:
            lines.append("Не удалось обновить данные; прежние показания не текущие.")
    lines.append("ЛКМ: опрашивать 60 секунд (может пробудить GPU).")
    return {"text": text, "tooltip": "\n".join(lines), "class": state}


def emit(sample, deadline, error=False):
    print(json.dumps(render(sample, deadline, error), ensure_ascii=False), flush=True)


def stream(directory, command):
    path = directory / f"{os.getpid()}.sock"
    sample = deadline = None
    next_sample = 0.0
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as listener:
        listener.bind(str(path))
        listener.setblocking(False)
        try:
            emit(sample, deadline)
            while True:
                now = clock()
                if deadline is not None and now >= deadline:
                    sample = deadline = None
                    emit(sample, deadline)
                if deadline is not None and now >= next_sample:
                    error = False
                    try:
                        current = collect(directory, deadline, command)
                        if current is not None:
                            sample = current
                    except (OSError, ValueError, subprocess.SubprocessError):
                        error = True
                        current = None
                    now = clock()
                    if now >= deadline:
                        sample = deadline = None
                    # Retry a busy multi-output lock, without querying twice.
                    next_sample = now + (0.1 if current is None and not error else INTERVAL)
                    if current is not None or error or deadline is None:
                        emit(sample, deadline, error)
                timeout = None if deadline is None else max(
                    0, min(deadline, next_sample) - clock()
                )
                ready, _, _ = select.select([listener], [], [], timeout)
                if ready:
                    while True:
                        try:
                            message = listener.recv(64)
                        except BlockingIOError:
                            break
                        requested = request_deadline(message, clock())
                        if requested is not None:
                            deadline = max(deadline or 0, requested)
                            next_sample = clock()
        finally:
            path.unlink(missing_ok=True)


def terminate(signum, frame):
    # subprocess.run also kills/reaps its child when this unwinds its context.
    raise SystemExit(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    directory = runtime_directory()
    if args.activate:
        activate(directory)
    else:
        signal.signal(signal.SIGTERM, terminate)
        signal.signal(signal.SIGINT, terminate)
        stream(directory, "nvidia-smi")


if __name__ == "__main__":
    main()
