"""Exercise the actual PipeWire X11 disconnect callback with contract stubs.

Pass upstream src/modules/module-x11-bell.c from the selected release. Normally
check the original invalid call and the upstream patch applied with zero fuzz.
--check-upstream checks fixed behavior without a patch for update/removal review.
No service, X server, device, full package build or activation is involved.
"""

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent


def exercise(source, root, name, invalid):
    match = re.search(
        r"static void x11_io_error_exit_handler\(Display \*display, void \*data\)"
        r"\n\{.*?\n\}",
        source,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError("Upstream callback changed; review the harness")
    harness = (HERE / "pipewire-x11-test.c").read_text().replace(
        "/* UPSTREAM_CALLBACK */", match.group()
    )
    c_file = root / f"{name}.c"
    binary = root / name
    c_file.write_text(harness)
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-DEXPECT_INVALID={invalid}",
            str(c_file),
            "-o",
            str(binary),
        ],
        check=True,
        timeout=10,
    )
    subprocess.run([str(binary)], check=True, timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--check-upstream", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pipewire-x11-", dir="/tmp/opencode") as d:
        root = Path(d)
        source = args.source.read_text()
        if args.check_upstream:
            exercise(source, root, "upstream-without-patch", 0)
            return
        exercise(source, root, "baseline", 1)
        target = root / "src" / "modules" / "module-x11-bell.c"
        target.parent.mkdir(parents=True)
        target.write_text(source)
        subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(HERE.parent / "pipewire-x11-idempotent.patch"),
            ],
            cwd=root,
            check=True,
            timeout=5,
        )
        exercise(target.read_text(), root, "patched", 0)


if __name__ == "__main__":
    main()
