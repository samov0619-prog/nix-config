# Lenovo Home Manager hotkeys

Left Alt/Super and Command-editing changes, permission separation, agreed
limitations and acceptance/recovery are documented in
[`command-keys/README.md`](command-keys/README.md). The user reports successful
ordinary use after application; the full hardware/UI matrix is not verified.

The F-key follow-up adds Super+F invoking native Ctrl+F in the
GUI allowlist, and the unused floating/tiled focus bindings are removed without
replacement (including the RU physical Shift+F Firefox launcher). See the
command-keys guide for scoped user-reported Chrome behavior, remaining checks
and the NixOS + HM apply procedure.

For a manually launched 5-second NVIDIA/PPD table, see
`home/linux/laptop/gpu-monitor.md`. It appends samples until Ctrl+C and does not
change profiles or add a service; explicit polling can postpone GPU sleep.

Lenovo dictation now uses [Handy / Parakeet Q4](handy/README.md): Intel-only
Vulkan, a hidden graphical-session service, Super+Shift+R to start/stop and
Super+Shift+T to cancel. Ctrl+Space stays available to Neovim.
The package, model, service and compositor bindings are declarative; initial
settings are seeded once, then remain writable through the GUI.

The previous Lenovo Whisper setup and measurements are
[archived](../../../docs/laptop-audit/archive/voice-dictate.md), with an inactive
[`archive/whisper.nix`](archive/whisper.nix). Acer/desktop keep the shared helper.
NixOS still prefers the built-in microphone and automatic headphone/speaker
output, with Bluetooth HFP selected manually; this migration does not change
audio/power policy. The same archive preserves its acceptance history.

The top row sends hardware functions without Fn; Fn exposes ordinary F1–F12.
Only the Lenovo leaf changes these bindings:

| Physical key | Hyprland event | Action |
| --- | --- | --- |
| Fn+F1 | F1 | Controls help |
| F8 | XF86TouchpadToggle | Toggle only `gxtp5100:00-27c6:01e7-touchpad` |
| F9 (star) | XF86Favorites | Open agent todo |
| F10 | Existing Print workflow | Region screenshot → Swappy, unchanged |
| Fn+F11 | F11 | Toggle theme, without Super |

The old F3 todo and Super+F11 theme bindings are removed on Lenovo only. F1–F6
hardware actions remain unchanged. F7 and Super+P pseudotile are unchanged: the
earlier wev capture suggests a firmware Super+P combination, not a confirmed raw
capture or an approved display-mode action. Calculator, moon/sleep and camera
have no new bindings. The user confirms camera, screen sharing and video calls
work; this is user acceptance, not independent UI observation.

The Smart Connect side of F11 emits scancode `0x148` / KEY_UNKNOWN on 7.3.4.
Because theme now uses ordinary Fn+F11, no kernel patch, KEY_UNKNOWN binding or
system-level remapping is needed. No NixOS, driver, RTD3, VPN or audio changes.

## Touchpad state

`lenovo-touchpad` is a short-lived helper, not a service. Hyprland 0.55.4's legacy
getoption cannot read per-device enabled state; its setter accepts
`device[gxtp5100:00-27c6:01e7-touchpad]:enabled`. The helper records only successful
changes under XDG_RUNTIME_DIR, isolated by HYPRLAND_INSTANCE_SIGNATURE. A lock
serializes presses. Command failures, timeouts and textual compositor errors do
not advance state. The separate `-mouse` device is never targeted.

The configured device starts enabled. Every config reload also runs
`lenovo-touchpad enable`, resetting helper state and enabling the touchpad again.
This is intentional recovery behavior, not persistence of disabled state across
reload/login. Do not modify the same enabled setting independently behind the
helper: it cannot detect external changes. Manual recovery is
`lenovo-touchpad enable` from the active Hyprland session. There is no sudo,
polling, disk-persistent toggle or suspend hook.

## Mouse resize and local Dwindle reset

Prepared on Lenovo only: **Super+Shift+LMB drag** uses Hyprland's native
`resizewindow` for floating windows and tiled splits. Start near the side/corner
you want to drag; visible borders are not required. **Super+LMB** still moves
windows. No extra service, helper or global resize-on-border setting was added.

**Super+Ctrl+T** runs `layoutmsg, splitratio 1 exact`: the active tiled window's
parent split returns to **50/50**. This is a size reset for the two-window case,
not restoration of an entire Dwindle tree, all ancestor ratios, window order or
split orientations. It does not restore previous floating geometry. Floating
windows can return to tiling with Super+G; that reinserts them, not undoing an old
layout. This scope follows Hyprland 0.55.4's `CDwindleAlgorithm::layoutMsg`.
No speculative full-workspace reconstruction is implemented.

F1 help lists both shortcuts. Apply HM and reload Hyprland using the steps below,
then test a floating terminal near multiple corners; test two ordinary tiled
windows and the 50/50 reset separately. Fullscreen/maximize policy is unchanged.
Live drag/reset acceptance is pending, not covered by selected declaration tests.

## Blender MCP add-on

The Lenovo leaf installs only `blender_mcp/bundled/addon.py` from the PyPI wheel
`mcp_for_blender-2.3.0-py3-none-any.whl`, matching Aina's MCP server pin. The wheel's
SHA-256 is `d420fe5382a7220162d9a8ed3f0740fa19ce83ad87f30c892248bb7c5254b618`.
There is no Blender add-on module/package for this in the pinned Home Manager or
nixpkgs; `blender.withPackages` supplies Python dependencies, not add-on files.
Stock `pkgs.blender` already includes the required `requests` dependency.
The bundled `bl_info.version` is still `(2, 0)`; this UI metadata is not the wheel
version and does not mean an older wheel was installed.

