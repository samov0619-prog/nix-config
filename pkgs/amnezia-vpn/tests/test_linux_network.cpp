// Real patched methods and Qt transport; no system networking operations.
#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QElapsedTimer>
#include <QJsonObject>
#include <QSharedPointer>
#include <QTemporaryDir>
#include <QThread>
#include <QTimer>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <functional>
#include <iostream>

struct TestLogger { QDebug debug() { return qDebug(); } };
static TestLogger logger;
enum NMState { NM_STATE_ASLEEP = 10, NM_STATE_DISABLED = 10,
               NM_STATE_CONNECTED_GLOBAL = 70 };

class LinuxNetworkWatcherWorker : public QObject {
    Q_OBJECT
public:
    void NMStateChanged(quint32 state);
signals:
    void wakeup();
    void networkChanged();
    void linuxNetworkStateChanged(int state);
};

#ifndef WORKER_BASELINE
#include <QRemoteObjectHost>
#include <QRemoteObjectNode>
#include <QRemoteObjectPendingCallWatcher>
#include "rep_network_replica.h"
#include "rep_network_source.h"
#include "linux-connection-state.h"

namespace Vpn {
enum ConnectionState { Unknown, Preparing, Connecting, Connected,
                       Disconnecting, Disconnected, Reconnecting, Error };
}
enum class ErrorCode { NoError, Failed };
enum class DockerContainer { Awg };
namespace configKey { const QString hostName = "hostName"; }
namespace ContainerUtils {
QString containerToString(DockerContainer) { return "Awg"; }
}
struct SecureServersRepository {};
struct SecureAppSettingsRepository { int routeMode() { return 0; } };
namespace NetworkUtilities {
static int resolutions = 0;
QString getIPAddress(const QString &host) { ++resolutions; return host; }
}

class VpnProtocol : public QObject {
    Q_OBJECT
public:
    static inline int starts = 0, stops = 0, prepares = 0;
    static inline ErrorCode startResult = ErrorCode::NoError;
    static VpnProtocol *factory(DockerContainer, const QJsonObject &) { return new VpnProtocol; }
    void prepare() { ++prepares; }
    ErrorCode start() { ++starts; return startResult; }
    void stop() { ++stops; emit connectionStateChanged(Vpn::Disconnected); }
signals:
    void protocolError(ErrorCode error);
    void connectionStateChanged(Vpn::ConnectionState state);
    void bytesChanged(quint64 received, quint64 sent);
};

class TestSource : public IpcInterfaceSimpleSource {
public:
    int value = 0;
    int linuxNetworkState() override { return value; }
    void change(int state) { value = state; emit linuxNetworkStateChanged(state); }
};

// Use native local QtRO for the changed RPC/signal. Only acquiring the already
// initialized replica is replaced; no shared production IPC singleton is used.
class IpcClient {
public:
    static inline QSharedPointer<IpcInterfaceReplica> replica;
    template<class Success, class Failure>
    static void withInterface(Success success, Failure failure) {
        if (replica && replica->isInitialized()) success(replica);
        else failure();
    }
};

class VpnConnection : public QObject {
    Q_OBJECT
public:
    SecureServersRepository repositories;
    SecureAppSettingsRepository settings;
    SecureServersRepository *m_serversRepository = &repositories;
    SecureAppSettingsRepository *m_appSettingsRepository = &settings;
    QSharedPointer<VpnProtocol> m_vpnProtocol;
    QJsonObject m_vpnConfiguration;
    QString m_remoteAddress;
    Vpn::ConnectionState m_connectionState = Vpn::Disconnected;
    AmneziaLinuxNetworking::ConnectionState m_linuxConnection;
    std::function<void()> m_linuxStartConnection;
    bool m_linuxNetworkMonitorConnected = false;
    unsigned m_linuxNetworkRevision = 0;
    int killSwitchConfigurations = 0, splitConfigurations = 0;

    void connectToVpn(const QString &, DockerContainer, const QJsonObject &);
    void monitorLinuxNetwork();
    void queryLinuxNetwork(const QSharedPointer<IpcInterfaceReplica> &);
    void linuxNetworkChanged(int);
    void resumeLinuxConnection();
    void startVpnConnection(const QString &, DockerContainer, const QJsonObject &);
    void createProtocolConnections();
    void reconnectToVpn();
    void disconnectFromVpn();
    void setConnectionState(Vpn::ConnectionState);
    void onConnectionStateChanged(Vpn::ConnectionState) {}
    void appendKillSwitchConfig() { ++killSwitchConfigurations; }
    void appendSplitTunnelingConfig() { ++splitConfigurations; }
public slots:
    void onBytesChanged(quint64, quint64) {}
signals:
    void connectionStateChanged(Vpn::ConnectionState state);
    void vpnProtocolError(ErrorCode error);
};
#endif

