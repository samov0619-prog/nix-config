// Event-driven connection intent, independent of Qt and of a particular host.
#ifndef AMNEZIA_LINUX_CONNECTION_STATE_H
#define AMNEZIA_LINUX_CONNECTION_STATE_H

namespace AmneziaLinuxNetworking {

class ConnectionState {
public:
    enum class Action { None, Start, Reconnect };

    bool ready() const
    {
        // -1 preserves upstream behavior on systems without NetworkManager.
        // SITE is sufficient: do not wait for an Internet connectivity probe
        // that the VPN or its kill switch may itself be needed to complete.
        return m_networkState == -1 || m_networkState == 60 || m_networkState == 70;
    }

    void networkChanged(int state)
    {
        m_networkState = state;
        if (m_requested && !m_pendingStart && !ready())
            m_pendingRecovery = true;
    }

    void request()
    {
        m_requested = true;
        m_pendingStart = true;
        m_pendingRecovery = false;
    }

    void cancel()
    {
        m_requested = false;
        m_pendingStart = false;
        m_pendingRecovery = false;
    }

    // A live protocol can confirm success after an earlier status notification.
    // Do not discard a pending replacement/recovery when that happens.
    void connected() { m_requested = true; }

    bool waiting() const { return m_requested && (m_pendingStart || m_pendingRecovery); }

    Action takeAction()
    {
        if (!m_requested || !ready())
            return Action::None;
        if (m_pendingStart) {
            m_pendingStart = false;
            return Action::Start;
        }
        if (m_pendingRecovery) {
            m_pendingRecovery = false;
            return Action::Reconnect;
        }
        return Action::None;
    }

private:
    int m_networkState = 0;
    bool m_requested = false;
    bool m_pendingStart = false;
    bool m_pendingRecovery = false;
};

} // namespace AmneziaLinuxNetworking

#endif
