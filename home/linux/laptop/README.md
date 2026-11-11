# Lenovo Home Manager hotkeys

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

## Checks and application

Small implementation-path fixtures (hyprctl mocked, not a real input device):

```fish
python3 -B home/linux/laptop/test_touchpad.py
python3 -B home/linux/modules/hyprland/tests/test_screenshot.py
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/laptop/test-hotkeys.nix
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
