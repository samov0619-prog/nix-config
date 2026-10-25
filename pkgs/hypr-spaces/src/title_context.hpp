#pragma once

#include "workspace_title.hpp"

#include <condition_variable>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <filesystem>
#include <mutex>
#include <nlohmann/json.hpp>
#include <optional>
#include <sstream>
#include <thread>
#include <unordered_map>
#include <vector>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

namespace hypr_spaces {

using Json = nlohmann::json;

inline std::string processStart(int pid) {
    std::ifstream file("/proc/" + std::to_string(pid) + "/stat");
    std::string line, field;
    std::getline(file, line);
    const auto end = line.rfind(')');
    if (end == std::string::npos) return {};
    std::istringstream fields(line.substr(end + 2));
    // The tail starts at field 3; starttime is field 22.
    for (int index = 3; index <= 22; ++index)
        if (!(fields >> field)) return {};
    return field;
}

inline int processParent(int pid) {
    std::ifstream file("/proc/" + std::to_string(pid) + "/stat");
    std::string line;
    std::getline(file, line);
    const auto end = line.rfind(')');
    if (end == std::string::npos) return 0;
    std::istringstream fields(line.substr(end + 2));
    char state;
    int parent = 0;
    fields >> state >> parent;
    return parent;
}

// Old Kitty processes cannot gain listen_on through a config reload. Only use
// /proc when exactly one direct child owns a controlling terminal: multiple
// panes/tabs/OS windows are ambiguous without Kitty's active-pane information.
inline std::optional<Json> singleTerminalPane(int kittyPID, const std::string& title) {
    std::ifstream children("/proc/" + std::to_string(kittyPID) + "/task/" + std::to_string(kittyPID) + "/children");
    int child = 0, shell = 0, foreground = 0;
    for (int count = 0; children >> child; ++count) {
        if (count >= 256) return {};
        std::ifstream stat("/proc/" + std::to_string(child) + "/stat");
        std::string line;
        std::getline(stat, line);
        const auto end = line.rfind(')');
        if (end == std::string::npos) continue;
        std::istringstream fields(line.substr(end + 2));
        char state;
        int parent, group, session, tty, tpgid;
        if (!(fields >> state >> parent >> group >> session >> tty >> tpgid) || tty == 0 || session != child || parent != kittyPID) continue;
        if (shell) return {};
        shell = child;
        foreground = tpgid;
    }
    if (!shell || foreground <= 0) return {};
    int ancestor = foreground;
    for (int steps = 0; ancestor > 1 && ancestor != shell && steps < 64; ++steps)
        ancestor = processParent(ancestor);
    if (ancestor != shell) return {};

    int paneID = -1;
    std::ifstream environment("/proc/" + std::to_string(shell) + "/environ");
    std::string field;
    for (size_t bytes = 0; bytes < 65536 && std::getline(environment, field, '\0'); bytes += field.size() + 1)
        if (field.starts_with("KITTY_WINDOW_ID=")) {
            try { paneID = std::stoi(field.substr(16)); } catch (...) {}
            break;
        }
    // A blocking opener and its child editor can share the foreground group.
    // Keep all its live members so paneTitle can prefer the nested publisher.
    std::vector<int> pending{shell};
    std::vector<Json> processes;
    for (size_t index = 0; index < pending.size(); ++index) {
        if (pending.size() > 256) return {};
        const auto pid = pending[index];
        std::ifstream descendants("/proc/" + std::to_string(pid) + "/task/" + std::to_string(pid) + "/children");
        while (descendants >> child) {
            pending.push_back(child);
            if (pending.size() > 256) return {};
        }
        std::ifstream stat("/proc/" + std::to_string(pid) + "/stat");
        std::string line;
        std::getline(stat, line);
        const auto end = line.rfind(')');
        if (end == std::string::npos) continue;
        std::istringstream fields(line.substr(end + 2));
        char state;
        int parent, group;
        if (!(fields >> state >> parent >> group) || group != foreground) continue;
        std::ifstream command("/proc/" + std::to_string(pid) + "/cmdline");
        std::string executable;
        std::getline(command, executable, '\0');
        if (executable.empty()) continue;
        std::error_code error;
        const auto cwd = std::filesystem::read_symlink("/proc/" + std::to_string(pid) + "/cwd", error).string();
        processes.push_back({{"pid", pid}, {"cmdline", {executable}}, {"cwd", error ? "" : cwd}});
    }
    const auto leader = std::find_if(processes.begin(), processes.end(), [foreground](const auto& process) { return process.at("pid") == foreground; });
    if (leader == processes.end()) return {};
    std::rotate(processes.begin(), leader, leader + 1);
    return Json{{"id", paneID}, {"title", title}, {"foreground_processes", processes}};
}

inline std::string terminalExecutable(const std::string& executable) {
    const auto leaf = pathLeaf(executable);
    for (const std::string app : {"opencode", "nvim", "yazi"}) {
        const auto wrapper = "." + app + "-wrapped";
        if (leaf.starts_with(wrapper) && leaf.find_first_not_of('_', wrapper.size()) == std::string::npos)
            return app;
    }
    return leaf;
}

inline std::optional<Json> kittyList(const std::string& path) {
    if (path.size() >= sizeof(sockaddr_un::sun_path)) return {};
    const int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    if (fd < 0) return {};
    struct Close { int fd; ~Close() { ::close(fd); } } close{fd};
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    std::copy(path.begin(), path.end(), address.sun_path);
    // A Unix-domain connect completes immediately or fails (including a full
    // backlog). Never wait for a terminal that cannot accept this request.
    if (connect(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) < 0) return {};
    const std::string request = "\x1bP@kitty-cmd{\"cmd\":\"ls\",\"version\":[0,47,0]}\x1b\\";
    if (send(fd, request.data(), request.size(), MSG_NOSIGNAL) != static_cast<ssize_t>(request.size())) return {};
    std::string response;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(80);
    while (response.size() < 1024 * 1024 && std::chrono::steady_clock::now() < deadline) {
        char buffer[8192];
        const auto count = recv(fd, buffer, sizeof(buffer), 0);
        if (count == 0) return {};
        if (count < 0) {
            if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) return {};
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
            continue;
        }
        response.append(buffer, count);
        const auto start = response.find("\x1bP@kitty-cmd");
        const auto end = response.find("\x1b\\");
        if (start == std::string::npos || end == std::string::npos) continue;
        const auto envelope = Json::parse(response.substr(start + 12, end - start - 12));
        if (!envelope.value("ok", false)) return {};
        return Json::parse(envelope.at("data").get<std::string>());
    }
    return {};
}

