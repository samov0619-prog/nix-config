from kittens.tui.handler import result_handler
from kitty.fast_data_types import request_attention


def main(args):
    pass


@result_handler(no_ui=True)
def handle_result(args, answer, target_window_id, boss):
    window = boss.window_id_map.get(target_window_id)
    if window is not None:
        # Preserve Kitty tab and compositor urgency without ringing the audio bell.
        if not window.is_active:
            window.needs_attention = True
            tab = window.tabref()
            if tab is not None:
                tab.relayout_borders()
                tab.mark_tab_bar_dirty()
        request_attention(window.os_window_id)
