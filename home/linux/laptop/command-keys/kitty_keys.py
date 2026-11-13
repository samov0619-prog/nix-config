"""In-process Kitty action: native TUI keys, no daemon or title heuristics."""

from pathlib import PurePath

from kittens.tui.handler import result_handler


def main(args):
    pass


def dispatch(window, key):
    names = {
        PurePath(p["cmdline"][0]).name
        for p in window.child.foreground_processes
        if p.get("cmdline")
    }
    editor = bool(names & {"nvim", "yazi"})
    fish = "fish" in names
    opencode = any(n.startswith("opencode") for n in names)
    if key == "c" and not editor and window.screen.has_selection():
        window.copy_to_clipboard()
    elif key == "v" and not editor and not fish:
        if opencode:
            window.send_key("ctrl+v")  # Native prompt paste, including attachments.
        else:
            from kitty.clipboard import get_clipboard_string

            if not window.send_paste_event():
                text = get_clipboard_string()
                if text:
                    window.paste_with_actions(text)
    elif key == "c" and not (editor or fish or opencode):
        window.copy_to_clipboard()  # Never copy_or_interrupt.
    else:
        window.send_key("super+" + key)  # Never globally turn undo into SIGTSTP.


@result_handler(no_ui=True)
def handle_result(args, answer, target_window_id, boss):
    window = boss.window_id_map.get(target_window_id)
    if window is not None:
        dispatch(window, args[1])
