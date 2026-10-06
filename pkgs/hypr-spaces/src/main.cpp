#include <hyprland/src/devices/IKeyboard.hpp>
#include <hyprland/src/devices/IPointer.hpp>
#include <hyprland/src/Compositor.hpp>
#include <hyprland/src/config/shared/actions/ConfigActions.hpp>
#include <hyprland/src/desktop/state/FocusState.hpp>
#include <hyprland/src/desktop/Workspace.hpp>
#include <hyprland/src/desktop/view/LayerSurface.hpp>
#include <hyprland/src/desktop/view/Window.hpp>
#include <hyprland/src/event/EventBus.hpp>
#include <hyprland/src/helpers/memory/Memory.hpp>
#include <hyprland/src/helpers/Monitor.hpp>
#include <hyprland/src/managers/input/InputManager.hpp>
#include <hyprland/src/layout/space/Space.hpp>
#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/plugins/PluginSystem.hpp>
#include <hyprland/src/render/Renderer.hpp>
#include <hyprland/src/render/pass/RectPassElement.hpp>
#include <hyprland/src/render/pass/RendererHintsPassElement.hpp>
#include <hyprland/src/render/pass/SurfacePassElement.hpp>
#include <hyprland/src/render/pass/TexPassElement.hpp>
#include <linux/input-event-codes.h>

#include "monitor_layout.hpp"
#include "canvas_model.hpp"
#include "preview_geometry.hpp"
#include "workspace_allocator.hpp"

#include <algorithm>
#include <cmath>
#include <ranges>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

bool                  g_open = false;
bool                  g_swallowEscapeRelease = false;
bool                  g_pendingOpenerSpaceRelease = false;
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
    bool  isTail = false;
};

struct SMonitorGroup {
    PHLMONITOR                 monitor;
    CBox                       box;
    std::vector<SWorkspaceCard> cards;
    std::vector<int>           rowColumns;
};

class CCanvasSurfacePassElement final : public CSurfacePassElement {
  public:
    CCanvasSurfacePassElement(const SRenderData& data, const CBox& bounds, float targetScale) : CSurfacePassElement(data) {
        const auto logical = hypr_spaces::targetPixelsToLogical({static_cast<float>(bounds.x), static_cast<float>(bounds.y), static_cast<float>(bounds.w), static_cast<float>(bounds.h)}, targetScale);
        m_bounds = {logical.x, logical.y, logical.width, logical.height};
    }

    std::optional<CBox> boundingBox() override {
        return m_bounds;
    }

    CRegion opaqueRegion() override {
        // Renderer hints transform this surface into its card after pass
        // simplification, so source-space opacity is invalid here.
        return {};
    }

  private:
    CBox m_bounds;
};

SCameraState                g_camera;
std::vector<SWorkspaceCard> g_cards;
std::vector<int>            g_rowColumns;
std::vector<SMonitorGroup>  g_groups;
struct STextCacheEntry {
    SP<Render::ITexture> texture;
    uint64_t lastUse;
    size_t bytes;
};
std::unordered_map<std::string, STextCacheEntry> g_titleTextures;
uint64_t                    g_textUse = 0;
size_t                      g_textBytes = 0;
int                         g_selectedWorkspaceID = 0;
bool                        g_selectedTail = false;
hypr_spaces::CanvasActivationLatch g_activation;
int                         g_gridRows = 0;
int                         g_gridColumns = 0;
bool                        g_emptyWorkspaceMode = false;

constexpr Vector2D GLOBAL_VIEWPORT = {1920.F, 1080.F};
constexpr float GROUP_GAP = 96.F;
constexpr float GROUP_PADDING = 48.F;
constexpr float CARD_GAP = 24.F;
constexpr float CARD_BORDER = 2.F;
constexpr float CARD_TITLE_HEIGHT = 56.F;

const CHyprColor WAYBAR_FOCUSED = CHyprColor(0.392F, 0.447F, 0.490F, 1.F); // #64727d
const CHyprColor WAYBAR_VISIBLE = CHyprColor(0.502F, 0.502F, 0.502F, 1.F); // #808080
const CHyprColor WAYBAR_TEXT = CHyprColor(1.F, 1.F, 1.F, 1.F);

void resetCamera() {
    g_camera = {};
}

bool globalCanvas() {
    return std::ranges::count_if(g_pCompositor->m_realMonitors, [](const auto& monitor) {
        return monitor && monitor->m_enabled && !monitor->isMirror();
    }) > 1;
}

