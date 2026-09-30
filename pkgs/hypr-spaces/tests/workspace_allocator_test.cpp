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

    auto cards = allocateWorkspaceCards({{1, 10}, {3, 20}});
    assert(card(cards, 2).owner == 20 && !card(cards, 2).real);
    assert(card(cards, 4).owner == 20 && !card(cards, 4).real);

    cards = allocateWorkspaceCards({{3, 20}, {10, 10}});
    assert(card(cards, 1).owner == 20 && !card(cards, 1).real);
    assert(card(cards, 2).owner == 20 && !card(cards, 2).real);
    assert(card(cards, 3).real && card(cards, 3).owner == 20);

    cards = allocateWorkspaceCards({{1, 10}, {44, 30}, {100, 20}});
    for (int id = 1; id <= 33; ++id) assert(card(cards, id).owner == 10);
    for (int id = 34; id <= 66; ++id) assert(card(cards, id).owner == 30);
    for (int id = 67; id <= 100; ++id) assert(card(cards, id).owner == 20);
    assert(card(cards, 101).owner == 20 && !card(cards, 101).real);
    assert(card(cards, 44).real && card(cards, 100).real);

    const auto inserted = allocateWorkspaceCards({{1, 10}, {44, 30}, {50, 30}, {100, 20}});
    assert(card(inserted, 50).real && card(inserted, 50).owner == 30);
    const auto moved = allocateWorkspaceCards({{1, 10}, {44, 20}, {100, 20}});
    assert(card(moved, 44).real && card(moved, 44).owner == 20);
    assert(card(moved, 67).owner == 20);

    std::set<int> ids;
    for (const auto& item : inserted)
        assert(ids.insert(item.id).second);
}
