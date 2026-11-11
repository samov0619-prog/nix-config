"""Actual patched C argument loop and Yazi wrapper, without D-Bus or a terminal."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = None


class LocalhostUriTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="filemanager1-uri-test-", dir="/tmp/opencode"
        )
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        tree = cls.root / "source"
        for name in ("src/file_manager_dbus.c", "config/yazi-wrapper.sh"):
            destination = tree / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / name, destination)
        cls.original = cls.compile_loop(tree, "original")
        patch_result = subprocess.run(
            ["patch", "--batch", "--fuzz=0", "-p1", "-i",
             str(ROOT / "localhost-uri.patch")],
            cwd=tree, capture_output=True, text=True, timeout=5,
        )
        if patch_result.returncode:
            raise AssertionError(patch_result.stdout + patch_result.stderr)
        cls.fixed = cls.compile_loop(tree, "fixed")
        wrapper = (tree / "config/yazi-wrapper.sh").read_text()
        # Match the existing Nix postPatch substitutions; no package build.
        cls.wrapper = wrapper.replace("/usr/bin/", "").replace(
            'eval "$termcmd -- ', 'eval "$termcmd '
        )

    @classmethod
    def compile_loop(cls, tree, name):
        source = (tree / "src/file_manager_dbus.c").read_text()
        start = "  for (size_t i = 0; i < uri_count; i++) {"
        end = "  args[arg_count - 1] = NULL;"
        if source.count(start) != 1 or source.count(end) != 1:
            raise AssertionError("Pinned production argument loop changed")
        loop = start + source.split(start, 1)[1].split(end, 1)[0]
        fixture = cls.root / f"{name}.c"
        fixture.write_text(
            '#include <stdio.h>\n#include <stdlib.h>\n'
            '#include <string.h>\n#include <strings.h>\n'
            'int main(int argc, char **argv) {\n'
            '  size_t uri_count = (size_t)argc - 1;\n'
            '  char **uri_array = argv + 1;\n'
            '  char **args = calloc(uri_count + 3, sizeof(*args));\n'
            '  if (!args) return 1;\n'
            + loop +
            '  for (size_t i = 0; i < uri_count; i++) {\n'
            '    fwrite(args[2 + i], 1, strlen(args[2 + i]) + 1, stdout);\n'
            '  }\n  free(args);\n  return 0;\n}\n'
        )
        binary = cls.root / name
        subprocess.run(
            ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", str(fixture),
             "-o", str(binary)],
            check=True, capture_output=True, timeout=15,
        )
        return binary

    def normalize(self, *uris, original=False):
        result = subprocess.run(
            [str(self.original if original else self.fixed), *uris],
            check=True, capture_output=True, timeout=5,
        )
        return result.stdout.decode().split("\0")[:-1]

    def test_original_control_reproduces_the_localhost_bug(self):
        self.assertEqual(
            self.normalize("file://localhost/fixture/a.txt", original=True),
            ["localhost/fixture/a.txt"],
        )

    def test_localhost_matches_empty_authority(self):
        for authority in ("localhost", "LOCALHOST", "LocalHost"):
            with self.subTest(authority=authority):
                self.assertEqual(
                    self.normalize(f"file://{authority}/fixture/a.txt"),
                    self.normalize("file:///fixture/a.txt"),
                )

    def test_root_and_multiple_uris(self):
        self.assertEqual(
            self.normalize("file://localhost/", "file:///", "/fixture/plain"),
            ["/", "/", "/fixture/plain"],
        )

    def test_percent_decoding_stays_in_the_wrapper(self):
        self.assertEqual(
            self.normalize("file://localhost/fixture/a%20b%2520.txt"),
            ["/fixture/a%20b%2520.txt"],
        )

    def test_only_the_exact_localhost_authority_is_changed(self):
        for uri in (
            "file://localhost.example/fixture/a.txt",
            "file://localhost:123/fixture/a.txt",
            "file://remote.example/fixture/a.txt",
            "file:///fixture/localhost/a.txt",
            "/fixture/localhost/a.txt",
        ):
            with self.subTest(uri=uri):
                self.assertEqual(self.normalize(uri), self.normalize(uri, original=True))

    def test_real_wrapper_receives_the_same_local_paths(self):
        uris = [
            "file://localhost/fixture/a%20b.txt",
            "file://LOCALHOST/fixture/%D1%82%D0%B5%D1%81%D1%82%20O%27Brien.txt",
            "file://localhost/fixture/%24%28exit%2077%29%20%25.txt",
        ]
        expected = [
            "--", "yazi", "/fixture/a b.txt", "/fixture/тест O'Brien.txt",
            "/fixture/$(exit 77) %.txt",
        ]
        # The terminal is a Bash function that only serializes argv. yazi is
        # never executed; PATH contains no external application executables.
        prefix = 'fixture_terminal() { printf "%s\\0" "$@"; }\n'
        for method in ("ShowItems", "ShowFolders"):
            with self.subTest(method=method):
                result = subprocess.run(
                    [shutil.which("bash"), "-c", prefix + self.wrapper,
                     "wrapper", method, *self.normalize(*uris)],
                    cwd=self.root,
                    env={"PATH": str(self.root), "HOME": str(self.root),
                         "TERMCMD": "fixture_terminal --"},
                    check=True, capture_output=True, timeout=5,
                )
                self.assertEqual(result.stdout.decode().split("\0")[:-1], expected)

    def test_nix_package_enables_the_patch(self):
        self.assertIn(
            "patches = [ ./localhost-uri.patch ];", (ROOT / "default.nix").read_text()
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Pinned source directory; this test never downloads it")
    args, remaining = parser.parse_known_args()
    SOURCE = args.source.resolve()
    unittest.main(argv=[sys.argv[0], *remaining])
