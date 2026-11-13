# Lenovo Command keys

This is a customization, not an upstream backport. No lock change, input-group
membership for samov, driver patch or global Ctrl translation is involved.
The user chose Kitty as the primary full-feature terminal and deferred any
OpenCode C/X plugin until an actual failure. The user subsequently applied the
changes and reported that ordinary use looks correct. This is scoped user
acceptance, not independent agent observation or full coverage of the cases below.

## Architecture and permissions

`hosts/laptop/command-keys.nix` runs the pinned xremap socket variant as
`lenovo-xremap`, not root or samov. A measured name + phys + bus udev match grants
only the built-in keyboard to its private group. The event number is not pinned.
The daemon also has uinput access. DeviceAllow's input class is a cgroup ceiling;
the per-device DAC rule, not `--device`, limits physical access.

The Hyprland variant runs as a graphical-session bridge under samov. Its IPC
group can access `/run/xremap/1000`, **not** the keyboard. UID 1000 matches the
installed account; update the directory if migrating to a different UID. Both
parts disable launch actions and window logging. No debug keystroke logging.
The private socket protocol supplies window context, not a raw keyboard stream.
The system daemon still processes untrusted session-side IPC responses; this is
privilege separation, not a security audit or proof of vulnerability absence.

Existing Steam uaccess to `/dev/uinput` is unchanged. This does not close that
pre-existing injection capability. Stopping the bridge does not stop the daemon:
the unconditional left Alt/Super swap remains in VTs and at login/lock screens.
When context is missing, the GUI allowlist must not match. Stop the system daemon
to restore the original keyboard, not just the bridge. Releasing all keys before
stopping avoids stuck modifier state; replug/relogin may be needed after failure.

There are no intentional typing sleeps (`keypress_delay_ms=0`, `throttle_ms=0`).
Only eligible editing chords query window context. The bridge request is
synchronous, with a 500 ms read timeout (not a total end-to-end deadline).
A stalled request can delay subsequent input. Latency has not been measured.

## Behavior

- Physical left Alt becomes Super; physical left Windows becomes Alt. Right Alt,
  Ctrl, Caps, Fn and other keys have no remap entries. External keyboards are not
  selected. Firmware-generated modifier chords still need real-device acceptance.
- C/V/X/A/Z/Shift+Z translate only for the explicit GUI allowlist in `rules.nix`.
  Actual classes, especially Freesm/Ardour/Qt apps and XWayland, need acceptance.
  Terminals, games, password dialogs, mpv, Tofi and unknown/empty context are not
  blanket-translated. A focused layer surface can leave a stale toplevel context;
  layer-shell behavior is not accepted by these source checks.
- Hyprland retains its window-control scheme. The conflicting Russian copy/redo
  aliases are removed (killactive on С, Zoom on Shift+Я). Super+Q still closes.
- Kitty's small in-process action normalizes the six keys using its ASCII layout
  fallback and inspects foreground processes, not titles. Neovim/Yazi receive
  native Super chords. Fish receives prompt-native chords. Otherwise C copies
  terminal selection without ever falling back to interrupt; V uses native paste
  handling. OpenCode V invokes its native Ctrl+V paste including attachments;
  Z/Shift+Z/A remain native Super. Unknown programs never receive Ctrl+Z as undo.
  SSH/tmux/nested shells and process wrappers are not universal context support.
- Fish binds only its prompt editor (default/insert maps). C copies the selection
  or command line; X cuts only a nonempty selection; A selects the command line.
  Z/Shift+Z call undo/redo, not signals or command execution rollback.
- The Neovim site plugin does not edit or own the manual Neovim repository. In
  Normal, C/X copy/cut a line; in Visual, the selection. V uses the system +
  register; A selects the buffer; Z/Shift+Z call native undo/redo. Insert supports
  paste/select/undo/redo; command-line and terminal modes support paste, but no
  guessed undo for nested terminal jobs. Both Latin/Cyrillic aliases are present.
- Yazi's manager C/X/V/A operate on files and its internal yank buffer. There is
  no new filesystem undo. Input-widget C/X/V/A/Z/Shift+Z use its native actions,
  not an invented Finder clipboard or universal system clipboard contract.

## Agreed limitations — not full Mac parity

