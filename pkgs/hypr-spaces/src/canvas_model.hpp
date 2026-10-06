#pragma once

#include "workspace_allocator.hpp"

#include <optional>

namespace hypr_spaces {

struct CanvasMonitor {
    int id;
    int activeWorkspaceID;
};

struct CanvasCard {
    int id;
    bool exists;
    bool hasWindows;
    bool crown;
};

struct CanvasSelection {
    int owner = -1;
    int id = 0;
    bool crown = false;
    bool operator==(const CanvasSelection&) const = default;
};

struct CanvasGroup {
    CanvasMonitor monitor;
    std::vector<CanvasCard> cards;
};

struct CanvasModel {
    std::vector<CanvasGroup> groups;
    CanvasSelection selection;
    bool noWindows = true;
};

// Monitors are supplied in navigation order. Existing IDs always keep their
// actual owner; only absent IDs may be assigned by the gap allocator.
inline CanvasModel buildCanvasModel(const std::vector<CanvasMonitor>& monitors,
                                    const std::vector<WorkspaceState>& workspaces, CanvasSelection selection) {
    CanvasModel model;
    if (monitors.empty())
        return model;
    for (const auto& monitor : monitors)
        model.groups.push_back({monitor, {}});
    if (std::ranges::find(monitors, selection.owner, &CanvasMonitor::id) == monitors.end())
        selection = {monitors.front().id, monitors.front().activeWorkspaceID, false};

    auto selected = std::ranges::find_if(model.groups, [&](const auto& group) { return group.monitor.id == selection.owner; });
    std::vector<WorkspaceAnchor> anchors;
    for (const auto& ws : workspaces)
        if (ws.id > 0 && ws.hasWindows && std::ranges::find(monitors, ws.owner, &CanvasMonitor::id) != monitors.end())
            anchors.push_back({ws.id, ws.owner});
    model.noWindows = anchors.empty();
    if (model.noWindows) {
        for (auto& group : model.groups)
            if (group.monitor.activeWorkspaceID > 0)
                group.cards.push_back({group.monitor.activeWorkspaceID, true, false, false});
    } else {
        for (const auto& allocated : allocateWorkspaceCards(anchors)) {
            const auto ws = std::ranges::find(workspaces, allocated.id, &WorkspaceState::id);
            const int owner = ws == workspaces.end() ? allocated.owner : ws->owner;
            auto group = std::ranges::find_if(model.groups, [owner](const auto& g) { return g.monitor.id == owner; });
            if (group == model.groups.end())
                continue;
            if (ws != workspaces.end() && !ws->hasWindows && !monitorHasRealWorkspace(owner, workspaces))
                continue; // empty-only outputs are represented by the movable crown
            group->cards.push_back({allocated.id, ws != workspaces.end(), allocated.real, false});
        }
        const int high = std::ranges::max(anchors, {}, &WorkspaceAnchor::id).id;
        const int head = workspaceHeadID(selection.owner, selected->monitor.activeWorkspaceID,
                                        monitorHasRealWorkspace(selection.owner, workspaces), high, workspaces);
        selected->cards.push_back({head, std::ranges::find(workspaces, head, &WorkspaceState::id) != workspaces.end(), false, true});
    }

    // Prefer the same ID (including crown -> ordinary after a move/window open).
    // If a crown's target was dropped, keep the crown selected rather than an
    // unrelated ordinary card. The monitor is never inferred from the ID.
    auto card = std::ranges::find(selected->cards, selection.id, &CanvasCard::id);
    if (card == selected->cards.end() && selection.crown)
        card = std::ranges::find(selected->cards, true, &CanvasCard::crown);
    if (card == selected->cards.end())
        card = std::ranges::find(selected->cards, selected->monitor.activeWorkspaceID, &CanvasCard::id);
    if (card == selected->cards.end() && !selected->cards.empty())
        card = selected->cards.begin();
    model.selection = {selection.owner, card == selected->cards.end() ? 0 : card->id, card != selected->cards.end() && card->crown};
    return model;
}

struct CanvasActivation {
    CanvasSelection selection;
    bool focusOnly;
};

// A repeat cannot re-arm a cancelled Enter. Another key/gesture cancels the
// activation until Enter is released and deliberately pressed again.
class CanvasActivationLatch {
  public:
    void press(CanvasSelection selection, bool focusOnly) {
        if (!m_held && selection.id > 0)
            m_pending = CanvasActivation{selection, focusOnly};
        m_held = true;
    }
    void cancel() { m_pending.reset(); }
    bool held() const { return m_held; }
    std::optional<CanvasActivation> release(CanvasSelection current, bool focusOnly) {
        const auto pending = m_pending;
        m_held = false;
        m_pending.reset();
        if (!pending || pending->selection != current || pending->focusOnly != focusOnly)
            return std::nullopt;
        return pending;
    }
  private:
    bool m_held = false;
    std::optional<CanvasActivation> m_pending;
};

} // namespace hypr_spaces
