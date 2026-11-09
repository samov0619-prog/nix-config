"""Run the installed Kitty's actual patch_colors code before/after the backport.

Native/GUI calls are fixtures enforcing the runtime image-path contract. This is
not a built-package or live terminal test; no display or packages are acquired.
"""

import ast
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parent
INSTALLED = Path(os.environ["KITTY_TEST_COLORS_SOURCE"]) if "KITTY_TEST_COLORS_SOURCE" in os.environ else Path(shutil.which("kitty") or "kitty").resolve().parents[1] / "lib/kitty/kitty/colors.py"


def load_function(text):
    tree = ast.parse(text)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "patch_colors")
    # Execute the real function with isolated native/GUI dependencies below.
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), function], type_ignores=[])
    ast.fix_missing_locations(module)
    return compile(module, "kitty/colors.py", "exec")


class Harness:
    def __init__(self, code):
        self.notifications = []
        self.images = []
        self.refreshes = []
        self.window = SimpleNamespace(
            id=1, screen=SimpleNamespace(color_profile=SimpleNamespace(default_bg=0x2C2E34)),
            refresh=lambda: self.refreshes.append(1),
        )
        self.boss = SimpleNamespace(
            all_windows=[self.window], all_tab_managers=[],
            set_background_image=self.set_image,
            default_bg_changed_for=self.notifications.append,
        )

        def native_colors(spec, transparent, profiles, configured):
            for profile in profiles:
                if "background" in spec:
                    profile.default_bg = spec["background"]

        namespace = {
            "get_boss": lambda: self.boss, "get_options": lambda: SimpleNamespace(),
            "patch_color_profiles": native_colors,
            "patch_options_with_color_spec": lambda *args: None,
            "patch_global_colors": lambda *args: None,
            "set_os_window_chrome": lambda *args: None,
        }
        exec(code, namespace)
        self.apply = namespace["patch_colors"]

    def set_image(self, path, windows, configured, **appearance):
        if path is not None and not isinstance(path, str):
            raise TypeError("argument 1 must be str or None, not tuple")
        self.images.append((path, windows, configured, appearance))


class AutoThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load_function(INSTALLED.read_text())
        with tempfile.TemporaryDirectory(prefix="kitty-auto-theme-", dir="/tmp/opencode") as temporary:
            root = Path(temporary)
            (root / "kitty").mkdir()
            copied = root / "kitty/colors.py"
            copied.write_text(INSTALLED.read_text())
            subprocess.run(["patch", "--batch", "-s", "-p1", "-i", str(ROOT / "auto-theme-background-images.patch")], cwd=root, check=True)
            cls.fixed = load_function(copied.read_text())

    def test_old_code_changes_colors_but_raises_before_notification(self):
        harness = Harness(self.original)
        with self.assertRaisesRegex(TypeError, "not tuple"):
            harness.apply({"background": 0xFAFAFA}, (), True, background_image_options={"background_image": ()})
        self.assertEqual(harness.window.screen.color_profile.default_bg, 0xFAFAFA)
        self.assertEqual(harness.notifications, [])

    def test_empty_images_clear_image_and_notify_in_both_directions(self):
        harness = Harness(self.fixed)
        for color in (0xFAFAFA, 0x2C2E34):
            harness.apply({"background": color}, (), True, background_image_options={"background_image": ()})
        self.assertEqual(harness.notifications, [1, 1])
        self.assertEqual([call[0] for call in harness.images], [None, None])
        self.assertEqual(harness.refreshes, [1, 1])

    def test_first_image_is_default_without_mutating_configured_collection(self):
        for paths in (("/fixture/one.png",), ("/fixture/one.png", "/fixture/two.png")):
            with self.subTest(paths=paths):
                harness = Harness(self.fixed)
                appearance = {
                    "background_image": paths, "background_image_layout": "scaled",
                    "background_image_linear": False, "background_tint": 0.3,
                    "background_tint_gaps": 0.5,
                }
                harness.apply({"background": 0xFAFAFA}, (), True, background_image_options=appearance)
                self.assertEqual(appearance["background_image"], paths)
                self.assertEqual(harness.images, [(paths[0], (), True, {
                    "layout": "scaled", "linear_interpolation": False,
                    "tint": 0.3, "tint_gaps": 0.5,
                })])
                self.assertEqual(harness.notifications, [1])

    def test_absent_image_value_uses_native_none(self):
        harness = Harness(self.fixed)
        harness.apply({"background": 0xFAFAFA}, (), background_image_options={})
        self.assertIsNone(harness.images[0][0])
        self.assertFalse(harness.images[0][2])
        self.assertEqual(harness.notifications, [1])

    def test_explicit_notification_suppression_remains_supported(self):
        harness = Harness(self.fixed)
        harness.apply({"background": 0xFAFAFA}, (), notify_on_bg_change=False, background_image_options={"background_image": ()})
        self.assertEqual(harness.notifications, [])
        self.assertEqual(harness.refreshes, [1])

    def test_unchanged_background_does_not_notify(self):
        harness = Harness(self.fixed)
        harness.apply({"background": 0x2C2E34}, (), background_image_options={"background_image": ()})
        self.assertEqual(harness.notifications, [])


if __name__ == "__main__":
    unittest.main()