void damage() {
    for (const auto& monitor : g_pCompositor->m_realMonitors)
        if (monitor && monitor->m_enabled && !monitor->isMirror())
            g_pHyprRenderer->damageMonitor(monitor);
}

SP<Render::ITexture> titleTexture(const std::string& title, int pointSize, bool accent = false, int weight = 400) {
    const auto key = title + ":" + std::to_string(pointSize) + ":" + std::to_string(accent) + ":" + std::to_string(weight);
    if (auto it = g_titleTextures.find(key); it != g_titleTextures.end()) {
        it->second.lastUse = ++g_textUse;
        return it->second.texture;
    }
    auto texture = g_pHyprRenderer->renderText(title, accent ? WAYBAR_FOCUSED : WAYBAR_TEXT, std::max(1, pointSize), false, "Noto Sans", 0, weight);
    if (!texture)
        return texture;
    const size_t bytes = static_cast<size_t>(texture->m_size.x) * static_cast<size_t>(texture->m_size.y) * 4;
    constexpr size_t maxEntries = 256;
    constexpr size_t maxBytes = 16 * 1024 * 1024;
    if (bytes > maxBytes)
        return texture;
    while (!g_titleTextures.empty() && (g_titleTextures.size() >= maxEntries || g_textBytes + bytes > maxBytes)) {
        const auto oldest = std::ranges::min_element(g_titleTextures, {}, [](const auto& item) { return item.second.lastUse; });
        g_textBytes -= oldest->second.bytes;
        g_titleTextures.erase(oldest);
    }
    g_titleTextures.emplace(key, STextCacheEntry{texture, ++g_textUse, bytes});
    g_textBytes += bytes;
    return texture;
}

void renderCardTitle(const CBox& cardBox, int workspaceID, bool active, float outputScale) {
    const std::string title = std::to_string(workspaceID);
    const auto texture = titleTexture(title, std::lround(26 * outputScale), false, active ? 600 : 400);
    if (!texture)
        return;

    const float headerHeight = std::min(CARD_TITLE_HEIGHT * outputScale, std::max(0.F, static_cast<float>(cardBox.h) - 2 * CARD_BORDER));
    if (headerHeight < 2.F)
        return;
    const CBox headerBox = {cardBox.pos() + Vector2D{CARD_BORDER, CARD_BORDER}, {cardBox.w - 2 * CARD_BORDER, headerHeight}};
    CRectPassElement::SRectData header{.box = headerBox, .color = CHyprColor(0.169F, 0.188F, 0.231F, 0.58F), .blur = true, .blurA = 0.58F};
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(header));
    CRectPassElement::SRectData headerBorder{.box = {Vector2D{headerBox.x, headerBox.y + headerBox.h - 1.F}, Vector2D{headerBox.w, 1.F}}, .color = CHyprColor(0.392F, 0.447F, 0.490F, 0.62F)};
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(headerBorder));

    CTexPassElement::SRenderData data;
    data.tex = texture;
    data.box = {cardBox.x + (cardBox.w - texture->m_size.x) / 2.F, headerBox.y + (headerBox.h - texture->m_size.y) / 2.F, texture->m_size.x, texture->m_size.y};
    data.clipBox = headerBox;
    data.a = 1.F;
    g_pHyprRenderer->m_renderPass.add(makeUnique<CTexPassElement>(std::move(data)));
}

void renderTailCrown(const CBox& cardBox) {
    const float diameter = std::min(static_cast<float>(cardBox.w), static_cast<float>(cardBox.h)) * 0.45F;
    const CBox circleBox = {{cardBox.x + (cardBox.w - diameter) / 2.F, cardBox.y + (cardBox.h - diameter) / 2.F}, {diameter, diameter}};
    CRectPassElement::SRectData circle{.box = circleBox, .color = CHyprColor(0.169F, 0.188F, 0.231F, 0.58F), .round = static_cast<int>(diameter / 2.F)};
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(circle));

    const std::string title = "+";
    const auto texture = titleTexture(title, static_cast<int>(diameter * 0.58F));
    if (!texture)
        return;

    CTexPassElement::SRenderData data;
    data.tex = texture;
    data.box = {circleBox.x + (circleBox.w - texture->m_size.x) / 2.F, circleBox.y + (circleBox.h - texture->m_size.y) / 2.F, texture->m_size.x, texture->m_size.y};
    data.a = 1.F;
    g_pHyprRenderer->m_renderPass.add(makeUnique<CTexPassElement>(std::move(data)));
}

