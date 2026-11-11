"""Check the actual generated updater with mock commands, never real builds.

Nix only evaluates the module's shell/completion text using a stub package writer.
The generated Bash is syntax-checked, then run with fake nix/git/uname executables.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
MOCK = """import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
if name == 'nix':
    with open(os.environ['CALL_LOG'], 'a') as log:
        log.write(json.dumps(sys.argv[1:]) + '\\n')
elif name == 'git':
    assert sys.argv[1:] == ['rev-parse', '--show-toplevel']
    print(os.environ['MOCK_REPO'])
elif name == 'uname':
    assert sys.argv[1:] == ['-s']
    print('Linux')
else:
    raise RuntimeError(name)
"""


class UpdaterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        expression = """let
          m = import ./nix-flake-update-verify.nix {
            pkgs.writeShellApplication = args: args.text;
          };
        in {
          script = builtins.head m.home.packages;
          completion = m.home.file.".config/fish/completions/nix-flake-update-verify.fish".text;
        }"""
        cls.generated = json.loads(
            subprocess.check_output(
                ["nix", "eval", "--impure", "--json", "--offline", "--expr", expression],
                cwd=HERE,
                text=True,
                timeout=15,
            )
        )
        subprocess.run(
            ["bash", "-n"], input=cls.generated["script"], text=True, check=True
        )

    def exercise(self, arguments, update):
        with tempfile.TemporaryDirectory(prefix="flake-updater-", dir="/tmp/opencode") as d:
            root = Path(d)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for name in ("nix", "git", "uname"):
                p = bin_dir / name
                p.write_text(f"#!{sys.executable}\n" + MOCK)
                p.chmod(0o755)
            log = root / "calls.jsonl"
            environment = os.environ | {
                "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                "CALL_LOG": str(log),
                "MOCK_REPO": str(root),
            }
            script = root / "updater.sh"
            script.write_text(self.generated["script"])
            subprocess.run(
                ["bash", str(script), "--hosts", "laptop", *arguments],
                env=environment,
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            expected = [] if update is None else [["flake", "update", *update]]
            expected += [
                ["build", "--no-link", ".#nixosConfigurations.laptop.config.system.build.toplevel"],
                ["build", "--no-link", ".#homeConfigurations.samov-laptop.activationPackage"],
            ]
            self.assertEqual(calls, expected)

    def test_kernel_input(self):
        self.assertIn("nixpkgs-kernel", self.generated["completion"])
        self.assertIn("nixpkgs-kernel", self.generated["script"])
        self.exercise(["--input", "nixpkgs-kernel"], ["nixpkgs-kernel"])

    def test_all_inputs(self):
        self.exercise(["--input", "all"], [])

    def test_no_update(self):
        self.exercise(["--no-update"], None)


if __name__ == "__main__":
    unittest.main()
