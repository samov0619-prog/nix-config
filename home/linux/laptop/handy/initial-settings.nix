# Handy v0.9.8 AppSettings, wrapped in Tauri's native store envelope.
# Initial preferences only; subsequent GUI edits/migrations remain writable.
{
  settings = {
    settings_schema_version = 2;
    selected_model = "handy-computer/parakeet-tdt-0.6b-v3-gguf/parakeet-tdt-0.6b-v3-Q4_K_M.gguf";
    onboarding_completed = true;
    selected_language = "auto";
    translate_to_english = false;
    transcribe_accelerator = "gpu";
    transcribe_gpu_device = ''["vulkan","id","0000:00:02.0"]'';
    experimental_enabled = true;

    # Wayland hotkeys belong to Hyprland, not Tauri/raw-input listeners.
    # Keep the GUI labels aligned with the compositor bindings. Empty bindings
    # are invalid in this version; omitting them restores the upstream defaults.
    keyboard_implementation = "tauri";
    shortcut_activation = "toggle";
    bindings = {
      transcribe = {
        id = "transcribe";
        name = "Transcribe";
        description = "Converts your speech into text.";
        default_binding = "ctrl+space";
        current_binding = "super+shift+r";
      };
      cancel = {
        id = "cancel";
        name = "Cancel";
        description = "Cancels the current recording.";
        default_binding = "escape";
        current_binding = "super+shift+t";
      };
      # Not registered while post-processing is off; no Hyprland bind for it.
      transcribe_with_post_process = {
        id = "transcribe_with_post_process";
        name = "Transcribe with Post-Processing";
        description = "Converts your speech into text and applies AI post-processing.";
        default_binding = "ctrl+shift+space";
        current_binding = "ctrl+shift+space";
      };
    };

    start_hidden = true;
    autostart_enabled = false;
    show_tray_icon = true;
    update_checks_enabled = false;
    show_whats_new_on_update = false;
    model_unload_timeout = "min5";
    always_on_microphone = false;
    lazy_stream_close = false;
    selected_microphone = null;
    selected_channel = null;
    clamshell_microphone = null;
    selected_output_device = null;
    mute_while_recording = false;
    # Upstream's ready/stop cues avoid relying on terminal debug output.
    audio_feedback = true;
    audio_feedback_volume = 0.5;
    sound_theme = "marimba";
    # The user disabled Minimal after unstable visibility on window/focus changes.
    overlay_style = "none";
    overlay_position = "bottom";

    paste_method = "direct";
    typing_tool = "wtype";
    clipboard_handling = "dont_modify";
    auto_submit = false;
    append_trailing_space = false;
    external_script_path = null;
    post_process_enabled = false;
    vad_enabled = true;
    vad_backend = "silero";
    filler_word_removal_enabled = true;
    custom_words = [ ];
    chinese_script = "as_transcribed";
    history_limit = 5;
    recording_retention_period = "preserve_limit";
  };
}
