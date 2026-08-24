{ config, pkgs, lib, ... }:
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
    ];
    text = ''
      set -eu

      state_dir="''${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is required}/voice-dictate"
      audio="$state_dir/recording.wav"
      pid_file="$state_dir/recording.pid"
      mkdir -p "$state_dir"

      if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        kill -INT "$(cat "$pid_file")"
        while kill -0 "$(cat "$pid_file")" 2>/dev/null; do sleep 0.1; done
        rm -f "$pid_file"

        if [ ! -s "$audio" ]; then
          notify-send "Voice dictate" "No audio was recorded" -u critical
          exit 1
        fi

        text="$(whisper-cli -m ${whisperSmallQ51} -f "$audio" -l ru${gpuFlag} -nt -np | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g; s/^ //; s/ $//')"
        rm -f "$audio"

        if [ -z "$text" ]; then
          notify-send "Voice dictate" "No speech recognized" -u critical
          exit 1
        fi

        printf '%s' "$text" | wl-copy
        wtype "$text"
        notify-send "Voice dictate" "Transcribed and copied to clipboard"
      else
        rm -f "$pid_file" "$audio"
        # PipeWire chooses the current default input, including USB and Bluetooth interfaces.
        pw-record --rate 16000 --channels 1 "$audio" >/dev/null 2>&1 &
        printf '%s\n' "$!" > "$pid_file"
        # Bluetooth HFP sources need time to switch profiles and link to PipeWire.
        # Do not invite speech until the recorder has had time to receive samples.
        sleep 2
        if ! kill -0 "$(cat "$pid_file")" 2>/dev/null; then
          rm -f "$pid_file" "$audio"
          notify-send "Voice dictate" "Could not start the microphone" -u critical
          exit 1
        fi
        notify-send "Voice dictate" "Recording: speak now; press Super+Shift+R again to transcribe"
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