// Match the selected pane of the selected tab, independently for each OS
// window. A process can own several OS windows: never guess on ambiguous titles.
inline std::optional<Json> selectedKittyPane(const Json& windows, const std::string& title) {
    std::vector<Json> candidates;
    for (const auto& window : windows)
        for (const auto& tab : window.at("tabs"))
            if (tab.value("is_active", false))
                for (const auto& pane : tab.at("windows"))
                    if (pane.value("is_active", false)) candidates.push_back(pane);
    if (candidates.size() == 1) return candidates.front();
    std::optional<Json> match;
    for (const auto& pane : candidates)
        if (pane.value("title", "") == title) {
            if (match) return {};
            match = pane;
        }
    return match;
}

inline std::optional<WorkspaceTitle> paneTitle(const Json& pane, const std::string& runtime, const std::string& home) {
    const auto& processes = pane.at("foreground_processes");
    if (processes.empty()) return {};
    // Multiple foreground members can include shell pipelines. Prefer a record
    // from the actual foreground application; never reuse a background record.
    std::unordered_map<int, WorkspaceTitle> records;
    for (const auto& process : processes) {
        const int pid = process.at("pid");
        std::ifstream file(runtime + "/hypr-spaces/apps/" + std::to_string(pid) + ".json");
        if (!file) continue;
        try {
            const auto record = Json::parse(file);
            const auto start = processStart(pid);
            if (start.empty() || record.value("start", "") != start || record.value("pane", "") != std::to_string(pane.at("id").get<int>())) continue;
            records.emplace(pid, terminalTitle(record.at("app"), record.value("title", ""), record.value("cwd", ""), home, true));
        } catch (...) { /* A missing or half-replaced publisher is just a fallback. */ }
    }
    // Blocking openers can keep both Yazi and its child Neovim in one process
    // group. Prefer the nested application, not whichever /proc listed first.
    if (!records.empty()) {
        int bestPID = 0, bestDepth = -1;
        for (const auto& [pid, context] : records) {
            int depth = 0, parent = processParent(pid);
            for (int steps = 0; parent > 1 && steps < 64; ++steps) {
                depth += records.contains(parent);
                const int next = processParent(parent);
                if (next == parent) break;
                parent = next;
            }
            if (depth > bestDepth || (depth == bestDepth && pid < bestPID)) {
                bestPID = pid;
                bestDepth = depth;
            }
        }
        return records.at(bestPID);
    }
    const auto& process = processes.front();
    const auto command = process.at("cmdline");
    if (command.empty()) return {};
    const auto app = terminalExecutable(command.at(0).get<std::string>());
    // Yazi's process CWD is not necessarily its active tab; do not claim it is.
    const auto cwd = app == "yazi" || !process.contains("cwd") || !process.at("cwd").is_string() ? "" : process.at("cwd").get<std::string>();
    return terminalTitle(app, pane.value("title", ""), cwd, home);
}

