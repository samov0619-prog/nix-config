"""Lenovo presentation contracts; optional native GTK CSS parsing, no display/audio."""

import ctypes
import importlib.util
import json
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
LINUX = ROOT.parents[1]


def config():
    text = (LINUX / "laptop/waybar-config.jsonc").read_text()
    return json.loads(re.sub(r",\s*([}\]])", r"\1", re.sub(r"//[^\n]*", "", text)))


def theme(mode):
    shared = LINUX / "modules/waybar"
    return (
        (shared / f"style-{mode}.css").read_text().replace(
            '@import url("./style.css");', (shared / "style.css").read_text()
        )
        + (ROOT / f"palette-{mode}.css").read_text()
        + (ROOT / "appearance.css").read_text()
    )


class AppearanceTests(unittest.TestCase):
    def test_network_uses_text_arrows_and_retains_bandwidth_fields(self):
        network = config()["network"]
        for key in ("format-wifi", "format-ethernet"):
            text = network[key]
            self.assertEqual(text, "↓ {bandwidthDownBytes}  ↑ {bandwidthUpBytes}")
            self.assertNotIn(":>", text)
            self.assertNotIn("\ufe0f", text)
            self.assertNotIn("⬇", text)
        self.assertEqual(network["interval"], 5)

    def test_ppd_profiles_color_foregrounds_only(self):
        css = (ROOT / "appearance.css").read_text()
        for profile in ("power-saver", "balanced", "performance"):
            body = re.search(r"#power-profiles-daemon\." + profile + r"\s*\{([^}]+)\}", css)[1]
            self.assertEqual(body.strip(), f"color: @lenovo_{profile.replace('-', '_')};")
        for mode in ("dark", "light"):
            palette = (ROOT / f"palette-{mode}.css").read_text()
            self.assertEqual(len(re.findall(r"@define-color lenovo_\w+ #[0-9a-f]{6};", palette)), 7)
        ppd = config()["power-profiles-daemon"]
        self.assertEqual(ppd["format"], "{icon}")
        self.assertEqual(ppd["format-icons"]["balanced"], "")

    def test_audio_groups_use_spacing_without_separator_or_whole_label_mono(self):
        audio = config()["pulseaudio"]
        for key in ("format", "format-muted", "format-bluetooth", "format-bluetooth-muted"):
            self.assertIn("   {format_source}", audio[key])
            self.assertNotIn("·", audio[key])
            self.assertNotIn(":3", audio[key])
        self.assertIn("{volume}%", audio["format"])
        self.assertIn("</span> {volume}%", audio["format-source"])
        self.assertIn("</span> off", audio["format-source-muted"])
        self.assertEqual(audio["on-click"], "pwvucontrol")
        self.assertNotIn("font-family:", (ROOT / "appearance.css").read_text())

    def test_common_right_side_spacing_and_existing_module_order(self):
        css = (ROOT / "appearance.css").read_text()
        self.assertIn("padding: 0 6px;", css)
        for identifier in ("power-profiles-daemon", "battery", "pulseaudio", "language", "clock"):
            self.assertIn(f".modules-right #{identifier}", css)
        self.assertEqual(config()["modules-right"], [
            "power-profiles-daemon", "battery", "pulseaudio", "hyprland/language", "clock",
        ])
        for identifier in ("custom-startup", "cpu", "memory", "custom-disk", "custom-gpu-manual", "network", "custom-nix-updates"):
            self.assertIn(f".modules-center #{identifier}", css)

    def test_hardware_icons_and_tooltip_only_swap_and_capacity(self):
        bar = config()
        for key, icon in (("cpu", ""), ("memory", ""), ("custom/disk", "")):
            self.assertIn(icon, bar[key]["format"])
            family = "Propo" if key == "cpu" else "Mono"
            self.assertIn(f"font_family='NotoSansM Nerd Font {family}'", bar[key]["format"])
            self.assertNotIn("min-length", bar[key])
            self.assertNotIn("max-length", bar[key])
        self.assertIn("{percentage}%", bar["memory"]["format"])
        self.assertNotIn("swap", bar["memory"]["format"].lower())
        self.assertIn("{swapUsed:.1f}", bar["memory"]["tooltip-format"])
        self.assertIn("{total:.1f}", bar["memory"]["tooltip-format"])
        self.assertIn("356H", bar["cpu"]["tooltip-format"])
        self.assertTrue(bar["custom/disk"]["exec"].endswith(" --compact"))
        for key in ("format-source", "format-source-muted"):
            self.assertIn("NotoSansM Nerd Font Propo", bar["pulseaudio"][key])
        for icon in bar["pulseaudio"]["format-icons"]["default"]:
            self.assertIn("NotoSansM Nerd Font Propo", icon)

    def test_network_inherits_and_startup_colors_are_muted(self):
        css = (ROOT / "appearance.css").read_text()
        self.assertRegex(css, r"#network\s*\{\s*color: inherit;")
        self.assertRegex(css, r"#custom-gpu-manual\.active\s*\{\s*box-shadow: none;")
        for state in ("grey", "green", "yellow", "red"):
            self.assertIn(f"color: @lenovo_startup_{state};", css)
        for mode in ("dark", "light"):
            self.assertNotIn("lenovo_network", theme(mode))

    def test_generated_themes_have_no_relative_import_dependency(self):
        for mode in ("dark", "light"):
            css = theme(mode)
            self.assertNotIn("@import", css)
            self.assertIn("#custom-gpu-manual:hover", css)
            self.assertIn("#battery.critical:not(.charging)", css)
            self.assertIn("@define-color lenovo_startup_yellow", css)

    @unittest.skipUnless(os.environ.get("WAYBAR_TEST_GTK3"), "Set WAYBAR_TEST_GTK3 to installed libgtk-3.so")
    def test_native_icon_ink_is_larger_than_old_mono_glyphs(self):
        gtk = ctypes.CDLL(os.environ["WAYBAR_TEST_GTK3"])
        gtk.pango_cairo_font_map_get_default.restype = ctypes.c_void_p
        gtk.pango_font_map_create_context.argtypes = [ctypes.c_void_p]
        gtk.pango_font_map_create_context.restype = ctypes.c_void_p
        gtk.pango_layout_new.argtypes = [ctypes.c_void_p]
        gtk.pango_layout_new.restype = ctypes.c_void_p
        gtk.pango_font_description_from_string.argtypes = [ctypes.c_char_p]
        gtk.pango_font_description_from_string.restype = ctypes.c_void_p
        gtk.pango_layout_set_font_description.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        gtk.pango_layout_set_markup.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        gtk.pango_font_description_free.argtypes = [ctypes.c_void_p]
        gtk.g_object_unref.argtypes = [ctypes.c_void_p]

        class Rectangle(ctypes.Structure):
            _fields_ = [(name, ctypes.c_int) for name in ("x", "y", "width", "height")]

        gtk.pango_layout_get_pixel_extents.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(Rectangle), ctypes.POINTER(Rectangle),
        ]
        context = gtk.pango_font_map_create_context(gtk.pango_cairo_font_map_get_default())
        layout = gtk.pango_layout_new(context)
        description = gtk.pango_font_description_from_string(b"DejaVu Sans 9.75")
        gtk.pango_layout_set_font_description(layout, description)

        def extent(markup):
            gtk.pango_layout_set_markup(layout, markup.encode(), -1)
            ink, logical = Rectangle(), Rectangle()
            gtk.pango_layout_get_pixel_extents(layout, ctypes.byref(ink), ctypes.byref(logical))
            return ink.width, ink.height

        try:
            bar = config()
            formats = [bar["cpu"]["format"], bar["pulseaudio"]["format-source"],
                       bar["pulseaudio"]["format-icons"]["default"][1]]
            spec = importlib.util.spec_from_file_location("ink_gpu", ROOT / "gpu-status.py")
            gpu = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gpu)
            formats.append(gpu.render(None, None)["text"])
            for markup in formats:
                icon = re.search(r"<span[^>]+>([^<]+)</span>", markup)[1]
                old = f"<span font_family='NotoSansM Nerd Font Mono' size='larger'>{icon}</span>"
                new = re.search(r"<span[^>]+>[^<]+</span>", markup)[0]
                with self.subTest(icon=icon):
                    old_width, old_height = extent(old)
                    new_width, new_height = extent(new)
                    self.assertGreater(new_width, old_width)
                    self.assertGreater(new_height, old_height)
        finally:
            gtk.pango_font_description_free(description)
            gtk.g_object_unref(layout)
            gtk.g_object_unref(context)

    @unittest.skipUnless(os.environ.get("WAYBAR_TEST_GTK3"), "Set WAYBAR_TEST_GTK3 to installed libgtk-3.so")
    def test_native_pango_parses_icon_and_audio_formats(self):
        gtk = ctypes.CDLL(os.environ["WAYBAR_TEST_GTK3"])
        gtk.pango_parse_markup.argtypes = [
            ctypes.c_char_p, ctypes.c_int, ctypes.c_uint,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        gtk.pango_parse_markup.restype = ctypes.c_int
        bar = config()
        formats = [bar[key]["format"].format("2%", usage=3, percentage=31)
                   for key in ("cpu", "memory", "custom/disk")]
        audio = bar["pulseaudio"]
        for key in ("format", "format-muted", "format-bluetooth", "format-bluetooth-muted"):
            for source in ("format-source", "format-source-muted"):
                formats.append(audio[key].format(
                    icon=audio["format-icons"]["default"][1], volume=35,
                    format_source=audio[source].format(volume=100),
                ))
        spec = importlib.util.spec_from_file_location("appearance_gpu", ROOT / "gpu-status.py")
        gpu = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gpu)
        formats.append(gpu.render(None, None)["text"])
        formats.append(gpu.render({"utilization": 12, "used": 512, "total": 8192,
                                   "time": "12:34:56"}, gpu.clock() + 60)["text"])
        for markup in formats:
            with self.subTest(markup=markup):
                error = ctypes.c_void_p()
                self.assertEqual(gtk.pango_parse_markup(
                    markup.encode(), -1, 0, None, None, None, ctypes.byref(error),
                ), 1)
                self.assertFalse(error.value)

    @unittest.skipUnless(os.environ.get("WAYBAR_TEST_GTK3"), "Set WAYBAR_TEST_GTK3 to installed libgtk-3.so")
    def test_native_gtk_provider_parses_both_effective_themes(self):
        gtk = ctypes.CDLL(os.environ["WAYBAR_TEST_GTK3"])
        gtk.gtk_css_provider_new.restype = ctypes.c_void_p
        gtk.gtk_css_provider_load_from_data.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_ssize_t, ctypes.POINTER(ctypes.c_void_p),
        ]
        gtk.gtk_css_provider_load_from_data.restype = ctypes.c_int
        gtk.g_object_unref.argtypes = [ctypes.c_void_p]
        for mode in ("dark", "light"):
            with self.subTest(mode=mode):
                provider = gtk.gtk_css_provider_new()
                try:
                    error = ctypes.c_void_p()
                    css = theme(mode).encode()
                    self.assertEqual(gtk.gtk_css_provider_load_from_data(provider, css, len(css), ctypes.byref(error)), 1)
                    self.assertFalse(error.value)
                finally:
                    gtk.g_object_unref(provider)


if __name__ == "__main__":
    unittest.main()
