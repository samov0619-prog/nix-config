"""Run with kitty +runpy 'import runpy; runpy.run_path("home/modules/kitty/tests/test_launch.py", run_name="__main__")'."""

import contextlib
import io
import re
import runpy
import shlex
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from kitty.colors import ThemeColors
from kitty.child import Child
from kitty.config import commented_out_default_config, load_config
from kitty.fast_data_types import GLFW_MOD_SHIFT, GLFW_MOD_SUPER, KeyEvent
from kitty.keys import get_shortcut
from kitty.launch import parse_launch_args
from kitty.options.utils import KeyFallbackType, parse_shortcut, tab_bar_edge


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT.parents[1]


def options(platform):
    source = commented_out_default_config() + "\n"
    if platform == "darwin":
        source = (ROOT / "darwin-prelude.conf").read_text() + "\n" + source
    source += (ROOT / "common.conf").read_text() + "\n"
    suffix = "darwin.conf" if platform == "darwin" else "linux-context.conf"
    source += (ROOT / suffix).read_text() + "\n"
    original_open = open

    def open_source(path, *args, **kwargs):
        if path == "test-source.conf":
            return io.StringIO(source)
        return original_open(path, *args, **kwargs)

    generated = io.StringIO()
    with patch.object(
        sys,
        "argv",
        ["build.py", "test-source.conf", str(ROOT / "kitty-langmap/map.txt")],
    ):
        with patch("builtins.open", open_source):
            with contextlib.redirect_stdout(generated):
                runpy.run_path(str(ROOT / "kitty-langmap/build.py"), run_name="__main__")
    bad = []
    opts = load_config(
        "/dev/null", overrides=generated.getvalue().splitlines(), accumulate_bad_lines=bad
    )
    if bad:
        raise AssertionError(bad)
    return opts


