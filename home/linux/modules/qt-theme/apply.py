"""Apply the declared Adwaita policy without replacing whole user settings files."""

import argparse
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile


def update_section(text, section, values):
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    headers = [
        (index, match.group(1))
        for index, line in enumerate(lines)
        if (match := re.fullmatch(r"\s*\[([^\]]+)\]\s*", line))
    ]
    matches = [index for index, name in headers if name == section]
    if len(matches) > 1:
        raise ValueError(f"Duplicate [{section}] sections; refusing an ambiguous edit")
    if not matches:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += newline
        if lines and lines[-1].strip():
            lines.append(newline)
        lines.append(f"[{section}]{newline}")
        start, end = len(lines), len(lines)
    else:
        start = matches[0] + 1
        end = next((index for index, _ in headers if index >= start), len(lines))

    missing = dict(values)
    seen = set()
    for index in range(start, end):
        match = re.match(r"^(\s*([^=;#\s]+)\s*=)(.*?)(\r?\n)?$", lines[index])
        if not match or match.group(2) not in values:
            continue
        key = match.group(2)
        if key in seen:
            raise ValueError(f"Duplicate [{section}]/{key}; refusing an ambiguous edit")
        seen.add(key)
        # Preserve an already correct line, including spacing and its line ending.
        if match.group(3).strip() != values[key]:
            lines[index] = f"{match.group(1)}{values[key]}{match.group(4) or newline}"
        missing.pop(key, None)

    if missing:
        if end and not lines[end - 1].endswith("\n"):
            lines[end - 1] += newline
        lines[end:end] = [f"{key}={value}{newline}" for key, value in missing.items()]
    return "".join(lines)


def plan_update(path, section, values):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Refusing to replace non-regular settings file: {path}")
    old = path.read_bytes() if path.exists() else b""
    new = update_section(old.decode("utf-8"), section, values).encode("utf-8")
    return path, old, new


def write_update(path, old, new):
    if old == new:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    backup = path.with_name(path.name + ".before-qt-theme")
    if path.exists() and not backup.exists() and not backup.is_symlink():
        shutil.copy2(path, backup)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def system_mode():
    result = subprocess.run(
        ["dconf", "read", "/org/gnome/desktop/interface/color-scheme"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if result == "'prefer-dark'":
        return "dark"
    if result in ("'prefer-light'", "'default'", ""):
        return "light"
    raise ValueError(f"Unrecognized system color scheme: {result!r}")


def apply(config, mode, initialize_nomacs=False):
    if mode == "system":
        mode = system_mode()
    style = "Adwaita-Dark" if mode == "dark" else "Adwaita"
    values = {
        "style": style,
        "custom_palette": "false",
        "standard_dialogs": "xdgdesktopportal",
    }
    updates = [
        plan_update(config / version / f"{version}.conf", "Appearance", values)
        for version in ("qt5ct", "qt6ct")
    ]
    if initialize_nomacs:
        updates.append(
            plan_update(
                config / "nomacs" / "Image Lounge.conf",
                "DisplaySettings",
                {"themeName312": "System.css", "stylePlugin": "qt6ct-style"},
            )
        )
    return sum(write_update(*update) for update in updates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("system", "light", "dark"), required=True)
    parser.add_argument("--initialize-nomacs", action="store_true")
    args = parser.parse_args()
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    try:
        changed = apply(config, args.mode, args.initialize_nomacs)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Qt appearance: {error}\n")
    print(f"Qt appearance: {changed} settings file(s) updated")


if __name__ == "__main__":
    main()