1. **Alacritty:** C/V use terminal-native Copy/Paste; X/A/Z/Shift+Z emit explicit
   CSI-u Super events. It has no Kitty foreground router, so C/V cannot also
   operate on Yazi files/Neovim Visual selection with this configuration. CSI-u
   compatibility and RU matching are unverified. The user explicitly chose Kitty
   as the primary terminal; a separate Alacritty routing design is not requested.
2. **OpenCode 2.1.4:** native Z/Shift+Z/A and paste are covered by source contracts;
   there are no published input.copy/input.cut command IDs. Forwarding Super+C/X
   without terminal selection does not implement input selection copy/cut.
   The user reports prior Kitty-based behavior and explicitly defers a TUI plugin
   until something fails in actual use. No plugin/cli.json changes are made here.
   Do not claim internal selection C/X acceptance or substitute Ctrl+C
   (clear/exit) or Ctrl+X (leader). Paste still uses OpenCode's native Ctrl+V,
   not text-only clipboard injection; real image attachment acceptance is pending.
3. **Hardware/UI acceptance:** the user reports successful ordinary use; the
   agent did not exercise real keyboard grabbing, bridge lifecycle, EN/RU
   applications, clipboard or latency. Those detailed scenarios remain open.
   In particular,
   F7 may emit a firmware Super+P chord on the same keyboard; verify it rather
   than promising that remapping cannot affect it.

## Checks, reapplication and recovery

Completed lightweight checks are recorded in the task handoff, not inferred from
this procedure. Reproducible small checks from the repository root:

```fish
python3 -B home/linux/laptop/command-keys/test_keys.py
nvim --headless -u NONE -l home/linux/laptop/command-keys/test_nvim.lua home/linux/laptop/command-keys/nvim.lua
fish --no-config -n home/linux/laptop/command-keys/fish.fish
nix eval --offline --impure --json --expr 'import ./home/linux/laptop/command-keys/test-declarations.nix { flake = builtins.getFlake "path:/home/samov/nix-config"; }'
```

These check mocks of the actual Kitty action, actual headless Neovim editing and
selected merged declarations, not a compiled xremap/native graphical integration.
Python/Markdown formatters were unavailable; layout is preserved, not replaced
with a different formatter. Nix uses the installed pinned nixfmt 1.5.0.

After reviewing the agreed scope and diff:

1. Make new files visible to the Git flake source with selective `git add` (this
   is not a commit). Build only Lenovo, if desired: `nix build
   .#nixosConfigurations.laptop.config.system.build.toplevel`, then `nix build
   .#homeConfigurations.samov-laptop.activationPackage`. The agent did not build.
2. Apply NixOS with `sudo nixos-rebuild switch --flake .#laptop`, then HM with
   `home-manager switch --flake .#samov-laptop`. Reboot to obtain the new IPC
   group in both interactive and systemd-user processes and the new udev access.
   Existing sessions otherwise may lack the IPC group even after HM activation.
   Save work first: the system switch can start swapping modifiers immediately,
   before HM has removed the old Russian aliases. Do not try the new shortcuts
   between the two switches; test only after both and the reboot.
3. Check `systemctl status lenovo-xremap` and `systemctl --user status
   lenovo-xremap-bridge`. `id` must not acquire input/uinput; verify keyboard node
   ownership and that samov still cannot read it. Do not test by recording keys.
4. In a disposable editor document, test all six chords in EN/RU, genuine Ctrl+C/Z,
   both left modifiers, AltGr, Caps, Fn/F1–F12, brightness and window controls.
   Check ordinary fast typing/repeat and chords immediately after focus changes.
5. Test Kitty terminal selection separately from Neovim Visual selection, Fish
   prompt selection and disposable Yazi file copy/move. Never test cut/delete on
   valuable files. Confirm native OpenCode input undo is not session rollback.
6. With keys released, stop/restart only the user bridge and confirm static
   modifier swapping continues but GUI translation does not guess a context.
   Check logout/login and one resume; no restart hooks are installed.
7. Recovery: release keys, then `sudo systemctl stop lenovo-xremap` and
   `systemctl --user stop lenovo-xremap-bridge`. This is temporary; boot restarts
   the enabled service. Remove both module imports/rebuild to persist removal,
   or use reviewed previous NixOS/HM generations. No firmware changes are needed.

Documentation and tests require no Nix activation. The Neovim mappings are HM
site-runtime data; no manual edit in `~/.config/nvim` is required.