CBox previewBoxFor(const CBox& cardBox) {
    return {cardBox.pos() + Vector2D{CARD_BORDER, CARD_BORDER}, cardBox.size() - Vector2D{2 * CARD_BORDER, 2 * CARD_BORDER}};
}

void zoom(float steps) {
    constexpr float minScale = 0.35F;
    constexpr float maxScale = 2.50F;

    g_camera.targetScale = std::clamp(g_camera.targetScale * std::pow(1.12F, steps), minScale, maxScale);
    // Keep zoom immediate until camera animation has a dedicated damage loop.
    g_camera.currentScale = g_camera.targetScale;
    damage();
}

void close() {
    g_open = false;
    g_pendingOpenerSpaceRelease = false;
    g_groups.clear();
    g_cards.clear();
    g_rowColumns.clear();
    g_selectedWorkspaceID = 0;
    g_selectedTail = false;
    g_activation.cancel();
    g_titleTextures.clear();
    g_textBytes = 0;
    g_gridRows = 0;
    g_gridColumns = 0;
    g_emptyWorkspaceMode = false;
    resetCamera();
    damage();
}

hypr_spaces::CanvasSelection currentSelection() {
    return {g_monitor ? static_cast<int>(g_monitor->m_id) : -1, g_selectedWorkspaceID, g_selectedTail};
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
        g_selectedTail = destination->isTail;
        damage();
    }
}

void renderWindow(PHLWINDOW window, PHLMONITOR source, PHLMONITOR target, float sourcePxToPreviewPx, const Vector2D& previewOrigin, const CBox& clipBox, const Time::steady_tp& time) {
    if (!window || !window->m_isMapped || !window->wlSurface() || !window->wlSurface()->resource())
        return;

    const auto position = window->m_realPosition->goal() + window->m_floatingOffset;
    const auto size = window->m_realSize->goal();
    if (size.x < 1 || size.y < 1)
        return;

    const float scale = sourcePxToPreviewPx * source->m_scale / target->m_scale;
    const auto preview = hypr_spaces::windowPreviewBox(
        {static_cast<float>(position.x), static_cast<float>(position.y), static_cast<float>(size.x), static_cast<float>(size.y)},
        source->m_position.x, source->m_position.y, source->m_scale * sourcePxToPreviewPx, previewOrigin.x, previewOrigin.y);
    const Vector2D destination = {preview.x, preview.y};
    Render::SRenderModifData transform;
    transform.enabled = true;
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_TRANSLATE, std::any(destination / scale - destination)});
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_SCALE, std::any(scale)});
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = transform}));

    CSurfacePassElement::SRenderData data = {target, time};
    data.pos = target->m_position + destination / target->m_scale;
    data.w = size.x;
    data.h = size.y;
    data.surface = window->wlSurface()->resource();
    data.pWindow = window;
    data.clipBox = clipBox;
    data.decorate = false;
    data.blur = false;
    // Focus remains in Hyprland while the canvas is open, but the window's
    // animated alpha can have already transitioned to inactive. Preserve the
    // focused thumbnail as opaque and use the configured inactive opacity for
    // the rest.
    data.alpha = Desktop::focusState()->window() == window ? 1.F : window->alphaValue(Desktop::View::WINDOW_ALPHA_ACTIVE);
    data.fadeAlpha = 1.F;
    data.surfaceCounter = 0;

    window->wlSurface()->resource()->breadthfirst(
        [&data, &window, &clipBox, &target](SP<CWLSurfaceResource> surface, const Vector2D& offset, void*) {
            if (!surface || !surface->m_current.texture || surface->m_current.size.x < 1 || surface->m_current.size.y < 1)
                return;
            data.localPos = offset;
            data.texture = surface->m_current.texture;
            data.surface = surface;
            data.mainSurface = surface == window->wlSurface()->resource();
            g_pHyprRenderer->m_renderPass.add(makeUnique<CCanvasSurfacePassElement>(data, clipBox, target->m_scale));
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
    const Vector2D destination = previewOrigin + sourcePosition * sourcePxToPreviewPx;
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_TRANSLATE, std::any(destination / scale - destination)});
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_SCALE, std::any(scale)});
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = transform}));

    CSurfacePassElement::SRenderData data = {target, time, position};
    data.pos = target->m_position + destination / target->m_scale;
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
        [&data, &layer, &clipBox, &target](SP<CWLSurfaceResource> surface, const Vector2D& offset, void*) {
            if (!surface || !surface->m_current.texture || surface->m_current.size.x < 1 || surface->m_current.size.y < 1)
                return;
            data.localPos = offset;
            data.texture = surface->m_current.texture;
            data.surface = surface;
            data.mainSurface = surface == layer->wlSurface()->resource();
            g_pHyprRenderer->m_renderPass.add(makeUnique<CCanvasSurfacePassElement>(data, clipBox, target->m_scale));
            data.surfaceCounter++;
        },
        &data);

    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = Render::SRenderModifData{}}));
}

