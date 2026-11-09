"""Probe real GTK3 colors without starting Blueman or changing desktop settings.

Uses Blueman's already-installed Python/GI runtime. The alias fixture is the exact
upstream gnome-themes-extra 3.28 GTK3 stylesheet, not a replacement theme design.
This tests CSS resolution, not the built/installed Nix package or portal events.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


# https://gitlab.gnome.org/GNOME/gnome-themes-extra/-/raw/3.28/themes/Adwaita-dark/gtk-3.0/gtk.css
ALIAS = '@import url("resource:///org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css");\n'

PROBE = '''
import json, site, sys
for path in json.loads(sys.argv[1]):
    site.addsitedir(path)
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
ok, _ = Gtk.init_check([])
if not ok:
    raise RuntimeError("GTK3 display initialization failed")
settings = Gtk.Settings.get_default()
settings.props.gtk_application_prefer_dark_theme = sys.argv[3] == "true"
window = Gtk.Window()  # Never shown; no application/Bluetooth code is imported.
colors = []
for name in json.loads(sys.argv[2]):
    settings.props.gtk_theme_name = name
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    found, color = window.get_style_context().lookup_color("theme_bg_color")
    assert found, "GTK3 theme has no background color"
    colors.append([round(component * 255) for component in (color.red, color.green, color.blue)])
print(json.dumps(colors))
window.destroy()
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueman", default=shutil.which("blueman-manager"))
    args = parser.parse_args()
    if not args.blueman:
        parser.error("Provide an already-installed --blueman launcher")
    launcher = Path(args.blueman).resolve()
    wrapper = launcher.read_bytes().decode("utf-8", errors="ignore")
    entry = (launcher.parent / "..blueman-manager-wrapped-wrapped").read_text()
    python = entry.splitlines()[0][2:]
    paths = re.findall(r"'(/nix/store/[^']+/lib/python[^']+/site-packages)'", entry.splitlines()[1])
    if not paths:
        raise RuntimeError("Installed Blueman wrapper layout changed; review the probe")
    env = os.environ.copy()
    # Only packaged runtime paths, not user theme directories, for the negative
    # control. Otherwise an already-installed alias could hide the regression.
    for key in ("GI_TYPELIB_PATH", "GIO_EXTRA_MODULES", "XDG_DATA_DIRS"):
        values = [value for name, value in re.findall(
            r"--prefix '([^']+)' ':' '([^']+)'", wrapper
        ) if name == key]
        if not values:
            raise RuntimeError(f"Missing {key} in installed Blueman wrapper")
        env[key] = ":".join(values)
    env.pop("GTK_THEME", None)
    env["GSETTINGS_BACKEND"] = "memory"
    with tempfile.TemporaryDirectory(prefix="gtk-theme-", dir="/tmp/opencode") as temporary:
        root = Path(temporary)
        env.update({
            "HOME": str(root), "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"), "XDG_CACHE_HOME": str(root / "cache"),
        })

        def probe(name, dark=False):
            single = isinstance(name, str)
            names = [name] if single else name
            result = subprocess.run(
                [python, "-B", "-c", PROBE, json.dumps(paths), json.dumps(names), str(dark).lower()],
                env=env, check=True, capture_output=True, text=True, timeout=8,
            )
            colors = json.loads(result.stdout)
            return colors[0] if single else colors

        # Separate processes avoid GTK's named-provider cache aliasing variants.
        light = probe("Adwaita")
        builtin_dark = probe("Adwaita", True)
        missing_alias = probe("Adwaita-dark")
        assert missing_alias == light, "Negative control no longer reproduces the fallback"
        assert sum(builtin_dark) < sum(light), "Built-in dark variant must be darker"
        alias = root / "data/themes/Adwaita-dark/gtk-3.0/gtk.css"
        alias.parent.mkdir(parents=True)
        alias.write_text(ALIAS)
        with_alias = probe("Adwaita-dark")
        assert with_alias == builtin_dark, "Named alias must use GTK's built-in dark variant"
        assert probe("Adwaita") == light, "Alias must not change the light theme"
        sequence = probe(["Adwaita", "Adwaita-dark", "Adwaita"])
        assert sequence == [light, builtin_dark, light], "GTK settings changes must reload the palette"
        print(json.dumps({
            "light": light, "missingAlias": missing_alias,
            "builtinDark": builtin_dark, "withAlias": with_alias,
            "sameProcessSequence": sequence,
        }))


if __name__ == "__main__":
    main()
