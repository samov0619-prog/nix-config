#include <hyprland/src/devices/IKeyboard.hpp>
#include <hyprland/src/devices/IPointer.hpp>
#include <hyprland/src/Compositor.hpp>
#include <hyprland/src/config/shared/actions/ConfigActions.hpp>
#include <hyprland/src/desktop/Workspace.hpp>
#include <hyprland/src/desktop/view/LayerSurface.hpp>
#include <hyprland/src/desktop/view/Window.hpp>
#include <hyprland/src/event/EventBus.hpp>
#include <hyprland/src/helpers/memory/Memory.hpp>
#include <hyprland/src/helpers/Monitor.hpp>
#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/plugins/PluginSystem.hpp>
#include <hyprland/src/render/Renderer.hpp>
#include <hyprland/src/render/pass/RectPassElement.hpp>
#include <hyprland/src/render/pass/RendererHintsPassElement.hpp>
#include <hyprland/src/render/pass/SurfacePassElement.hpp>
#include <linux/input-event-codes.h>

#include "monitor_layout.hpp"
#include "workspace_allocator.hpp"

#include <algorithm>
#include <cmath>
#include <ranges>
#include <vector>

namespace {

bool                  g_open = false;
bool                  g_swallowEscapeRelease = false;
bool                  g_pendingOpenerSpaceRelease = false;
bool                  g_shiftHeld = false;
PHLMONITOR            g_monitor;
CHyprSignalListener   g_renderHook;
CHyprSignalListener   g_keyboardHook;
CHyprSignalListener   g_mouseButtonHook;
CHyprSignalListener   g_mouseAxisHook;
CHyprSignalListener   g_mouseMoveHook;

struct SCameraState {
    float    currentScale = 1.F;
    float    targetScale = 1.F;
    Vector2D currentOffset;
    Vector2D targetOffset;
    Vector2D center;
};

struct SWorkspaceCard {
    int   workspaceID = 0;
    CBox  box;
    int   row = 0;
    int   column = 0;
};

struct SMonitorGroup {
    PHLMONITOR                 monitor;
    CBox                       box;
    std::vector<SWorkspaceCard> cards;
    std::vector<int>           rowColumns;
};

SCameraState                g_camera;
std::vector<SWorkspaceCard> g_cards;
std::vector<int>            g_rowColumns;
std::vector<SMonitorGroup>  g_groups;
int                         g_selectedWorkspaceID = 0;
int                         g_pendingWorkspaceID = 0;
int                         g_gridRows = 0;
int                         g_gridColumns = 0;

constexpr Vector2D GLOBAL_VIEWPORT = {1920.F, 1080.F};
constexpr float GROUP_GAP = 96.F;
constexpr float GROUP_PADDING = 48.F;
constexpr float CARD_GAP = 24.F;
constexpr float CARD_BORDER = 2.F;

void resetCamera() {
    g_camera = {};
}

bool globalCanvas() {
    return std::ranges::count_if(g_pCompositor->m_realMonitors, [](const auto& monitor) {
        return monitor && monitor->m_enabled;
    }) > 1;
}

void damage() {
    if (!globalCanvas() && g_monitor) {
        g_pHyprRenderer->damageMonitor(g_monitor);
        return;
    }
    for (const auto& monitor : g_pCompositor->m_realMonitors)
        if (monitor && monitor->m_enabled)
            g_pHyprRenderer->damageMonitor(monitor);
}

void zoom(float steps) {
    constexpr float minScale = 0.55F;
    constexpr float maxScale = 2.50F;

    g_camera.targetScale = std::clamp(g_camera.targetScale * std::pow(1.12F, steps), minScale, maxScale);
    // Keep zoom immediate until camera animation has a dedicated damage loop.
    g_camera.currentScale = g_camera.targetScale;
    damage();
}

void close() {
    g_open = false;
    g_pendingOpenerSpaceRelease = false;
    g_shiftHeld = false;
    g_groups.clear();
    g_cards.clear();
    g_rowColumns.clear();
    g_selectedWorkspaceID = 0;
    g_pendingWorkspaceID = 0;
    g_gridRows = 0;
    g_gridColumns = 0;
    resetCamera();
    damage();
}

void selectCard(int columnDirection, int rowDirection) {
    const auto selected = std::ranges::find(g_cards, g_selectedWorkspaceID, &SWorkspaceCard::workspaceID);
    if (selected == g_cards.end() || g_gridRows == 0 || g_rowColumns.empty())
        return;

    int row = selected->row;
    int column = selected->column;
    if (columnDirection) {
        column = (column + columnDirection + g_rowColumns[row]) % g_rowColumns[row];
    } else if (rowDirection) {
        const int adjacentRow = (row + rowDirection + g_gridRows) % g_gridRows;
        // Never cross a missing slot between a short row and a long row.
        if (column >= g_rowColumns[adjacentRow])
            return;
        row = adjacentRow;
    }

    const auto destination = std::ranges::find_if(g_cards, [row, column](const auto& card) {
        return card.row == row && card.column == column;
    });
    if (destination != g_cards.end()) {
        g_selectedWorkspaceID = destination->workspaceID;
        damage();
    }
}

void renderWindow(PHLWINDOW window, PHLMONITOR source, PHLMONITOR target, float sourcePxToPreviewPx, const Vector2D& previewOrigin, const CBox& clipBox, const Time::steady_tp& time) {
    if (!window || !window->m_isMapped || !window->wlSurface() || !window->wlSurface()->resource())
        return;

    const auto position = window->m_realPosition->value() + window->m_floatingOffset;
    const auto size = window->m_realSize->value();
    if (size.x < 1 || size.y < 1)
        return;

    const float scale = sourcePxToPreviewPx * source->m_scale / target->m_scale;
    const Vector2D sourcePosition = (position - source->m_position) * source->m_scale;
    const Vector2D targetPosition = (position - target->m_position) * target->m_scale;
    const Vector2D destination = previewOrigin + sourcePosition * sourcePxToPreviewPx;
    Render::SRenderModifData transform;
    transform.enabled = true;
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_TRANSLATE, std::any(destination / scale - targetPosition)});
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_SCALE, std::any(scale)});
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = transform}));

    CSurfacePassElement::SRenderData data = {target, time};
    data.pos = position;
    data.w = size.x;
    data.h = size.y;
    data.surface = window->wlSurface()->resource();
    data.pWindow = window;
    data.clipBox = clipBox;
    data.decorate = false;
    data.blur = false;
    data.alpha = 1.F;
    data.fadeAlpha = 1.F;
    data.surfaceCounter = 0;

    window->wlSurface()->resource()->breadthfirst(
        [&data, &window](SP<CWLSurfaceResource> surface, const Vector2D& offset, void*) {
            if (!surface || !surface->m_current.texture || surface->m_current.size.x < 1 || surface->m_current.size.y < 1)
                return;
            data.localPos = offset;
            data.texture = surface->m_current.texture;
            data.surface = surface;
            data.mainSurface = surface == window->wlSurface()->resource();
            g_pHyprRenderer->m_renderPass.add(makeUnique<CSurfacePassElement>(data));
            data.surfaceCounter++;
        },
        nullptr);

    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = Render::SRenderModifData{}}));
}

