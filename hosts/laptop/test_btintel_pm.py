"""Exercise actual btintel_pcie PM/D-state functions with contract stubs.

Input: unpatched Linux source directory containing drivers/bluetooth/btintel_pcie.*.
Default: reproduce the baseline defects, apply both backports with zero fuzz,
then require fixed behavior. --check-upstream requires fixed behavior WITHOUT
applying patches, for explicit update/removal review. No kernel build or devices.
"""

import argparse
from pathlib import Path
import re
import resource
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
PATCHES = ("btintel-pcie-refresh-dstate.patch", "btintel-pcie-pm-flow.patch")


def function(source, name):
    match = re.search(
        rf"static (?:inline )?[^\n]+\b{re.escape(name)}\([^;]*?\)\n\{{.*?\n\}}",
        source,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError(f"Upstream {name} changed; review the harness")
    return match.group()


def exercise(source, header, root, name, fixed):
    table = re.search(
        r"static const struct dev_pm_ops btintel_pcie_pm_ops = \{.*?\n\};",
        source,
        re.DOTALL,
    )
    states = re.search(
        r"enum \{\n\s*BTINTEL_PCIE_STATE_D0 = 0,.*?\n\};", header, re.DOTALL
    )
    d3 = re.search(r"^#define BTINTEL_PCIE_CSR_BOOT_STAGE_D3_STATE_READY[^\n]+", header, re.M)
    if table is None or states is None or d3 is None:
        raise RuntimeError("Upstream PM table/state definitions changed; review the harness")
    if fixed and "pm_sx_event" in header:
        raise RuntimeError("Obsolete saved PM event remains; review upstream before removal")
    callbacks = [
        "btintel_pcie_suspend_late",
        "btintel_pcie_suspend",
        "btintel_pcie_hibernate",
        "btintel_pcie_freeze",
    ]
    if fixed:
        callbacks.append("btintel_pcie_resume_event")
    callbacks.append("btintel_pcie_resume")
    if fixed:
        callbacks.extend(("btintel_pcie_restore", "btintel_pcie_thaw"))
    harness = (HERE / "btintel-pm-test.c").read_text()
    harness = harness.replace("/* UPSTREAM_STATE_DEFINITIONS */", states[0] + "\n" + d3[0])
    harness = harness.replace(
        "/* UPSTREAM_DSTATE_FUNCTIONS */",
        "\n\n".join(
            function(source, name)
            for name in (
                "btintel_pcie_in_d0",
                "btintel_pcie_in_d3",
                "btintel_pcie_set_dxstate",
            )
        ),
    )
    harness = harness.replace(
        "/* UPSTREAM_PM_CALLBACKS */",
        "\n\n".join(function(source, name) for name in callbacks) + "\n" + table[0],
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
            f"-DEXPECT_FIXED={int(fixed)}",
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
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    relative = Path("drivers/bluetooth")
    originals = {
        name: (args.source / relative / name).read_text()
        for name in ("btintel_pcie.c", "btintel_pcie.h")
    }
    with tempfile.TemporaryDirectory(prefix="btintel-pm-", dir="/tmp/opencode") as d:
        root = Path(d)
        if args.check_upstream:
            exercise(*originals.values(), root, "upstream-without-patches", True)
            return
        exercise(*originals.values(), root, "baseline", False)
        target = root / relative
        target.mkdir(parents=True)
        for name, text in originals.items():
            (target / name).write_text(text)
        for patch in PATCHES:
            subprocess.run(
                ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-i", str(HERE / patch)],
                cwd=root,
                check=True,
                timeout=5,
            )
        exercise(
            (target / "btintel_pcie.c").read_text(),
            (target / "btintel_pcie.h").read_text(),
            root,
            "patched",
            True,
        )


if __name__ == "__main__":
    main()
