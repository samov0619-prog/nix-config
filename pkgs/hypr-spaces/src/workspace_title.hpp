#pragma once

#include <algorithm>
#include <cctype>
#include <string>

namespace hypr_spaces {

struct WorkspaceTitle {
    std::string primary;
    std::string secondary;
};

// One logical line; preserve UTF-8, but never render terminal/control escapes.
inline std::string titleLine(std::string text) {
    for (auto& ch : text)
        if (static_cast<unsigned char>(ch) < 32 || ch == 127)
            ch = ' ';
    const auto first = text.find_first_not_of(' ');
    if (first == std::string::npos)
        return {};
    return text.substr(first, text.find_last_not_of(' ') - first + 1);
}

inline std::string displayPath(const std::string& path, const std::string& home) {
    if (!home.empty() && (path == home || path.starts_with(home + "/")))
        return "~" + path.substr(home.size());
    return titleLine(path);
}

inline std::string pathLeaf(std::string path) {
    while (path.size() > 1 && path.back() == '/')
        path.pop_back();
    const auto slash = path.find_last_of('/');
    return slash == std::string::npos ? path : slash + 1 == path.size() ? path : path.substr(slash + 1);
}

inline std::string appName(const std::string& app) {
    if (app == "google-chrome" || app == "google-chrome-stable") return "Chrome";
    if (app == "chromium") return "Chromium";
    if (app == "firefox" || app == "org.mozilla.firefox") return "Firefox";
    if (app == "kitty") return "Kitty";
    if (app == "Alacritty" || app == "org.alacritty.Alacritty") return "Alacritty";
    if (app == "mpv" || app == "io.mpv.Mpv") return "MPV";
    if (app == "org.blender.Blender" || app == "blender") return "Blender";
    return titleLine(app);
}

inline WorkspaceTitle windowTitle(const std::string& app, const std::string& title) {
    const auto name = appName(app);
    auto text = titleLine(title);
    // Browser titles commonly already contain their application name.
    for (const auto& suffix : {" - Google Chrome", " — Mozilla Firefox", " - Chromium"})
        if (text.ends_with(suffix))
            text.resize(text.size() - std::string(suffix).size());
    if (app == "kitty" || app == "Alacritty" || app == "org.alacritty.Alacritty") {
        if (text.starts_with("OC | ")) text.erase(0, 5);
        if (text.starts_with("Yazi: ")) text.erase(0, 6);
        for (const auto& label : {"OpenCode", "opencode", "Neovim", "nvim", "Yazi", "yazi", "Fish", "fish", "bash", "zsh"})
            if (text == label) return {};
    }
    if (text.empty() || text == name || text == app) return {};
    return {text, {}};
}

inline WorkspaceTitle terminalTitle(const std::string& app, const std::string& title, const std::string& cwd, const std::string& home, bool published = false) {
    const auto path = displayPath(cwd, home);
    const auto text = titleLine(title);
    if (app == "opencode") {
        auto session = text;
        // Publisher data is a real session name, even when it happens to look
        // like an application label or the ordinary terminal-title prefix.
        if (!published) {
            if (session.starts_with("OC | ")) session.erase(0, 5);
            if (session == "OpenCode") session.clear();
        }
        return session.empty() ? WorkspaceTitle{path, {}} : WorkspaceTitle{session, path};
    }
    if (app == "nvim" || app == "yazi") {
        return {path, {}};
    }
    const bool shell = app == "fish" || app == "bash" || app == "zsh";
    if (shell || text.empty() || text == app || text == appName(app) || text == path)
        return {path, {}};
    return {text, path};
}

} // namespace hypr_spaces
