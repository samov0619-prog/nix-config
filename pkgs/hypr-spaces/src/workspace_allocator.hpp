#pragma once

#include <algorithm>
#include <ranges>
#include <vector>

namespace hypr_spaces {

struct WorkspaceAnchor {
    int id;
    int owner;
};

struct WorkspaceCard {
    int  id;
    int  owner;
    bool real;
};

struct WorkspaceState {
    int  id;
    int  owner;
    bool hasWindows;
};

inline int workspaceCardOwner(int id, int fallbackOwner, const std::vector<WorkspaceState>& workspaces) {
    const auto existing = std::ranges::find_if(workspaces, [id](const auto& workspace) { return workspace.id == id; });
    return existing == workspaces.end() ? fallbackOwner : existing->owner;
}

inline bool monitorHasRealWorkspace(int owner, const std::vector<WorkspaceState>& workspaces) {
    return std::ranges::any_of(workspaces, [owner](const auto& workspace) { return workspace.id > 0 && workspace.owner == owner && workspace.hasWindows; });
}

// Real workspaces are immutable anchors. Every virtual gap belongs to the
// preceding numeric ID, while the leading range belongs to the first anchor.
inline std::vector<WorkspaceCard> allocateWorkspaceCards(std::vector<WorkspaceAnchor> anchors) {
    std::erase_if(anchors, [](const auto& anchor) { return anchor.id <= 0; });
    std::ranges::sort(anchors, {}, &WorkspaceAnchor::id);
    anchors.erase(std::unique(anchors.begin(), anchors.end(), [](const auto& a, const auto& b) { return a.id == b.id; }), anchors.end());
    if (anchors.empty())
        return {};

    const int maxID = anchors.back().id;
    std::vector<WorkspaceCard> cards;
    cards.reserve(maxID);
    size_t anchorIndex = 0;
    int owner = anchors.front().owner;
    for (int id = 1; id <= maxID; ++id) {
        if (anchorIndex < anchors.size() && anchors[anchorIndex].id == id) {
            owner = anchors[anchorIndex].owner;
            cards.push_back({id, owner, true});
            ++anchorIndex;
        } else {
            cards.push_back({id, owner, false});
        }
    }
    return cards;
}

inline int nextUnoccupiedWorkspaceID(int firstID, std::vector<int> occupiedIDs) {
    std::ranges::sort(occupiedIDs);
    int candidate = std::max(1, firstID);
    for (const int id : occupiedIDs) {
        if (id < candidate)
            continue;
        if (id > candidate)
            break;
        ++candidate;
    }
    return candidate;
}

// An output without real workspaces exposes its active empty workspace as the
// crown. Otherwise, only empty IDs above the global real range are crowns.
inline int workspaceHeadID(int owner, int activeWorkspaceID, bool hasRealWorkspace, int maxRealID, const std::vector<WorkspaceState>& workspaces) {
    if (!hasRealWorkspace) {
        const auto active = std::ranges::find_if(workspaces, [=](const auto& workspace) {
            return workspace.id > 0 && workspace.id == activeWorkspaceID && workspace.owner == owner && !workspace.hasWindows;
        });
        if (active != workspaces.end())
            return active->id;
    }
    std::vector<int> occupiedIDs;
    int              localHeadID = 0;
    for (const auto& workspace : workspaces) {
        if (workspace.id <= 0)
            continue;
        occupiedIDs.push_back(workspace.id);
        if (workspace.owner == owner && !workspace.hasWindows && workspace.id > maxRealID)
            localHeadID = std::max(localHeadID, workspace.id);
    }
    return localHeadID > 0 ? localHeadID : nextUnoccupiedWorkspaceID(maxRealID + 1, std::move(occupiedIDs));
}

} // namespace hypr_spaces
