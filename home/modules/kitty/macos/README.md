# Independent macOS Kitty patches

These are one-time patches for the supplied Kitty config at commit `019c79e`,
not Home Manager modules. None changes macOS system shortcuts.

- `kitty-ui.patch`: the previously prepared appearance changes.
- `kitty-keybindings.patch`: only Kitty keyboard mappings in `kitty.conf`.
  It applies to the original config or after `kitty-ui.patch`; the patches can
  be applied in either order. Do not reapply an already installed patch.
- `kitty-keybindings-fix.patch`: correction for the **previously applied** keyboard
  patch. Use this instead of reapplying the revised full keyboard patch. It
  restores the original Mac launch methods and disables the Shift app launches.

## Keyboard scheme

| Keys | Action |
| --- | --- |
| `Cmd+,` | Native `new_tab`, as in the original Mac config |
| `Cmd+E` | New Yazi tab at home via `fish -l -c yazi` |
| `Cmd+N` | New Neovim tab at home via `fish -l -c nvim` |
| `Cmd+Shift+,/E/N` | Disabled; no app/window launch |
| `Cmd+W` | Close the current tab, including its panes |
| `Cmd+[` / `Cmd+]` | Previous / next tab |
| `Cmd+Shift+[` / `Cmd+Shift+]` | Move the current tab left / right |

All eleven mappings use Kitty's native shifted/ASCII layout fallback for EN/RU.
Unlike the HM launch scheme, the Mac app commands retain their original login
Fish startup and tab titles instead of executing Yazi/Neovim directly. The user
reported disappearing tabs after that direct-launch migration; restoring Fish
startup is a compatibility correction, not a verified diagnosis of the Mac error.
The original `Cmd+, new_tab` action is restored without a forced directory: it
uses Kitty's startup directory (normally home when opened from the GUI), not
the active pane's cwd. Yazi/Neovim explicitly use `--cwd=~`.
Shift app launches are explicitly unbound with `no_op` so removing an override
cannot accidentally restore Kitty's default new-window action.
The old explicit
Russian Neovim/Yazi aliases and the later `Cmd+, new_tab` override are removed
so they cannot bypass the new launch behavior.

`Ctrl+Tab` / `Ctrl+Shift+Tab`, `Cmd+Shift+Left/Right` pane navigation, recording
reservations, project/Chrome launchers and font shortcuts are preserved.
Colors, fonts, opacity and the close-confirmation policy are unchanged.
These shortcuts only act while Kitty is focused; no global app launcher is added.

## Apply and verify on the Mac

1. Save any local config edits and choose **one** patch:
   - Original config, with or without the UI patch: `kitty-keybindings.patch`.
   - Earlier keyboard patch already installed: `kitty-keybindings-fix.patch`.
   Copy it to `~/Downloads/` and inspect it before applying it.
2. In Fish, check and apply separately; if the check fails, stop rather than
   forcing the patch over a different configuration:

   ```fish
   git -C ~/.config/kitty apply --check ~/Downloads/kitty-keybindings-fix.patch
   git -C ~/.config/kitty apply ~/Downloads/kitty-keybindings-fix.patch
   ```

   These commands assume the earlier keyboard patch is installed. For an
   original config, use `kitty-keybindings.patch` in both commands instead.

3. Reload Kitty with `Cmd+Shift+F5` or its native `Ctrl+Cmd+,`. If Kitty reports
   an unknown `--allow-fallback` option, check its version before continuing;
   parsing was verified with Kitty 0.49.1, not with the actual Mac installation.
4. Create disposable tabs with `Cmd+,/E/N`: expect an interactive shell, Yazi and
   Neovim, respectively. Check shell startup cwd with `pwd` (see its native
   directory behavior above). Switch and reorder tabs using brackets, then close
   only a disposable tab with `Cmd+W`. Repeat in EN/RU.
5. Test `Cmd+Shift+,/E/N`: none should open a tab or OS window.
   Check existing recording, pane navigation and project launchers still work.
   If the Hyprland/layout error persists, capture its exact text, `kitty --version`
   and whether `fish -l -c nvim` also reports it when run directly on the Mac.
   No Hyprland command is present in either keyboard patch.

Local checks covered clean patch application to the original snapshot, both
application orders with the UI patch, full patched-config parsing and synthetic
EN/RU shortcut resolution. The correction applied after the earlier patch
produces the same config as the revised full keyboard patch. The theme files
remain byte-identical with the keyboard-only patches. No real macOS keypress,
Fish environment, app launch or UI test was performed.