#include "network-methods.h"
#include "network-harness.moc"

#ifndef WORKER_BASELINE
static void drain()
{
    QElapsedTimer timer;
    timer.start();
    while (timer.elapsed() < 25) {
        QCoreApplication::processEvents();
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
        QThread::msleep(1);
    }
}

static void until(const std::function<bool()> &condition)
{
    QElapsedTimer timer;
    timer.start();
    while (!condition() && timer.elapsed() < 2000) drain();
    assert(condition());
}

static void request(VpnConnection &vpn)
{
    vpn.connectToVpn("fixture", DockerContainer::Awg, {{"hostName", "fixture.invalid"}});
}
#endif

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    LinuxNetworkWatcherWorker worker;
    int wakes = 0, legacy = 0, raw = 0;
    QObject::connect(&worker, &LinuxNetworkWatcherWorker::wakeup, [&] { ++wakes; });
    QObject::connect(&worker, &LinuxNetworkWatcherWorker::networkChanged, [&] { ++legacy; });
    QObject::connect(&worker, &LinuxNetworkWatcherWorker::linuxNetworkStateChanged, [&](int) { ++raw; });
    worker.NMStateChanged(10);
#ifdef WORKER_BASELINE
    assert(wakes == 1 && raw == 0);
    std::cout << "baseline: ASLEEP incorrectly emits wakeup\n";
    return 0;
