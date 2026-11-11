"""Compile actual NVIDIA config-open/probe functions with contract stubs.

No kernel/module build, device access, live tracing or driver operation. The
filesystem and worker model are mocks, NOT a native Linux nullfs/probe test.
--check-upstream runs the same fixed contract without applying our patch.
"""

import argparse
import itertools
from pathlib import Path
import re
import resource
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
FILES = ["kernel-open/nvidia/nv-pci.c", "kernel-open/nvidia/nvidia.Kbuild"]


def function(source, name):
    match = re.search(
        rf"(?:static (?:void|int)\s+){name}\s*\([^{{]*?\n\{{.*?\n\}}",
        source,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError(f"{name} changed; review extraction/contract")
    return match.group()


def exercise(root, fixed):
    source = (root / FILES[0]).read_text()
    functions = "\n\n".join(
        function(source, name)
        for name in ("nv_get_pci_sysfs_config", "nv_pci_probe")
    )
    if fixed:
        kbuild = (root / FILES[1]).read_text()
        for kind in ("present", "gpl"):
            assert f"is_export_symbol_{kind}_userspace_init_fs" in kbuild
        assert "#if NV_CHECK_EXPORT_SYMBOL(userspace_init_fs)\n#include <linux/fs_struct.h>" in source
    harness = (HERE / "nvidia-init-root-test.c").read_text().replace(
        "/* ACTUAL_FUNCTIONS */", functions
    )
    c_file = root / "contract.c"
    c_file.write_text(harness)
    for export, asynchronous, seq in itertools.product((0, 1), repeat=3):
        binary = root / "contract"
        subprocess.run(
            [
                "cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                "-Wno-sign-compare", f"-DEXPECT_FIXED={int(fixed)}",
                f"-DEXPORT_INIT_FS={export}",
                f"-DNV_PCI_ASYNC_PROBE_SUPPORTED={asynchronous}",
                *(["-DNV_SEQ_READ_ITER_PRESENT"] if seq else []),
                str(c_file), "-o", str(binary),
            ],
            check=True, timeout=10,
        )
        subprocess.run([str(binary)], check=True, timeout=5)
    print(f"{'fixed' if fixed else 'baseline'}: 8 compile variants, open/cleanup/probe cases pass")


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="unmodified NVIDIA source root")
    parser.add_argument("--check-upstream", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="nvidia-contract-", dir="/tmp/opencode") as d:
        root = Path(d)
        for name in FILES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((args.source / name).read_bytes())
        if args.check_upstream:
            exercise(root, True)
            return
        exercise(root, False)
        result = subprocess.run(
            ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-i",
             str(HERE.parent / "nvidia-init-root.patch")],
            cwd=root, check=True, capture_output=True, text=True, timeout=5,
        )
        assert "offset" not in result.stdout, result.stdout
        exercise(root, True)


if __name__ == "__main__":
    main()
