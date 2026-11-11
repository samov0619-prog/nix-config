"""Test the actual BlueZ adapter function with stubbed management calls.

Provide an upstream src/adapter.c from the selected package (currently 5.87).
Test fixed behavior without a local patch; do not adjust expectations on updates.
No Bluetooth device, service or full package build is involved.
"""

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent


def exercise(source, directory, name, empty_errors):
    match = re.search(
        r"static void load_defaults\(struct btd_adapter \*adapter\)\n\{.*?\n\}",
        source,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError("Upstream load_defaults() changed; review the harness")
    harness = (HERE / "bluez-test.c").read_text().replace(
        "/* LOAD_DEFAULTS_FUNCTION */", match.group()
    )
    c_file = directory / f"{name}.c"
    binary = directory / name
    c_file.write_text(harness)
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            f"-DEXPECT_EMPTY_ERROR={empty_errors}",
            str(c_file),
            "-o",
            str(binary),
        ],
        check=True,
        timeout=10,
    )
    subprocess.run([str(binary)], check=True, timeout=5)
    print(f"{name}: 7 management/cleanup scenarios passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Upstream src/adapter.c")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="bluez-defaults-", dir="/tmp/opencode") as d:
        root = Path(d)
        source = args.source.read_text()
        exercise(source, root, "upstream-without-patch", 0)


if __name__ == "__main__":
    main()
