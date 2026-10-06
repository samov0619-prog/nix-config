#include "canvas_model.hpp"

#include <cassert>
#include <set>

using namespace hypr_spaces;

const CanvasGroup& group(const CanvasModel& model, int owner) {
    const auto it = std::ranges::find_if(model.groups, [owner](const auto& g) { return g.monitor.id == owner; });
    assert(it != model.groups.end());
    return *it;
}

std::vector<int> regular(const CanvasModel& model, int owner) {
    std::vector<int> ids;
    for (const auto& card : group(model, owner).cards)
        if (!card.crown) ids.push_back(card.id);
    return ids;
}

int crown(const CanvasModel& model, int owner) {
    for (const auto& card : group(model, owner).cards)
        if (card.crown) return card.id;
    return 0;
}

void invariants(const CanvasModel& model, const std::vector<WorkspaceState>& workspaces) {
    std::set<int> ids;
    int crowns = 0;
    bool selectionFound = false;
    for (const auto& g : model.groups) {
        int previous = 0;
        for (const auto& card : g.cards) {
            assert(ids.insert(card.id).second);
            if (card.crown) {
                ++crowns;
                assert(g.monitor.id == model.selection.owner);
            } else {
                assert(card.id > previous);
                previous = card.id;
            }
            const auto ws = std::ranges::find(workspaces, card.id, &WorkspaceState::id);
            assert(card.exists == (ws != workspaces.end()));
            if (card.exists) {
                assert(ws->owner == g.monitor.id);
                assert(ws->hasWindows == card.hasWindows);
            }
            selectionFound |= model.selection == CanvasSelection{g.monitor.id, card.id, card.crown};
        }
    }
    assert(crowns == (model.noWindows ? 0 : 1));
    assert(selectionFound);
}

