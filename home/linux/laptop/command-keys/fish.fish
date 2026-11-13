# These execute only in Fish's prompt editor, never in foreground programs.
function __lenovo_command_cut
    if test -n (commandline --current-selection | string collect)
        fish_clipboard_copy
        commandline -f kill-selection
    end
end
for mode in default insert
    bind -M $mode super-c fish_clipboard_copy
    bind -M $mode super-v fish_clipboard_paste
    bind -M $mode super-x __lenovo_command_cut
    bind -M $mode super-a beginning-of-buffer begin-selection end-of-buffer
    bind -M $mode super-z undo
    bind -M $mode super-shift-z redo
end
