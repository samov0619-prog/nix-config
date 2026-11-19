"""Exercise the declared installCheck shell from a Meson-style build directory."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]


class InstallCheckTests(unittest.TestCase):
    def test_source_root_is_independent_of_build_working_directory(self):
        recipe = (HERE / "default.nix").read_text()
        phase = recipe.split("installCheckPhase = ''\n", 1)[1].split("\n  '';", 1)[0]
        for source_name in ("source", "source with spaces"):
            with self.subTest(source_root=source_name):
                with tempfile.TemporaryDirectory(
                    prefix="slurp-phase-", dir=os.environ.get("TMPDIR", "/tmp/opencode")
                ) as directory:
                    root = Path(directory)
                    source = root / source_name
                    build = source / "build"
                    build.mkdir(parents=True)
                    (source / "main.c").write_text("source-root fixture, not Slurp source")
                    interpreter = root / "python" / "bin" / "python3"
                    interpreter.parent.mkdir(parents=True)
                    interpreter.write_text(
                        f"#!{sys.executable}\n"
                        "import os\n"
                        "from pathlib import Path\n"
                        "import sys\n"
                        "assert Path(sys.argv[1]).is_file()\n"
                        "assert sys.argv[3:] == ['--check-upstream']\n"
                        "source = Path(sys.argv[2])\n"
                        "assert source == Path(os.environ['EXPECTED_SOURCE'])\n"
                        "assert (source / 'main.c').is_file()\n"
                        "Path(os.environ['CALLED']).touch()\n"
                    )
                    interpreter.chmod(0o700)
                    body = phase.replace("${python3}", str(interpreter.parents[1])).replace(
                        "${./tests/test_cursor_shape.py}", str(HERE / "tests/test_cursor_shape.py")
                    )
                    result = subprocess.run(
                        [shutil.which("bash"), "-euo", "pipefail", "-c",
                         "runHook() { :; }\n" + body],
                        cwd=build,
                        env={
                            "NIX_BUILD_TOP": str(root),
                            "sourceRoot": source_name,
                            "EXPECTED_SOURCE": str(source),
                            "CALLED": str(root / "called"),
                        },
                        capture_output=True, text=True, timeout=5,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue((root / "called").is_file())


if __name__ == "__main__":
    unittest.main()
