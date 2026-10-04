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
    bool real;
};

// Real workspaces are immutable anchors. The leading tail follows the first
// anchor; short gaps follow their successor, while larger gaps fill the
// predecessor's balanced global quota before continuing on the successor.
inline std::vector<WorkspaceCard> allocateWorkspaceCards(std::vector<WorkspaceAnchor> anchors) {
    std::erase_if(anchors, [](const auto& anchor) { return anchor.id <= 0; });
    std::ranges::sort(anchors, {}, &WorkspaceAnchor::id);
    anchors.erase(std::unique(anchors.begin(), anchors.end(), [](const auto& a, const auto& b) { return a.id == b.id; }), anchors.end());
    if (anchors.empty())
        return {};

    std::vector<int> owners;
    for (const auto& anchor : anchors)
        if (std::ranges::find(owners, anchor.owner) == owners.end())
            owners.push_back(anchor.owner);

    const int maxID = anchors.back().id;
    std::vector<int> counts(owners.size());
    for (const auto& anchor : anchors)
        ++counts[std::ranges::find(owners, anchor.owner) - owners.begin()];

    std::vector<int> targets(owners.size(), maxID / static_cast<int>(owners.size()));
    for (size_t index = owners.size() - maxID % owners.size(); index < owners.size(); ++index)
        ++targets[index];

    std::vector<WorkspaceCard> cards;
    cards.reserve(maxID + 1);
    const auto& first = anchors.front();
    for (int id = 1; id < first.id; ++id)
        cards.push_back({id, first.owner, false});
    counts[std::ranges::find(owners, first.owner) - owners.begin()] += first.id - 1;
    cards.push_back({first.id, first.owner, true});

    for (size_t index = 1; index < anchors.size(); ++index) {
        const auto& predecessor = anchors[index - 1];
        const auto& successor = anchors[index];
        const int gapLength = successor.id - predecessor.id - 1;
        const size_t predecessorOwner = std::ranges::find(owners, predecessor.owner) - owners.begin();
        const int predecessorCards = gapLength < static_cast<int>(owners.size()) ? 0 :
            std::min(gapLength, std::max(0, targets[predecessorOwner] - counts[predecessorOwner]));
        for (int id = predecessor.id + 1; id < successor.id; ++id)
            cards.push_back({id, id < successor.id - (gapLength - predecessorCards) ? predecessor.owner : successor.owner, false});
        counts[predecessorOwner] += predecessorCards;
        counts[std::ranges::find(owners, successor.owner) - owners.begin()] += gapLength - predecessorCards;
        cards.push_back({successor.id, successor.owner, true});
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

// Hyprland keeps an empty workspace head per output. Reuse the selected
// output's head; otherwise reserve the first globally unoccupied ID.
inline int workspaceHeadID(int owner, int maxRealID, const std::vector<WorkspaceState>& workspaces) {
    std::vector<int> occupiedIDs;
    int              localHeadID = 0;
    for (const auto& workspace : workspaces) {
        if (workspace.id <= 0)
            continue;
        occupiedIDs.push_back(workspace.id);
        if (workspace.owner == owner && !workspace.real && workspace.id > maxRealID)
            localHeadID = std::max(localHeadID, workspace.id);
    }
    return localHeadID > 0 ? localHeadID : nextUnoccupiedWorkspaceID(maxRealID + 1, std::move(occupiedIDs));
}

} // namespace hypr_spaces
