"""Exercise the HM function and evaluate its expressions with tiny local flakes.

No package builds or interactive shells; Darwin is evaluator-fixture coverage only.
"""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


class NshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fish = shutil.which("fish")
        cls.nix = shutil.which("nix")
        if not cls.fish or not cls.nix:
            raise RuntimeError("Tests require already-installed Fish and Nix")
        repository = Path(__file__).resolve().parents[3]
        cls.body = subprocess.check_output(
            [
                cls.nix,
                "eval",
                "--impure",
                "--offline",
                "--raw",
                "--expr",
                "(import ./home/core-set/shell.nix "
                "{ pkgsUnstable = {}; lib = {}; config = {}; })"
                ".programs.fish.functions.nsh.body",
            ],
            cwd=repository,
            text=True,
        )
        directory = tempfile.TemporaryDirectory(prefix="nsh-", dir="/tmp/opencode")
        cls.addClassCleanup(directory.cleanup)
        cls.root = Path(directory.name)
        cls.home = cls.root / "home with spaces"
        cls.checkout = cls.home / "nix-config"
        cls.alternate = cls.root / "alternate ' checkout"
        for checkout in (cls.checkout, cls.alternate):
            checkout.mkdir(parents=True)
            (checkout / "flake.nix").write_text(
                '{ inputs.nixpkgs.url = "path:./stable"; '
                'inputs.nixpkgs-unstable.url = "path:./unstable"; '
                "outputs = _: {}; }\n"
            )
            for channel in ("stable", "unstable"):
                source = checkout / channel
                source.mkdir()
                label = channel if checkout == cls.checkout else "alternate-" + channel
                (source / "flake.nix").write_text(
                    "{ outputs = _: { legacyPackages = builtins.listToAttrs "
                    "(map (system: { name = system; value.hello = { inherit system; "
                    f"channel = {json.dumps(label)}; "
                    '}; }) [ "x86_64-linux" "aarch64-darwin" ]); }; }\n'
                )
            subprocess.run(
                [cls.nix, "flake", "lock", "--offline", str(checkout)],
                check=True,
                capture_output=True,
                text=True,
            )

    def invoke(self, arguments, override=None):
        env = os.environ | {"HOME": str(self.home)}
        env.pop("NSH_FLAKE", None)
        if override is not None:
            env["NSH_FLAKE"] = override
        # No real Fish config or personal environment is sourced. Capture only
        # the nix invocation, never the inherited environment or real packages.
        script = (
            f"function nsh\n{self.body}\nend\n"
            "function nix\n"
            "    printf '%s\\0' $argv\n"
            "    return 37\n"
            "end\n"
            f"nsh {shlex.join(arguments)}\n"
        )
        result = subprocess.run(
            [self.fish, "--no-config", "-c", script],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )
        return result, env

    def captured(self, arguments, override=None):
        result, env = self.invoke(arguments, override)
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(result.stderr, "")
        args = result.stdout.removesuffix("\0").split("\0")
        self.assertEqual(args[:3], ["shell", "--impure", "--expr"])
        self.assertEqual(args[-3], "--command")
        self.assertEqual(Path(args[-2]).resolve(), Path(self.fish).resolve())
        self.assertEqual(args[-1], "--interactive")
        return args, env

    def test_channels_and_native_platform(self):
        for selector, channel in (
            (None, "stable"),
            ("stable", "stable"),
            ("-s", "stable"),
            ("--stable", "stable"),
            ("unstable", "unstable"),
            ("-u", "unstable"),
            ("--unstable", "unstable"),
        ):
            arguments = ([selector] if selector else []) + ["hello"]
            args, env = self.captured(arguments)
            self.assertEqual(args[4:-3], ["hello"])
            for system in ("x86_64-linux", "aarch64-darwin"):
                with self.subTest(selector=selector, system=system):
                    output = subprocess.check_output(
                        [
                            self.nix,
                            "eval",
                            "--offline",
                            "--impure",
                            "--json",
                            "--eval-system",
                            system,
                            "--expr",
                            args[3],
                            "hello",
                        ],
                        cwd=self.root,
                        env=env,
                        text=True,
                    )
                    self.assertEqual(
                        json.loads(output), {"channel": channel, "system": system}
                    )

    def test_checkout_override_and_empty_default(self):
        for override in ("", str(self.alternate)):
            with self.subTest(override=override):
                args, env = self.captured(["hello"], override)
                output = subprocess.check_output(
                    [
                        self.nix,
                        "eval",
                        "--offline",
                        "--impure",
                        "--json",
                        "--expr",
                        args[3],
                        "hello",
                    ],
                    cwd=self.root,
                    env=env,
                    text=True,
                )
                expected = "alternate-stable" if override else "stable"
                self.assertEqual(json.loads(output)["channel"], expected)

    def test_package_arguments_are_not_split(self):
        packages = ["hello", "python3Packages.requests", "two words"]
        args, _ = self.captured(["unstable", *packages])
        self.assertEqual(args[4:-3], packages)

    def test_missing_packages_do_not_invoke_nix(self):
        for selector in (None, "stable", "unstable", "-s", "--stable", "-u", "--unstable"):
            with self.subTest(selector=selector):
                result, _ = self.invoke([selector] if selector else [])
                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    result.stdout, "Usage: nsh [stable|unstable] PACKAGE [PACKAGE ...]\n"
                )
                self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