Home Manager links one file at
`$XDG_CONFIG_HOME/blender/<major.minor>/scripts/addons/blender_mcp.py` (normally
`~/.config/blender/5.1/scripts/addons/blender_mcp.py` today). The directory version
comes from `pkgs.blender.version`, not a fixed `5.1`. Other add-ons, preferences
and scene files stay unmanaged; `force = false` preserves collision protection.
There is no global MCP/uv installation, service, firewall change or auto-enable.

After reviewing the changes:

1. Run `home-manager switch --flake /home/samov/nix-config#samov-laptop`.
2. For an already running Blender, switch a 3D Viewport to **Python Console**
   with **Shift+F4** and run
   `bpy.utils.refresh_script_paths(); bpy.ops.preferences.addon_refresh()`.
   Return with **Shift+F5**. This refreshes discovery without enabling the add-on
   or changing preferences/scene data. Alternatively, save your work and restart
   Blender; a restart discovers the new directory automatically.
3. Open **Edit > Preferences > Add-ons**, clear any enabled-only filter,
   search for **MCP for Blender** and enable its checkbox. Do not use Install from
   Disk: Home Manager already supplies the file.
4. Keep **Bind Address** at `localhost`, **Allow Remote Connections** and
   **Allow Telemetry** off, and external asset/generation integrations disabled.
   The upstream add-on defaults to **Auto-Start Server** on: enabling it starts
   a local listener on port `9876`. It also checks for updates over the network.
   These are upstream behaviors, not a system service or HM activation action.
5. In the 3D Viewport, press **N** and open the **MCP for Blender** tab. Check the
   connection status there; do not use **Update Addon** for this store-managed
   file. Update the declarative wheel pin/hash together with Aina instead.

Wheel hash and Python syntax were checked without importing/registering the
add-on. Builds, activation, Blender UI compatibility and an MCP connection remain
user verification; no running Blender session or preferences were modified.

## Checks and application

### Screenshot selection cursor

The shared Linux screenshot workflow carries a small upstream Slurp backport
so Hyprland can supply its own themed crosshair through `cursor-shape`. It does
not force Adwaita or change global cursor settings, scale, capture resolution or
Swappy. Diagnosis and live acceptance are in the
[screenshot audit](../../../docs/laptop-audit/screenshots.md); the
[package guide](../../../pkgs/slurp-cursor-shape/README.md) records checks and
the removal contract. Apply HM and test F10 selection, Esc cancellation and
completion into Swappy; no NixOS change, session restart or Hyprland reload is
required for this package-only change. The user reports that the corrected setup
works on Lenovo; this is user acceptance, not independent all-host/UI verification.

### Other checks and application

The HM Kitty launch scheme is now tab-first: `Super+,`, `Super+E`, `Super+N`
open Fish/Yazi/Neovim tabs in the focused Kitty at the home directory. Shift+comma/E/N
open OS windows globally through Hyprland, using its normal launch cwd.
The shifted launcher binds use physical keycodes for EN/RU, and the old unshifted
aliases are removed. `Super+Shift+E` is ordinary Yazi, not sudo Yazi. The same
launch migration applies to Acer/desktop; unrelated host controls are unchanged.
See the [Kitty audit and checks](../../modules/kitty/README.md). Apply HM, reload
Hyprland and reload Kitty's config before testing the new bindings; no NixOS
change or reboot is needed for this follow-up.

`Super+W` now closes the current Kitty tab, including all panes. Hyprland's
textual-switcher W/Ц bindings are removed; `hypr-semantic-switcher-tofi` remains
available as a terminal command. `Super+Space` is unchanged. This applies to the
same three Linux profiles and is listed in F1 help.

`Super+]` / `Super+[` switch to the next/previous Kitty tab.
`Super+Shift+[` / `Super+Shift+]` move the current tab left/right. The shared
Shift+comma/period tab mappings are removed. All four bracket controls use
the same physical keys in EN/RU. `Ctrl+Tab` / `Ctrl+Shift+Tab` remain available.
`Super+Shift+,` opens a new terminal OS window, including outside Kitty.

Small implementation-path fixtures (hyprctl mocked, not a real input device):

```fish
python3 -B home/linux/laptop/tests/test_touchpad.py
python3 -B home/linux/modules/hyprland/tests/test_screenshot.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/laptop/tests/test-hotkeys.nix
```

These checks do not establish installed helper discovery, native compositor
keyword acceptance or actual hardware-key behavior. Builds and activation are
left to the user:

1. Review changes, then run `home-manager switch --flake .#samov-laptop`.
2. Run `hyprctl reload`, then `hyprctl configerrors`; expect no errors. No NixOS
   application or reboot is needed.
3. Press F8 twice: only touchpad input stops/returns; an external mouse stays
   usable. Reload with the touchpad disabled: it should become enabled again.
4. Check F9 opens todo, Fn+F1 opens help with these Lenovo labels, Fn+F11 switches
   themes, and F10 still opens region selection/Swappy. F3 should reach apps now.
5. Confirm F1–F6 hardware functions remain working. F7/Smart Connect are not new
   actions and should not be treated as acceptance criteria for this batch.

The user applied the HM changes and accepted the hotkey behavior. This is user
acceptance, not independent agent observation of every key, external-mouse
isolation or reload/login scenario. No additional build or activation was run by
the agent for this acceptance record.