SMonitorGroup* groupFor(PHLMONITOR monitor) {
    const auto group = std::ranges::find(g_groups, monitor, &SMonitorGroup::monitor);
    return group == g_groups.end() ? nullptr : &*group;
}

void focusGlobalCamera(bool resetZoom = false) {
    const auto* group = groupFor(g_monitor);
    if (!group)
        return;

    g_camera.center = group->box.pos() + group->box.size() / 2.F;
    if (resetZoom) {
        g_camera.currentScale = globalCanvas() ? 0.8064F : 1.F;
        g_camera.targetScale = g_camera.currentScale;
    }
    g_camera.currentOffset = {};
    g_camera.targetOffset = {};
}

PHLMONITOR adjacentMonitor(PHLMONITOR current, int direction) {
    if (direction == 0)
        return nullptr;
    if (!current)
        return nullptr;

    std::vector<PHLMONITOR> monitors;
    std::vector<hypr_spaces::MonitorRect> rectangles;
    for (const auto& monitor : g_pCompositor->m_realMonitors) {
        if (!monitor || !monitor->m_enabled || monitor->isMirror() || monitor->m_size.x < 1 || monitor->m_size.y < 1)
            continue;
        monitors.push_back(monitor);
        rectangles.push_back({static_cast<int>(monitor->m_id), static_cast<int>(monitor->m_position.x), static_cast<int>(monitor->m_position.y),
                              static_cast<int>(monitor->m_size.x), static_cast<int>(monitor->m_size.y)});
    }

    const auto order = hypr_spaces::monitorTabOrder(rectangles);
    const auto position = std::ranges::find(order, static_cast<int>(current->m_id));
    if (order.size() < 2 || position == order.end())
        return nullptr;

    const auto index = (std::distance(order.begin(), position) + direction + static_cast<int>(order.size())) % order.size();
    const auto target = std::ranges::find_if(monitors, [&order, index](const auto& monitor) { return static_cast<int>(monitor->m_id) == order[index]; });
    return target == monitors.end() ? nullptr : *target;
}

int monitorDirection(const std::string& argument) {
    if (argument == "next")
        return 1;
    if (argument == "previous")
        return -1;
    return 0;
}

SDispatchResult focusAdjacentMonitor(std::string argument) {
    if (const auto target = adjacentMonitor(Desktop::focusState()->monitor(), monitorDirection(argument)))
        Config::Actions::focusMonitor(target);
    return {};
}

SDispatchResult moveWorkspaceToAdjacentMonitor(std::string argument) {
    const auto current = Desktop::focusState()->monitor();
    if (const auto target = adjacentMonitor(current, monitorDirection(argument)); current && target && current->m_activeWorkspace)
        Config::Actions::moveToMonitor(current->m_activeWorkspace, target);
    return {};
}