int main() {
    // Empty-only B is an empty group while A is selected; Tab must build B's
    // crown before resolving the destination selection.
    std::vector<WorkspaceState> state = {{1, 0, true}, {2, 1, false}, {3, 0, true}, {4, 0, true}};
    auto model = buildCanvasModel({{0, 3}, {1, 2}}, state, {0, 3, false});
    invariants(model, state);
    assert(group(model, 1).cards.empty());
    assert((regular(model, 0) == std::vector{1, 3, 4}));
    model = buildCanvasModel({{0, 3}, {1, 2}}, state, {1, 2, false});
    invariants(model, state);
    assert((model.selection == CanvasSelection{1, 2, true}));
    assert(group(model, 1).cards.size() == 1);

    // Move empty 2 B->A. Hyprland keeps 2 active on A and creates 5 on B.
    state[1].owner = 0;
    state.push_back({5, 1, false});
    model = buildCanvasModel({{0, 2}, {1, 5}}, state, {0, 2, true});
    invariants(model, state);
    assert((regular(model, 0) == std::vector{1, 2, 3, 4}));
    assert((model.selection == CanvasSelection{0, 2, false}));
    assert(crown(model, 0) == 6);
    model = buildCanvasModel({{0, 2}, {1, 5}}, state, {1, 5, false});
    invariants(model, state);
    assert(crown(model, 1) == 5);

    // Moving back drops B's former head. No duplicate 2 or synthetic tail 5.
    state[1].owner = 1;
    state.pop_back();
    model = buildCanvasModel({{0, 1}, {1, 2}}, state, {1, 2, false});
    invariants(model, state);
    assert((model.selection == CanvasSelection{1, 2, true}));
    assert((regular(model, 0) == std::vector{1, 3, 4}));

    // Virtual 2 becomes materialized on B; use live ownership, not gap owner.
    state = {{1, 0, true}, {3, 0, true}, {4, 0, true}, {5, 1, false}};
    model = buildCanvasModel({{0, 3}, {1, 5}}, state, {0, 2, false});
    invariants(model, state);
    assert((regular(model, 0) == std::vector{1, 2, 3, 4}));
    state.back().id = 2;
    model = buildCanvasModel({{0, 3}, {1, 2}}, state, {1, 2, false});
    invariants(model, state);
    assert(crown(model, 1) == 2);

    // Move window-backed 3: B now has both regular empty 2 and real 3.
    state[1].owner = 1;
    model = buildCanvasModel({{0, 1}, {1, 2}}, state, {1, 3, false});
    invariants(model, state);
    assert((regular(model, 1) == std::vector{2, 3}));
    assert((model.selection == CanvasSelection{1, 3, false}));
    assert(crown(model, 1) == 5);

    // Reordering Hyprland's workspace enumeration cannot change the result.
    std::reverse(state.begin(), state.end());
    const auto reordered = buildCanvasModel({{0, 1}, {1, 2}}, state, model.selection);
    invariants(reordered, state);
    assert(regular(reordered, 1) == regular(model, 1));
    assert(reordered.selection == model.selection);

    // Existing persistent empty IDs must not override the active empty head.
    state = {{1, 0, true}, {2, 1, false}, {4, 0, true}, {8, 1, false}};
    assert(workspaceHeadID(1, 2, false, 4, state) == 2);
    std::reverse(state.begin(), state.end());
    assert(workspaceHeadID(1, 2, false, 4, state) == 2);

    // A selected crown survives a target change; promotion to real follows ID.
    state = {{1, 0, true}, {4, 0, true}, {5, 1, false}};
    model = buildCanvasModel({{0, 1}, {1, 5}}, state, {0, 5, true});
    invariants(model, state);
    assert((model.selection == CanvasSelection{0, 6, true}));
    state.push_back({6, 0, true});
    model = buildCanvasModel({{0, 6}, {1, 5}}, state, model.selection);
    invariants(model, state);
    assert((model.selection == CanvasSelection{0, 6, false}));

    // Selected B unplugged: repair selection against the remaining snapshot.
    state = {{1, 0, true}, {3, 0, true}, {4, 0, true}};
    model = buildCanvasModel({{0, 3}}, state, {1, 2, true});
    invariants(model, state);
    assert((model.selection == CanvasSelection{0, 3, false}));
    assert(buildCanvasModel({}, state, model.selection).groups.empty());

    // No-window mode uses actual active IDs and no crown, on one or many outputs.
    state = {{7, 0, false}, {12, 1, false}};
    model = buildCanvasModel({{0, 7}, {1, 12}}, state, {1, 99, true});
    invariants(model, state);
    assert(model.noWindows && model.selection.id == 12 && !model.selection.crown);
    model = buildCanvasModel({{0, 7}}, {{7, 0, false}}, {0, 0, false});
    invariants(model, {{7, 0, false}});

    CanvasActivationLatch enter;
    const CanvasSelection a{0, 2, false}, b{1, 2, false};
    enter.press(a, false);
    assert(enter.release(a, false).has_value());
    enter.press(a, false);
    enter.cancel(); // another key down, including modifier/Tab/navigation
    enter.press(b, false); // autorepeat cannot re-arm the held Enter
    assert(!enter.release(b, false));
    enter.press(b, false); // deliberate new press can activate new selection
    assert(enter.release(b, false));
    enter.press(a, false);
    assert(!enter.release(b, false)); // output changed externally while held
    enter.press(a, false);
    assert(!enter.release(a, true)); // model switched to focus-only mode
    assert(!enter.release(a, false)); // no pending activation

    // Small exhaustive snapshots include multiple empty/persistent IDs per
    // monitor. Rendering order and active-head priority must not depend on the
    // order in which Hyprland enumerates the workspaces.
    for (int encoding = 0; encoding < 3125; ++encoding) {
        std::vector<WorkspaceState> snapshot;
        int active[2] = {0, 0};
        int value = encoding;
        for (int id = 1; id <= 5; ++id) {
            const int status = value % 5;
            value /= 5;
            if (!status) continue;
            const int owner = (status - 1) % 2;
            snapshot.push_back({id, owner, status >= 3});
            if (!active[owner]) active[owner] = id;
        }
        if (!active[0] || !active[1]) continue;
        auto reversed = snapshot;
        std::reverse(reversed.begin(), reversed.end());
        for (int owner = 0; owner < 2; ++owner) {
            const auto forward = buildCanvasModel({{0, active[0]}, {1, active[1]}}, snapshot, {owner, active[owner], false});
            const auto backward = buildCanvasModel({{0, active[0]}, {1, active[1]}}, reversed, {owner, active[owner], false});
            invariants(forward, snapshot);
            invariants(backward, reversed);
            assert(forward.selection == backward.selection);
            for (int monitor = 0; monitor < 2; ++monitor) {
                assert(regular(forward, monitor) == regular(backward, monitor));
                assert(crown(forward, monitor) == crown(backward, monitor));
            }
        }
    }
}