#else
    worker.NMStateChanged(40);
    worker.NMStateChanged(60);
    worker.NMStateChanged(70);
    assert(wakes == 0 && legacy == 0 && raw == 4);

    QTemporaryDir directory(QDir::tempPath() + "/amnezia-ipc-XXXXXX");
    assert(directory.isValid());
    QUrl url("local:" + directory.path() + "/network");
    QRemoteObjectHost host(url);
    TestSource source;
    assert(host.enableRemoting(&source));
    QRemoteObjectNode node;
    assert(node.connectToNode(url));
    IpcClient::replica.reset(node.acquire<IpcInterfaceReplica>());
    until([] { return IpcClient::replica->isInitialized(); });

    // Cold startup: no DNS, protocol preparation or tunnel until a routed
    // network exists. Initial query and queued signal must not double-start.
    {
        source.value = 40;
        VpnConnection vpn;
        int starts = VpnProtocol::starts, dns = NetworkUtilities::resolutions;
        request(vpn);
        drain();
        assert(vpn.m_linuxConnection.waiting());
        assert(VpnProtocol::starts == starts && NetworkUtilities::resolutions == dns);
        assert(vpn.killSwitchConfigurations == 0 && vpn.splitConfigurations == 0);
        source.change(50); drain();
        assert(VpnProtocol::starts == starts);
        source.change(60); source.change(70);
        until([&] { return VpnProtocol::starts == starts + 1; });
        drain();
        assert(NetworkUtilities::resolutions == dns + 1);
        assert(vpn.killSwitchConfigurations == 1 && vpn.splitConfigurations == 1);
        assert(vpn.m_linuxConnection.ready() && !vpn.m_linuxConnection.waiting());
        source.change(60); source.change(70); drain();
        assert(VpnProtocol::starts == starts + 1 && VpnProtocol::stops == 0);
    }

    // UI started after the network: initial native RPC is enough; no new NM
    // event is required. Sleep must not reconnect until readiness returns.
    {
        source.value = 70;
        VpnConnection vpn;
        int starts = VpnProtocol::starts, stops = VpnProtocol::stops;
        request(vpn);
        until([&] { return VpnProtocol::starts == starts + 1; });
        vpn.setConnectionState(Vpn::Connected);
        source.change(10); drain();
        assert(VpnProtocol::starts == starts + 1 && VpnProtocol::stops == stops);
        source.change(20); source.change(40); source.change(50); drain();
        assert(VpnProtocol::starts == starts + 1);
        source.change(60); source.change(70);
        until([&] { return VpnProtocol::starts == starts + 2; });
        drain();
        assert(VpnProtocol::stops == stops + 1);
        vpn.setConnectionState(Vpn::Connected);
        source.change(60); source.change(70); drain();
        assert(VpnProtocol::starts == starts + 2);
    }

    // Recover interrupted Connecting and already-Reconnecting states too.
    for (auto state : {Vpn::Connecting, Vpn::Reconnecting}) {
        source.value = 70;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn);
        until([&] { return VpnProtocol::starts == starts + 1; });
        vpn.setConnectionState(state);
        source.change(40); drain();
        vpn.setConnectionState(Vpn::Disconnected);
        assert(vpn.m_connectionState == Vpn::Reconnecting);
        source.change(70);
        until([&] { return VpnProtocol::starts == starts + 2; });
        drain();
        assert(VpnProtocol::starts == starts + 2);
    }

    // Cancelling while waiting, including after ready is queued, must not
    // reconnect. An unused client must not turn itself on when the network does.
    {
        source.value = 40;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn); drain();
        vpn.linuxNetworkChanged(70);
        vpn.disconnectFromVpn();
        drain();
        source.change(40); source.change(70); drain();
        assert(VpnProtocol::starts == starts && vpn.m_vpnProtocol.isNull());
    }
    {
        source.value = 70;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn);
        until([&] { return VpnProtocol::starts == starts + 1; });
        source.change(10); drain();
        vpn.disconnectFromVpn();
        source.change(70); drain();
        assert(VpnProtocol::starts == starts + 1);
    }

    // Switching servers must not let a retired protocol's Disconnected cancel
    // the newer request. A later real outage must still recover that request.
    {
        source.value = 70;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn);
        until([&] { return VpnProtocol::starts == starts + 1; });
        vpn.setConnectionState(Vpn::Connected);
        vpn.connectToVpn("second", DockerContainer::Awg, {{"hostName", "second.invalid"}});
        drain();
        assert(VpnProtocol::starts == starts + 2 && vpn.m_remoteAddress == "second.invalid");
        source.change(40); drain();
        source.change(60);
        until([&] { return VpnProtocol::starts == starts + 3; });
    }

    // Replacing a request before network recovery starts only the newest one.
    {
        source.value = 40;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn); drain();
        vpn.connectToVpn("second", DockerContainer::Awg, {{"hostName", "second.invalid"}});
        source.change(70);
        until([&] { return VpnProtocol::starts == starts + 1; });
        assert(vpn.m_remoteAddress == "second.invalid");
    }

    {
        VpnConnection unused;
        int starts = VpnProtocol::starts;
        unused.linuxNetworkChanged(40);
        unused.linuxNetworkChanged(70);
        drain();
        assert(VpnProtocol::starts == starts);
    }

    // A confirmed connection remains recoverable after an earlier status event.
    {
        source.value = 70;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn);
        until([&] { return VpnProtocol::starts == starts + 1; });
        vpn.setConnectionState(Vpn::Disconnected);
        vpn.setConnectionState(Vpn::Connected);
        source.change(40); drain();
        source.change(70);
        until([&] { return VpnProtocol::starts == starts + 2; });
    }

    // A newer state signal must win over an in-flight initial-state query.
    {
        source.value = 70;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn);
        vpn.linuxNetworkChanged(10);
        drain();
        assert(VpnProtocol::starts == starts);
        source.change(70);
        until([&] { return VpnProtocol::starts == starts + 1; });
    }

    // Non-network errors do not silently enable a later automatic retry.
    {
        source.value = 70;
        VpnProtocol::startResult = ErrorCode::Failed;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn);
        until([&] { return vpn.m_connectionState == Vpn::Error; });
        source.change(40); source.change(70); drain();
        assert(VpnProtocol::starts == starts + 1 && !vpn.m_linuxConnection.waiting());
        VpnProtocol::startResult = ErrorCode::NoError;
    }

    // A host without NM keeps the existing connection path instead of waiting
    // forever for a service it does not use.
    {
        source.value = -1;
        VpnConnection vpn;
        int starts = VpnProtocol::starts;
        request(vpn);
        until([&] { return VpnProtocol::starts == starts + 1; });
    }
    IpcClient::replica.reset();
    std::cout << "fixed: Qt events, native readiness IPC, startup/sleep/recovery/cancel/error cases pass\n";
#endif
}
