#include <hyprland/src/devices/IKeyboard.hpp>
#include <hyprland/src/devices/IPointer.hpp>
#include <hyprland/src/Compositor.hpp>
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

namespace {

bool                  g_open = false;
bool                  g_swallowEscapeRelease = false;
PHLMONITOR            g_monitor;
CHyprSignalListener   g_renderHook;
CHyprSignalListener   g_keyboardHook;
CHyprSignalListener   g_mouseButtonHook;
CHyprSignalListener   g_mouseAxisHook;

void damage() {
    if (g_monitor)
        g_pHyprRenderer->damageMonitor(g_monitor);
}

void close() {
    g_open = false;
    damage();
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

void render() {
    if (!g_open || !g_monitor || g_pHyprRenderer->m_renderData.pMonitor != g_monitor)
        return;

    const CBox fullMonitor = {{0, 0}, g_monitor->m_transformedSize};
    CRectPassElement::SRectData backdrop;
    backdrop.box = fullMonitor;
    backdrop.color = CHyprColor(0.02F, 0.03F, 0.05F, 1.F);
    g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(backdrop));

    constexpr float padding = 64.F;
    const float scale = std::min((g_monitor->m_transformedSize.x - 2 * padding) / g_monitor->m_transformedSize.x,
                                 (g_monitor->m_transformedSize.y - 2 * padding) / g_monitor->m_transformedSize.y);
    const Vector2D previewSize = g_monitor->m_transformedSize * scale;
    const Vector2D origin = (g_monitor->m_transformedSize - previewSize) / 2.F;

    for (const auto& window : g_pCompositor->m_windows) {
        if (window && window->m_workspace == g_monitor->m_activeWorkspace && !window->m_isFloating)
            renderWindow(window, g_monitor, scale, origin, fullMonitor, Time::steadyNow());
    }
    for (const auto& window : g_pCompositor->m_windows) {
        if (window && window->m_workspace == g_monitor->m_activeWorkspace && window->m_isFloating)
            renderWindow(window, g_monitor, scale, origin, fullMonitor, Time::steadyNow());
    }
    damage();
}

SDispatchResult toggle(std::string) {
    if (g_open) {
        close();
        return {};
    }
    g_monitor = g_pCompositor->getMonitorFromCursor();
    if (g_monitor) {
        g_open = true;
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
        info.cancelled = true;
        if (event.keycode == KEY_ESC && event.state == WL_KEYBOARD_KEY_STATE_PRESSED) {
            g_swallowEscapeRelease = true;
            close();
        }
    });
    g_mouseButtonHook = Event::bus()->m_events.input.mouse.button.listen([](const IPointer::SButtonEvent&, Event::SCallbackInfo& info) {
        info.cancelled = g_open;
    });
    g_mouseAxisHook = Event::bus()->m_events.input.mouse.axis.listen([](const IPointer::SAxisEvent&, Event::SCallbackInfo& info) {
        info.cancelled = g_open;
    });
    return {"hypr-spaces", "Live workspace canvas", "samov", "0.0.0"};
}

APICALL EXPORT void PLUGIN_EXIT() {
    g_renderHook.reset();
    g_keyboardHook.reset();
    g_mouseButtonHook.reset();
    g_mouseAxisHook.reset();
    close();
}
