"""Small actual-action fixtures; no keyboard grab, renderer or live clipboard."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).parent
handler = types.ModuleType("kittens.tui.handler")
handler.result_handler = lambda **kw: lambda fn: fn
clipboard = types.ModuleType("kitty.clipboard")
clipboard.get_clipboard_string = lambda: "fixture"
sys.modules["kittens.tui.handler"] = handler
sys.modules["kitty.clipboard"] = clipboard
spec = importlib.util.spec_from_file_location("command_keys", ROOT / "kitty_keys.py")
keys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keys)


def window(name, selection=False):
    w = Mock()
    w.child.foreground_processes = [{"cmdline": ["/nix/store/fixture/bin/" + name]}]
    w.screen.has_selection.return_value = selection
    w.send_paste_event.return_value = False
    return w


class Routing(unittest.TestCase):
    def test_editors_keep_all_native_keys_even_with_terminal_selection(self):
        for app in ("nvim", "yazi"):
            for key in ("c", "v", "x", "a", "z", "shift+z"):
                with self.subTest(app=app, key=key):
                    w = window(app, True)
                    keys.dispatch(w, key)
                    w.send_key.assert_called_once_with("super+" + key)
                    w.copy_to_clipboard.assert_not_called()

    def test_fish_native_prompt_keys(self):
        for key in ("c", "v", "x", "a", "z", "shift+z"):
            w = window("fish")
            keys.dispatch(w, key)
            w.send_key.assert_called_once_with("super+" + key)

    def test_terminal_copy_does_not_interrupt(self):
        for selected in (True, False):
            w = window("ssh", selected)
            keys.dispatch(w, "c")
            w.copy_to_clipboard.assert_called_once()
            w.send_key.assert_not_called()

    def test_unknown_program_native_paste_and_no_control_z(self):
        w = window("ssh")
        keys.dispatch(w, "v")
        w.paste_with_actions.assert_called_once_with("fixture")
        for key in ("z", "shift+z", "x", "a"):
            keys.dispatch(w, key)
        self.assertNotIn(unittest.mock.call("ctrl+z"), w.send_key.call_args_list)

    def test_opencode_native_undo_select_and_paste(self):
        w = window("opencode")
        for key in ("z", "shift+z", "a", "v"):
            keys.dispatch(w, key)
        self.assertEqual(w.send_key.call_args_list, [
            unittest.mock.call("super+z"), unittest.mock.call("super+shift+z"),
            unittest.mock.call("super+a"), unittest.mock.call("ctrl+v"),
        ])

    def test_exited_target_is_ignored(self):
        keys.handle_result(["command_keys.py", "c"], None, 123, types.SimpleNamespace(window_id_map={}))

    def test_empty_foreground_is_not_treated_as_editor(self):
        w = window("unused")
        w.child.foreground_processes = [{"cmdline": []}]
        keys.dispatch(w, "c")
        w.copy_to_clipboard.assert_called_once()


if __name__ == "__main__":
    unittest.main()
