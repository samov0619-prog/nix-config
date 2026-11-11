"""Explicit, isolated native nomacs/qt6ct check; never obtains or builds packages."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import apply as appearance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nomacs", required=True, type=Path)
    parser.add_argument("--qt6ct", required=True, type=Path)
    parser.add_argument("--adwaita-qt6", required=True, type=Path)
    args = parser.parse_args()
    for path in (args.nomacs, args.qt6ct, args.adwaita_qt6):
        if not path.exists():
            parser.error(f"Package must already exist: {path}")
    if not shutil.which("magick"):
        parser.error("ImageMagick's magick CLI is required to sample rendered frames")

    root = Path(tempfile.mkdtemp(prefix="nomacs-qt6ct-", dir="/tmp/opencode"))
    config = root / "config"
    (config / "nomacs").mkdir(parents=True)
    # Start with the previous explicit user choice, not the desired result.
    (config / "nomacs" / "Image Lounge.conf").write_text(
        "[General]\nfirstTime=false\n"
        "[AppSettings]\nfirstTime.nomacs.3=false\n"
        "[DisplaySettings]\nthemeName312=System.css\nstylePlugin=adwaita-dark\n"
    )
    appearance.apply(config, "light", initialize_nomacs=True)
    env = os.environ | {
        "HOME": str(root / "home"),
        "XDG_CONFIG_HOME": str(config),
        "XDG_CACHE_HOME": str(root / "cache"),
        "XDG_DATA_HOME": str(root / "data"),
        "QT_QPA_PLATFORM": "minimal",
        "QT_QPA_PLATFORMTHEME": "qt5ct",
        "QT_STYLE_OVERRIDE": "",
        "QT_DEBUG_BACKINGSTORE": "1",
        "QT_FORCE_STDERR_LOGGING": "1",
        "QT_LOGGING_RULES": "qt6ct.debug=true",
    }
    env["QT_PLUGIN_PATH"] = os.pathsep.join(
        [
            str(args.qt6ct / "lib/qt-6/plugins"),
            str(args.adwaita_qt6 / "lib/qt-6/plugins"),
            os.environ.get("QT_PLUGIN_PATH", ""),
        ]
    )
    results = []
    with (root / "runtime.log").open("w") as log:
        def launch():
            return subprocess.Popen(
                [str(args.nomacs)], cwd=root, env=env, stdout=log, stderr=log
            )

        def stop(process):
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        def sample(process, phase, dark):
            time.sleep(4)  # qt6ct's native directory-change debounce is 3 seconds.
            if process.poll() is not None:
                raise RuntimeError(f"nomacs exited: {process.returncode}; see {root}")
            text = (root / "runtime.log").read_text()
            names = re.findall(r'saving contents to "?(output\d+\.png)', text)
            if not names:
                raise RuntimeError(f"No backing-store frame; see {root}")
            frame = root / f"{phase}.png"
            shutil.copyfile(root / names[-1], frame)
            rendered = subprocess.check_output(
                ["magick", str(frame), "-format", "%[pixel:p{10,100}]", "info:"],
                text=True,
            )
            match = re.fullmatch(r"srgba?\((\d+),(\d+),(\d+)(?:,[^)]+)?\)", rendered)
            if not match:
                raise RuntimeError(f"Unexpected rendered pixel: {rendered}")
            rgb = tuple(map(int, match.groups()))
            # Native Adwaita's light surface must be bright; its dark surface dark.
            assert max(rgb) < 100 if dark else min(rgb) > 200, (phase, rgb)
            results.append({"phase": phase, "rgb": rgb, "frame": str(frame)})

        process = launch()
        try:
            sample(process, "startup-light", False)
            appearance.apply(config, "dark")
            sample(process, "live-dark", True)
            appearance.apply(config, "light")
            sample(process, "live-light", False)
        finally:
            stop(process)
        appearance.apply(config, "dark")
        process = launch()
        try:
            sample(process, "reopened-dark", True)
        finally:
            stop(process)

    text = (root / "runtime.log").read_text()
    assert "qt6ct: using qt6ct plugin" in text
    assert text.count("system palette changed, reapplying theme") >= 2
    assert "invalid style override" not in text
    assert results[0]["rgb"] == results[2]["rgb"]
    print(json.dumps({"root": str(root), "checks": results}, indent=2))


if __name__ == "__main__":
    main()
