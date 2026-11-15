# Lenovo dictation: Handy / Parakeet Q4

Handy 0.9.8 from locked unstable is the primary Lenovo dictation path. The user
prefers Parakeet TDT v3 Q4 for more stable sentence structure in ordinary speech;
English technical names remain imperfect. Q8/streaming are not needed for now.
Whisper's Intel acceleration did not come from Handy: it was a separate HM
change. The [archived audit and measurements](../../../../docs/laptop-audit/archive/voice-dictate.md)
preserve the comparison and former setup. Shared Whisper code/tests remain active
on Acer/desktop; Lenovo's inactive alternative is [`../archive/whisper.nix`](../archive/whisper.nix).

## Declarative boundary

`default.nix` declares the package, Intel-only wrapper, pinned Q4 model, hidden
systemd user service and initial settings. Lenovo's `hyprland.conf` owns hotkeys
and the wtype device policy. No new NixOS options, raw-input/uinput permissions,
polling daemon, package patch or flake input is introduced.

- `handy` wraps the unchanged unstable package through standard `symlinkJoin` /
  `makeWrapper`. Every PATH/desktop launch and CLI action sees only Intel ANV via
  `VK_DRIVER_FILES=/run/opengl-driver/share/vulkan/icd.d/intel_icd.x86_64.json`.
  This is not a session-wide environment variable. Do not launch the unwrapped
  store binary from an old generation.
- The native Q4 local-model path remains HM-managed, without forced overwrite:
  `$XDG_DATA_HOME/com.pais.handy/models/parakeet-tdt-0.6b-v3-Q4_K_M.gguf`.
  The upstream catalog revision/hash pin 485,425,504 bytes. Do not delete or
  replace that model through the GUI; the ordinary catalog Download defaults to Q8.
