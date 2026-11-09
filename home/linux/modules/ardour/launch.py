"""Select Ardour's startup palette from the desktop mode, then exec upstream."""

import argparse
import fcntl
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def running_ardour(proc=Path("/proc")):
    for entry in proc.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            try:
                name = (entry / "exe").readlink().name
            except PermissionError:
                # Non-dumpable same-user processes hide exe (e.g. privileged
                # desktop helpers), but Linux still exposes their command name.
                name = (entry / "comm").read_text().strip()
            if re.fullmatch(r"ardour-\d[\w.-]*", name):
                return True
        except (FileNotFoundError, ProcessLookupError):
            continue
        # If neither identity is readable, do not edit while uncertain.
    return False


def system_theme(dconf):
    value = subprocess.run(
        [dconf, "read", "/org/gnome/desktop/interface/color-scheme"],
        check=True,
        capture_output=True,
        text=True,
        timeout=3,
    ).stdout.strip()
    if value == "'prefer-dark'":
        return "dark"
    if value in ("'prefer-light'", "'default'", ""):
        return "captain_light"
    raise ValueError("Unrecognized desktop color scheme")


def apply_theme(path, theme):
    # Never create a first-run config: Ardour owns setup and version migration.
    if path.is_symlink():
        raise ValueError("Refusing a symlinked Ardour UI configuration")
    if not path.exists():
        return
    old = path.read_bytes()
    if b"<!DOCTYPE" in old:
        raise ValueError("Refusing an Ardour UI configuration with a DTD")
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    root = ET.fromstring(old, parser=parser)
    if root.tag != "Ardour" or len(root.findall("UI")) != 1:
        raise ValueError("Unexpected Ardour UI configuration structure")
    ui = root.find("UI")
    options = ui.findall("Option[@name='color-file']")
    if len(options) > 1:
        raise ValueError("Ambiguous Ardour color-file options")
    if options and options[0].get("value") == theme:
        return
    option = options[0] if options else ET.SubElement(ui, "Option", name="color-file")
    option.set("value", theme)
    new = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    mode = stat.S_IMODE(path.stat().st_mode)
    # One original backup, never replaced by subsequent theme selections.
    backup = path.with_name(path.name + ".before-system-theme")
    try:
        descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(old)
    descriptor, temporary = tempfile.mkstemp(prefix=".ui_config.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink() or path.read_bytes() != old:
            raise ValueError("Ardour UI configuration changed during theme selection")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--major", required=True, type=int)
    parser.add_argument("--dconf", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Missing upstream Ardour command")
    if any(arg in ("--help", "-h", "--version", "-v") for arg in command[1:]):
        os.execv(command[0], command)
    # Hold the lock across exec and the whole Ardour lifetime. A second launch
    # still works, but must not edit settings used by an already running instance.
    lock = None
    try:
        home = Path.home()
        cache = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache")
        directory = cache / "ardour-system-theme"
        directory.mkdir(parents=True, exist_ok=True)
        lock = (directory / "launch.lock").open("a")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.set_inheritable(lock.fileno(), True)
        if not running_ardour():
            config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
            apply_theme(config / f"ardour{args.major}" / "ui_config", system_theme(args.dconf))
    except (OSError, ValueError, ET.ParseError, subprocess.SubprocessError) as error:
        # Theme selection must not prevent opening the DAW. Do not print settings.
        print(f"Ardour startup theme skipped ({type(error).__name__}).", file=sys.stderr)
    os.execv(command[0], command)


if __name__ == "__main__":
    main()