void renderLayer(PHLLS layer, PHLMONITOR source, PHLMONITOR target, float sourcePxToPreviewPx, const Vector2D& previewOrigin, const CBox& clipBox, const Time::steady_tp& time) {
    if (!layer || !layer->m_mapped || layer->m_readyToDelete || !layer->m_layerSurface || !layer->wlSurface() || !layer->wlSurface()->resource())
        return;

    const auto position = layer->m_realPosition->value();
    const auto size = layer->m_realSize->value();
    const float scale = sourcePxToPreviewPx * source->m_scale / target->m_scale;
    if (!(scale > 0.F) || size.x < 1 || size.y < 1)
        return;

    Render::SRenderModifData transform;
    transform.enabled = true;
    const Vector2D sourcePosition = (position - source->m_position) * source->m_scale;
    const Vector2D targetPosition = (position - target->m_position) * target->m_scale;
    const Vector2D destination = previewOrigin + sourcePosition * sourcePxToPreviewPx;
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_TRANSLATE, std::any(destination / scale - targetPosition)});
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_SCALE, std::any(scale)});
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = transform}));

    CSurfacePassElement::SRenderData data = {target, time, position};
    data.pos = position;
    data.w = size.x;
    data.h = size.y;
    data.surface = layer->wlSurface()->resource();
    data.pLS = layer;
    data.clipBox = clipBox;
    data.decorate = false;
    data.blur = false;
    data.alpha = 1.F;
    data.fadeAlpha = 1.F;
    data.surfaceCounter = 0;

    layer->wlSurface()->resource()->breadthfirst(
        [&data, &layer](SP<CWLSurfaceResource> surface, const Vector2D& offset, void*) {
            if (!surface || !surface->m_current.texture || surface->m_current.size.x < 1 || surface->m_current.size.y < 1)
                return;
            data.localPos = offset;
            data.texture = surface->m_current.texture;
            data.surface = surface;
            data.mainSurface = surface == layer->wlSurface()->resource();
            g_pHyprRenderer->m_renderPass.add(makeUnique<CSurfacePassElement>(data));
            data.surfaceCounter++;
        },
        &data);

    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = Render::SRenderModifData{}}));
}

