"""Actual registry callback with C stubs; cleanup/request source contracts, no display."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]
SOURCE = ""


class CursorShapeContracts(unittest.TestCase):
    def test_actual_registry_callback_binds_shape_protocol(self):
        callback = re.search(r"static void handle_global\([\s\S]*?\n}", SOURCE)
        self.assertIsNotNone(callback, "Registry callback changed; inspect upstream")
        harness = r"""
#include <assert.h>
#include <stdint.h>
#include <string.h>
struct wl_registry { int unused; };
struct wl_interface { const char *name; };
struct slurp_state {
    void *compositor, *shm, *layer_shell, *xdg_output_manager, *cursor_shape_manager;
};
struct slurp_seat { int unused; };
struct slurp_output { int unused; };
#define INTERFACE(name) static const struct wl_interface name##_interface = { #name }
INTERFACE(wl_compositor);
INTERFACE(wl_shm);
INTERFACE(zwlr_layer_shell_v1);
INTERFACE(wl_seat);
INTERFACE(wl_output);
INTERFACE(zxdg_output_manager_v1);
INTERFACE(wp_cursor_shape_manager_v1);
static int calls;
static const struct wl_interface *expected;
static void *wl_registry_bind(struct wl_registry *registry, uint32_t name,
        const struct wl_interface *interface, uint32_t version) {
    assert(name == 77 && version == 1 && interface == expected);
    calls++;
    return registry;
}
static void create_seat(struct slurp_state *state, void *seat) {
    (void)state; (void)seat;
}
static void create_output(struct slurp_state *state, void *output) {
    (void)state; (void)output;
}
""" + callback.group() + r"""
int main(void) {
    struct wl_registry registry = {0};
    struct slurp_state state = {0};
    expected = &wp_cursor_shape_manager_v1_interface;
    handle_global(&state, &registry, 77, "wp_cursor_shape_manager_v1", 2);
    assert(calls == 1 && state.cursor_shape_manager == &registry);
    calls = 0;
    state = (struct slurp_state){0};
    handle_global(&state, &registry, 77, "unknown_protocol", 1);
    assert(calls == 0 && state.cursor_shape_manager == NULL);
    expected = &wl_shm_interface;
    handle_global(&state, &registry, 77, "wl_shm", 1);
    assert(calls == 1 && state.shm == &registry);
    assert(state.cursor_shape_manager == NULL);
    return 0;
}
"""
        compiler = shutil.which("cc")
        self.assertIsNotNone(compiler, "A C compiler is required for this contract")
        with tempfile.TemporaryDirectory(
            prefix="slurp-callback-", dir=os.environ.get("TMPDIR", "/tmp/opencode")
        ) as directory:
            root = Path(directory)
            source = root / "callback.c"
            source.write_text(harness)
            # Upstream deliberately ignores the registry's advertised version.
            compiled = subprocess.run(
                [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                 "-Wno-unused-parameter", str(source),
                 "-o", str(root / "callback")],
                capture_output=True, timeout=10,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr.decode())
            result = subprocess.run(
                [str(root / "callback")], capture_output=True, timeout=5
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_missing_client_theme_is_not_destroyed(self):
        self.assertIsNotNone(
            re.search(
                r"if \(output->cursor_theme\)\s*\{\s*"
                r"wl_cursor_theme_destroy\(output->cursor_theme\);", SOURCE
            ),
            "Missing guard for the unused Xcursor theme",
        )

    def test_shape_manager_cleanup_is_guarded(self):
        self.assertIsNotNone(
            re.search(
                r"if \(state.cursor_shape_manager != NULL\)\s*\{\s*"
                r"wp_cursor_shape_manager_v1_destroy\(state.cursor_shape_manager\);", SOURCE
            ),
            "Missing guarded cursor-shape manager cleanup",
        )

    def test_native_crosshair_request_and_xcursor_fallback_remain(self):
        self.assertTrue("WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_CROSSHAIR" in SOURCE)
        self.assertTrue("if (!state.cursor_shape_manager && !create_cursors(&state))" in SOURCE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Slurp source directory or main.c")
    parser.add_argument("--check-upstream", action="store_true", help="Do not apply the patch")
    args = parser.parse_args()
    source_file = args.source / "main.c" if args.source.is_dir() else args.source
    with tempfile.TemporaryDirectory(
        prefix="slurp-source-", dir=os.environ.get("TMPDIR", "/tmp/opencode")
    ) as directory:
        root = Path(directory)
        shutil.copyfile(source_file, root / "main.c")
        if not args.check_upstream:
            subprocess.run(
                ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-i",
                 str(HERE / "cursor-shape.patch")],
                cwd=root, check=True, timeout=5,
            )
        SOURCE = (root / "main.c").read_text()
    unittest.main(argv=[__file__])
