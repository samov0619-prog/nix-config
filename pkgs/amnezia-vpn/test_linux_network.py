"""Exercise patched connection methods with real Qt events and local QtRO IPC.

Protocol operations, repositories, DNS and routing are test doubles. No live
NetworkManager, logind, tunnel, external server or installed service is used.
"""

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess


HERE = Path(__file__).resolve().parent


def function(source, name):
    match = re.search(
        r"(?:void|ErrorCode) " + re.escape(name) + r"\([^\n]*\)\s*\{.*?\n\}",
        source,
        re.DOTALL,
    )
    if match is None:
        raise RuntimeError(f"Upstream {name} changed; review the harness")
    return match.group()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--moc", default="moc")
    parser.add_argument("--repc", default="repc")
    parser.add_argument("--worker-baseline", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    build = args.build.resolve()
    worker = (source / "client/platforms/linux/linuxnetworkwatcherworker.cpp").read_text()
    methods = function(worker, "LinuxNetworkWatcherWorker::NMStateChanged")
    if not args.worker_baseline:
        assert (source / "client/linux-connection-state.h").read_bytes() == (
            HERE / "linux-connection-state.h"
        ).read_bytes()
        vpn = (source / "client/vpnConnection.cpp").read_text()
        names = [
            "connectToVpn",
            "monitorLinuxNetwork",
            "queryLinuxNetwork",
            "linuxNetworkChanged",
            "resumeLinuxConnection",
            "startVpnConnection",
            "createProtocolConnections",
            "reconnectToVpn",
            "disconnectFromVpn",
            "setConnectionState",
        ]
        methods += "\n" + "\n".join(function(vpn, "VpnConnection::" + n) for n in names)
        # Readiness must be available on wired-only hosts and after late UI startup.
        assert worker.index('nm.property("State")') < worker.index('nm.call("GetDevices")')
        assert worker.index('"StateChanged"') < worker.index('nm.property("State")')
        for path, fragment in [
            ("client/platforms/linux/linuxnetworkwatcher.cpp", "&NetworkWatcherImpl::linuxNetworkStateChanged"),
            ("client/mozilla/networkwatcher.cpp", "&NetworkWatcher::linuxNetworkStateChanged"),
            ("service/server/localserver.cpp", "&IpcServer::setLinuxNetworkState"),
            ("ipc/ipcserver.h", "int linuxNetworkState() override { return m_linuxNetworkState; }"),
        ]:
            assert fragment in (source / path).read_text(), path
        rep = (source / "ipc/ipc_interface.rep").read_text()
        declarations = [
            "SLOT( int linuxNetworkState() );",
            "SIGNAL( linuxNetworkStateChanged(int state) );",
        ]
        assert all(d in rep for d in declarations)
        # Generate the real readiness subset of the changed IPC schema. Other
        # upstream RPCs are outside this unit harness, not silently mocked here.
        rep_file = build / "network.rep"
        rep_file.write_text("class IpcInterface\n{\n" + "\n".join(declarations) + "\n};\n")
        for kind in ["replica", "source"]:
            subprocess.run(
                [args.repc, "-i", "rep", "-o", kind, str(rep_file), str(build / f"rep_network_{kind}.h")],
                check=True,
                timeout=10,
            )
    (build / "network-methods.h").write_text(methods + "\n")
    harness = HERE / "test_linux_network.cpp"
    flags = shlex.split(subprocess.check_output(
        ["pkg-config", "--cflags", "--libs", "Qt6Core", "Qt6Network", "Qt6RemoteObjects"], text=True
    ))
    defines = ["-DAMNEZIA_DESKTOP"]
    if args.worker_baseline:
        defines.append("-DWORKER_BASELINE")
    subprocess.run(
        [args.moc, *defines, "-I", str(build), *[f for f in flags if f.startswith("-I")], str(harness), "-o", str(build / "network-harness.moc")],
        check=True,
        timeout=10,
    )
    moc_files = []
    if not args.worker_baseline:
        for kind in ["replica", "source"]:
            moc_file = build / f"moc_{kind}.cpp"
            subprocess.run(
                [args.moc, *[f for f in flags if f.startswith("-I")], str(build / f"rep_network_{kind}.h"), "-o", str(moc_file)],
                check=True,
                timeout=10,
            )
            moc_files.append(str(moc_file))
    binary = build / "test-linux-network"
    # Nix enables Fortify: keep optimization rather than disabling hardening.
    subprocess.run(
        [os.environ.get("CXX", "c++"), "-std=c++17", "-O1", "-g", "-Wall", "-Wextra", "-Werror", *defines,
         "-I", str(build), "-I", str(HERE), str(harness), *moc_files, *flags, "-o", str(binary)],
        check=True,
        timeout=45,
    )
    subprocess.run([str(binary)], check=True, timeout=15)


if __name__ == "__main__":
    main()
