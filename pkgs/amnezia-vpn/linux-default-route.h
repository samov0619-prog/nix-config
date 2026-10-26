// Linux IPv4 default-route discovery for AmneziaVPN 5.0.1.5.
// Keep each netlink datagram separate: a route dump has no fixed total size.
#pragma once

#include <arpa/inet.h>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <limits>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <sys/socket.h>
#include <unistd.h>
#include <vector>

namespace AmneziaLinuxRouting {

struct DefaultRoute {
    in_addr gateway {};
    unsigned int interfaceIndex = 0;
    uint32_t metric = std::numeric_limits<uint32_t>::max();

    explicit operator bool() const {
        return gateway.s_addr != 0 && interfaceIndex != 0;
    }
};

// Also used by the regression harness with datagram sockets. The caller owns
// the socket and must set a receive timeout. Never return a partial dump.
inline DefaultRoute readDefaultRoute(int sock, uint32_t sequence, uint32_t portId) {
    DefaultRoute best;
    for (;;) {
        ssize_t size;
        do {
            size = recv(sock, nullptr, 0, MSG_PEEK | MSG_TRUNC);
        } while (size < 0 && errno == EINTR);
        if (size <= 0 || size > std::numeric_limits<int>::max()) {
            return {};
        }

        std::vector<char> buffer(static_cast<size_t>(size));
        iovec iov { buffer.data(), buffer.size() };
        msghdr message {};
        message.msg_iov = &iov;
        message.msg_iovlen = 1;
        ssize_t received;
        do {
            received = recvmsg(sock, &message, 0);
        } while (received < 0 && errno == EINTR);
        if (received != size || (message.msg_flags & MSG_TRUNC)) {
            return {};
        }

        int remaining = static_cast<int>(received);
        auto *header = reinterpret_cast<nlmsghdr *>(buffer.data());
        for (; NLMSG_OK(header, remaining); header = NLMSG_NEXT(header, remaining)) {
            if (header->nlmsg_seq != sequence || header->nlmsg_pid != portId) {
                continue;
            }
            if (header->nlmsg_flags & NLM_F_DUMP_INTR) {
                return {};
            }
            if (header->nlmsg_type == NLMSG_DONE) {
                // Modern kernels include an error code in NLMSG_DONE.
                const auto payload = NLMSG_PAYLOAD(header, 0);
                if (payload != 0) {
                    int error;
                    if (payload < sizeof(error)) {
                        return {};
                    }
                    memcpy(&error, NLMSG_DATA(header), sizeof(error));
                    if (error != 0) {
                        return {};
                    }
                }
                return best;
            }
            if (header->nlmsg_type == NLMSG_ERROR) {
                if (NLMSG_PAYLOAD(header, 0) < sizeof(nlmsgerr)) {
                    return {};
                }
                const auto *error = static_cast<const nlmsgerr *>(NLMSG_DATA(header));
                if (error->error != 0) {
                    return {};
                }
                continue;
            }
            if (header->nlmsg_type == NLMSG_OVERRUN) {
                return {};
            }
            if (header->nlmsg_type != RTM_NEWROUTE) {
                continue;
            }
            if (NLMSG_PAYLOAD(header, 0) < sizeof(rtmsg)) {
                return {};
            }
            const auto *route = static_cast<const rtmsg *>(NLMSG_DATA(header));
            // Ignore VPN /1 routes, host routes, IPv6, and non-default tables.
            if (route->rtm_family != AF_INET || route->rtm_dst_len != 0 ||
                route->rtm_src_len != 0 || route->rtm_tos != 0 ||
                route->rtm_type != RTN_UNICAST) {
                continue;
            }

            DefaultRoute candidate;
            candidate.metric = 0;
            uint32_t table = route->rtm_table;
            int attributesLeft = RTM_PAYLOAD(header);
            auto *attribute = RTM_RTA(route);
            for (; RTA_OK(attribute, attributesLeft);
                 attribute = RTA_NEXT(attribute, attributesLeft)) {
                switch (attribute->rta_type) {
                case RTA_GATEWAY:
                    if (RTA_PAYLOAD(attribute) != sizeof(candidate.gateway)) return {};
                    memcpy(&candidate.gateway, RTA_DATA(attribute), sizeof(candidate.gateway));
                    break;
                case RTA_OIF:
                    if (RTA_PAYLOAD(attribute) != sizeof(candidate.interfaceIndex)) return {};
                    memcpy(&candidate.interfaceIndex, RTA_DATA(attribute), sizeof(candidate.interfaceIndex));
                    break;
                case RTA_PRIORITY:
                    if (RTA_PAYLOAD(attribute) != sizeof(candidate.metric)) return {};
                    memcpy(&candidate.metric, RTA_DATA(attribute), sizeof(candidate.metric));
                    break;
                case RTA_TABLE:
                    if (RTA_PAYLOAD(attribute) != sizeof(table)) return {};
                    memcpy(&table, RTA_DATA(attribute), sizeof(table));
                    break;
                default:
                    break;
                }
            }
            if (attributesLeft != 0) {
                return {};
            }
            if (table == RT_TABLE_MAIN && candidate &&
                (!best || candidate.metric < best.metric)) {
                best = candidate;
            }
        }
        if (remaining != 0) {
            return {};
        }
    }
}

inline DefaultRoute defaultRoute() {
    struct Socket {
        int fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_ROUTE);
        ~Socket() { if (fd >= 0) close(fd); }
    } sock;
    if (sock.fd < 0) {
        return {};
    }
    // Initialize both fields; the old code left tv_usec indeterminate.
    const timeval timeout { 1, 0 };
    if (setsockopt(sock.fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0) {
        return {};
    }
    sockaddr_nl local {};
    local.nl_family = AF_NETLINK;
    if (bind(sock.fd, reinterpret_cast<sockaddr *>(&local), sizeof(local)) < 0) {
        return {};
    }
    socklen_t length = sizeof(local);
    if (getsockname(sock.fd, reinterpret_cast<sockaddr *>(&local), &length) < 0) {
        return {};
    }
    sockaddr_nl kernel {};
    kernel.nl_family = AF_NETLINK;
    if (connect(sock.fd, reinterpret_cast<sockaddr *>(&kernel), sizeof(kernel)) < 0) {
        return {};
    }
    struct {
        nlmsghdr header;
        rtmsg route;
    } request {};
    request.header.nlmsg_len = NLMSG_LENGTH(sizeof(rtmsg));
    request.header.nlmsg_type = RTM_GETROUTE;
    request.header.nlmsg_flags = NLM_F_REQUEST | NLM_F_DUMP;
    request.header.nlmsg_seq = 1;
    request.header.nlmsg_pid = local.nl_pid;
    request.route.rtm_family = AF_INET;
    ssize_t sent;
    do {
        sent = send(sock.fd, &request, request.header.nlmsg_len, 0);
    } while (sent < 0 && errno == EINTR);
    if (sent != request.header.nlmsg_len) {
        return {};
    }
    return readDefaultRoute(sock.fd, request.header.nlmsg_seq, local.nl_pid);
}

} // namespace AmneziaLinuxRouting