struct TitleRequest {
    uintptr_t key;
    int pid;
    std::string title;
};
struct TitleResult {
    int pid;
    std::string title;
    WorkspaceTitle context;
};
using TitleResults = std::unordered_map<uintptr_t, TitleResult>;

// No compositor pointers, subprocesses or disk/socket I/O on the render thread.
// Only a bounded request/result swap crosses threads; unload joins the worker.
class TitleContext {
  public:
    void start() {
        if (worker.joinable()) return;
        runtime = std::getenv("XDG_RUNTIME_DIR") ? std::getenv("XDG_RUNTIME_DIR") : "";
        home = std::getenv("HOME") ? std::getenv("HOME") : "";
        worker = std::jthread([this](std::stop_token stop) {
            size_t cursor = 0;
            TitleResults cached;
            while (!stop.stop_requested()) {
                std::vector<TitleRequest> batch;
                {
                    std::unique_lock lock(mutex);
                    ready.wait(lock, stop, [this] { return pending; });
                    if (stop.stop_requested()) break;
                    batch = std::move(requests);
                    pending = false;
                }
                TitleResults next;
                // Keep only still-matching windows from the previous batch.
                // A bounded poll may leave some unvisited; do not make their
                // labels flicker while slow terminals consume the time budget.
                for (const auto& request : batch)
                    if (const auto it = cached.find(request.key); it != cached.end() && it->second.pid == request.pid && it->second.title == request.title)
                        next.emplace(request.key, it->second);
                std::unordered_map<int, std::optional<Json>> lists;
                const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(300);
                size_t processed = 0;
                for (; processed < batch.size(); ++processed) {
                    if (stop.stop_requested() || std::chrono::steady_clock::now() > deadline) break;
                    const auto& request = batch[(cursor + processed) % batch.size()];
                    next.erase(request.key);
                    try {
                        if (runtime.empty()) continue;
                        if (!lists.contains(request.pid))
                            lists[request.pid] = kittyList(runtime + "/hypr-spaces-kitty-" + std::to_string(request.pid));
                        const auto& list = lists.at(request.pid);
                        const auto pane = list ? selectedKittyPane(*list, request.title) : singleTerminalPane(request.pid, request.title);
                        if (!pane) continue;
                        const auto context = paneTitle(*pane, runtime, home);
                        if (context) next.emplace(request.key, TitleResult{request.pid, request.title, *context});
                    } catch (...) { /* Terminal shutdown and malformed replies are nonfatal. */ }
                }
                // Continue where the budget ran out, rather than starving the
                // same tail windows on every poll of the compositor's list.
                cursor = batch.empty() ? 0 : (cursor + processed) % batch.size();
                cached = next;
                std::lock_guard lock(mutex);
                results = std::move(next);
                resultsReady = true;
            }
        });
    }
    void request(std::vector<TitleRequest> batch) {
        std::lock_guard lock(mutex);
        requests = std::move(batch);
        pending = true;
        ready.notify_one();
    }
    std::optional<TitleResults> takeResults() {
        std::lock_guard lock(mutex);
        if (!resultsReady) return {};
        resultsReady = false;
        return std::move(results);
    }
    void clear() {
        if (worker.joinable()) { worker.request_stop(); ready.notify_all(); worker.join(); }
        std::lock_guard lock(mutex);
        requests.clear(); results.clear(); pending = false; resultsReady = false;
    }
    ~TitleContext() { clear(); }
  private:
    std::mutex mutex;
    std::condition_variable_any ready;
    std::vector<TitleRequest> requests;
    TitleResults results;
    bool pending = false;
    bool resultsReady = false;
    std::string runtime, home;
    std::jthread worker;
};

} // namespace hypr_spaces
