# Shared notification lifetimes

Configured for standalone HM `samov-laptop`, `samov-laptop-old` and `samov-desktop`.
Mac/server do not gain Mako. All changes here need **HM only**, not NixOS activation.
Lenovo's separate input/output preference needs NixOS too; see
the [archived audio-policy acceptance](../../../../docs/laptop-audit/archive/voice-dictate.md#15112026-lenovo--встроенный-микрофон-и-быстрый-старт).
Lenovo now uses [Handy](../../laptop/handy/README.md); the Whisper notification
lifecycles below remain active on Acer/desktop, not on Lenovo. Handy uses its
native tray/audio feedback and CLI cancellation, not this helper's Mako actions.

| Notification | Lifetime |
| --- | --- |
| Mako default (udiskie, menu errors, apps without an override) | 15 seconds |
| Battery warning/critical | Until manual dismissal or Waybar's charging event |
| Battery full | 3 seconds, no sound |
| Whisper recording (Acer/desktop) | Until second hotkey, left-click cancellation, manual dismissal or recorder failure |
| Whisper transcription (Acer/desktop) | Until recognition finishes, left-click cancellation or manual dismissal |
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
on exit. Hotkeys serialize with a session-local lock. Lenovo's classified local
ALSA input waits for the first PCM frame instead of a fixed two seconds; Bluetooth,
unknown inputs and Acer/desktop retain the existing HFP allowance. A second press during startup stops
without publishing a late recording notice. The recording notice shows both
**Super+Shift+R — stop and transcribe** and **Left-click — cancel recording**.
Its native `default=Cancel` action stops the microphone and removes the audio
without starting recognition, typing text or changing the clipboard. A 3-second
`Recording cancelled` notice confirms cancellation. Right-click dismissal does
not stop audio recording and is not followed by notification polling/reposting.
The second hotkey closes the notice before recognition; success/error notices
have separate lifetimes.
An older worker cannot delete newer recording state. This is a shell worker for the
active recording, not an added daemon. Abrupt worker kill/session termination and
unresponsive kernel/audio operations are not guaranteed recoverable.

Recognition now publishes a persistent **Transcribing… Left-click to cancel**
notice with a native `default=Cancel` action. Mako does not render separate action
buttons: its standard left click invokes the default action on the whole notice.
Left-clicking stops the current recognizer, removes temporary audio/text and shows
`Transcription cancelled` for 3 seconds. It does not type text or change clipboard
contents. Right-click dismissal only hides the notice; recognition continues.
Recording and recognition have separate cancellation actions: after the second
hotkey claims the recording, an old recording action cannot cancel recognition.
Recognition cancellation remains available until recognition finishes, not after
insertion starts. The existing second hotkey still stops recording and begins recognition.
The action listener and its `notify-send` child are reaped on completion; closure
uses the transcription invocation's PID-scoped category. Notification delivery
failure does not cancel otherwise successful recognition. No Mako binding, new
daemon, recognition/GPU option or microphone startup timing was changed.

The recording notice uses libnotify's `--print-id` acknowledgement before
releasing the startup lock, then waits for its action on the same pipe. This
prevents a second hotkey from closing a notice that has not yet been published.
The notification ID is not persisted or used across daemon restarts. Cancellation
targets the recording worker's `BASHPID`, not the already-exited toggle launcher.

### Temporary audio and text

There is one `$XDG_RUNTIME_DIR/voice-dictate/recording.wav`, not an archive of
recordings. Normal recognition success/failure, recording/recognition cancellation
and handled microphone failures remove it. Recognition also removes `transcript.txt`
and `transcription-action`. Starting a new recording removes stale audio/text/action
files from an interrupted invocation before opening the microphone. `toggle.lock`
is intentionally retained; it contains no audio or transcript.

An abrupt process/session termination can leave the current files until the next
recording or runtime-directory cleanup. There is no periodic cleanup or guarantee
of secure erasure. No recording duration/size limit is configured: an active
recording left running continues to grow, even though completed recordings do
not accumulate.

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
For the two laptops, `pkgs/blueman-polkit/notification-timeout.patch` now prepares
3-second expiry of informational GTK dialogs, because upstream ignores their
timeout argument. Explicit positive/zero timeouts are honored; dialogs with
buttons remain pending. This is a NixOS package change, not a Mako timeout rule.
See `pkgs/blueman-polkit/README.md` for contracts, removal checks and application.
The user applied and accepted the initial 15-second expiry, then requested three
seconds; that final duration is not yet applied/live-accepted. Mako's general
15-second default is unchanged. No new notification daemon route is added.
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
coverage; recording/recognition cancellation, dismissal without cancellation and pending listener
cleanup use actual shell signals with a synthetic recognizer. These do not verify
live Mako interaction. Selected merged declarations cover host timings, thresholds, absence of
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
   second hotkey still transcribes. Repeat with a left-click during recording:
   expect `Recording cancelled`, a stopped microphone, no recognition/insertion,
   unchanged clipboard and no `recording.wav`. Do not unplug an active USB microphone to test errors.
5. Observe charger dismissal/full notice only during normal battery use. Do not
   deliberately discharge or fake live battery state. Real low-battery Hibernate
    triggering and reserve sufficiency remain separate, unverified acceptance.

For transcription cancellation, apply HM as in step 1 (no Mako reload or NixOS
activation needed), then:

1. Dictate a sufficiently long phrase with Super+Shift+R and press it again.
   While **Transcribing…** is visible, left-click it. Expect the cancellation
   notice, no inserted text and the previous clipboard contents unchanged. A very
   short recording may finish before a click can be made.
2. Repeat and right-click the transcription notice instead. Recognition should
   continue and insert/copy the result normally.
3. Start another dictation after cancellation. It should record and transcribe
   normally, with no leftover transcription notice. On 15 November the user
   reported that recognition cancellation appeared to work consistently; this
   is not independent observation or full UI acceptance. Recording cancellation
   and the combined recording hints were added after that report and still need
   user acceptance.

Documentation itself needs no activation. The agent did not build or activate this
batch; the user accepted the notifications and manually enabled Blueman dialogs.
