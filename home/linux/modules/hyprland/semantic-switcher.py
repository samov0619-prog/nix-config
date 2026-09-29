#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def hyprctl_json(command):
    return json.loads(subprocess.check_output(["hyprctl", "-j", command], text=True))


def process_table():
    processes = {}
    children = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
            closing_parenthesis = stat.rfind(")")
            fields = stat[closing_parenthesis + 2 :].split()
            pid = int(entry.name)
            ppid = int(fields[1])
            tpgid = int(fields[5])
            processes[pid] = {
                "ppid": ppid,
                "tpgid": tpgid,
                "comm": stat[stat.index("(") + 1 : closing_parenthesis],
            }
            children.setdefault(ppid, []).append(pid)
        except (FileNotFoundError, IndexError, PermissionError, ValueError):
            continue
    return processes, children


def foreground_process(pid, processes, children):
    descendants = []
    pending = list(children.get(pid, []))
    while pending:
        child = pending.pop()
        descendants.append(child)
        pending.extend(children.get(child, []))

    descendant_set = set(descendants)
    for child in descendants:
        tpgid = processes[child]["tpgid"]
        if tpgid in descendant_set:
            return tpgid, processes[tpgid]["comm"]
    return None, None


def process_cwd(pid):
    if pid is None:
        return None
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return None


def display_path(path):
    if not path:
        return None
    home = str(Path.home())
    return "~" + path[len(home) :] if path == home or path.startswith(home + "/") else path


def inventory():
    processes, children = process_table()
    workspaces = hyprctl_json("workspaces")
    clients = hyprctl_json("clients")
    active_workspace = hyprctl_json("activeworkspace")["id"]
    active_window = hyprctl_json("activewindow").get("address")
    workspace_entries = {
        workspace["id"]: workspace.get("name") or str(workspace["id"])
        for workspace in workspaces
        if workspace["id"] > 0
    }

    windows = []
    for client in clients:
        workspace = client["workspace"]
        workspace_id = workspace["id"]
        if workspace_id <= 0:
            continue
        workspace_entries.setdefault(workspace_id, workspace.get("name") or str(workspace_id))
        process_name = None
        cwd = None
        if client.get("class", "").lower() == "kitty":
            foreground_pid, process_name = foreground_process(client["pid"], processes, children)
            cwd = process_cwd(foreground_pid)
        title = client.get("title") or client.get("class") or "unknown"
        app = client.get("class") or "unknown"
        details = [f"[WS {workspace_id}]", app]
        if process_name and process_name.lower() not in title.lower():
            details.append(process_name)
        details.extend([title, display_path(cwd)])
        windows.append(
            {
                "kind": "window",
                "workspace": workspace_id,
                "address": client["address"],
                "label": " / ".join(part for part in details if part),
                "active": client["address"] == active_window,
            }
        )

    entries = []
    for workspace_id, workspace_name in sorted(workspace_entries.items()):
        entries.append(
            {
                "kind": "workspace",
                "workspace": workspace_id,
                "label": f"WS {workspace_name}",
                "active": workspace_id == active_workspace,
            }
        )
        entries.extend(
            sorted(
                (window for window in windows if window["workspace"] == workspace_id),
                key=lambda window: window["label"].lower(),
            )
        )
    return entries


def snapshot_path():
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
    return runtime_dir / "hypr-semantic-switcher.json"


def menu():
    entries = inventory()
    snapshot = {}
    for number, entry in enumerate(entries, 1):
        snapshot[str(number)] = entry
        entry_type = "Workspace" if entry["kind"] == "workspace" else "Window"
        marker = ">" if entry["active"] else " "
        print(f"{number:02d} {marker} {entry_type:<10} {entry['label']}")
    with tempfile.NamedTemporaryFile("w", dir=snapshot_path().parent, delete=False) as temporary:
        os.chmod(temporary.name, 0o600)
        json.dump(snapshot, temporary)
    os.replace(temporary.name, snapshot_path())


def activate(selection):
    identifier = selection.split(maxsplit=1)[0].lstrip("0") or "0"
    try:
        entry = json.loads(snapshot_path().read_text())[identifier]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        raise SystemExit("Switcher selection expired; open it again.")

    subprocess.run(["hyprctl", "dispatch", "workspace", str(entry["workspace"])], check=True)
    if entry["kind"] == "window":
        subprocess.run(["hyprctl", "dispatch", "focuswindow", f"address:{entry['address']}"], check=True)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "menu":
        menu()
    elif len(sys.argv) == 3 and sys.argv[1] == "activate":
        activate(sys.argv[2])
    else:
        raise SystemExit("Usage: hypr-semantic-switcher menu | activate <selection>")
