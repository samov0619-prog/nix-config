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

The package's `checkPhase` runs `test_linux_routing.py`. It compiles the real
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
g++ -std=c++17 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -I pkgs/amnezia-vpn pkgs/amnezia-vpn/test_linux_routing.cpp -o /tmp/amnezia-routing-tests
/tmp/amnezia-routing-tests --live
```

It runs the gateway fixtures and 201 queries to the real kernel. It does not
run the Qt prefix tests; those run during the package build.

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
