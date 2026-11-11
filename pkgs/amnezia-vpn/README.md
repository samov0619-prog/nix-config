# Local AmneziaVPN Linux fixes

The client stays pinned to 5.0.1.5 with its matching AWG 3.1 backend.
`default.nix` also retains the dual-stack client-address and empty-DNS fixes.

## Split-tunnel routes

`linux-routing.patch` replaces Linux gateway discovery with
`linux-default-route.h` and fixes a dangling `qPrintable()` pointer in
`buildAllowedIp()`, which is shared by tunnel and exclusion routes.

Upstream gateway discovery accumulates a whole netlink dump into 8192 bytes,
does not initialize `timeval.tv_usec`, and leaks its socket on early errors.
Large routing tables can therefore prevent exclusions from being installed,
even though the ordinary default gateway exists. The replacement reads each
datagram at its actual size, consumes multipart replies through `NLMSG_DONE`,
rejects incomplete/interrupted/error replies, and closes the socket on every
exit path. It selects the lowest-metric main-table IPv4 default route, rather
than an arbitrary route with a gateway. VPN `/1` and host routes are ignored.

This helper supports the single-next-hop IPv4 default routes used by these
hosts. It does not add multipath routing or IPv6 split-tunneling support.
Recheck the fixes and tests against upstream when changing the client pin.

## Automated checks

The package's `checkPhase` runs `tests/test_linux_routing.py`. It compiles the real
gateway helper and extracts `buildAllowedIp()` verbatim from the patched
source, using the real upstream `IPAddress` implementation. ASan/UBSan cover
IPv4/IPv6 prefix conversion and the former temporary-string lifetime bug.
The lifetime test also reads the libc input through an instrumented linker
wrapper: the unpatched function fails with `heap-use-after-free`. Fortify is
disabled only for this test executable so it cannot bypass that wrapper.

Netlink fixtures use local datagram sockets and never install routes. They
cover a multipart dump exceeding 8 KiB, a single datagram exceeding 8 KiB,
`NLMSG_DONE` in the same datagram as routes, gateway/metric/table/family
selection, unrelated replies, malformed messages, errors and timeout.

Build the actual package without activation:

```fish
nix build --no-link .#nixosConfigurations.laptop.pkgs.amnezia-vpn
```

An optional standalone read-only kernel check requires a C++ compiler:

```fish
g++ -std=c++17 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -I pkgs/amnezia-vpn pkgs/amnezia-vpn/tests/test_linux_routing.cpp -o /tmp/amnezia-routing-tests
/tmp/amnezia-routing-tests --live
```

It runs the gateway fixtures and 201 queries to the real kernel. It does not
run the Qt prefix tests; those run during the package build.

## Startup and sleep network readiness

`linux-network-readiness.patch` is a local Linux client fix, not a Lenovo quirk
or an upstream backport. It belongs to the shared package used by NixOS
`laptop`, `laptop-old` and `desktop`. The 5.0.1.5 pin, AWG 3.1 backend, DNS,
split-route and client-address fixes remain unchanged. No new service, boot
ordering override, fixed sleep, connectivity probe or VPN restart hook is added.