void renderSingleMonitor() {
    if (!g_open || !g_monitor || g_pHyprRenderer->m_renderData.pMonitor != g_monitor)
        return;

    const CBox fullMonitor = {{0, 0}, g_monitor->m_transformedSize};
    CRectPassElement::SRectData backdrop;
    backdrop.box = fullMonitor;
    backdrop.color = CHyprColor(0.02F, 0.03F, 0.05F, 1.F);
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(backdrop));

    int highestWorkspaceID = 0;
    for (const auto& workspaceRef : g_pCompositor->getWorkspaces()) {
        const auto workspace = workspaceRef.lock();
        if (workspace && workspace->m_id > 0 && workspace->m_monitor.lock() == g_monitor)
            highestWorkspaceID = std::max(highestWorkspaceID, static_cast<int>(workspace->m_id));
    }

    if (highestWorkspaceID == 0) {
        g_cards.clear();
        g_rowColumns.clear();
        g_gridRows = 0;
        g_gridColumns = 0;
        g_selectedWorkspaceID = 0;
        damage();
        return;
    }

    // Slots are numbered rather than enumerated so their positions do not change
    // when Hyprland creates or destroys an otherwise empty workspace.
    std::vector<PHLWORKSPACE> workspaces(highestWorkspaceID);
    for (const auto& workspaceRef : g_pCompositor->getWorkspaces()) {
        const auto workspace = workspaceRef.lock();
        if (workspace && workspace->m_id > 0 && workspace->m_id <= highestWorkspaceID && workspace->m_monitor.lock() == g_monitor)
            workspaces[workspace->m_id - 1] = workspace;
    }

    constexpr float padding = 48.F;
    constexpr float gap = 24.F;
    constexpr float border = 2.F;
    const Vector2D canvasSize = g_monitor->m_transformedSize - Vector2D{2 * padding, 2 * padding};
    const float aspect = g_monitor->m_transformedSize.x / g_monitor->m_transformedSize.y;

    int columns = 1;
    float cardWidth = 0.F;
    for (int candidate = 1; candidate <= static_cast<int>(workspaces.size()); candidate++) {
        const int rows = static_cast<int>(std::ceil(static_cast<float>(workspaces.size()) / candidate));
        const float width = std::min((canvasSize.x - gap * (candidate - 1)) / candidate,
                                     ((canvasSize.y - gap * (rows - 1)) / rows) * aspect);
        if (width > cardWidth) {
            columns = candidate;
            cardWidth = width;
        }
    }

    const int rows = static_cast<int>(std::ceil(static_cast<float>(workspaces.size()) / columns));
    const Vector2D cardSize = {cardWidth, cardWidth / aspect};
    const Vector2D gridSize = {columns * cardSize.x + (columns - 1) * gap, rows * cardSize.y + (rows - 1) * gap};
    const Vector2D gridOrigin = (g_monitor->m_transformedSize - gridSize) / 2.F;
    const auto time = Time::steadyNow();

    g_cards.clear();
    g_cards.reserve(workspaces.size());
    g_gridRows = rows;
    g_gridColumns = columns;
    g_rowColumns.assign(rows, columns);
    g_rowColumns.back() = static_cast<int>(workspaces.size()) - (rows - 1) * columns;
    for (size_t index = 0; index < workspaces.size(); index++) {
        const int column = index % columns;
        const int row = index / columns;
        const Vector2D unscaledOrigin = gridOrigin + Vector2D{column * (cardSize.x + gap), row * (cardSize.y + gap)};
        const Vector2D cardOrigin = g_monitor->m_transformedSize / 2.F +
            (unscaledOrigin - g_monitor->m_transformedSize / 2.F) * g_camera.currentScale + g_camera.currentOffset;
        g_cards.emplace_back(static_cast<int>(index) + 1, CBox{cardOrigin, cardSize * g_camera.currentScale}, row, column);
    }

    if (std::ranges::find(g_cards, g_selectedWorkspaceID, &SWorkspaceCard::workspaceID) == g_cards.end())
        g_selectedWorkspaceID = g_monitor->m_activeWorkspace ? g_monitor->m_activeWorkspace->m_id : g_cards.front().workspaceID;
    if (std::ranges::find(g_cards, g_selectedWorkspaceID, &SWorkspaceCard::workspaceID) == g_cards.end())
        g_selectedWorkspaceID = g_cards.front().workspaceID;

    for (size_t index = 0; index < workspaces.size(); index++) {
        const CBox cardBox = g_cards[index].box;
        const CBox previewBox = {cardBox.pos() + Vector2D{border, border}, Vector2D{cardBox.w, cardBox.h} - Vector2D{2 * border, 2 * border}};

        CRectPassElement::SRectData cardBackground;
        cardBackground.box = cardBox;
        if (g_cards[index].workspaceID == g_selectedWorkspaceID)
            cardBackground.color = CHyprColor(0.42F, 0.12F, 0.62F, 1.F);
        else if (g_cards[index].workspaceID == (g_monitor->m_activeWorkspace ? g_monitor->m_activeWorkspace->m_id : 0))
            cardBackground.color = CHyprColor(0.10F, 0.35F, 0.14F, 1.F);
        else
            cardBackground.color = CHyprColor(0.12F, 0.15F, 0.20F, 1.F);
        g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(cardBackground));

        CRectPassElement::SRectData previewBackground;
        previewBackground.box = previewBox;
        previewBackground.color = CHyprColor(0.04F, 0.06F, 0.09F, 1.F);
        g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(previewBackground));

        const float scale = previewBox.w / g_monitor->m_transformedSize.x;
        for (const auto& layerRef : g_monitor->m_layerSurfaceLayers[0]) {
            const auto layer = layerRef.lock();
            if (layer)
                renderLayer(layer, g_monitor, g_monitor, scale, previewBox.pos(), previewBox, time);
        }
        for (const auto& layerRef : g_monitor->m_layerSurfaceLayers[1]) {
            const auto layer = layerRef.lock();
            if (layer)
                renderLayer(layer, g_monitor, g_monitor, scale, previewBox.pos(), previewBox, time);
        }
        if (!workspaces[index])
            continue;
        for (const auto& window : g_pCompositor->m_windows) {
            if (window && window->m_workspace == workspaces[index] && !window->m_isFloating) {
                renderWindow(window, g_monitor, g_monitor, scale, previewBox.pos(), previewBox, time);
            }
        }
        for (const auto& window : g_pCompositor->m_windows) {
            if (window && window->m_workspace == workspaces[index] && window->m_isFloating) {
                renderWindow(window, g_monitor, g_monitor, scale, previewBox.pos(), previewBox, time);
            }
        }
    }
    damage();
}

