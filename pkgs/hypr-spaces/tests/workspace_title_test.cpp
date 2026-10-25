#include "title_context.hpp"

#include <cassert>
#include <filesystem>
#include <future>
#include <sys/wait.h>
#include <signal.h>
#include <pty.h>

using namespace hypr_spaces;

int terminalNestedPID = 0;

int main(int argc, char**) {
    if (argc > 1) {
        assert(chdir("/tmp") == 0);
        terminalNestedPID = fork();
        assert(terminalNestedPID >= 0);
        if (terminalNestedPID == 0) { pause(); _exit(0); }
        signal(SIGTERM, [](int) {
            kill(terminalNestedPID, SIGTERM);
            waitpid(terminalNestedPID, nullptr, 0);
            _exit(0);
        });
        assert(write(STDOUT_FILENO, "ready\n", 6) == 6);
        pause();
        return 0;
    }
    assert(displayPath("/home/samov/project", "/home/samov") == "~/project");
    assert(displayPath("/home/samov-other/project", "/home/samov") == "/home/samov-other/project");
    assert(titleLine("\n Проект\t ") == "Проект");
    auto title = terminalTitle("opencode", "OC | Полное название сессии", "/home/samov/nix-config", "/home/samov");
    assert(title.primary == "Полное название сессии" && title.secondary == "~/nix-config");
    assert(terminalTitle("opencode", "New session - 2026-10-23T10:19:12.809Z", "/tmp", "").primary ==
        "New session - 2026-10-23T10:19:12.809Z");
    title = terminalTitle("nvim", "nvim", "/tmp/project/", "");
    assert(title.primary == "/tmp/project/" && title.secondary.empty());
    title = windowTitle("google-chrome", "Документ - Google Chrome");
    assert(title.primary == "Документ" && title.secondary.empty());
    assert(windowTitle("unknown", "").primary.empty());
    assert(windowTitle("kitty", "OpenCode").primary.empty());
    assert(windowTitle("kitty", "OC | Название сессии").primary == "Название сессии");
    assert(windowTitle("kitty", "Yazi: project").primary == "project");
    assert(windowTitle("kitty", "Fish").primary.empty());
    assert(terminalTitle("fish", "Fish", "/home/samov/project", "/home/samov").primary == "~/project");
    assert(terminalTitle("opencode", "OpenCode", "/tmp", "").primary == "/tmp");
    assert(terminalTitle("opencode", "", "", "").primary.empty());
    assert(terminalTitle("yazi", "Yazi: project", "", "").primary.empty());

    const Json pane = {{"id", 42}, {"title", "nvim"}, {"is_active", true},
        {"foreground_processes", Json::array({{{"pid", getpid()}, {"cmdline", {"nvim"}}, {"cwd", "/tmp/global"}}})}};
    const Json otherPane = {{"id", 43}, {"title", "other"}, {"is_active", false}};
    const Json windows = Json::array({{{"tabs", Json::array({{{"is_active", true}, {"windows", {pane, otherPane}}}})}}});
    assert(selectedKittyPane(windows, "nvim")->at("id") == 42);
    auto multiple = windows;
    multiple.push_back(windows.front());
    assert(!selectedKittyPane(multiple, "nvim")); // Same title across OS windows: no guessing.
    multiple.back()["tabs"][0]["windows"][0]["title"] = "second";
    assert(selectedKittyPane(multiple, "second")->at("title") == "second");

    char temporary[] = "/tmp/hypr-spaces-context-XXXXXX";
    const std::string runtime = mkdtemp(temporary);
    std::filesystem::create_directories(runtime + "/hypr-spaces/apps");
    const auto recordPath = runtime + "/hypr-spaces/apps/" + std::to_string(getpid()) + ".json";
    auto record = Json{{"app", "nvim"}, {"pane", "42"}, {"start", processStart(getpid())}, {"cwd", "/tmp/window-local"}};
    { std::ofstream file(recordPath); file << record; }
    assert(paneTitle(pane, runtime, "")->primary == "/tmp/window-local");
    record["app"] = "opencode";
    for (const auto& session : {"OpenCode", "OC | Actual session name"}) {
        record["title"] = session;
        { std::ofstream file(recordPath); file << record; }
        assert(paneTitle(pane, runtime, "")->primary == session);
    }
    record["app"] = "nvim";
    record.erase("title");
    record["start"] = "stale";
    { std::ofstream file(recordPath); file << record; }
    assert(paneTitle(pane, runtime, "")->primary == "/tmp/global");
    record["start"] = processStart(getpid()); record["pane"] = "43";
    { std::ofstream file(recordPath); file << record; }
    assert(paneTitle(pane, runtime, "")->primary == "/tmp/global");
    auto yazi = pane;
    yazi["foreground_processes"][0]["cmdline"] = {"yazi"};
    assert(paneTitle(yazi, runtime, "")->primary.empty()); // Never substitute launch CWD.

    // A blocking opener and its editor can share the foreground process group.
    const int child = fork();
    assert(child >= 0);
    if (child == 0) { pause(); _exit(0); }
    struct ChildGuard { int pid; ~ChildGuard() { kill(pid, SIGTERM); waitpid(pid, nullptr, 0); } } guard{child};
    record["app"] = "yazi"; record["pane"] = "42";
    { std::ofstream file(recordPath); file << record; }
    const auto childPath = runtime + "/hypr-spaces/apps/" + std::to_string(child) + ".json";
    const Json childRecord = {{"app", "nvim"}, {"pane", "42"}, {"start", processStart(child)}, {"cwd", "/tmp/nested-editor"}};
    { std::ofstream file(childPath); file << childRecord; }
    auto nested = pane;
    nested["foreground_processes"].push_back({{"pid", child}, {"cmdline", {"nvim"}}, {"cwd", "/tmp/global"}});
    assert(paneTitle(nested, runtime, "")->primary == "/tmp/nested-editor");
    std::filesystem::remove(childPath);
    auto shell = pane;
    shell["foreground_processes"][0]["pid"] = child;
    shell["foreground_processes"][0]["cmdline"] = {"fish"};
    assert(paneTitle(shell, runtime, "")->primary == "/tmp/global"); // Old parent's record is not foreground.
    shell["foreground_processes"][0]["cwd"] = nullptr;
    assert(paneTitle(shell, runtime, "")->primary.empty()); // Kitty can report a disappearing process.
    shell["foreground_processes"][0]["cmdline"] = {"/nix/store/example/bin/.opencode-wrapped_"};
    shell["foreground_processes"][0]["cwd"] = "/tmp/project";
    assert(paneTitle(shell, runtime, "")->primary == "nvim");
    assert(terminalExecutable(".yazi-wrapped") == "yazi");
    assert(terminalExecutable(".nvim-wrapped-helper") == ".nvim-wrapped-helper");

    // A real controlling terminal exercises the old-Kitty fallback without
    // inventing a /proc tree. Multiple panes must not pick an arbitrary CWD.
    // Keep masters open: closing the last PTY master would SIGHUP the session.
    auto spawnTerminal = [] {
        int master = -1;
        const int pid = forkpty(&master, nullptr, nullptr, nullptr);
        assert(pid >= 0);
        if (pid == 0) {
            setenv("KITTY_WINDOW_ID", "42", 1);
            execl("/proc/self/exe", "context-test", "--terminal-child", nullptr);
            _exit(127);
        }
        char ready[32];
        assert(read(master, ready, sizeof(ready)) >= 6);
        return std::pair{pid, master};
    };
    const auto [terminalPID, master] = spawnTerminal();
    const auto legacy = singleTerminalPane(getpid(), "legacy");
    assert(legacy && legacy->at("id") == 42);
    assert(legacy->at("foreground_processes")[0].at("pid") == terminalPID);
    assert(paneTitle(*legacy, runtime, "")->primary == "legacy" && paneTitle(*legacy, runtime, "")->secondary == "/tmp");
    const auto legacyRecordPath = runtime + "/hypr-spaces/apps/" + std::to_string(terminalPID) + ".json";
    { std::ofstream file(legacyRecordPath); file << Json{{"app", "opencode"}, {"pane", "42"},
        {"start", processStart(terminalPID)}, {"title", "Full session title"}, {"cwd", "/tmp/project"}}; }
    assert(paneTitle(*legacy, runtime, "")->primary == "Full session title");
    assert(legacy->at("foreground_processes").size() == 2);
    const int nestedPID = legacy->at("foreground_processes")[1].at("pid");
    const auto nestedRecordPath = runtime + "/hypr-spaces/apps/" + std::to_string(nestedPID) + ".json";
    { std::ofstream file(nestedRecordPath); file << Json{{"app", "nvim"}, {"pane", "42"},
        {"start", processStart(nestedPID)}, {"cwd", "/tmp/nested-editor"}}; }
    assert(paneTitle(*legacy, runtime, "")->primary == "/tmp/nested-editor");
    std::filesystem::remove(nestedRecordPath);
    std::filesystem::remove(legacyRecordPath);
    setenv("XDG_RUNTIME_DIR", runtime.c_str(), 1);
    TitleContext worker;
    worker.start();
    worker.request({{123, getpid(), "legacy"}});
    std::optional<TitleResults> collected;
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(1);
    while (!(collected = worker.takeResults()) && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    assert(collected && collected->at(123).context.secondary == "/tmp");
    assert(!worker.takeResults());
    worker.clear();
    const auto [secondPID, secondMaster] = spawnTerminal();
    assert(!singleTerminalPane(getpid(), "legacy"));
    kill(secondPID, SIGTERM); waitpid(secondPID, nullptr, 0); close(secondMaster);
    kill(terminalPID, SIGTERM); waitpid(terminalPID, nullptr, 0); close(master);
    assert(!singleTerminalPane(getpid(), "legacy"));

    const auto socketPath = runtime + "/kitty";
    const int server = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    assert(server >= 0);
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    std::copy(socketPath.begin(), socketPath.end(), address.sun_path);
    assert(bind(server, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 0);
    assert(listen(server, 1) == 0);
    auto response = std::async(std::launch::async, [&] {
        const int client = accept(server, nullptr, nullptr);
        char request[256];
        assert(recv(client, request, sizeof(request), 0) > 0);
        const auto message = "\x1bP@kitty-cmd" + Json{{"ok", true}, {"data", windows.dump()}}.dump() + "\x1b\\";
        // Fragments exercise framing without depending on packet boundaries.
        assert(send(client, message.data(), 7, MSG_NOSIGNAL) == 7);
        std::this_thread::sleep_for(std::chrono::milliseconds(3));
        assert(send(client, message.data() + 7, message.size() - 7, MSG_NOSIGNAL) == static_cast<ssize_t>(message.size() - 7));
        close(client);
    });
    assert(kittyList(socketPath) == windows);
    response.get();
    auto silent = std::async(std::launch::async, [&] {
        const int client = accept(server, nullptr, nullptr);
        std::this_thread::sleep_for(std::chrono::milliseconds(180));
        close(client);
    });
    assert(!kittyList(socketPath)); // A stopped terminal cannot block collection forever.
    silent.get();
    close(server);
    assert(!kittyList(runtime + "/absent"));

    // More slow terminals than fit in one poll must not starve later windows,
    // and a cached fast result must survive a batch that cannot revisit it.
    std::vector<int> servers;
    std::vector<std::jthread> responders;
    std::vector<TitleRequest> requests;
    auto fairWindows = windows;
    auto& fairPane = fairWindows[0]["tabs"][0]["windows"][0];
    fairPane["id"] = 99; // Ignore the publisher fixture above.
    fairPane["foreground_processes"][0]["cmdline"] = {"fish"};
    fairPane["foreground_processes"][0]["cwd"] = "/tmp/fairness";
    const auto message = "\x1bP@kitty-cmd" + Json{{"ok", true}, {"data", fairWindows.dump()}}.dump() + "\x1b\\";
    for (int index = 0; index < 6; ++index) {
        const int pid = 2000000000 + index;
        const auto path = runtime + "/hypr-spaces-kitty-" + std::to_string(pid);
        const int listener = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
        assert(listener >= 0);
        sockaddr_un addr{};
        addr.sun_family = AF_UNIX;
        std::copy(path.begin(), path.end(), addr.sun_path);
        assert(bind(listener, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == 0);
        assert(listen(listener, 4) == 0);
        servers.push_back(listener);
        requests.push_back({static_cast<uintptr_t>(index + 1), pid, "fairness"});
        responders.emplace_back([listener, slow = index > 0 && index < 5, &message](std::stop_token stop) {
            while (!stop.stop_requested()) {
                const int client = accept(listener, nullptr, nullptr);
                if (client < 0) { std::this_thread::sleep_for(std::chrono::milliseconds(2)); continue; }
                char request[256];
                assert(recv(client, request, sizeof(request), 0) > 0);
                if (slow) std::this_thread::sleep_for(std::chrono::milliseconds(100));
                else assert(send(client, message.data(), message.size(), MSG_NOSIGNAL) == static_cast<ssize_t>(message.size()));
                close(client);
            }
        });
    }
    worker.start();
    auto collect = [&](const std::vector<TitleRequest>& batch) {
        worker.request(batch);
        std::optional<TitleResults> results;
        const auto limit = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!(results = worker.takeResults()) && std::chrono::steady_clock::now() < limit)
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        assert(results);
        return *results;
    };
    assert(collect(requests).contains(1));
    const auto fairResults = collect(requests);
    assert(fairResults.contains(1) && fairResults.at(6).context.primary == "/tmp/fairness");
    assert(!collect({requests.back()}).contains(1)); // Removed windows lose cached context.
    worker.clear();
    for (auto& responder : responders) responder.request_stop();
    responders.clear();
    for (const auto listener : servers) close(listener);
    std::filesystem::remove_all(runtime);
}
