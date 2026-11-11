"""Offline backport inventory/update review. Never writes repo/review state or builds.

Default: validate coverage and compare declared input/package fingerprints.
--cached: bounded offline Nix source-path evaluation for changed entries only.
--all: also examine unchanged entries. Cached archives yield only selected files,
with a 20-second subprocess limit; no fetchers or full source trees are realized.
--contracts: opt into small actual-function removal contracts when source is a
directory and cc is available. A failed contract is NOT proof a fix is needed.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "docs/backports/registry.json"
BASELINE = "docs/backports/reviewed.json"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def snapshot(root, registry):
    lock = json.loads((root / "flake.lock").read_text())
    nodes = lock["nodes"]
    root_node = nodes[lock["root"]]

    def resolve(reference):
        if isinstance(reference, str):
            return nodes[reference]
        node = root_node
        for name in reference:
            node = resolve(node["inputs"][name])
        return node

    inputs = {
        name: digest(json.dumps(resolve(ref).get("locked", {}), sort_keys=True).encode())
        for name, ref in root_node["inputs"].items()
    }
    for entry in registry["entries"]:
        for name in entry["inputs"]:
            if name not in inputs:
                raise ValueError(f"Unknown watched input: {name}")
    files = sorted({p for entry in registry["entries"] for p in entry["watch"] + entry["patches"]})
    return {
        "inputs": inputs,
        "files": {name: digest((root / name).read_bytes()) for name in files},
    }


def active(path):
    return not any(part in (".git", "archive", "node_modules") for part in path.parts)


def validate(root, registry):
    if registry["schema"] != 1:
        raise ValueError("Unsupported registry schema")
    owners = {}
    ids = set()
    covered = set(registry.get("coverageExclusions", {}))
    for entry in registry["entries"]:
        if entry["kind"] not in {
            "upstream-backport", "unmerged-backport", "local-bugfix",
            "packaging-compatibility", "temporary-selection", "customization", "test-only",
        }:
            raise ValueError(f"Unknown fix kind: {entry['kind']}")
        if entry["id"] in ids:
            raise ValueError(f"Duplicate ID: {entry['id']}")
        ids.add(entry["id"])
        for name in entry["watch"] + entry["patches"] + [entry["details"]]:
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or not (root / path).is_file():
                raise ValueError(f"Invalid/missing registered artifact: {name}")
        covered.update(entry["watch"])
        for name in entry.get("sourceFiles", []):
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError(f"Unsafe source-file path: {name}")
        if entry.get("contract"):
            script = Path(entry["contract"][0])
            if script.is_absolute() or ".." in script.parts or not (root / script).is_file():
                raise ValueError(f"Invalid/missing contract script: {script}")
        for name in entry["patches"]:
            if name in owners:
                raise ValueError(f"Patch registered twice: {name}")
            owners[name] = entry["id"]
    patches = {str(p.relative_to(root)) for p in root.rglob("*.patch") if active(p.relative_to(root))}
    if patches != set(owners):
        raise ValueError(f"Patch coverage mismatch: {sorted(patches ^ set(owners))}")
    for path in root.rglob("*.nix"):
        rel = path.relative_to(root)
        if not active(rel) or path.name.startswith("test"):
            continue
        # A safety net, not a semantic detector for arbitrary inline workarounds.
        if re.search(r"overrideAttrs|substituteInPlace|fetchpatch|boot\.kernelPatches", path.read_text()):
            if str(rel) not in covered:
                raise ValueError(f"Unregistered source transformation: {rel}")


def cached_sources(root, names):
    if not names:
        return {}, ""
    quoted_root = json.dumps(str(root), ensure_ascii=False).replace("${", "\\${")
    expression = (
        f"import (builtins.toPath ({quoted_root} + \"/scripts/backport-sources.nix\")) "
        f"{{ root = {quoted_root}; names = builtins.fromJSON "
        f"{json.dumps(json.dumps(sorted(names)))}; }}"
    )
    try:
        result = subprocess.run(
            ["nix", "eval", "--impure", "--offline", "--json",
             "--no-write-lock-file", "--no-update-lock-file",
             "--option", "allow-import-from-derivation", "false", "--expr", expression],
            cwd=root, capture_output=True, text=True, timeout=20,
            env=os.environ | {"GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"},
        )
        if result.returncode:
            return {}, "offline source evaluation unavailable"
        return json.loads(result.stdout), ""
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}, "offline source evaluation failed/timed out (20s)"


def patch_files(text):
    names = re.findall(r"^\+\+\+ b/(.+)$", text, re.M)
    for name in names:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe patch path: {name}")
    return names


def probe(root, entry, source, contracts):
    source = Path(source).resolve()
    if entry.get("platform") == "linux" and not sys.platform.startswith("linux"):
        return "review-required", "this contract requires Linux; not run on this platform"
    if source.is_file():
        names = sorted(set(entry.get("sourceFiles", [])) | {
            name for patch in entry["patches"]
            for name in patch_files((root / patch).read_text())
        })
        if not names:
            return "review-required", "no selected archive files registered"
        with tempfile.TemporaryDirectory(prefix="backport-source-", dir="/tmp/opencode") as d:
            try:
                result = subprocess.run(
                    [sys.executable, "-B", str(root / "scripts/backport-unpack.py"),
                     str(source), d, json.dumps(names)],
                    capture_output=True, text=True, timeout=20,
                )
            except (OSError, subprocess.TimeoutExpired):
                return "review-required", "selected archive extraction unavailable/timed out (20s)"
            if result.returncode:
                return "review-required", "selected source files unavailable in cached archive"
            return probe(root, entry, d, contracts)
    if not source.is_dir():
        return "review-required", "source not cached; no fetch/build attempted"
    if contracts and entry.get("contract"):
        if shutil.which("cc") is None:
            return "review-required", "cc unavailable; removal contract not run"
        command = [sys.executable, "-B"] + [
            str(root / arg) if i == 0 else arg.replace("{source}", str(source))
            for i, arg in enumerate(entry["contract"])
        ]
        try:
            result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=45)
        except (OSError, subprocess.TimeoutExpired):
            return "review-required", "unpatched contract unavailable/timed out"
        if result.returncode == 0:
            return "removal-candidate", "unpatched-source contract passed; review/integration still required"
        # Compilation/extraction/assertion failures are deliberately indistinguishable
        # here: inspect the dedicated harness before interpreting any failure.
        return "review-required", "unpatched contract failed; run dedicated harness for details"
    if not entry["patches"]:
        return "review-required", "inline/package-selection removal needs its documented checks"
    with tempfile.TemporaryDirectory(prefix="backport-review-", dir="/tmp/opencode") as d:
        target = Path(d)
        for patch in entry["patches"]:
            for name in patch_files((root / patch).read_text()):
                original = source / name
                if original.is_file():
                    dest = target / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, dest)
        for patch in entry["patches"]:
            base = ["patch", "--batch", "--fuzz=0", "-p1", "-i", str(root / patch)]
            try:
                # --batch alone silently flips an unsuccessful reverse probe
                # back to forward application and can falsely claim inclusion.
                reverse = subprocess.run(base + ["--reverse", "--force", "--dry-run"], cwd=target,
                                         capture_output=True, text=True, timeout=5)
                if reverse.returncode == 0:
                    if entry["kind"] in ("customization", "test-only"):
                        return "review-required", f"upstream contains patch text: {patch}; retain policy/tests"
                    return "removal-candidate", f"upstream contains patch text: {patch}; NOT behavioral proof"
                forward = subprocess.run(base + ["--forward"], cwd=target,
                                         capture_output=True, text=True, timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                return "review-required", "patch tool unavailable/timed out"
            if forward.returncode or "offset" in forward.stdout:
                return "review-required", f"patch changed/conflicts: {patch}; NOT inclusion proof"
    return "applies-not-proof", "zero-fuzz/offset application succeeds; bug/removal behavior unproven"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--contracts", action="store_true")
    parser.add_argument("--only", action="append", default=[], help="entry ID (repeatable)")
    parser.add_argument("--source", action="append", default=[], help="source key=unmodified directory")
    parser.add_argument("--snapshot", action="store_true", help="print fingerprints; never accepts/writes a review")
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    Path("/tmp/opencode").mkdir(exist_ok=True)
    root = args.root.resolve()
    try:
        registry = json.loads((root / REGISTRY).read_text())
        validate(root, registry)
        current = snapshot(root, registry)
        if args.snapshot:
            print(json.dumps(current, indent=2, sort_keys=True))
            return 0
        baseline = json.loads((root / BASELINE).read_text())
        if args.only and set(args.only) - {e["id"] for e in registry["entries"]}:
            raise ValueError("Unknown --only entry")
        sources = dict(value.split("=", 1) for value in args.source)
        if set(sources) - {e.get("source") for e in registry["entries"]}:
            raise ValueError("Unknown --source key")
        pending = []
        for entry in registry["entries"]:
            if args.only and entry["id"] not in args.only:
                continue
            changed = [
                name for name in entry["inputs"]
                if current["inputs"].get(name) != baseline["inputs"].get(name)
            ] + [
                name for name in entry["watch"] + entry["patches"]
                if current["files"][name] != baseline["files"].get(name)
            ]
            pending.append((entry, changed))
        names = {
            entry["source"] for entry, changed in pending
            if entry.get("source") and (changed or args.all) and entry["source"] not in sources
        }
        error = ""
        if args.cached:
            resolved, error = cached_sources(root, names)
            sources = resolved | sources
        counts = Counter()
        for entry, changed in pending:
            source = sources.get(entry.get("source"))
            if source and (changed or args.all or args.source):
                status, detail = probe(root, entry, source, args.contracts)
            elif changed:
                status, detail = "review-required", error or "source not inspected"
            elif args.all:
                status, detail = "review-required", error or "no cached-source probe available"
            else:
                status, detail = "unchanged", "declared input/artifact fingerprints match; NOT upstream verification"
            counts[status] += 1
            suffix = f"; changed: {', '.join(changed)}" if changed else ""
            if status != "unchanged" or args.only:
                print(f"BACKPORT {entry['id']}: {status}; {detail}{suffix}")
        print("BACKPORT summary: " + "; ".join(f"{key}={value}" for key, value in sorted(counts.items())))
        if counts["unchanged"]:
            print("Unchanged fingerprints are NOT upstream verification.")
        print("Backport review is advisory; no fixes removed or reviews auto-accepted.")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"BACKPORT inventory-error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
