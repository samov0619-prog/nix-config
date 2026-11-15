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
  vulkanEnv = lib.optionalString (
    config.voiceDictate.vulkan.enable && config.voiceDictate.vulkan.driverFile != null
  ) "VK_DRIVER_FILES=${lib.escapeShellArg config.voiceDictate.vulkan.driverFile} ";
  notificationClose = pkgs.callPackage ../../linux/modules/notifications/package.nix { };
  inputReady = pkgs.writeShellScriptBin "voice-input-ready" ''
    exec ${pkgs.python3}/bin/python3 ${./input-ready.py} "$@"
  '';

  voiceDictateLinux = pkgs.writeShellApplication {
    name = "voice-dictate";
    runtimeInputs =
      (with pkgs; [
        coreutils
        gnused
        libnotify
        pipewire
        whisperCpp
        wl-clipboard
        wtype
        util-linux
        notificationClose
      ])
      ++ lib.optional config.voiceDictate.fastLocalInput inputReady;
    text = ''
      set -eu
      umask 077

      state_dir="''${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is required}/voice-dictate"
      audio="$state_dir/recording.wav"
      pid_file="$state_dir/recording.pid"
      fast_local_input=${lib.boolToString config.voiceDictate.fastLocalInput}
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

      transcription_notification() {
        notice_pid=
        stop_notice=false
        # Do not exit from the trap: TERM can arrive before PID assignment.
        trap 'stop_notice=true; if [ -n "$notice_pid" ]; then kill -TERM "$notice_pid" 2>/dev/null || true; fi' TERM
        notify-send --app-name="Voice dictate" \
          --category="voice-dictate.transcribing.$transcription_owner" --expire-time=0 \
          --action=default=Cancel "Voice dictate" \
          "Transcribing… Left-click to cancel" > "$action_file" &
        notice_pid=$!
        if "$stop_notice"; then
          kill -TERM "$notice_pid" 2>/dev/null || true
        fi
        notice_status=0
        wait "$notice_pid" || notice_status=$?
        if "$stop_notice"; then
          wait "$notice_pid" || true
          return 0
        fi
        if [ "$notice_status" -eq 0 ] && [ "$(cat "$action_file")" = default ]; then
          kill -USR1 "$transcription_owner" 2>/dev/null || true
        fi
      }

      cancel_recording() {
        # Race the second hotkey under the same lock. Once that hotkey has
        # claimed the audio, this old notice must not cancel recognition.
        flock 9
        if [ -f "$pid_file" ] && [ "$(cat "$pid_file")" = "$recording_pid" ]; then
          recording_cancelled=true
          rm -f "$pid_file"
          kill -INT "$recording_pid" 2>/dev/null || true
          wait "$recording_pid" || true
          rm -f "$audio"
        fi
        flock -u 9
      }

      recording_action() {
        if IFS= read -r action <&8 && [ "$action" = default ]; then
          kill -USR1 "$recording_owner" 2>/dev/null || true
        fi
      }

      stop_recording_notification() {
        if [ -n "''${recording_action_pid-}" ]; then
          kill -TERM "$recording_action_pid" 2>/dev/null || true
          wait "$recording_action_pid" || true
        fi
        kill -TERM "$recording_notice_pid" 2>/dev/null || true
        wait "$recording_notice_pid" || true
        exec 8<&-
        close_recording_notification
      }

      record_microphone() {
        # This worker waits for its own recorder; no new timer or polling service.
        record_args=()
        local_input=false
        if "$fast_local_input"; then
          if source_serial="$(voice-input-ready source)"; then
            # Pin the classified source for this capture. Do not classify one
            # default and then let a remembered stream target choose Bluetooth.
            record_args=(--target "$source_serial" --properties='{"node.dont-fallback":true,"node.dont-reconnect":true}')
            local_input=true
          fi
        fi
        pw-record "''${record_args[@]}" --rate 16000 --channels 1 "$audio" 9>&- >/dev/null 2>&1 &
        recording_pid=$!
        printf '%s\n' "$recording_pid" > "$pid_file"
        # Publish the PID before another hotkey can inspect state. Reopen a
        # separate lock description for this worker's later lifecycle changes.
        flock -u 9
        exec 9>&-
        exec 9>"$state_dir/toggle.lock"
        input_ready=true
        if "$local_input"; then
          voice-input-ready wait "$audio" "$recording_pid" || input_ready=false
        else
          # Preserve the existing HFP allowance for Bluetooth/unknown inputs
          # and hosts that have not accepted the local-input readiness path.
          sleep 2
        fi
        flock 9
        if [ ! -f "$pid_file" ] || [ "$(cat "$pid_file")" != "$recording_pid" ]; then
          flock -u 9
          wait "$recording_pid" || true
          return
        fi
        if ! "$input_ready" || ! kill -0 "$recording_pid" 2>/dev/null; then
          kill -INT "$recording_pid" 2>/dev/null || true
          wait "$recording_pid" || true
          rm -f "$pid_file" "$audio"
          notify-send "Voice dictate" "Could not start the microphone" -u critical --expire-time=15000
          return 1
        fi
        recording_owner=$BASHPID
        recording_cancelled=false
        trap cancel_recording USR1
        # Native --print-id flushes before waiting for an action. Read that
        # acknowledgement while locked so a hotkey cannot close an unpublished
        # notice; the second line is the selected action, not a stored ID.
        exec 8< <(exec notify-send --print-id --action=default=Cancel --app-name="Voice dictate" \
          --category="voice-dictate.recording.$recording_pid" --expire-time=0 \
          "Voice dictate" 'Recording: speak now.\nSuper+Shift+R — stop and transcribe\nLeft-click — cancel recording' 9>&-)
        recording_notice_pid=$!
        if ! IFS= read -r recording_notice_id <&8 || ! [[ "$recording_notice_id" =~ ^[1-9][0-9]*$ ]]; then
          trap "" USR1
          kill -INT "$recording_pid" 2>/dev/null || true
          wait "$recording_pid" || true
          stop_recording_notification
          rm -f "$pid_file" "$audio"
          return 1
        fi
        flock -u 9
        recording_action 9>&- &
        recording_action_pid=$!
        wait "$recording_pid" || true
        trap "" USR1
        # A cancellation trap may have interrupted the outer wait.
        wait "$recording_pid" || true
        stop_recording_notification
        # A normal second hotkey removes this marker before stopping the child.
        # Only an unexpected exit owns cleanup/error reporting here. PID-scoped
        # categories cannot dismiss a later recording's notification.
        flock 9
        if "$recording_cancelled"; then
          notify-send "Voice dictate" "Recording cancelled" --expire-time=3000
          return 0
        fi
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

        transcription_owner=$$
        transcript_file="$state_dir/transcript.txt"
        action_file="$state_dir/transcription-action"
        cancelled=false
        ${vulkanEnv}whisper-cli -m ${whisperSmallQ51} -f "$audio" -l ru${gpuFlag} -nt -np > "$transcript_file" 9>&- &
        transcription_pid=$!
        # A native default action works with Mako's normal left-click binding.
        # Signal this invocation, never a PID read from a previous session.
        trap 'cancelled=true; kill -TERM "$transcription_pid" 2>/dev/null || true' USR1
        transcription_notification 9>&- &
        action_worker=$!
        transcription_status=0
        wait "$transcription_pid" || transcription_status=$?
        # Acceptance ends when recognition completes. Ignore a racing late click
        # while reaping the action worker and its notify-send child.
        trap "" USR1
        if "$cancelled"; then
          wait "$transcription_pid" || true
        fi
        kill -TERM "$action_worker" 2>/dev/null || true
        wait "$action_worker" || true
        notification-close --app-name="Voice dictate" \
          --category="voice-dictate.transcribing.$transcription_owner" || true
        rm -f "$audio" "$action_file"
        trap - USR1

        if "$cancelled"; then
          rm -f "$transcript_file"
          notify-send "Voice dictate" "Transcription cancelled" --expire-time=3000
          exit 0
        fi
        if [ "$transcription_status" -ne 0 ]; then
          rm -f "$transcript_file"
          notify-send "Voice dictate" "Transcription failed" -u critical --expire-time=15000
          exit 1
        fi
        text="$(tr '\n' ' ' < "$transcript_file" | sed 's/[[:space:]]\+/ /g; s/^ //; s/ $//')"
        rm -f "$transcript_file"

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
        # Recover this single session's files after an interrupted invocation;
        # recordings are never archived or numbered.
        rm -f "$pid_file" "$audio" "$state_dir/transcript.txt" "$state_dir/transcription-action"
        # PipeWire chooses the current default input, including USB and Bluetooth interfaces.
        record_microphone >/dev/null 2>&1 &
      fi
    '';
  };

in
{
  options.voiceDictate.fastLocalInput = lib.mkEnableOption "sample-ready startup for the current local ALSA input instead of the Bluetooth allowance";
  options.voiceDictate.vulkan = {
    enable = lib.mkEnableOption "Vulkan acceleration for whisper.cpp";
    device = lib.mkOption {
      type = lib.types.int;
      default = 0;
      description = "Vulkan device index used by whisper.cpp.";
    };
    driverFile = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Absolute Vulkan ICD manifest path exposed only to Whisper; null keeps normal driver discovery.";
    };
  };

  # Future macOS port: use AVFoundation through ffmpeg and pbcopy. Keep paste
  # manual until the terminal is explicitly granted Accessibility permission.
  config.home.packages = lib.optionals pkgs.stdenv.hostPlatform.isLinux [ voiceDictateLinux ];
}
