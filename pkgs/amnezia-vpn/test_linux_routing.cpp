#include "linux-default-route.h"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

#ifdef TEST_ROUTE_PREFIX
#include <QByteArray>
#include "ipaddress.h"
// Extracted verbatim from the patched linuxroutemonitor.cpp by the runner.
#include "route-prefix-under-test.h"

// libc's inet_pton is not ASan-instrumented. Read the input in instrumented
// code too, so a dangling QByteArray pointer cannot pass merely because freed
// storage still happens to contain the old text.
extern "C" int __real_inet_pton(int family, const char *text, void *destination);
extern "C" int __wrap_inet_pton(int family, const char *text, void *destination) {
    for (const char *cursor = text; *cursor; ++cursor) {
        volatile char character = *cursor;
        (void)character;
    }
    return __real_inet_pton(family, text, destination);
}
#endif

using namespace AmneziaLinuxRouting;
using Bytes = std::vector<char>;
constexpr uint32_t sequence = 42;
constexpr uint32_t port = 123;

static void require(bool condition, const char *description) {
    if (!condition) throw std::runtime_error(description);
}

static void attribute(Bytes &message, uint16_t type, const void *data, size_t size) {
    const size_t offset = message.size();
    message.resize(offset + RTA_SPACE(size), 0);
    auto *attr = reinterpret_cast<rtattr *>(message.data() + offset);
    attr->rta_type = type;
    attr->rta_len = RTA_LENGTH(size);
    memcpy(RTA_DATA(attr), data, size);
    reinterpret_cast<nlmsghdr *>(message.data())->nlmsg_len = message.size();
}

static Bytes route(const char *gateway = "192.168.0.1", unsigned index = 3,
                   uint32_t metric = 600, uint8_t prefix = 0,
                   uint32_t table = RT_TABLE_MAIN, uint8_t family = AF_INET) {
    Bytes message(NLMSG_SPACE(sizeof(rtmsg)), 0);
    auto *header = reinterpret_cast<nlmsghdr *>(message.data());
    header->nlmsg_len = message.size();
    header->nlmsg_type = RTM_NEWROUTE;
    header->nlmsg_flags = NLM_F_MULTI;
    header->nlmsg_seq = sequence;
    header->nlmsg_pid = port;
    auto *entry = static_cast<rtmsg *>(NLMSG_DATA(header));
    entry->rtm_family = family;
    entry->rtm_dst_len = prefix;
    entry->rtm_table = RT_TABLE_UNSPEC; // Exercise RTA_TABLE too.
    entry->rtm_type = RTN_UNICAST;
    in_addr address {};
    require(inet_pton(AF_INET, gateway, &address) == 1, "fixture gateway");
    attribute(message, RTA_GATEWAY, &address, sizeof(address));
    attribute(message, RTA_OIF, &index, sizeof(index));
    attribute(message, RTA_PRIORITY, &metric, sizeof(metric));
    attribute(message, RTA_TABLE, &table, sizeof(table));
    return message;
}

static Bytes control(uint16_t type = NLMSG_DONE, int error = 0) {
    const size_t payload = type == NLMSG_ERROR ? sizeof(nlmsgerr) : sizeof(error);
    Bytes message(NLMSG_SPACE(payload), 0);
    auto *header = reinterpret_cast<nlmsghdr *>(message.data());
    header->nlmsg_len = message.size();
    header->nlmsg_type = type;
    header->nlmsg_flags = NLM_F_MULTI;
    header->nlmsg_seq = sequence;
    header->nlmsg_pid = port;
    memcpy(NLMSG_DATA(header), &error, sizeof(error));
    return message;
}

static void append(Bytes &dump, const Bytes &message) {
    dump.insert(dump.end(), message.begin(), message.end());
}

static DefaultRoute readFixture(const std::vector<Bytes> &datagrams) {
    int sockets[2];
    require(socketpair(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0, sockets) == 0, "socketpair");
    const timeval timeout { 0, 20000 };
    require(setsockopt(sockets[0], SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) == 0,
            "fixture timeout");
    for (const auto &datagram : datagrams) {
        require(send(sockets[1], datagram.data(), datagram.size(), 0) ==
                static_cast<ssize_t>(datagram.size()), "send fixture");
    }
    const auto result = readDefaultRoute(sockets[0], sequence, port);
    close(sockets[0]);
    close(sockets[1]);
    return result;
}

static bool matches(const DefaultRoute &route, const char *gateway, unsigned index) {
    in_addr expected {};
    inet_pton(AF_INET, gateway, &expected);
    return route && route.gateway.s_addr == expected.s_addr && route.interfaceIndex == index;
}

