# Shared Qt appearance

Imported by the Linux GUI set on Acer (`samov-laptop`), desktop and the Lenovo
draft (`samov-laptop-next`). Server and Mac do not import it. No NixOS change,
extra daemon, polling or custom application UI is needed.

## Policy and mechanism

- Home Manager installs both native qtct platform/proxy plugins and the Qt5/Qt6
  Adwaita widget styles. `QT_QPA_PLATFORMTHEME=qt5ct` is HM's `qtct` mapping;
  qt6ct also accepts that name. There is **no fixed `QT_STYLE_OVERRIDE`**: it would
  bypass the proxy and prevent live updates. Login and systemd session variables
  clear the old override, and UWSM no longer sources the old `uwsm/env-toggle` file.
- HM activation reads the existing dconf `color-scheme`; `prefer-dark` selects
  `Adwaita-Dark`, while light/default/unset selects `Adwaita`. F11 uses the same
  helper after changing dconf. Changes made directly through another dconf tool
  are not watched: rerun `qt-theme-apply --mode system` to synchronize them.
- The helper manages only qt5ct/qt6ct `[Appearance]` keys `style`,
  `custom_palette=false` and `standard_dialogs=xdgdesktopportal`. Disabling a saved
  custom palette lets the selected Adwaita style supply its colors. Native portal
  dialogs remain available. Other qtct preferences, including fonts/icons, remain
  untouched.
- On activation only, nomacs `[DisplaySettings]` receives
  `themeName312=System.css` and `stylePlugin=qt6ct-style`. This removes persisted
  Fusion or fixed light/dark choices without replacing the rest of its settings.
  F11 never rewrites nomacs preferences. Activation reasserts these two keys if
  the user later changes them in the application.
- Running Qt Widgets applications using the qtct proxy reload the mutable config
  through the plugin's native directory watcher. qt6ct 0.11 debounces changes for
  **about three seconds**. Reopened applications read the current config, even
  when launched by a terminal opened before the last F11 toggle in the new session.

This is a default for applications that honor Qt's platform theme, not a promise
to override every program. Explicit per-application widget styles, private CSS,
Qt Quick controls, bundled/sandboxed Qt plugins and custom-rendered UIs may not
follow it. GTK is separate from this helper: F11 also selects native GTK3
`Adwaita`/`Adwaita-dark` through dconf (see [GTK policy](../../../../docs/laptop-audit/gtk-theme.md)).
Browsers, Blender and other custom-rendered UIs are not forced to use Qt styles.
Only nomacs has a targeted application-preference migration.

## Preservation and activation

The qtct and nomacs INI files remain ordinary user-writable files, not Nix-store
symlinks. The helper validates all targeted files before writing, rejects duplicate
managed sections/keys and symlink/non-regular target files, preserves unrelated
text and CRLF line endings, and atomically replaces each changed file. It keeps
the original file mode (new files are `0600`) and creates a one-time adjacent
`*.before-qt-theme` backup before the first replacement of an existing file.
Existing backups are never replaced; unchanged files are not rewritten. Writes
are atomic per file, not a cross-file transaction or a lock against an application's
concurrent settings save. Close Qt applications before activation, especially
nomacs, which could otherwise overwrite the migrated keys from its cached settings.

After personal review, on Acer:

1. Close nomacs and other Qt applications.
2. Apply `home-manager switch --flake .#samov-laptop` (desktop uses
   `.#samov-desktop`). Do not apply the Lenovo draft to Acer.
3. Log out and back into Hyprland, reopening terminals. Activation alone cannot
   replace environment variables in existing Kitty/Yazi/launcher processes.
4. Open an image in nomacs; press F11, wait about three seconds and check that
   the open viewer changes theme. Repeat in the other direction, then close and
   reopen it from Yazi and check that it keeps the current system appearance.

No NixOS activation is required. The obsolete generated `uwsm/env-toggle` may
remain on disk but is no longer read; deleting it is unnecessary. Reverting the
Nix module alone does not undo mutable application keys. If restoring a backup,
first close the application and inspect the backup so that newer preferences
are not inadvertently discarded.

## Checks and limits

Small, source-only checks from the repository root:

```fish
python3 home/linux/modules/qt-theme/test_apply.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/qt-theme/test-declarations.nix
```

The 12 Python tests exercise the actual helper and actual F11 script with external
desktop commands stubbed out. A separate case within that suite also runs real
dconf on a private D-Bus with temporary settings (skipped when dconf or
dbus-run-session is unavailable); it checks GTK/desktop writes without touching
the live desktop or Bluetooth devices. This does not exercise GTK rendering or
portal notifications. The Nix check evaluates selected merged attributes
for all five HM profiles: shared Qt policy, stable nomacs 3.22.1, Yazi/MIME and
preserved Swappy on the three GUI profiles; no added viewer/qtct on server/Mac.
It does not realize packages or evaluate a complete activation closure.

`test_native.py` is a separate, explicitly authorized real nomacs/qt6ct test. It
requires already-present package paths and ImageMagick; it obtains/builds nothing:

```fish
python3 home/linux/modules/qt-theme/test_native.py --nomacs /nix/store/<nomacs>/bin/nomacs --qt6ct /nix/store/<qt6ct> --adwaita-qt6 /nix/store/<adwaita-qt6>
```

It uses isolated settings under `/tmp/opencode`, migrates a saved `adwaita-dark`
choice with the actual helper, and renders through Qt's headless `minimal` plugin.
With nomacs 3.22.1, qt6ct 0.11 and adwaita-qt 1.4.2, the checked surface pixels were
`246,245,244 → 53,53,53 → 246,245,244` for startup-light/live-dark/live-light, and
`53,53,53` after reopening in dark mode. Two actual palette-change events occurred.
This proves the native Qt6 reload path, not the installed HM plugin layout or a
live Hyprland window. Qt5 runtime, other Qt applications, actual F11/Wayland/HiDPI,
nomacs Paint and saved-copy editing remain unverified. No full HM/NixOS build or
activation was performed for this change.