void rebuildGlobalCanvas() {
    const auto previousSelection = currentSelection();
    std::vector<PHLMONITOR> monitors;
    std::vector<hypr_spaces::MonitorRect> rectangles;
    for (const auto& monitor : g_pCompositor->m_realMonitors) {
        if (!monitor || !monitor->m_enabled || monitor->isMirror() || monitor->m_size.x < 1 || monitor->m_size.y < 1)
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

    std::vector<hypr_spaces::WorkspaceState>  workspaceStates;
    for (const auto& workspaceRef : g_pCompositor->getWorkspaces()) {
        const auto workspace = workspaceRef.lock();
        const auto owner = workspace ? workspace->m_monitor.lock() : nullptr;
        if (workspace && workspace->m_id > 0)
            workspaceStates.push_back({static_cast<int>(workspace->m_id), owner ? static_cast<int>(owner->m_id) : -1, workspace->getWindows() > 0});
    }
    std::vector<hypr_spaces::CanvasMonitor> monitorStates;
    for (const auto& group : g_groups)
        monitorStates.push_back({static_cast<int>(group.monitor->m_id), group.monitor->m_activeWorkspace ? static_cast<int>(group.monitor->m_activeWorkspace->m_id) : 0});
    const auto model = hypr_spaces::buildCanvasModel(monitorStates, workspaceStates, currentSelection());
    if (model.groups.empty()) {
        close();
        g_monitor.reset();
        return;
    }
    g_emptyWorkspaceMode = model.noWindows;
    for (size_t i = 0; i < model.groups.size(); ++i) {
        for (const auto& card : model.groups[i].cards)
            g_groups[i].cards.emplace_back(card.id, CBox{}, 0, 0, card.crown);
        if (model.groups[i].monitor.id == model.selection.owner)
            g_monitor = g_groups[i].monitor;
    }
    g_selectedWorkspaceID = model.selection.id;
    g_selectedTail = model.selection.crown;

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

    const auto* selectedGroup = groupFor(g_monitor);
    g_cards = selectedGroup ? selectedGroup->cards : std::vector<SWorkspaceCard>{};
    g_rowColumns = selectedGroup ? selectedGroup->rowColumns : std::vector<int>{};
    g_gridRows = static_cast<int>(g_rowColumns.size());
    g_gridColumns = g_gridRows > 0 ? *std::ranges::max_element(g_rowColumns) : 0;
    if (currentSelection() != previousSelection)
        g_activation.cancel();
    // Recenter after hotplug/layout changes without resetting the user's zoom.
    focusGlobalCamera();
}

void selectMonitor(int direction) {
    const auto current = std::ranges::find(g_groups, g_monitor, &SMonitorGroup::monitor);
    if (current == g_groups.end() || g_groups.empty())
        return;

    const auto index = (std::distance(g_groups.begin(), current) + direction + static_cast<int>(g_groups.size())) % g_groups.size();
    const auto selected = g_groups.begin() + index;

    g_monitor = selected->monitor;
    g_selectedWorkspaceID = g_monitor->m_activeWorkspace ? g_monitor->m_activeWorkspace->m_id : 0;
    g_selectedTail = false;
    rebuildGlobalCanvas(); // adds the destination crown before resolving selection
    damage();
}

void moveSelectedWorkspace(int direction) {
    rebuildGlobalCanvas();
    if (!g_monitor)
        return;

    const auto workspace = g_pCompositor->getWorkspaceByID(g_selectedWorkspaceID);
    const auto owner = workspace ? workspace->m_monitor.lock() : nullptr;
    const auto target = adjacentMonitor(g_monitor, direction);
    if (!target)
        return;

    if (!workspace) {
        // A virtual regular card has no Hyprland workspace to move. Materialize
        // it on the target, replacing that monitor's active empty head.
        if (g_selectedTail)
            return;
        if (!Config::Actions::focusMonitor(target) || !Config::Actions::changeWorkspace(std::to_string(g_selectedWorkspaceID)))
            return;
        const auto created = g_pCompositor->getWorkspaceByID(g_selectedWorkspaceID);
        if (!created || created->m_monitor.lock() != target)
            return;
        g_monitor = target;
        rebuildGlobalCanvas();
        focusGlobalCamera();
        damage();
        return;
    }

    if (!owner || owner != g_monitor)
        return;

    // An empty workspace survives a move only while it is active on its source.
    if (workspace->getWindows() == 0) {
        if (!Config::Actions::focusMonitor(g_monitor) || !Config::Actions::changeWorkspace(workspace))
            return;
    }
    if (!Config::Actions::moveToMonitor(workspace, target) || workspace->m_monitor.lock() != target)
        return;
    // Recalculate only the move explicitly initiated by the canvas. Hyprland
    // also emits workspace.moveToMonitor while tearing down an unplugged output.
    if (workspace->m_space)
        workspace->m_space->recalculate();
    g_monitor = target;
    rebuildGlobalCanvas();
    focusGlobalCamera();
    damage();
}

CBox screenBox(const CBox& logical, PHLMONITOR output) {
    const float base = std::min(output->m_transformedSize.x / GLOBAL_VIEWPORT.x, output->m_transformedSize.y / GLOBAL_VIEWPORT.y);
    const Vector2D center = output->m_transformedSize / 2.F;
    return {center + (logical.pos() - g_camera.center) * base * g_camera.currentScale, logical.size() * base * g_camera.currentScale};
}

void renderWorkspaceOutline(PHLMONITOR output) {
    struct SOutlinePart {
        std::string text;
        bool        accent;
        int         weight;
    };

    const float     margin = 24.F * output->m_scale;
    const float     lineGap = 10.F * output->m_scale;
    const int       pointSize = std::lround(20 * output->m_scale);
    const CBox      clip = {{margin - 8.F * output->m_scale, margin - 4.F * output->m_scale},
                            output->m_transformedSize - Vector2D{2 * margin - 16.F * output->m_scale, 2 * margin - 8.F * output->m_scale}};
    float           y = margin;
    for (const auto& group : g_groups) {
        const bool selectedMonitor = group.monitor == g_monitor;
        const int activeWorkspaceID = group.monitor->m_activeWorkspace ? group.monitor->m_activeWorkspace->m_id : 0;
        std::vector<SOutlinePart> parts = {{group.monitor->m_name + ": [", false, selectedMonitor ? 700 : 400}};
        for (const auto& card : group.cards) {
            if (card.isTail)
                continue;
            const bool selectedCard = selectedMonitor && !g_selectedTail && card.workspaceID == g_selectedWorkspaceID;
            parts.push_back({std::to_string(card.workspaceID), selectedCard, card.workspaceID == activeWorkspaceID ? 600 : 400});
            parts.push_back({" ", false, 400});
        }
        if (selectedMonitor && g_selectedTail)
            parts.push_back({"... ", true, 400});
        parts.push_back({"]", false, selectedMonitor ? 700 : 400});

        float width = 0.F;
        float height = 0.F;
        for (const auto& part : parts) {
            const auto texture = titleTexture(part.text, pointSize, part.accent, part.weight);
            if (texture) {
                width += texture->m_size.x;
                height = std::max(height, static_cast<float>(texture->m_size.y));
            }
        }
        if (y + height > clip.y + clip.h)
            break;
        const CBox background = {{clip.x, y - 4.F * output->m_scale},
                                 {std::min(static_cast<double>(width + 16.F * output->m_scale), clip.w), height + 8.F * output->m_scale}};
        CRectPassElement::SRectData backgroundData{.box = background, .color = CHyprColor(0.169F, 0.188F, 0.231F, 0.78F)};
        g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(backgroundData));

        float x = margin;
        for (const auto& part : parts) {
            const auto texture = titleTexture(part.text, pointSize, part.accent, part.weight);
            if (!texture)
                continue;
            CTexPassElement::SRenderData data;
            data.tex = texture;
            data.box = {x, y + (height - texture->m_size.y) / 2.F, texture->m_size.x, texture->m_size.y};
            data.clipBox = clip;
            data.a = 1.F;
            g_pHyprRenderer->m_renderPass.add(makeUnique<CTexPassElement>(std::move(data)));
            x += texture->m_size.x;
        }
        y += height + lineGap;
    }
}

