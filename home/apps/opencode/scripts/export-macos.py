"""Materialize the pure Mac export into a new staging directory, never install it."""

import argparse
import hashlib
import os
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new, non-existing staging directory")
    parser.add_argument("--personal-directory", default="~/.config/opencode-local")
    args = parser.parse_args()
    output = args.output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        parser.error("output must not exist; this command never updates a live configuration")
    # Do not offer an installer disguised as an export, even with a fresh HOME.
    if output.name in {"opencode", "opencode-local"} or ".config" in output.parts:
        parser.error("choose a separate staging directory, not an OpenCode configuration path")
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).resolve()
    if output.resolve().is_relative_to(config_root):
        parser.error("choose a staging directory outside the active XDG config root")
    definition = Path(__file__).resolve().parents[1] / "macos/export.nix"
    parameter = json.dumps(args.personal_directory).replace("${", r"\${")
    result = subprocess.run(
        ["nix", "eval", "--offline", "--json", "--file", str(definition),
         "--apply", f"f: f {{ personalDirectory = {parameter}; }}"],
        check=True, capture_output=True, text=True, timeout=20,
    )
    files = json.loads(result.stdout)["files"]
    for name, entry in files.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or set(entry) not in ({"source"}, {"text"}):
            raise ValueError(f"Unsafe export entry: {name}")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    hashes = {}
    for name, entry in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if "text" in entry:
            target.write_text(entry["text"])
        else:
            shutil.copyfile(entry["source"], target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "manifest.json").write_text(json.dumps({
        "target": "OpenCode 2.4.0 corporate Mac; acceptance pending",
        "personalDirectory": args.personal_directory,
        "files": hashes,
    }, indent=2) + "\n")
    print(f"Exported {len(files)} ordinary files to {output}; nothing installed.")


if __name__ == "__main__":
    main()
