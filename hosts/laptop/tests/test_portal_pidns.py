"""Exercise upstream portal pidns code with real Linux descriptors and ioctl.

Pass the selected release's src directory; optionally pass 1.20.4's src as
--baseline to reproduce ENOTDIR. Only GLib diagnostics are stubbed. No portal
service, D-Bus method, device, package build or activation is involved.
"""

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent


def exercise(source, root, baseline=False):
    name = "xdp_pidfd_get_namespace" if baseline else "xdp_pidfd_get_pidns"
    text = (source / "xdp-utils.c").read_text()
    match = re.search(r"gboolean\n" + name + r" \(.*?\n\}", text, re.DOTALL)
    if match is None:
        raise RuntimeError("Upstream pidns function changed; review the harness")
    caller = (source / "xdp-app-info.c").read_text()
    assert f"{name} (priv->pidfd, &ns, error)" in caller
    if not baseline:
        assert "#define PIDFD_GET_PID_NAMESPACE _IO(PIDFS_IOCTL_MAGIC, 5)" in text
    harness = (HERE / "portal-pidns-test.c").read_text().replace(
        "/* UPSTREAM_FUNCTION */", match.group()
    )
    target = root / ("baseline" if baseline else "fixed")
    c_file = target.with_suffix(".c")
    c_file.write_text(harness)
    subprocess.run(
        [
            "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
            f"-DBASELINE={int(baseline)}", f"-Dquery={name}",
            str(c_file), "-o", str(target),
        ],
        check=True,
        timeout=10,
    )
    subprocess.run([str(target)], check=True, timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="portal-pidns-", dir="/tmp/opencode") as d:
        root = Path(d)
        if args.baseline:
            exercise(args.baseline, root, baseline=True)
        exercise(args.source, root)


if __name__ == "__main__":
    main()
