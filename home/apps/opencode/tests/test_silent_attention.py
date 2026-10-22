import runpy
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class SilentAttentionTest(unittest.TestCase):
    def setUp(self):
        self.request_attention = Mock()
        handler = ModuleType("kittens.tui.handler")
        handler.result_handler = lambda **kwargs: lambda function: function
        kitty = ModuleType("kitty.fast_data_types")
        kitty.request_attention = self.request_attention
        with patch.dict("sys.modules", {"kittens.tui.handler": handler, "kitty.fast_data_types": kitty}):
            self.handle = runpy.run_path(str(Path(__file__).parents[1] / "silent-attention.py"))["handle_result"]

    def test_inactive_window_marks_tab_without_invoking_bell_hooks(self):
        tab = SimpleNamespace(relayout_borders=Mock(), mark_tab_bar_dirty=Mock())
        window = SimpleNamespace(is_active=False, needs_attention=False, os_window_id=7,
                                 tabref=lambda: tab, on_bell=Mock(side_effect=AssertionError("bell hook")))
        self.handle([], None, 42, SimpleNamespace(window_id_map={42: window}))
        self.assertTrue(window.needs_attention)
        tab.relayout_borders.assert_called_once()
        tab.mark_tab_bar_dirty.assert_called_once()
        window.on_bell.assert_not_called()
        self.request_attention.assert_called_once_with(7)

    def test_active_tab_still_requests_workspace_attention(self):
        window = SimpleNamespace(is_active=True, os_window_id=7)
        self.handle([], None, 42, SimpleNamespace(window_id_map={42: window}))
        self.request_attention.assert_called_once_with(7)

    def test_deleted_window_is_ignored(self):
        self.handle([], None, 42, SimpleNamespace(window_id_map={}))
        self.request_attention.assert_not_called()


if __name__ == "__main__":
    unittest.main()
