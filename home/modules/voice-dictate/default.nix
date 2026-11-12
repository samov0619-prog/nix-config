{
  config,
  pkgs,
  lib,
  ...
}:
let
  # Fixed upstream artifact: Whisper Small Q5_1 is multilingual and keeps
  # Russian dictation compact enough for responsive CPU transcription.
  whisperSmallQ51 = pkgs.fetchurl {
    url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q5_1.bin";
    hash = "sha256-roXkqTXXpWe9EC/lWvwWu1lb22GOEbL8dZG8CBIEEbs=";
  };

  whisperCpp =
    if config.voiceDictate.vulkan.enable then
      pkgs.whisper-cpp.override {
        vulkanSupport = true;
        withSDL = false;
      }
    else
      pkgs.whisper-cpp;

  gpuFlag = lib.optionalString config.voiceDictate.vulkan.enable " -dev ${toString config.voiceDictate.vulkan.device}";
  notificationClose = pkgs.callPackage ../../linux/modules/notifications/package.nix { };

  voiceDictateLinux = pkgs.writeShellApplication {
    name = "voice-dictate";
    runtimeInputs = with pkgs; [
      coreutils
      gnused
      libnotify
      pipewire
      whisperCpp
      wl-clipboard
      wtype
      util-linux
      notificationClose
    ];
    text = ''
      set -eu

      state_dir="''${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is required}/voice-dictate"
      audio="$state_dir/recording.wav"
      pid_file="$state_dir/recording.pid"
      mkdir -p "$state_dir"
      # Serialize hotkeys, including startup publication and transcription.
      exec 9>"$state_dir/toggle.lock"
      flock 9

      close_recording_notification() {
        if [ -n "''${recording_pid-}" ]; then
          notification-close --app-name="Voice dictate" \
            --category="voice-dictate.recording.$recording_pid" || true
        fi
      }

      record_microphone() {
        # This worker waits for its own recorder; no new timer or polling service.
        pw-record --rate 16000 --channels 1 "$audio" 9>&- >/dev/null 2>&1 &
        recording_pid=$!
        printf '%s\n' "$recording_pid" > "$pid_file"
        # Publish the PID before another hotkey can inspect state. Reopen a
        # separate lock description for this worker's later lifecycle changes.
        flock -u 9
        exec 9>&-
        exec 9>"$state_dir/toggle.lock"
        # Preserve the existing Bluetooth HFP startup allowance.
        sleep 2
        flock 9
        if [ ! -f "$pid_file" ] || [ "$(cat "$pid_file")" != "$recording_pid" ]; then
          flock -u 9
          wait "$recording_pid" || true
          return
        fi
        if ! kill -0 "$recording_pid" 2>/dev/null; then
          wait "$recording_pid" || true
          rm -f "$pid_file" "$audio"
          notify-send "Voice dictate" "Could not start the microphone" -u critical --expire-time=15000
          return 1
        fi
        if ! notify-send --app-name="Voice dictate" \
          --category="voice-dictate.recording.$recording_pid" --expire-time=0 \
          "Voice dictate" "Recording: speak now; press Super+Shift+R again to transcribe"; then
          kill -INT "$recording_pid" 2>/dev/null || true
          wait "$recording_pid" || true
          close_recording_notification
          rm -f "$pid_file" "$audio"
          return 1
        fi
        flock -u 9
        wait "$recording_pid" || true
        close_recording_notification
        # A normal second hotkey removes this marker before stopping the child.
        # Only an unexpected exit owns cleanup/error reporting here. PID-scoped
        # categories cannot dismiss a later recording's notification.
        flock 9
        if [ -f "$pid_file" ] && [ "$(cat "$pid_file")" = "$recording_pid" ]; then
          rm -f "$pid_file" "$audio"
          notify-send "Voice dictate" "Microphone stopped unexpectedly" -u critical --expire-time=15000
          return 1
        fi
      }

      if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        recording_pid="$(cat "$pid_file")"
        close_recording_notification
        rm -f "$pid_file"
        kill -INT "$recording_pid" 2>/dev/null || true
        while kill -0 "$recording_pid" 2>/dev/null; do sleep 0.1; done

        if [ ! -s "$audio" ]; then
          rm -f "$audio"
          notify-send "Voice dictate" "No audio was recorded" -u critical --expire-time=15000
          exit 1
        fi

        if ! text="$(whisper-cli -m ${whisperSmallQ51} -f "$audio" -l ru${gpuFlag} -nt -np | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g; s/^ //; s/ $//')"; then
          rm -f "$audio"
          notify-send "Voice dictate" "Transcription failed" -u critical --expire-time=15000
          exit 1
        fi
        rm -f "$audio"

        if [ -z "$text" ]; then
          notify-send "Voice dictate" "No speech recognized" -u critical --expire-time=15000
          exit 1
        fi

        # Clipboard ownership can outlive this invocation; do not leak the lock.
        printf '%s' "$text" | wl-copy 9>&-
        printf '%s' "$text" | wtype - 9>&-
        notify-send "Voice dictate" "Transcribed and copied to clipboard" --expire-time=3000
      else
        if [ -f "$pid_file" ]; then
          recording_pid="$(cat "$pid_file")"
          close_recording_notification
        fi
        rm -f "$pid_file" "$audio"
        # PipeWire chooses the current default input, including USB and Bluetooth interfaces.
        record_microphone >/dev/null 2>&1 &
      fi
    '';
  };

in
{
  options.voiceDictate.vulkan = {
    enable = lib.mkEnableOption "Vulkan acceleration for whisper.cpp";
    device = lib.mkOption {
      type = lib.types.int;
      default = 0;
      description = "Vulkan device index used by whisper.cpp.";
    };
  };

  # Future macOS port: use AVFoundation through ffmpeg and pbcopy. Keep paste
  # manual until the terminal is explicitly granted Accessibility permission.
  config.home.packages = lib.optionals pkgs.stdenv.hostPlatform.isLinux [ voiceDictateLinux ];
}
