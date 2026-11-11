"""Synthetic inventory/source/update scenarios; no real updates/builds/network."""

import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("backport_review", HERE / "backport-review.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)
UNPACK = importlib.util.spec_from_file_location("backport_unpack", HERE / "backport-unpack.py")
unpack = importlib.util.module_from_spec(UNPACK)
UNPACK.loader.exec_module(unpack)
DIFF = """--- a/src/unit.c
+++ b/src/unit.c
@@ -1 +1 @@
-old
+fixed
"""


class ReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="backport-fixture-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("flake.lock", json.dumps({
            "root": "root", "nodes": {
                "root": {"inputs": {"nixpkgs": "stable", "alias": ["nixpkgs"]}},
                "stable": {"locked": {"rev": "original"}},
            },
        }))
        self.entry = {
            "id": "fix", "kind": "local-bugfix", "inputs": ["nixpkgs"],
            "watch": ["package.nix"], "patches": ["fix.patch"],
            "source": "fixture", "details": "README.md",
        }
        self.registry = {"schema": 1, "entries": [self.entry]}
        self.write("package.nix", "package.overrideAttrs (_: {})")
        self.write("fix.patch", DIFF)
        self.write("README.md", "Fixture removal requirements")
        self.write(review.REGISTRY, json.dumps(self.registry))
        self.write(review.BASELINE, json.dumps(review.snapshot(self.root, self.registry)))
        self.source = self.root / "upstream"
        self.write("upstream/src/unit.c", "old\n")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def command(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(HERE / "backport-review.py"),
             "--root", str(self.root), *args],
            capture_output=True, text=True, timeout=10,
        )

    def test_unchanged_is_not_claimed_verified(self):
        result = self.command()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unchanged", result.stdout)
        self.assertIn("NOT upstream verification", result.stdout)

    def test_lock_change_is_reported(self):
        lock = json.loads((self.root / "flake.lock").read_text())
        lock["nodes"]["stable"]["locked"]["rev"] = "updated"
        self.write("flake.lock", json.dumps(lock))
        result = self.command()
        self.assertIn("review-required", result.stdout)
        self.assertIn("changed: nixpkgs", result.stdout)

    def test_inline_edit_is_reported(self):
        self.write("package.nix", "package.overrideAttrs (_: { changed = true; })")
        self.assertIn("changed: package.nix", self.command().stdout)

    def test_unregistered_patch_blocks(self):
        self.write("missing.patch", DIFF)
        result = self.command()
        self.assertEqual(result.returncode, 1)
        self.assertIn("coverage mismatch", result.stderr)

    def test_unregistered_inline_transform_blocks(self):
        self.write("other.nix", "substituteInPlace upstream")
        result = self.command()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unregistered source transformation", result.stderr)

    def test_archived_patch_excluded(self):
        self.write("archive/retired.patch", DIFF)
        self.assertEqual(self.command().returncode, 0)

    def test_follows_fingerprinted(self):
        snap = review.snapshot(self.root, self.registry)
        self.assertEqual(snap["inputs"]["nixpkgs"], snap["inputs"]["alias"])

    def test_unknown_input_is_error(self):
        self.entry["inputs"] = ["typo"]
        with self.assertRaisesRegex(ValueError, "Unknown watched input"):
            review.snapshot(self.root, self.registry)

    def test_unknown_source_is_error(self):
        result = self.command("--source", f"typo={self.source}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown --source key", result.stderr)

    def test_forward_application_is_not_proof(self):
        before = (self.source / "src/unit.c").read_bytes()
        result = self.command("--source", f"fixture={self.source}")
        self.assertIn("applies-not-proof", result.stdout)
        self.assertEqual((self.source / "src/unit.c").read_bytes(), before)

    def test_reverse_match_is_candidate_only(self):
        self.write("upstream/src/unit.c", "fixed\n")
        result = self.command("--source", f"fixture={self.source}")
        self.assertIn("removal-candidate", result.stdout)
        self.assertIn("NOT behavioral proof", result.stdout)
        self.assertTrue((self.root / "fix.patch").is_file())

    def test_customizations_not_auto_obsolete(self):
        self.entry["kind"] = "customization"
        self.write("upstream/src/unit.c", "fixed\n")
        status, detail = review.probe(self.root, self.entry, self.source, False)
        self.assertEqual(status, "review-required")
        self.assertIn("retain policy/tests", detail)

    def test_patch_conflict_not_inclusion(self):
        self.write("upstream/src/unit.c", "third implementation\n")
        result = self.command("--source", f"fixture={self.source}")
        self.assertIn("review-required", result.stdout)
        self.assertIn("NOT inclusion proof", result.stdout)

    def test_contract_pass_is_candidate(self):
        self.write("contract.py", "pass")
        self.entry["contract"] = ["contract.py", "{source}"]
        with patch.object(review.shutil, "which", return_value="cc"):
            status, _ = review.probe(self.root, self.entry, self.source, True)
        self.assertEqual(status, "removal-candidate")

    def test_contract_failure_is_unknown(self):
        self.write("contract.py", "raise RuntimeError('API changed')")
        self.entry["contract"] = ["contract.py", "{source}"]
        with patch.object(review.shutil, "which", return_value="cc"):
            status, detail = review.probe(self.root, self.entry, self.source, True)
        self.assertEqual(status, "review-required")
        self.assertIn("failed", detail)

    def test_missing_compiler_not_success(self):
        self.entry["contract"] = ["contract.py", "{source}"]
        with patch.object(review.shutil, "which", return_value=None):
            status, detail = review.probe(self.root, self.entry, self.source, True)
        self.assertEqual(status, "review-required")
        self.assertIn("not run", detail)

    def test_source_eval_timeout_not_success(self):
        with patch.object(review.subprocess, "run", side_effect=subprocess.TimeoutExpired("nix", 20)):
            sources, error = review.cached_sources(self.root, {"fixture"})
        self.assertEqual(sources, {})
        self.assertIn("timed out", error)

    def test_archive_extracts_only_selected_regular_files(self):
        archive = self.root / "source.tar.gz"
        with tarfile.open(archive, "w:gz") as out:
            for name in ("source/src/unit.c", "source/unwanted", "../escape"):
                member = tarfile.TarInfo(name)
                member.size = 4
                out.addfile(member, io.BytesIO(b"old\n"))
        target = self.root / "extracted"
        unpack.unpack(archive, target, ["src/unit.c"])
        self.assertEqual((target / "src/unit.c").read_text(), "old\n")
        self.assertFalse((target / "unwanted").exists())
        self.assertFalse((self.root / "escape").exists())

    def test_archive_probe_uses_real_checker(self):
        self.write("scripts/backport-unpack.py", (HERE / "backport-unpack.py").read_text())
        archive = self.root / "source.tar"
        with tarfile.open(archive, "w") as out:
            member = tarfile.TarInfo("source/src/unit.c")
            member.size = 4
            out.addfile(member, io.BytesIO(b"old\n"))
        status, _ = review.probe(self.root, self.entry, archive, False)
        self.assertEqual(status, "applies-not-proof")

    def test_archive_inline_contract_uses_explicit_files(self):
        self.write("scripts/backport-unpack.py", (HERE / "backport-unpack.py").read_text())
        self.write("contract.py", "import pathlib, sys\nassert (pathlib.Path(sys.argv[1]) / 'src/unit.c').read_text() == 'old\\n'\n")
        self.entry["patches"] = []
        self.entry["sourceFiles"] = ["src/unit.c"]
        self.entry["contract"] = ["contract.py", "{source}"]
        archive = self.root / "source.tar"
        with tarfile.open(archive, "w") as out:
            member = tarfile.TarInfo("source/src/unit.c")
            member.size = 4
            out.addfile(member, io.BytesIO(b"old\n"))
        with patch.object(review.shutil, "which", return_value="cc"):
            status, _ = review.probe(self.root, self.entry, archive, True)
        self.assertEqual(status, "removal-candidate")

    def test_linux_contract_is_explicitly_skipped_elsewhere(self):
        self.entry["platform"] = "linux"
        with patch.object(review.sys, "platform", "darwin"):
            status, detail = review.probe(self.root, self.entry, self.source, True)
        self.assertEqual(status, "review-required")
        self.assertIn("requires Linux", detail)

    def test_archive_allowlist_cannot_escape(self):
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            unpack.unpack(self.root / "absent", self.root / "extract", ["../escape"])


if __name__ == "__main__":
    unittest.main()
