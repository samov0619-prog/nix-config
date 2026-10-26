#!/usr/bin/env python3
"""Compile real routing code with ASan/UBSan; never change system routes."""

import argparse
import os
from pathlib import Path
import shlex
import subprocess


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True, help="unpacked, patched Amnezia source")
parser.add_argument("--build", type=Path, required=True, help="existing directory for test artifacts")
parser.add_argument("--live", action="store_true", help="also query the host kernel, read-only")
args = parser.parse_args()
source = args.source.resolve()
build = args.build.resolve()
monitor = (source / "client/platforms/linux/daemon/linuxroutemonitor.cpp").read_text()
# Compile the actual function and struct, not a copy of their implementation.
struct_start = monitor.index("typedef struct wg_allowedip {")
struct_end = monitor.index("} wg_allowedip;", struct_start) + len("} wg_allowedip;")
function_start = monitor.rindex("static bool buildAllowedIp(")
(build / "route-prefix-under-test.h").write_text(
    monitor[struct_start:struct_end] + "\n" + monitor[function_start:]
)
flags = shlex.split(subprocess.check_output(
    ["pkg-config", "--cflags", "--libs", "Qt6Core", "Qt6Network"], text=True
))
# Only the test executable: make inet_pton go through the instrumented wrapper
# rather than glibc's uninstrumented fortified entry point. Keep package
# hardening unchanged.
compiler_env = os.environ.copy()
if "NIX_HARDENING_ENABLE" in compiler_env:
    compiler_env["NIX_HARDENING_ENABLE"] = " ".join(
        flag for flag in compiler_env["NIX_HARDENING_ENABLE"].split()
        if not flag.startswith("fortify")
    )
subprocess.run([
    os.environ.get("CXX", "c++"), "-std=c++17", "-g", "-O1",
    "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
    "-fno-omit-frame-pointer", "-DTEST_ROUTE_PREFIX", "-Wl,--wrap=inet_pton",
    # Test-only: prevent glibc fortify from redirecting past the ASan wrapper.
    "-U_FORTIFY_SOURCE",
    "-I", str(build), "-I", str(source / "client/core/utils"),
    "-I", str(source / "client/mozilla/shared"),
    str(Path(__file__).with_suffix(".cpp")),
    str(source / "client/mozilla/shared/ipaddress.cpp"),
    *flags, "-o", str(build / "test-linux-routing"),
], check=True, env=compiler_env)
subprocess.run([str(build / "test-linux-routing"), *(["--live"] if args.live else [])], check=True)
