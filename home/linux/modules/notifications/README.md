# Shared notification lifetimes

Configured for standalone HM `samov-laptop`, `samov-laptop-old` and `samov-desktop`.
Mac/server do not gain Mako. All changes here need **HM only**, not NixOS activation.

| Notification | Lifetime |
| --- | --- |
| Mako default (udiskie, menu errors, apps without an override) | 15 seconds |
| Battery warning/critical | Until manual dismissal or Waybar's charging event |
| Battery full | 3 seconds, no sound |
| Dictation recording | Until second hotkey, manual dismissal or recorder failure |
| Transcribed and copied to clipboard | 3 seconds |
| Dictation errors | 15 seconds |
| Hyprland theme switch | Unchanged: 3 seconds |

Applications retain their explicit timeout, including persistent notices. Internal
application popups are not controlled by Mako. Lenovo retains battery thresholds
15%/2%; Acer retains 30%/15%. Desktop has no battery module. Battery warning/critical
also play one standard short `dialog-warning.oga`, without changing volume/mute.
UPower/Hibernate, audio/input selection, recognizer options and GPU policy are unchanged.

## Lifecycle and limitations

`notification-close` queries active Mako notices and dismisses exact app/category
matches by current ID. It never dismisses all, stores an ID across daemon restarts,
or prints unrelated notification contents. Commands have bounded timeouts; failures
are reported, not proof of successful dismissal. A daemon/IPC failure can prevent
automatic closure; there is no retry service. A daemon restart between list/dismiss
is not an atomic transaction.

Battery low/critical use the same native replacement tag and category. Native Waybar
events close them on charging; normal=99/full=100 ensure every level has a named
event. Waybar maps every non-discharging status (including Unknown/Not charging) to
charging events; this preserves its native semantics, not measured charger current.
The configured interval is 30 seconds, so closure is not guaranteed instantaneous.
No battery watcher or service was added; multi-output sounds are not deduplicated.
Manual dismissal stays dismissed until another threshold/status event or bar restart.

The dictation worker waits for its own recorder and closes a PID-scoped category
on exit. Hotkeys serialize with a session-local lock; startup retains the existing
two-second Bluetooth HFP allowance. A second press during that allowance stops
without publishing a late recording notice. Manual dismissal does not stop audio
recording and is not followed by notification polling/reposting. The second press
closes the notice before recognition; success/error notices have separate lifetimes.
An older worker cannot delete newer recording state. This is a shell worker for the
active recording, not an added daemon. Abrupt worker kill/session termination and
unresponsive kernel/audio operations are not guaranteed recoverable.

## Blueman pairing confirmations

`home/linux/gui-set/default.nix` sets
`dconf.settings."org/blueman/general".notification-daemon = false` on all three
Linux GUI profiles. Blueman 2.4.6 sends named Confirm/Deny actions without a
default action; Mako's default left click invokes only the default action and
does not render those buttons. A visible Pairing request/Connected notice is
therefore not proof of completed pairing. Its installed `BluezAgent.py` and
`gui/Notification.py` confirm that this setting selects the native GTK fallback
dialog, including pairing and service authorization, with no daemon restart.

This changes **all Blueman notification presentation**, not just mouse pairing.
Other apps still use Mako; no Bluetooth trust, device keys, driver, power or
audio policy is changed. The user reports successful mouse setup after the manual
equivalent, `dconf write /org/blueman/general/notification-daemon false`.
Declarative HM delivery is checked separately, not yet user-applied. No automatic
reconnection, repeated pairing or post-resume acceptance follows from that report.
To revert, remove the declaration, apply HM and run
`dconf reset /org/blueman/general/notification-daemon` to restore the upstream default.

## Checks

```fish
python3 -B home/linux/modules/notifications/tests/test_close.py
python3 -B home/linux/modules/waybar/tests/test_battery_notify.py
python3 -B -m unittest discover -s home/modules/voice-dictate/tests
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/modules/waybar/tests/test-battery.nix
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/modules/voice-dictate/tests/test-declarations.nix
nix eval --impure --offline --json --option allow-import-from-derivation false --file hosts/laptop/tests/test-battery.nix
nix eval --impure --offline --json --option allow-import-from-derivation false --file home/linux/gui-set/tests/test-blueman.nix
```

Mocks exercise exact Mako selection, actual battery helper and dictation shell.
Recording tests use isolated synthetic recorder processes, not real microphones:
normal stop, startup allowance, startup/notification failure, unexpected exit and
newer-session isolation. Stop/transcription fixtures retain Unicode/stdin/error
coverage. Selected merged declarations cover host timings, thresholds, absence of
new Mac/server daemons and unchanged Lenovo power/resume policy. No build, activation,
live Waybar charger transition, audible sound or microphone/UI acceptance by the agent.

On 12 November 2026 the user accepted the notification behavior. This is user UI
acceptance on Lenovo, not independent agent observation or evidence that every
threshold, charger transition, recorder failure or other host was exercised.
The earlier source/mock checks remain distinct from this acceptance; no deliberate
discharge or real low-battery power action was tested.

## Apply and accept

1. Finish any current dictation. Review changes, then apply HM on each GUI machine:
   `home-manager switch --flake .#samov-laptop` (Lenovo),
   `home-manager switch --flake .#samov-laptop-old` (Acer), or
   `home-manager switch --flake .#samov-desktop` (desktop). Never apply Lenovo on Acer.
2. Run `makoctl reload` and `pkill -USR2 -x 'waybar|\.waybar-wrapped'`.
3. Send a normal notice: `notify-send 'Timing test' 'Should close after 15 seconds'`.
   Then `~/.config/waybar/scripts/battery-notify test` checks the safe 15-second popup
   and one warning sound, without reading/changing charge or triggering power actions.
4. Press Super+Shift+R, wait for Recording, speak, then press again. Recording must
   disappear; the copied/transcribed success notice lasts 3 seconds. Repeat once
   with manual dismissal: recording continues, the notice stays dismissed, and the
   second hotkey still transcribes. Do not unplug an active USB microphone to test errors.
5. Observe charger dismissal/full notice only during normal battery use. Do not
   deliberately discharge or fake live battery state. Real low-battery Hibernate
   triggering and reserve sufficiency remain separate, unverified acceptance.

Documentation itself needs no activation. The agent did not build or activate this
batch; the user accepted the notifications and manually enabled Blueman dialogs.