SMonitorGroup* groupFor(PHLMONITOR monitor) {
    const auto group = std::ranges::find(g_groups, monitor, &SMonitorGroup::monitor);
    return group == g_groups.end() ? nullptr : &*group;
}

void focusGlobalCamera() {
    const auto* group = groupFor(g_monitor);
    if (!group)
        return;

    g_camera.center = group->box.pos() + group->box.size() / 2.F;
    g_camera.currentScale = 0.90F;
    g_camera.targetScale = g_camera.currentScale;
    g_camera.currentOffset = {};
    g_camera.targetOffset = {};
}

void rebuildGlobalCanvas() {
    std::vector<PHLMONITOR> monitors;
    std::vector<hypr_spaces::MonitorRect> rectangles;
    for (const auto& monitor : g_pCompositor->m_realMonitors) {
        if (!monitor || !monitor->m_enabled || monitor->m_size.x < 1 || monitor->m_size.y < 1)
            continue;
        monitors.push_back(monitor);
        rectangles.push_back({static_cast<int>(monitor->m_id), static_cast<int>(monitor->m_position.x), static_cast<int>(monitor->m_position.y),
                              static_cast<int>(monitor->m_size.x), static_cast<int>(monitor->m_size.y)});
    }

    g_groups.clear();
    for (const int id : hypr_spaces::monitorTabOrder(rectangles)) {
        const auto monitor = *std::ranges::find_if(monitors, [id](const auto& item) { return static_cast<int>(item->m_id) == id; });
        const float aspect = monitor->m_transformedSize.x / monitor->m_transformedSize.y;
        g_groups.push_back({.monitor = monitor, .box = {{0, 0}, {GLOBAL_VIEWPORT.y * aspect, GLOBAL_VIEWPORT.y}}});
    }

    const auto rows = hypr_spaces::groupMonitorsInVisualRows(rectangles);
    float y = 0.F;
    size_t groupIndex = 0;
    for (const auto& row : rows) {
        float x = 0.F;
        float height = 0.F;
        for (size_t column = 0; column < row.monitorIDs.size(); ++column, ++groupIndex) {
            auto& group = g_groups[groupIndex];
            group.box.x = x;
            group.box.y = y;
            x += group.box.w + GROUP_GAP;
            height = std::max(height, static_cast<float>(group.box.h));
        }
        y += height + GROUP_GAP;
    }

    std::vector<hypr_spaces::WorkspaceAnchor> anchors;
    for (const auto& workspaceRef : g_pCompositor->getWorkspaces()) {
        const auto workspace = workspaceRef.lock();
        const auto owner = workspace ? workspace->m_monitor.lock() : nullptr;
        if (workspace && workspace->m_id > 0 && owner && owner->m_enabled)
            anchors.push_back({static_cast<int>(workspace->m_id), static_cast<int>(owner->m_id)});
    }

    for (const auto& allocated : hypr_spaces::allocateWorkspaceCards(anchors)) {
        const auto group = std::ranges::find_if(g_groups, [&allocated](const auto& item) {
            return static_cast<int>(item.monitor->m_id) == allocated.owner;
        });
        if (group != g_groups.end())
            group->cards.emplace_back(allocated.id, CBox{}, 0, 0);
    }

    for (auto& group : g_groups) {
        const int cardCount = static_cast<int>(group.cards.size());
        if (cardCount == 0)
            continue;

        const Vector2D canvasSize = group.box.size() - Vector2D{2 * GROUP_PADDING, 2 * GROUP_PADDING};
        const float aspect = group.monitor->m_transformedSize.x / group.monitor->m_transformedSize.y;
        int columns = 1;
        float cardWidth = 0.F;
        for (int candidate = 1; candidate <= cardCount; ++candidate) {
            const int rowsCount = static_cast<int>(std::ceil(static_cast<float>(cardCount) / candidate));
            const float width = std::min((canvasSize.x - CARD_GAP * (candidate - 1)) / candidate,
                                         ((canvasSize.y - CARD_GAP * (rowsCount - 1)) / rowsCount) * aspect);
            if (width > cardWidth) {
                columns = candidate;
                cardWidth = width;
            }
        }

        const int rowsCount = static_cast<int>(std::ceil(static_cast<float>(cardCount) / columns));
        const Vector2D cardSize = {cardWidth, cardWidth / aspect};
        const Vector2D gridSize = {columns * cardSize.x + (columns - 1) * CARD_GAP, rowsCount * cardSize.y + (rowsCount - 1) * CARD_GAP};
        const Vector2D origin = group.box.pos() + (group.box.size() - gridSize) / 2.F;
        group.rowColumns.assign(rowsCount, columns);
        group.rowColumns.back() = cardCount - (rowsCount - 1) * columns;
        for (int index = 0; index < cardCount; ++index) {
            const int column = index % columns;
            const int row = index / columns;
            group.cards[index].box = {origin + Vector2D{column * (cardSize.x + CARD_GAP), row * (cardSize.y + CARD_GAP)}, cardSize};
            group.cards[index].row = row;
            group.cards[index].column = column;
        }
    }

    const auto selectable = std::ranges::find_if(g_groups, [](const auto& group) { return !group.cards.empty(); });
    if ((!groupFor(g_monitor) || groupFor(g_monitor)->cards.empty()) && selectable != g_groups.end())
        g_monitor = selectable->monitor;
    const auto* selectedGroup = groupFor(g_monitor);
    g_cards = selectedGroup ? selectedGroup->cards : std::vector<SWorkspaceCard>{};
    g_rowColumns = selectedGroup ? selectedGroup->rowColumns : std::vector<int>{};
    g_gridRows = static_cast<int>(g_rowColumns.size());
    g_gridColumns = g_gridRows > 0 ? *std::ranges::max_element(g_rowColumns) : 0;
    if (std::ranges::find(g_cards, g_selectedWorkspaceID, &SWorkspaceCard::workspaceID) == g_cards.end())
        g_selectedWorkspaceID = g_monitor && g_monitor->m_activeWorkspace ? g_monitor->m_activeWorkspace->m_id : 0;
    if (std::ranges::find(g_cards, g_selectedWorkspaceID, &SWorkspaceCard::workspaceID) == g_cards.end() && !g_cards.empty())
        g_selectedWorkspaceID = g_cards.front().workspaceID;
}

