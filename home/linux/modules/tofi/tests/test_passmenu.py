"""Exercise the production shell pipeline with fake pass/tofi/wtype, no secrets or GUI."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PassmenuTests(unittest.TestCase):
    def run_menu(self, password, selection="fixture entry"):
        source = (ROOT / "module.nix").read_text()
        opening = '(pkgs.writeShellScriptBin "tofi-passmenu" \'\''
        self.assertEqual(source.count(opening), 1)
        body = source.split(opening, 1)[1].split("        '')", 1)[0]
        body = textwrap.dedent(body)
        body = body.replace("${pkgs.runtimeShell}", shutil.which("bash"))
        body = body.replace("''${", "${")
        self.assertNotIn("${pkgs.", body)

        with tempfile.TemporaryDirectory(
            prefix="passmenu-test-", dir="/tmp/opencode"
        ) as directory:
            root = Path(directory)
            binaries = root / "bin"
            store = root / "store"
            binaries.mkdir()
            store.mkdir()
            (store / "fixture entry.gpg").touch()
            (root / "password.bin").write_bytes(password)
            (root / "selection.txt").write_text(selection)
            scripts = {
                "tofi": """
                    import sys
                    from pathlib import Path
                    sys.stdin.read()
                    choice = Path("selection.txt").read_text()
                    if not choice:
                        sys.exit(1)
                    print(choice)
                """,
                "pass": """
                    import json
                    import sys
                    from pathlib import Path
                    Path("pass-argv.json").write_text(json.dumps(sys.argv[1:]))
                    sys.stdout.buffer.write(Path("password.bin").read_bytes())
                """,
                "wtype": """
                    import json
                    import sys
                    from pathlib import Path
                    Path("wtype-argv.json").write_text(json.dumps(sys.argv[1:]))
                    Path("typed.bin").write_bytes(sys.stdin.buffer.read())
                """,
            }
            for name, script in scripts.items():
                executable = binaries / name
                executable.write_text(
                    f"#!{shutil.which('python3')}\n" + textwrap.dedent(script)
                )
                executable.chmod(0o700)
            helper = root / "passmenu.sh"
            helper.write_text(body)
            env = {
                **os.environ,
                "HOME": str(root),
                "PASSWORD_STORE_DIR": str(store),
                "PATH": str(binaries) + ":" + os.environ["PATH"],
            }
            subprocess.run(
                [shutil.which("bash"), str(helper)],
                cwd=root,
                env=env,
                check=True,
                timeout=5,
                capture_output=True,
            )
            self.assertEqual(json.loads((root / "wtype-argv.json").read_text()), ["-"])
            pass_arguments = root / "pass-argv.json"
            if selection:
                self.assertEqual(
                    json.loads(pass_arguments.read_text()), ["show", selection]
                )
            else:
                self.assertFalse(pass_arguments.exists())
            return (root / "typed.bin").read_bytes()

    def test_password_does_not_submit(self):
        self.assertEqual(self.run_menu(b"fixture-password\n"), b"fixture-password")

    def test_only_first_line_is_typed(self):
        self.assertEqual(
            self.run_menu(b"fixture-password\nusername: fixture\n"),
            b"fixture-password",
        )

    def test_spaces_unicode_and_shell_characters_remain_literal(self):
        password = "  -n 'пароль' $HOME * \\  ".encode()
        self.assertEqual(self.run_menu(password + b"\n"), password)

    def test_password_without_final_newline(self):
        self.assertEqual(self.run_menu(b"fixture-password"), b"fixture-password")

    def test_cancellation_does_not_decrypt_or_type(self):
        self.assertEqual(self.run_menu(b"fixture-password\n", selection=""), b"")


if __name__ == "__main__":
    unittest.main()