class LaunchBindings(unittest.TestCase):
    def test_user_border_padding_and_title_layout(self):
        for platform in ("linux", "darwin"):
            opts = options(platform)
            with self.subTest(platform=platform):
                self.assertEqual(opts.window_border_width, (1, "px"))
                self.assertFalse(opts.draw_minimal_borders)
                self.assertEqual(tuple(opts.window_margin_width), (0, 0, 0, 0))
                self.assertEqual(tuple(opts.window_padding_width), (4, 4, 4, 4))
                self.assertEqual(opts.placement_strategy, "center")
                self.assertEqual(opts.window_title_bar_min_windows, 2)
                self.assertEqual(opts.window_title_bar_align, "left")
                self.assertEqual(opts.tab_bar_edge, tab_bar_edge("top"))

    def test_user_automatic_theme_colors(self):
        expected = {
            "dark": {
                "background": 0x2C2E34,
                "active_tab_foreground": 0xF5F6F8,
                "active_tab_background": 0x4B6D79,
                "inactive_tab_foreground": 0xC7CBD4,
                "inactive_tab_background": 0x455360,
                "active_border_color": 0x525866,
                "inactive_border_color": 0x2C2E34,
            },
            "light": {
                "background": 0xFFFFFF,
                "active_tab_foreground": 0x23272F,
                "active_tab_background": 0xC7D0DF,
                "inactive_tab_foreground": 0x444444,
                "inactive_tab_background": 0xECEEF2,
                "active_border_color": 0x444444,
                "inactive_border_color": 0xFAFAFA,
            },
        }
        for theme, colors in expected.items():
            with (ROOT / f"{theme}-theme.auto.conf").open() as stream:
                spec, _ = ThemeColors().parse_colors(stream)
            for key, value in colors.items():
                with self.subTest(theme=theme, key=key):
                    self.assertEqual(spec[key], value)

    def test_shared_launch_pairs_and_startup_directories(self):
        for platform in ("linux", "darwin"):
            opts = options(platform)
            for key, command in ((",", ""), ("e", " env EDITOR=nvim yazi"), ("n", " nvim")):
                for modifier, target in (("super", "tab"), ("super+shift", "os-window")):
                    chord = f"{modifier}+{key}"
                    cwd = "~" if target == "tab" else "current"
                    with self.subTest(platform=platform, chord=chord):
                        binding = opts.keyboard_modes[""].keymap[parse_shortcut(chord)][-1]
                        self.assertEqual(
                            binding.definition,
                            f"launch --type={target} --cwd={cwd}{command}",
                        )
                        self.assertEqual(
                            binding.options.allow_fallback,
                            # The public "ascii" option maps to the alternate enum.
                            (KeyFallbackType.shifted, KeyFallbackType.alternate),
                        )

    def test_kitty_child_expands_home_directory(self):
        child = Child(["fish"], cwd="~")
        self.assertEqual(child.cwd, str(Path.home()))

    def test_independent_macos_patch_preserves_native_launch_method(self):
        source = (ROOT / "macos/kitty-keybindings.patch").read_text()
        maps = [line[1:] for line in source.splitlines() if line.startswith("+map ")]
        self.assertEqual(len(maps), 11)
        bad = []
        opts = load_config("/dev/null", overrides=maps, accumulate_bad_lines=bad)
        self.assertEqual(bad, [])
        keymap = opts.keyboard_modes[""].keymap
        expected = {
            "cmd+,": "new_tab",
            "cmd+shift+,": "",
            "cmd+e": "launch --type=tab --cwd=~ --tab-title=yazi fish -l -c yazi",
            "cmd+shift+e": "",
            "cmd+n": "launch --type=tab --cwd=~ --tab-title=nvim fish -l -c nvim",
            "cmd+shift+n": "",
            "cmd+w": "close_tab",
            "cmd+[": "previous_tab",
            "cmd+]": "next_tab",
            "cmd+shift+[": "move_tab_backward",
            "cmd+shift+]": "move_tab_forward",
        }
        for chord, action in expected.items():
            binding = keymap[parse_shortcut(chord)][-1]
            with self.subTest(chord=chord):
                self.assertEqual(binding.definition, action)
                self.assertEqual(
                    binding.options.allow_fallback,
                    (KeyFallbackType.shifted, KeyFallbackType.alternate),
                )
                if action.startswith("launch "):
                    launch_opts, command = parse_launch_args(shlex.split(action)[1:])
                    self.assertEqual(launch_opts.type, "tab")
                    self.assertEqual(launch_opts.cwd, "~")
                    program = "yazi" if chord == "cmd+e" else "nvim"
                    self.assertEqual(command, ["fish", "-l", "-c", program])
                    self.assertEqual(launch_opts.tab_title, program)

    def test_light_text_palette_is_independent_of_title_colors(self):
        with (ROOT / "light-theme.auto.conf").open() as stream:
            spec, _ = ThemeColors().parse_colors(stream)
        self.assertEqual(spec["foreground"], 0x383A42)
        self.assertEqual(spec["background"], 0xFFFFFF)
        base_colors = (
            0x383A42, 0xE45649, 0x40A14F, 0xC18401,
            0x0184BC, 0xA626A4, 0x0997B3, 0xFAFAFA,
        )
        for index, color in enumerate(base_colors * 2):
            with self.subTest(index=index):
                self.assertEqual(spec[f"color{index}"], color)
        for platform in ("linux", "darwin"):
            self.assertEqual(options(platform).dim_opacity, 0.4)

    def test_common_tab_navigation_stays_available(self):
        for platform in ("linux", "darwin"):
            opts = options(platform)
            for chord, action in (
                ("ctrl+tab", "next_tab"),
                ("ctrl+shift+tab", "previous_tab"),
                ("super+]", "next_tab"),
                ("super+[", "previous_tab"),
                ("super+shift+[", "move_tab_backward"),
                ("super+shift+]", "move_tab_forward"),
            ):
                with self.subTest(platform=platform, chord=chord):
                    self.assertEqual(
                        opts.keyboard_modes[""].keymap[parse_shortcut(chord)][-1].definition,
                        action,
                    )

    def test_bracket_tab_controls_in_english_and_russian(self):
        for platform in ("linux", "darwin"):
            keymap = options(platform).keyboard_modes[""].keymap
            for latin, shifted, russian, navigation, movement in (
                ("]", "}", "ъ", "next_tab", "move_tab_forward"),
                ("[", "{", "х", "previous_tab", "move_tab_backward"),
            ):
                for key, shifted_key, alternate in (
                    (latin, shifted, latin),
                    (russian, russian.upper(), latin),
                ):
                    for use_shift, action in ((False, navigation), (True, movement)):
                        event = KeyEvent(
                            key=ord(key), shifted_key=ord(shifted_key) if use_shift else 0,
                            alternate_key=ord(alternate),
                            mods=GLFW_MOD_SUPER | (GLFW_MOD_SHIFT if use_shift else 0),
                        )
                        with self.subTest(platform=platform, key=key, shift=use_shift):
                            self.assertEqual(get_shortcut(keymap, event)[-1].definition, action)

    def test_close_tab_and_russian_key(self):
        for platform in ("linux", "darwin"):
            keymap = options(platform).keyboard_modes[""].keymap
            with self.subTest(platform=platform):
                self.assertEqual(
                    keymap[parse_shortcut("super+w")][-1].definition, "close_tab"
                )
                event = KeyEvent(
                    key=ord("ц"), alternate_key=ord("w"), mods=GLFW_MOD_SUPER
                )
                self.assertEqual(get_shortcut(keymap, event)[-1].definition, "close_tab")

    def test_switcher_remains_a_command_not_a_global_binding(self):
        for host in ("laptop", "laptop-old", "desktop"):
            source = (HOME / "linux" / host / "hyprland.conf").read_text()
            with self.subTest(host=host):
                self.assertNotIn("hypr-semantic-switcher-tofi", source)
                self.assertNotRegex(source, r"(?m)^bind\w*\s*=\s*\$mainMod,\s*(W|Ц|code:25),")
        module = (HOME / "linux/modules/hyprland/default.nix").read_text()
        self.assertIn('name = "hypr-semantic-switcher-tofi";', module)
        self.assertIn("    semanticSwitcherTofi\n", module)

    def test_russian_events_use_ascii_launch_bindings(self):
        for platform in ("linux", "darwin"):
            keymap = options(platform).keyboard_modes[""].keymap
            for latin, russian in ((",", "б"), ("e", "у"), ("n", "т")):
                for shifted in (False, True):
                    modifiers = GLFW_MOD_SUPER | (GLFW_MOD_SHIFT if shifted else 0)
                    event = KeyEvent(
                        key=ord(russian),
                        alternate_key=ord(latin),
                        shifted_key=ord(russian.upper()) if shifted else 0,
                        mods=modifiers,
                    )
                    chord = f"super+{'shift+' if shifted else ''}{latin}"
                    with self.subTest(platform=platform, chord=chord):
                        self.assertEqual(
                            get_shortcut(keymap, event)[-1].definition,
                            keymap[parse_shortcut(chord)][-1].definition,
                        )

    def test_hyprland_only_intercepts_shifted_launches(self):
        for host in ("laptop", "laptop-old", "desktop"):
            source = (HOME / "linux" / host / "hyprland.conf").read_text()
            with self.subTest(host=host):
                bindings = []
                for line in source.splitlines():
                    if re.match(r"^bind\w*\s*=", line):
                        bindings.append(tuple(part.strip() for part in line.split("=", 1)[1].split(",", 3)))
                for key, command in (("code:59", "$terminal"), ("code:26", "$fileManager"), ("code:57", "$terminal -- nvim")):
                    matches = [entry for entry in bindings if entry[:2] == ("$mainMod SHIFT", key)]
                    self.assertEqual(matches, [("$mainMod SHIFT", key, "exec", command)])
                for modifiers, key, *_ in bindings:
                    if modifiers == "$mainMod":
                        self.assertNotIn(key, ("0x2c", "comma", "code:59", "E", "N", "У", "Т", "Й"))
                    if modifiers == "$mainMod SHIFT":
                        self.assertNotIn(key, (
                            "code:60", "code:34", "code:35",
                            "comma", "period", "less", "greater",
                            "bracketleft", "bracketright", "braceleft", "braceright",
                            "Б", "Ю", "Х", "Ъ",
                        ))
                self.assertNotIn("$fileManagerSudo", source)

    def test_help_matches_launches(self):
        source = (HOME / "linux/modules/tofi/module.nix").read_text()
        self.assertIn("In Kitty: Super+, / Super+E / Super+N", source)
        self.assertIn("new shell / Yazi / Neovim tab (home directory)", source)
        self.assertIn("Super+]             next Kitty tab", source)
        self.assertIn("Super+[             previous Kitty tab", source)
        self.assertIn("Super+Shift+[       move current Kitty tab left", source)
        self.assertIn("Super+Shift+]       move current Kitty tab right", source)
        self.assertIn("Super+Shift+,       new Kitty OS window", source)
        for chord in ("Super+Shift+E", "Super+Shift+N"):
            self.assertIn(chord, source)
        self.assertNotIn("sudo Yazi window", source)
        self.assertIn("In Kitty: Super+W  close current tab", source)
        self.assertIn("Terminal command: hypr-semantic-switcher-tofi", source)


if __name__ == "__main__":
    unittest.main(argv=[__file__], verbosity=2)