void selectMonitor(int direction) {
    const auto current = std::ranges::find(g_groups, g_monitor, &SMonitorGroup::monitor);
    if (current == g_groups.end() || g_groups.empty())
        return;

    auto selected = current;
    for (size_t attempts = 0; attempts < g_groups.size(); ++attempts) {
        const auto index = (std::distance(g_groups.begin(), selected) + direction + static_cast<int>(g_groups.size())) % g_groups.size();
        selected = g_groups.begin() + index;
        if (!selected->cards.empty())
            break;
    }
    if (selected->cards.empty())
        return;

    g_monitor = selected->monitor;
    g_cards = selected->cards;
    g_rowColumns = selected->rowColumns;
    g_gridRows = static_cast<int>(g_rowColumns.size());
    g_gridColumns = g_gridRows > 0 ? *std::ranges::max_element(g_rowColumns) : 0;
    g_selectedWorkspaceID = g_monitor->m_activeWorkspace ? g_monitor->m_activeWorkspace->m_id : g_cards.front().workspaceID;
    if (std::ranges::find(g_cards, g_selectedWorkspaceID, &SWorkspaceCard::workspaceID) == g_cards.end())
        g_selectedWorkspaceID = g_cards.front().workspaceID;
    focusGlobalCamera();
    damage();
}