void renderGlobalCanvas(PHLMONITOR output) {
    rebuildGlobalCanvas();
    if (!g_open)
        return;
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
            const CBox previewBox = previewBoxFor(cardBox);
            CRectPassElement::SRectData cardBackground{.box = cardBox, .color = CHyprColor(0.12F, 0.15F, 0.20F, 1.F)};
            if (group.monitor == g_monitor && card.workspaceID == g_selectedWorkspaceID && card.isTail == g_selectedTail)
                cardBackground.color = WAYBAR_FOCUSED;
            else if (card.workspaceID == (group.monitor->m_activeWorkspace ? group.monitor->m_activeWorkspace->m_id : 0))
                cardBackground.color = WAYBAR_VISIBLE;
            g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(cardBackground));

            CRectPassElement::SRectData previewBackground{.box = previewBox, .color = CHyprColor(0.04F, 0.06F, 0.09F, 1.F)};
            g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(previewBackground));

            const float sourcePxToPreviewPx = previewBox.w / group.monitor->m_transformedSize.x;
            for (const auto& layers : {&group.monitor->m_layerSurfaceLayers[0], &group.monitor->m_layerSurfaceLayers[1]})
                for (const auto& layerRef : *layers)
                    if (const auto layer = layerRef.lock())
                        renderLayer(layer, group.monitor, output, sourcePxToPreviewPx, previewBox.pos(), previewBox, time);

            if (card.isTail) {
                renderCardTitle(cardBox, card.workspaceID, card.workspaceID == (group.monitor->m_activeWorkspace ? group.monitor->m_activeWorkspace->m_id : 0), output->m_scale);
                renderTailCrown(cardBox);
                continue;
            }

            for (const bool floating : {false, true})
                for (const auto& window : g_pCompositor->m_windows)
                    if (window && window->m_workspace && window->m_workspace->m_monitor.lock() == group.monitor && window->m_workspace->m_id == card.workspaceID && window->m_isFloating == floating)
                        renderWindow(window, group.monitor, output, sourcePxToPreviewPx, previewBox.pos(), previewBox, time);
            renderCardTitle(cardBox, card.workspaceID, card.workspaceID == (group.monitor->m_activeWorkspace ? group.monitor->m_activeWorkspace->m_id : 0), output->m_scale);
        }
    }
    renderWorkspaceOutline(output);
    // Every viewport contains surfaces from every output. Native surface damage
    // is in desktop coordinates, so it cannot invalidate these thumbnails.
    // Keep a refresh-rate-paced full redraw while open; close() stops the loop.
    g_pHyprRenderer->damageMonitor(output);
}

