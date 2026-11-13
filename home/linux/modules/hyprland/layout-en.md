# Focus-triggered English layout

`scripts/focus-layout-en.sh` is the shared Hyprland focus/layout listener, renamed
from `terminal-layout-en.sh` now that it also handles Qt pinentry. It is shared
by Lenovo, Acer and desktop. Home Manager installs it; each host starts one
listener through its existing `exec-once`. There is no additional service,
keyboard hook or idle layout polling.

- Entering the terminal group from a nonterminal selects layout index 0 (`us`
  in all three host configurations). Moving directly between terminals retains
  the chosen layout, as before.
- Every focus event for Qt GPG pinentry selects index 0, including moving
  directly between two pinentry windows. Matching is case-insensitive and exact:
  `org.gnupg.pinentry-qt` for Wayland, `pinentry-qt` / `pinentry` for legacy
  class / invocation-name forms. Titles are not matched or logged.
- Manual layout changes while pinentry remains focused are allowed. No
  `activelayout` handling, keyboard-layout lock or restoration on leaving
  pinentry is added. The user explicitly chose to retain this simple policy
  rather than introduce saved-layout restoration. The old terminal watcher did
  not restore the previous layout either. Interface language is unchanged.
- The existing socket reconnection loop remains. Each new stream starts with
  fresh terminal state. The listener does not inspect initial focus: if started
  or reconnected while pinentry is already focused, refocus the dialog once.
  Event handling is asynchronous, not a guarantee ahead of the first keystroke.

Pinentry 1.3.2's [`qt/main.cpp`](https://github.com/gpg/pinentry/blob/pinentry-1.3.2/qt/main.cpp)
sets `QApplication::setDesktopFileName("org.gnupg.pinentry-qt")`. The installed
GPG agent selects the Qt package's `bin/pinentry`. Actual compositor class and
live focus/layout behavior still need target-session acceptance; no secret-entry
prompt was opened by the agent for inspection.

## Installed-session follow-up

The user applied Lenovo HM. Read-only inspection confirmed the new installed
script and launcher, but the old `terminal-layout-en.sh` processes were still
running when the user reported no EN switch. With explicit approval, the agent
stopped only that watcher tree (Bash, socat and Bash handler) and launched the
installed `focus-layout-en.sh` through Hyprland. One new watcher tree was then
confirmed; no compositor, application or GPG-agent restart was performed.
This does not independently verify the pinentry UI or other hosts.

One 2-second idle sample recorded no CPU ticks at 10 ms resolution and about
11 MiB summed RSS for the three processes, including shared pages. It is not
a focus-switch stress test or a guarantee of zero CPU use.

## Checks and application

1. Run the small fixtures: `python3 -B home/linux/modules/hyprland/tests/test_layout_en.py`.
   They execute the production Bash handler with a fake `hyprctl`: terminal
   transitions, each pinentry focus, exact classes, ignored titles/layout events,
   failed switches, no restoration on leaving pinentry and state reset between
   streams. A static check also covers
   the shared installation path and all three host launchers. They do not test the real
   compositor, socket transport or password entry.
2. Make the renamed source visible to the Git flake with
   `git add home/linux/modules/hyprland/scripts/focus-layout-en.sh` if it is not
   already tracked. Apply only Home Manager, e.g. `home-manager switch --flake .#samov-laptop`
   (or the corresponding Acer/desktop profile). No NixOS change is needed.
3. Replace the already-running `exec-once` listener: restart only the watcher and
   its socat/handler children, or log out/in. A config reload alone does not
   replace it. This is a process restart, not a cache reset. Avoid starting a
   second listener alongside it or killing its whole process group: it can share
   the compositor's group. Lenovo's current listener was already replaced above.
4. Select RU in a GUI app and invoke an ordinary GPG operation that needs pinentry.
   Before entering a password, verify EN using the layout indicator. Refocus from
   another window and check EN again. A manual RU change while focused should
   persist until the next focus; never test by typing a real password visibly.
5. Check terminal → terminal preserves a manually chosen RU layout, while
   nonterminal → terminal still selects EN. If pinentry does not switch, inspect
   only `hyprctl -j activewindow`'s `class` while that window is focused; do not
   export its title or password-related content.

Documentation/tests need no activation. No build, Nix activation or direct
keyboard-layout command was run by the agent; the approved watcher restart is
recorded above. Project formatter CLIs (Beautysh, Ruff and
Prettier) were unavailable; existing style is retained without a substitute.