CBox screenBox(const CBox& logical, PHLMONITOR output) {
    const float base = std::min(output->m_transformedSize.x / GLOBAL_VIEWPORT.x, output->m_transformedSize.y / GLOBAL_VIEWPORT.y);
    const Vector2D center = output->m_transformedSize / 2.F;
    return {center + (logical.pos() - g_camera.center) * base * g_camera.currentScale, logical.size() * base * g_camera.currentScale};
}

void renderGlobalCanvas(PHLMONITOR output) {
    rebuildGlobalCanvas();
    const CBox fullOutput = {{0, 0}, output->m_transformedSize};
    CRectPassElement::SRectData backdrop{.box = fullOutput, .color = CHyprColor(0.02F, 0.03F, 0.05F, 1.F)};
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(backdrop));
    const auto time = Time::steadyNow();

    for (const auto& group : g_groups) {
        const CBox groupBox = screenBox(group.box, output);
        CRectPassElement::SRectData boundary{.box = groupBox, .color = group.monitor == g_monitor ? CHyprColor(0.20F, 0.10F, 0.32F, 1.F) : CHyprColor(0.07F, 0.09F, 0.14F, 1.F)};
        g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(boundary));

        for (const auto& card : group.cards) {
            const CBox cardBox = screenBox(card.box, output);
            const CBox previewBox = {cardBox.pos() + Vector2D{CARD_BORDER, CARD_BORDER}, cardBox.size() - Vector2D{2 * CARD_BORDER, 2 * CARD_BORDER}};
            CRectPassElement::SRectData cardBackground{.box = cardBox, .color = CHyprColor(0.12F, 0.15F, 0.20F, 1.F)};
            if (group.monitor == g_monitor && card.workspaceID == g_selectedWorkspaceID)
                cardBackground.color = CHyprColor(0.42F, 0.12F, 0.62F, 1.F);
            else if (card.workspaceID == (group.monitor->m_activeWorkspace ? group.monitor->m_activeWorkspace->m_id : 0))
                cardBackground.color = CHyprColor(0.10F, 0.35F, 0.14F, 1.F);
            g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(cardBackground));

            CRectPassElement::SRectData previewBackground{.box = previewBox, .color = CHyprColor(0.04F, 0.06F, 0.09F, 1.F)};
            g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(previewBackground));

            const float sourcePxToPreviewPx = previewBox.w / group.monitor->m_transformedSize.x;
            for (const auto& layers : {&group.monitor->m_layerSurfaceLayers[0], &group.monitor->m_layerSurfaceLayers[1]})
                for (const auto& layerRef : *layers)
                    if (const auto layer = layerRef.lock())
                        renderLayer(layer, group.monitor, output, sourcePxToPreviewPx, previewBox.pos(), previewBox, time);

            for (const bool floating : {false, true})
                for (const auto& window : g_pCompositor->m_windows)
                    if (window && window->m_workspace && window->m_workspace->m_monitor.lock() == group.monitor && window->m_workspace->m_id == card.workspaceID && window->m_isFloating == floating)
                        renderWindow(window, group.monitor, output, sourcePxToPreviewPx, previewBox.pos(), previewBox, time);
        }
    }
}

