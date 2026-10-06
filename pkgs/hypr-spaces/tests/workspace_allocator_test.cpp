#include "workspace_allocator.hpp"

#include <cassert>
#include <set>
#include <vector>

namespace {

using hypr_spaces::WorkspaceCard;

const WorkspaceCard& card(const std::vector<WorkspaceCard>& cards, int id) {
    for (const auto& item : cards)
        if (item.id == id)
            return item;
    assert(false);
    __builtin_unreachable();
}

} // namespace

int main() {
    using hypr_spaces::allocateWorkspaceCards;
    using hypr_spaces::monitorHasRealWorkspace;
    using hypr_spaces::nextUnoccupiedWorkspaceID;
    using hypr_spaces::workspaceCardOwner;
    using hypr_spaces::workspaceHeadID;

    auto cards = allocateWorkspaceCards({{1, 10}, {3, 20}});
    assert(card(cards, 2).owner == 10 && !card(cards, 2).real);
    assert(cards.size() == 3);

    cards = allocateWorkspaceCards({{3, 20}, {10, 10}});
    assert(card(cards, 1).owner == 20 && !card(cards, 1).real);
    assert(card(cards, 2).owner == 20 && !card(cards, 2).real);
    assert(card(cards, 3).real && card(cards, 3).owner == 20);
    for (int id = 4; id <= 9; ++id) assert(card(cards, id).owner == 20 && !card(cards, id).real);

    cards = allocateWorkspaceCards({{1, 10}, {44, 30}, {100, 20}});
    for (int id = 1; id < 44; ++id) assert(card(cards, id).owner == 10);
    for (int id = 44; id < 100; ++id) assert(card(cards, id).owner == 30);
    assert(card(cards, 100).owner == 20);
    assert(cards.size() == 100);
    assert(card(cards, 44).real && card(cards, 100).real);

    const auto inserted = allocateWorkspaceCards({{1, 10}, {44, 30}, {50, 30}, {100, 20}});
    assert(card(inserted, 50).real && card(inserted, 50).owner == 30);
    const auto moved = allocateWorkspaceCards({{1, 10}, {44, 20}, {100, 20}});
    assert(card(moved, 44).real && card(moved, 44).owner == 20);
    assert(card(moved, 67).owner == 20);

    std::set<int> ids;
    for (const auto& item : inserted)
        assert(ids.insert(item.id).second);
    assert(nextUnoccupiedWorkspaceID(8, {9}) == 8);
    assert(nextUnoccupiedWorkspaceID(8, {8, 9}) == 10);
    assert(nextUnoccupiedWorkspaceID(1, {1, 3, 4}) == 2);

    const std::vector<hypr_spaces::WorkspaceState> heads = {
        {1, 10, true}, {2, 10, true}, {3, 10, true}, {4, 10, true}, {5, 20, false}, {10, 10, false},
    };
    assert(workspaceHeadID(10, 3, true, 4, heads) == 10);
    assert(workspaceHeadID(20, 5, false, 4, heads) == 5);
    assert(workspaceHeadID(30, 0, false, 4, heads) == 6);

    const std::vector<hypr_spaces::WorkspaceState> droppedHead = {
        {1, 10, true}, {2, 10, true}, {3, 10, true}, {4, 10, true}, {5, 20, false},
    };
    assert(workspaceHeadID(10, 3, true, 4, droppedHead) == 6);

    const std::vector<hypr_spaces::WorkspaceState> activeEmptyBelowMaximum = {
        {1, 10, true}, {2, 20, false}, {3, 10, true}, {4, 10, true},
    };
    assert(!monitorHasRealWorkspace(20, activeEmptyBelowMaximum));
    assert(workspaceHeadID(20, 2, false, 4, activeEmptyBelowMaximum) == 2);
    assert(workspaceHeadID(10, 3, true, 4, activeEmptyBelowMaximum) == 5);
    assert(workspaceCardOwner(2, 10, activeEmptyBelowMaximum) == 20);
    assert(workspaceCardOwner(3, 20, activeEmptyBelowMaximum) == 10);
}