void render() {
    if (!g_open)
        return;
    const auto output = g_pHyprRenderer->m_renderData.pMonitor.lock();
    if (output && output->m_enabled && !output->isMirror())
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
        rebuildGlobalCanvas();
        focusGlobalCamera(true);
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
    HyprlandAPI::addDispatcherV2(handle, "spaces:focus-monitor", focusAdjacentMonitor);
    HyprlandAPI::addDispatcherV2(handle, "spaces:move-workspace", moveWorkspaceToAdjacentMonitor);
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
            if (event.keycode == KEY_ENTER && event.state == WL_KEYBOARD_KEY_STATE_RELEASED && g_activation.held()) {
                g_activation.release({}, false);
                info.cancelled = true;
            }
            return;
        }
        if (g_pendingOpenerSpaceRelease && event.keycode == KEY_SPACE && event.state == WL_KEYBOARD_KEY_STATE_RELEASED) {
            g_pendingOpenerSpaceRelease = false;
            return;
        }
        info.cancelled = true;
        if (event.state == WL_KEYBOARD_KEY_STATE_PRESSED && event.keycode != KEY_ENTER)
            g_activation.cancel();
        if (event.keycode == KEY_ESC && event.state == WL_KEYBOARD_KEY_STATE_PRESSED) {
            g_swallowEscapeRelease = true;
            close();
            return;
        }
        if (event.state != WL_KEYBOARD_KEY_STATE_PRESSED)
        {
            if (event.keycode == KEY_ENTER && event.state == WL_KEYBOARD_KEY_STATE_RELEASED) {
                rebuildGlobalCanvas();
                const auto activation = g_activation.release(currentSelection(), g_emptyWorkspaceMode);
                if (!g_open || !activation || !g_monitor)
                    return;
                if (!Config::Actions::focusMonitor(g_monitor))
                    return;
                if (!activation->focusOnly && !Config::Actions::changeWorkspace(std::to_string(activation->selection.id)))
                    return;
                close();
            }
            return;
        }

        rebuildGlobalCanvas();
        if (!g_open)
            return;
        const auto modifiers = g_pInputManager->getModsFromAllKBs();
        const int direction = (modifiers & HL_MODIFIER_SHIFT) ? -1 : 1;
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
                if (globalCanvas() && (modifiers & HL_MODIFIER_CTRL))
                    moveSelectedWorkspace(direction);
                else if (globalCanvas())
                    selectMonitor(direction);
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
                g_activation.press(currentSelection(), g_emptyWorkspaceMode);
                break;
        }
    });
    g_mouseButtonHook = Event::bus()->m_events.input.mouse.button.listen([](const IPointer::SButtonEvent&, Event::SCallbackInfo& info) {
        info.cancelled = g_open;
        if (g_open)
            g_activation.cancel();
    });
    g_mouseAxisHook = Event::bus()->m_events.input.mouse.axis.listen([](const IPointer::SAxisEvent& event, Event::SCallbackInfo& info) {
        if (!g_open)
            return;

        info.cancelled = true;
        g_activation.cancel();
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