The original watcher treats NetworkManager's ASLEEP state as a wakeup and starts
reconnecting before processes freeze. Later network-ready signals are ignored
while the client is already Connecting/Reconnecting. An early startup attempt can
also install tunnel routes before its physical endpoint escape route exists.
The captured Lenovo boot/resume timelines match these paths. Upstream reports
[3037](https://github.com/amnezia-vpn/amnezia-client/issues/3037) and
[3110](https://github.com/amnezia-vpn/amnezia-client/issues/3110) describe the
startup route race and unnecessary reconnects; the two originally affected files
are unchanged in 5.0.3.0, which also has the separately documented IPv4 regression.

The patch forwards raw NM states over the existing local IPC and provides an
initial-state RPC for clients opened after networking is ready. Subscription and
the initial NM state read precede Wi-Fi enumeration, so wired-only hosts work too.
Connection intent is separate from protocol status: the first start, including
DNS resolution and protocol setup, waits for NM state SITE (60) or GLOBAL (70).
SITE is sufficient; requiring a successful Internet probe can deadlock with a
VPN/kill switch. A genuine unavailable-to-ready cycle allows one recovery from
Connected, Connecting or Reconnecting. SITE/GLOBAL reclassification alone does
not tear down a healthy tunnel. Disconnect cancels pending work; queued callbacks
recheck intent/readiness, and newer state signals supersede stale initial replies.
Signals from a retired protocol cannot cancel a replacement request.

Without NetworkManager, or when the IPC source cannot initially be acquired, the
client retains the upstream connection path rather than waiting indefinitely.
This is not a new generic network monitor for non-NM hosts. It does not detect
every possible route/address change while NM remains continuously ready, or prove
server reachability. Kill-switch enforcement/leak protection still requires real
integration acceptance; these tests do not establish it.

The package also runs `tests/test_linux_network.py` in `checkPhase`. It compiles actual
patched watcher/connection methods with real Qt events and native local QtRO
readiness RPC/signals. Protocol/backend operations, DNS, repository access and
route side effects are doubles; it is not the complete GUI/helper. Fixtures cover
early/late startup, sleep, interrupted Connecting/Reconnecting, event coalescing,
SITE/GLOBAL transitions, cancellation, replacement requests, stale replies,
non-network errors and absent NM. `--worker-baseline` against original 5.0.1.5
explicitly detects the ASLEEP-to-wakeup bug. The small tests pass locally, as do
the existing routing ASan/UBSan fixtures. The harness uses `-O1` to preserve Nix's
Fortify hardening with `-Werror`; a local compile control reproduced the old `-O0`
failure and the full native fixture passed with explicit `_FORTIFY_SOURCE=3`.

On 11 November the user built/applied the changes on Lenovo and accepted immediate
autoconnect after reboot and quick automatic recovery after Hibernate, without
manual Connect. A read-only fresh-boot check confirms matching new GUI/helper
store paths. This is user acceptance of those two scenarios, not independent
agent VPN/DNS/egress, split-routing, cancellation or kill-switch/leak testing,
repeated-cycle coverage, or acceptance on Acer/desktop. Exact scope and private
journal references are in [the boot audit](../../hosts/laptop/boot-errors.md).

Selected package declarations for all three hosts pass without a build:

```fish
nix eval --impure --offline --json --option allow-import-from-derivation false --file pkgs/amnezia-vpn/tests/test-network-declarations.nix
```

On pin updates, retain the event scenarios and review equivalent upstream behavior
before removing this patch/helper. A patch conflict is not proof of a fix. The
IPC schema changes, so the GUI and system helper must come from the same package;
fully exit and reopen the GUI after applying NixOS, not just disconnect the VPN.

### Apply and accept network readiness

1. Review/include the new files in the Git flake, then run the package-only build
   above for the affected host. Builds and activation remain user-run operations.
2. With a local console available, finish SSH/transfers and fully exit Amnezia.
   Apply NixOS on the chosen host, for example
   `sudo nixos-rebuild switch --flake .#laptop`, then reopen the client. No HM
   update is needed. Review the whole pending system diff first: Lenovo also has
   a separate PipeWire fix, not an Amnezia dependency.
3. On a normal boot, expect autoconnect without manual recovery. If the physical
   network is delayed, expect Connecting until it becomes ready, then one start,
   not repeated teardown on SITE/GLOBAL changes. Check endpoint escape routing,
   fresh HTTPS, expected egress and ordinary/VPN DNS, not just the status label.
4. After saving work, repeat manual Hibernate. Expect restored session and VPN
   recovery after the physical network returns, with no pre-sleep reconnect.
   Also cancel while waiting: later network recovery must not turn the VPN on.
5. Recheck both split modes below and any enabled kill-switch policy, including
   leak protection during network loss/recovery. Keep full logs private. A real
   discharge-to-critical action and other hosts are separate acceptance scenarios.

## Manual validation after applying NixOS

Fully exit AmneziaVPN through its tray menu, apply the NixOS configuration,
then reopen it. Change split settings while disconnected. Check each mode
with a fresh connection, and repeat after disconnect/reconnect:

1. **All except listed:** listed Ozon/Yandex IPv4 addresses must route through
   the physical interface and ordinary gateway; a public address outside the
   list must route through `amn0`.
2. **Only listed:** an IPv4 address in this mode's list must route through
   `amn0`; an address outside the list must use the physical interface.
3. **Disconnected:** public destinations must again use the ordinary gateway.

Use `ip -4 route get <address>` for route checks. A browser page loading, or
the client's Connected status, does not establish that split routing works.
After route checks pass, verify fresh browser requests and their public IPs.
An Ozon `403` alone does not establish which route was used.