- `handy.service` follows the graphical-session lifecycle used by
  [upstream's HM module](https://github.com/cjpais/Handy/blob/v0.9.8/nix/hm-module.nix),
  with `--start-hidden`, a Hyprland environment condition and restart on failure.
  It stays in the tray; closing the settings window is not Quit. App-managed
  "Launch on Startup" must remain **off** to avoid a second autostart path.
- `initial-settings.nix` is **seed-only**, not continuous enforcement. HM installs
  a regular mode-0600 native JSON store only when the path is absent, before HM
  reloads/starts systemd services. Existing
  files, malformed JSON and symlinks are untouched. GUI changes and app migrations
  remain writable; later Nix edits do not reset them. No merge/watcher or readonly
  settings symlink is used. Secrets/provider settings are not copied into Nix.

This boundary is deliberate: Handy's upstream HM module has only service/package
options, and v0.9.8 has no settings-override CLI/API. Changing the ASR model would
not change the application's settings format. A different runtime/quantization
could change recognition results; it is not a configuration-only substitution.

## Settings audit and initial preferences

| Setting | Decision |
| --- | --- |
| Model / language | Parakeet TDT v3 Q4_K_M, auto language, no translation |
| Compute | GPU, observed stable Intel selector `["vulkan","id","0000:00:02.0"]`; wrapper restricts discovery |
| Background | Start hidden, tray on; HM service, not app autostart |
| Model unload | After 5 minutes; retain the accepted warm-use/memory trade-off |
| Microphone | Default input, not a hard-coded Bluetooth mic; always-on and keep-stream-open off |
| Feedback | Native start/stop sounds on at 50%; overlay None after the user's unsuccessful Minimal trial |
| Output | Direct + wtype; no clipboard modification, trailing space or Auto Submit |
| Recognition | VAD/Silero and filler removal retained; no LLM/post-processing or external script |
| History/audio | Retain 5 entries / latest 5 recordings, matching the user's current preferences |
| Updates | Nix supplies the package; nixpkgs disables the in-app updater independently of its GUI checkbox |

The native start sound follows the first input callback/readiness check in
[`actions.rs`](https://github.com/cjpais/Handy/blob/v0.9.8/src-tauri/src/actions.rs#L475-L522),
not an arbitrary added sleep. Start speaking after that cue. Real first-syllable
and audio-device behavior still need acceptance after adoption of these settings.
The user reports that Handy generally works after migration, but the Minimal
overlay disappears unstably during window/focus changes and looks poor. The user
explicitly reports that it does not take focus from application windows and has
disabled it in the GUI. Initial settings now also use Overlay Style None. No
window-rule workaround or replacement notification daemon is added. Native
sounds and keyboard cancellation remain available; the old helper's Mako
lifecycle, clickable cancellation and separate success/copied notice are not
provided. This is scoped user feedback, not independent UI verification or full
acceptance of every service/input/audio scenario below.

The earlier long Handy trial recognized 44.61 seconds of retained audio in 3.03 s,
using about 11–12 CPU-seconds with a short whole-machine CPU burst. The user accepts
that load. This is not evidence of idle power consumption, battery impact,
temperature, or NVIDIA sleep during dictation. With the configured microphone
options off, it is not intended to continuously capture/transcribe in the background.

NixOS audio policy in `hosts/laptop/audio.nix` is unchanged: built-in microphone
preferred, headphones selected for output when connected, speakers otherwise,
and Bluetooth HFP input selected manually. Saved GUI defaults can override that
policy. The [historical acceptance](../../../../docs/laptop-audit/archive/voice-dictate.md#15112026-lenovo--встроенный-микрофон-и-быстрый-старт)
remains available; this HM migration does not require NixOS activation.

## Hotkeys and synthetic input

- **Super+Shift+R:** native `handy --toggle-transcription`, press to start/stop.
- **Super+Shift+T:** native `handy --cancel`, cancel recording/recognition without insertion.
  T is adjacent to R; the previous Super+Ctrl+Shift+Escape binding is removed.
- No post-processing or Ctrl+Space Hyprland binding, and no extra trial R binding.
  Tauri is retained; do not enable the raw-input HandyKeys implementation.

Ctrl+Space is already used by the user's manually managed Neovim: Normal/Visual
selection (`lua/config/mapping.lua`) and Insert completion (`lua/plugins/blink.lua`).
It is intentionally not made a global dictation shortcut. Handy's UI binding
labels in the initial store match Hyprland; its disabled post-processing shortcut
remains inert. Empty bindings are not a supported disable mechanism in v0.9.8,
and omitting bindings restores the defaults. Wayland hotkeys are explicitly
delegated to the compositor in the upstream documentation.

Existing GUI shortcut labels are seed-only and may still show the previous cancel
combination. Applying HM and reloading Hyprland updates the actual Wayland hotkey
without resetting the native store; changing its GUI label is optional.

Long Direct/wtype text previously opened **Hyprland controls**, not Tofi launcher,
on both Whisper and Handy. wtype 0.4 allocates sequential codes to distinct
characters; code 59 can collide with the compositor's physical F1 interpretation.
The native per-device setting `keybinds = false` for
`hl-virtual-keyboard-wtype` prevents **compositor** shortcuts from this virtual
keyboard while still delivering text to the application. Physical/xremap keys,
their layouts and actual F1 help remain unchanged. This does not suppress
application-level shortcuts or prove all insertion/focus problems resolved.
The source is Hyprland 0.55.4 `InputManager::applyConfigToKeyboard` and
`KeybindManager::onKeyEvent`; long insertion still needs live acceptance.

## Application and acceptance

1. Review changes. New source files must be visible to Git before a Git-backed
   flake build; add only this task's intended files, without disturbing existing
   staging. Optional user build:
   `nix build .#homeConfigurations.samov-laptop.activationPackage`.
2. Quit the manually launched Handy through its tray menu. On later updates,
   stop `handy.service` first if resetting settings. A second single-instance
   launch cannot change the original process's environment/settings.
3. **Optional, one-time adoption of the initial settings:** preserve the existing
   native store before applying HM. This intentionally resets GUI preferences
   to the declared initial values, not history/audio. If you prefer to keep the
   current store, skip this step and align the relevant GUI values manually.

   ```fish
   set handy_data "$HOME/.local/share/com.pais.handy"
   set handy_backup "$handy_data/settings_store.before-hm-"(date +%Y%m%d-%H%M%S)".json"
   mv --no-clobber -- "$handy_data/settings_store.json" "$handy_backup"
   ```

   Keep the private backup for recovery; do not commit it. If the move fails,
   stop and investigate, not delete or force the file.
4. Apply `home-manager switch --flake .#samov-laptop`, then `hyprctl reload` and
   `hyprctl configerrors`. Expect no errors; the reload also removes old live-only
   trial bindings. No NixOS rebuild, reboot or WirePlumber restart is needed.
5. Run `systemctl --user start handy.service` and
   `systemctl --user is-active handy.service`. Expect `active`, no settings window,
   one Handy instance and a tray icon. Keep app "Launch on Startup" off.
6. Check the GUI model/Q4, Intel acceleration, Direct/wtype and microphone options.
   If initial settings were adopted, expect matching hotkey labels and audio cues;
   otherwise existing GUI preferences are intentionally unchanged.
7. In disposable Neovim Insert and OpenCode input fields, test start/stop, first
   words, native cancellation during recording and recognition, and complete long
   RU/EN insertion without extra Enter or a help popup. Test actual Fn+F1 help
   separately; Ctrl+Space should retain Neovim selection/completion behavior.
8. Check no ongoing microphone capture after stop/cancel and normal headphone
   routing. After logout/login, expect automatic hidden startup and working keys
   without a terminal. Cold-model startup after 5 minutes is a separate check.

The agent does not build, activate, start the service, dictate or inject test
text. Packaging/service behavior, the wtype device rule, ready cues, cancellation
and idle resource use need live acceptance; declaration/fixture checks alone do
not establish those properties.

## Checks and recovery

Small checks, without builds, audio capture or service changes:

```fish
set handy_checks (mktemp -d /tmp/opencode/handy-checks-XXXXXXXX)
nix eval --offline --impure --json --option allow-import-from-derivation false --file home/linux/laptop/handy/tests/test-declarations.nix > "$handy_checks/declarations.json"
python3 -B home/linux/laptop/handy/tests/test_seed.py "$handy_checks/declarations.json"
nix eval --offline --impure --json --option allow-import-from-derivation false --file home/modules/voice-dictate/tests/test-declarations.nix
```

The seed fixture executes the actual evaluated activation snippet in disposable
directories, including paths with spaces, existing GUI data, symlinks, repeated
activation and dry-run. It does not launch Handy or validate Tauri migrations.

To temporarily stop dictation, `systemctl --user stop handy.service`; it starts
again at the next graphical session. HM generation rollback restores declarative
packages/units/bindings, **not** mutable Handy settings/history. Quit Handy before
restoring a settings backup. To deliberately restore Lenovo Whisper in source,
replace the `./handy` import with `./archive/whisper.nix`, restore
Super+Shift+R → `voice-dictate` and remove Handy's cancel binding; review and apply
HM. Do not import both into the active dictation path. Other hosts are unchanged.