void render() {
    if (!g_open)
        return;
    if (!globalCanvas()) {
        renderSingleMonitor();
        return;
    }

    const auto output = g_pHyprRenderer->m_renderData.pMonitor.lock();
    if (output && output->m_enabled)
        renderGlobalCanvas(output);
}

SDispatchResult toggle(std::string) {
    if (g_open) {
        close();
        return {};
    }
    g_pendingOpenerSpaceRelease = false;
    g_monitor = g_pCompositor->getMonitorFromCursor();
    if (g_monitor) {
        g_open = true;
        g_pendingOpenerSpaceRelease = true;
        g_cards.clear();
        g_rowColumns.clear();
        g_selectedWorkspaceID = g_monitor->m_activeWorkspace ? g_monitor->m_activeWorkspace->m_id : 0;
        resetCamera();
        if (globalCanvas()) {
            rebuildGlobalCanvas();
            focusGlobalCamera();
        }
        damage();
    }
    return {};
}

} // namespace

APICALL EXPORT std::string PLUGIN_API_VERSION() {
    return HYPRLAND_API_VERSION;
}

APICALL EXPORT PLUGIN_DESCRIPTION_INFO PLUGIN_INIT(HANDLE handle) {
    HyprlandAPI::addDispatcherV2(handle, "spaces:toggle", toggle);
    g_renderHook = Event::bus()->m_events.render.stage.listen([](eRenderStage stage) {
        if (stage == eRenderStage::RENDER_LAST_MOMENT)
            render();
    });
    g_keyboardHook = Event::bus()->m_events.input.keyboard.key.listen([](const IKeyboard::SKeyEvent& event, Event::SCallbackInfo& info) {
        if (!g_open) {
            if (g_swallowEscapeRelease && event.keycode == KEY_ESC && event.state == WL_KEYBOARD_KEY_STATE_RELEASED) {
                info.cancelled = true;
                g_swallowEscapeRelease = false;
            }
            return;
        }
        if (g_pendingOpenerSpaceRelease && event.keycode == KEY_SPACE && event.state == WL_KEYBOARD_KEY_STATE_RELEASED) {
            g_pendingOpenerSpaceRelease = false;
            return;
        }
        if (event.keycode == KEY_LEFTSHIFT || event.keycode == KEY_RIGHTSHIFT)
            g_shiftHeld = event.state == WL_KEYBOARD_KEY_STATE_PRESSED;
        info.cancelled = true;
        if (event.keycode == KEY_ESC && event.state == WL_KEYBOARD_KEY_STATE_PRESSED) {
            g_swallowEscapeRelease = true;
            close();
            return;
        }
        if (event.state != WL_KEYBOARD_KEY_STATE_PRESSED)
        {
            if (event.keycode == KEY_ENTER && event.state == WL_KEYBOARD_KEY_STATE_RELEASED && g_pendingWorkspaceID > 0) {
                const int workspaceID = g_pendingWorkspaceID;
                g_pendingWorkspaceID = 0;
                // Hyprland creates an unknown numeric workspace on its focused
                // monitor, which must remain the monitor that owns this canvas.
                Config::Actions::focusMonitor(g_monitor);
                HyprlandAPI::invokeHyprctlCommand("dispatch", "workspace " + std::to_string(workspaceID));
                close();
                damage();
            }
            return;
        }

        switch (event.keycode) {
            case KEY_EQUAL:
            case KEY_KPPLUS:
                zoom(1.F);
                break;
            case KEY_MINUS:
            case KEY_KPMINUS:
                zoom(-1.F);
                break;
            case KEY_F12:
                // The canvas remains open while grim captures the rendered output.
                HyprlandAPI::invokeHyprctlCommand("dispatch", "exec grim -o " + g_monitor->m_name + " \"$HOME/Screenshots/hypr-spaces-$(date +%Y%m%d-%H%M%S).png\"");
                break;
            case KEY_TAB:
                if (globalCanvas())
                    selectMonitor(g_shiftHeld ? -1 : 1);
                break;
            case KEY_H:
                selectCard(-1, 0);
                break;
            case KEY_J:
                selectCard(0, 1);
                break;
            case KEY_K:
                selectCard(0, -1);
                break;
            case KEY_L:
                selectCard(1, 0);
                break;
            case KEY_ENTER:
                if (g_selectedWorkspaceID > 0)
                    g_pendingWorkspaceID = g_selectedWorkspaceID;
                break;
        }
    });
    g_mouseButtonHook = Event::bus()->m_events.input.mouse.button.listen([](const IPointer::SButtonEvent&, Event::SCallbackInfo& info) {
        info.cancelled = g_open;
    });
    g_mouseAxisHook = Event::bus()->m_events.input.mouse.axis.listen([](const IPointer::SAxisEvent& event, Event::SCallbackInfo& info) {
        if (!g_open)
            return;

        info.cancelled = true;
        // Two-finger scrolling and pinch remain available to a future canvas
        // pan/zoom handler. Wheel input is the only zoom gesture for now.
        if (event.source != WL_POINTER_AXIS_SOURCE_WHEEL || event.axis != WL_POINTER_AXIS_VERTICAL_SCROLL)
            return;

        // This event is emitted before CInputManager normalizes high-resolution
        // wheel units (such as +/-120) to application-facing +/-1 discrete steps.
        const float steps = event.deltaDiscrete != 0 ? -std::copysign(1.F, static_cast<float>(event.deltaDiscrete)) : -static_cast<float>(event.delta) / 15.F;
        if (steps == 0.F)
            return;
        zoom(steps * 0.08F);
    });
    g_mouseMoveHook = Event::bus()->m_events.input.mouse.move.listen([](const Vector2D&, Event::SCallbackInfo& info) {
        info.cancelled = g_open;
    });
    return {"hypr-spaces", "Live workspace canvas", "samov", "0.0.0"};
}

APICALL EXPORT void PLUGIN_EXIT() {
    g_renderHook.reset();
    g_keyboardHook.reset();
    g_mouseButtonHook.reset();
    g_mouseAxisHook.reset();
    g_mouseMoveHook.reset();
    close();
}