static void fixtureTests() {
    require(matches(readFixture({route(), control()}), "192.168.0.1", 3), "small multipart dump");

    Bytes first, second;
    for (int i = 0; i < 100; ++i) append(first, route("10.0.0.1", 8, 0, 32));
    for (int i = 0; i < 100; ++i) append(second, route("10.0.0.1", 8, 0, 24));
    append(second, route());
    require(first.size() + second.size() > 8192, "large fixture size");
    require(matches(readFixture({first, second, control()}), "192.168.0.1", 3),
            "multipart dump larger than 8 KiB, default route last");

    Bytes single = first;
    append(single, second);
    append(single, control());
    require(single.size() > 8192, "large datagram size");
    require(matches(readFixture({single}), "192.168.0.1", 3),
            "single datagram larger than 8 KiB with embedded DONE");

    Bytes candidates;
    append(candidates, route("10.0.0.1", 8, 0, 1)); // VPN /1 is not default.
    append(candidates, route("10.0.0.2", 8, 0, 0, 100));
    append(candidates, route("10.0.0.3", 8, 0, 0, RT_TABLE_MAIN, AF_INET6));
    append(candidates, route("10.0.0.4", 8, 0, 32));
    append(candidates, route("192.168.1.1", 4, 700));
    append(candidates, route());
    append(candidates, route("192.168.2.1", 5, 800));
    append(candidates, control());
    require(matches(readFixture({candidates}), "192.168.0.1", 3),
            "only main IPv4 default route, lowest metric");

    auto wrongSequence = route("10.0.0.1");
    reinterpret_cast<nlmsghdr *>(wrongSequence.data())->nlmsg_seq++;
    auto wrongPort = route("10.0.0.2");
    reinterpret_cast<nlmsghdr *>(wrongPort.data())->nlmsg_pid++;
    require(matches(readFixture({wrongSequence, wrongPort, route(), control()}), "192.168.0.1", 3),
            "ignore unrelated netlink messages");
    require(!readFixture({control()}), "empty table");
    require(!readFixture({route("0.0.0.0"), control()}), "missing gateway");
    require(!readFixture({route("192.168.0.1", 0), control()}), "missing interface");
    require(!readFixture({route(), control(NLMSG_ERROR, -EPERM)}), "netlink error discards partial result");
    require(!readFixture({route(), control(NLMSG_DONE, -EINTR)}), "DONE error discards partial result");
    require(matches(readFixture({control(NLMSG_ERROR, 0), route(), control()}), "192.168.0.1", 3),
            "zero-error ACK is not end of dump");

    auto interrupted = control();
    reinterpret_cast<nlmsghdr *>(interrupted.data())->nlmsg_flags |= NLM_F_DUMP_INTR;
    require(!readFixture({route(), interrupted}), "interrupted dump discards partial result");
    require(!readFixture({route(), control(NLMSG_OVERRUN)}), "overrun discards partial result");
    require(!readFixture({route()}), "missing DONE times out without a partial result");

    auto truncated = route();
    truncated.resize(truncated.size() - 1);
    require(!readFixture({truncated, control()}), "truncated message");
    auto malformed = route();
    auto *entry = static_cast<rtmsg *>(NLMSG_DATA(reinterpret_cast<nlmsghdr *>(malformed.data())));
    RTM_RTA(entry)->rta_len = 3;
    require(!readFixture({malformed, control()}), "malformed route attribute");
    std::cout << "PASS: netlink fixtures (large multipart/single datagrams, selection, errors, timeout)\n";
}

#ifdef TEST_ROUTE_PREFIX
static void prefixTests() {
    for (int i = 0; i < 1000; ++i) {
        wg_allowedip parsed {};
        IPAddress ipv4(QStringLiteral("185.73.193.0/24"));
        require(buildAllowedIp(&parsed, ipv4), "IPv4 prefix conversion");
        require(parsed.family == AF_INET && parsed.cidr == 24, "IPv4 prefix fields");
        in_addr expected4 {};
        inet_pton(AF_INET, "185.73.193.0", &expected4);
        require(memcmp(&parsed.ip4, &expected4, sizeof(expected4)) == 0, "IPv4 prefix bytes");
        IPAddress ipv6(QStringLiteral("2001:db8:1234:5678:9abc:def0:1234:5678/128"));
        require(buildAllowedIp(&parsed, ipv6), "IPv6 prefix conversion");
        require(parsed.family == AF_INET6 && parsed.cidr == 128, "IPv6 prefix fields");
        in6_addr expected6 {};
        inet_pton(AF_INET6, "2001:db8:1234:5678:9abc:def0:1234:5678", &expected6);
        require(memcmp(&parsed.ip6, &expected6, sizeof(expected6)) == 0, "IPv6 prefix bytes");
        require(!buildAllowedIp(&parsed, IPAddress(QStringLiteral(""))), "invalid prefix rejected");
    }
    std::cout << "PASS: actual buildAllowedIp under ASan/UBSan (IPv4/IPv6/invalid)\n";
}
#endif

int main(int argc, char **argv) {
    try {
        fixtureTests();
#ifdef TEST_ROUTE_PREFIX
        prefixTests();
#endif
        if (argc > 1 && std::string(argv[1]) == "--live") {
            const auto route = defaultRoute();
            require(static_cast<bool>(route), "live default route discovery");
            char gateway[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &route.gateway, gateway, sizeof(gateway));
            for (int i = 0; i < 200; ++i) {
                const auto again = defaultRoute();
                require(again && again.gateway.s_addr == route.gateway.s_addr &&
                        again.interfaceIndex == route.interfaceIndex, "repeated live discovery");
            }
            std::cout << "PASS: 201 read-only kernel queries; gateway=" << gateway
                      << " interface_index=" << route.interfaceIndex << '\n';
        }
        return EXIT_SUCCESS;
    } catch (const std::exception &error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
