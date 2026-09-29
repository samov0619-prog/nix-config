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

#include <algorithm>
#include <cmath>
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
};

struct SWorkspaceCard {
    int   workspaceID = 0;
    CBox  box;
    int   row = 0;
    int   column = 0;
};

SCameraState                g_camera;
std::vector<SWorkspaceCard> g_cards;
std::vector<int>            g_rowColumns;
int                         g_selectedWorkspaceID = 0;
int                         g_pendingWorkspaceID = 0;
int                         g_gridRows = 0;
int                         g_gridColumns = 0;

void resetCamera() {
    g_camera = {};
}

void damage() {
    if (g_monitor)
        g_pHyprRenderer->damageMonitor(g_monitor);
}

void close() {
    g_open = false;
    g_pendingOpenerSpaceRelease = false;
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

void renderWindow(PHLWINDOW window, PHLMONITOR monitor, float scale, const Vector2D& origin, const CBox& clipBox, const Time::steady_tp& time) {
    if (!window || !window->m_isMapped || !window->wlSurface() || !window->wlSurface()->resource())
        return;

    const auto position = window->m_realPosition->value() + window->m_floatingOffset;
    const auto size = window->m_realSize->value();
    if (size.x < 1 || size.y < 1)
        return;

    const Vector2D sourcePosition = (position - monitor->m_position) * monitor->m_scale;
    Render::SRenderModifData transform;
    transform.enabled = true;
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_TRANSLATE, std::any(origin / scale - sourcePosition)});
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_SCALE, std::any(scale)});
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = transform}));

    CSurfacePassElement::SRenderData data = {monitor, time};
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

void renderLayer(PHLLS layer, PHLMONITOR monitor, const CBox& box, const CBox& clipBox, const Time::steady_tp& time) {
    if (!layer || !layer->m_mapped || layer->m_readyToDelete || !layer->m_layerSurface || !layer->wlSurface() || !layer->wlSurface()->resource())
        return;

    const auto position = layer->m_realPosition->value();
    const auto size = layer->m_realSize->value();
    const float scale = box.w / size.x;
    if (!(scale > 0.F) || size.x < 1 || size.y < 1)
        return;

    Render::SRenderModifData transform;
    transform.enabled = true;
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_TRANSLATE, std::any(monitor->m_position + box.pos() / scale - position)});
    transform.modifs.push_back({Render::SRenderModifData::eRenderModifType::RMOD_TYPE_SCALE, std::any(scale)});
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRendererHintsPassElement>(CRendererHintsPassElement::SData{.renderModif = transform}));

    CSurfacePassElement::SRenderData data = {monitor, time, position};
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

void render() {
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
            if (layer) {
                const CBox layerBox = {previewBox.pos() + (layer->m_realPosition->value() - g_monitor->m_position) * g_monitor->m_scale * scale,
                                       layer->m_realSize->value() * g_monitor->m_scale * scale};
                renderLayer(layer, g_monitor, layerBox, previewBox, time);
            }
        }
        for (const auto& layerRef : g_monitor->m_layerSurfaceLayers[1]) {
            const auto layer = layerRef.lock();
            if (layer) {
                const CBox layerBox = {previewBox.pos() + (layer->m_realPosition->value() - g_monitor->m_position) * g_monitor->m_scale * scale,
                                       layer->m_realSize->value() * g_monitor->m_scale * scale};
                renderLayer(layer, g_monitor, layerBox, previewBox, time);
            }
        }
        if (!workspaces[index])
            continue;
        for (const auto& window : g_pCompositor->m_windows) {
            if (window && window->m_workspace == workspaces[index] && !window->m_isFloating) {
                const auto position = window->m_realPosition->value() + window->m_floatingOffset;
                const Vector2D target = previewBox.pos() + (position - g_monitor->m_position) * g_monitor->m_scale * scale;
                renderWindow(window, g_monitor, scale, target, previewBox, time);
            }
        }
        for (const auto& window : g_pCompositor->m_windows) {
            if (window && window->m_workspace == workspaces[index] && window->m_isFloating) {
                const auto position = window->m_realPosition->value() + window->m_floatingOffset;
                const Vector2D target = previewBox.pos() + (position - g_monitor->m_position) * g_monitor->m_scale * scale;
                renderWindow(window, g_monitor, scale, target, previewBox, time);
            }
        }
    }
    damage();
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
    g_mouseAxisHook = Event::bus()->m_events.input.mouse.axis.listen([](const IPointer::SAxisEvent&, Event::SCallbackInfo& info) {
        info.cancelled = g_open;
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
