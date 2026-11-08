#!/usr/bin/env python3
"""Small local fixtures; the rclone executable is always a fake."""

import fcntl
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SCRIPT = Path(__file__).with_name("backup-sync.py")
SPEC = importlib.util.spec_from_file_location("backup_sync", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BackupSyncTests(unittest.TestCase):
    def setUp(self):
        base = "/tmp/opencode" if Path("/tmp/opencode").is_dir() else None
        self.temporary = tempfile.TemporaryDirectory(prefix="ftb sync test ", dir=base)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "server with spaces" / "backups"
        self.source.mkdir(parents=True)
        self.result = self.root / "result.json"
        self.fake = self.root / "fake rclone"
        self.fake.write_text(
            f"#!{sys.executable}\n"
            "import json, os, pathlib, sys, zipfile\n"
            "args = sys.argv[1:]\n"
            "source = pathlib.Path(args[1])\n"
            "original = pathlib.Path(os.environ['FIXTURE_SOURCE'])\n"
            "if os.environ.get('FIXTURE_HOLD'):\n"
            "    print('fixture transfer ready', flush=True)\n"
            "    sys.stdin.read(1)\n"
            "names = sorted(p.name for p in source.iterdir())\n"
            "linked = all((source / n).stat().st_ino == (original / n).stat().st_ino\n"
            "             for n in names if n.endswith('.zip'))\n"
            "if os.environ.get('FIXTURE_ROTATE'):\n"
            "    for p in original.glob('*.zip'):\n"
            "        p.unlink()\n"
            "    (original / 'backups.json').write_text('[]')\n"
            "contents = {}\n"
            "for n in names:\n"
            "    if n.endswith('.zip'):\n"
            "        with zipfile.ZipFile(source / n) as archive:\n"
            "            contents[n] = archive.read('world/level.dat').decode()\n"
            "data = {'args': args, 'names': names, 'linked': linked,\n"
            "        'contents': contents,\n"
            "        'metadata': json.loads((source / 'backups.json').read_text())}\n"
            "pathlib.Path(os.environ['FIXTURE_RESULT']).write_text(json.dumps(data))\n"
            "sys.exit(int(os.environ.get('FIXTURE_EXIT', '0')))\n"
        )
        self.fake.chmod(0o700)

    def manifest(self, entries):
        (self.source / "backups.json").write_text(json.dumps({"backups": entries}))

    def archive(self, name="2026-11-8_12-0-0.zip", complete=True):
        path = self.source / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("world/level.dat", "fixture world")
        return {
            "backupLocation": f"./backups/{name}",
            "backupFormat": "ZIP",
            "complete": complete,
            "size": path.stat().st_size,
            "sha1": hashlib.sha1(path.read_bytes()).hexdigest(),
        }

    def run_guard(self, **extra):
        environment = os.environ.copy()
        environment.update(
            FIXTURE_SOURCE=str(self.source), FIXTURE_RESULT=str(self.result)
        )
        environment.update(extra)
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                str(self.source),
                "fixture:backups",
                "--rclone",
                str(self.fake),
            ],
            capture_output=True,
            text=True,
            env=environment,
            timeout=10,
            check=False,
        )

    def assert_blocked(self):
        result = self.run_guard()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Backup sync blocked:", result.stderr)
        self.assertFalse(self.result.exists())

    def test_missing_source(self):
        self.source.rmdir()
        self.assert_blocked()

    def test_empty_source(self):
        self.assert_blocked()

    def test_metadata_only_and_empty_ftb_list(self):
        for data in [{"backups": []}, []]:
            with self.subTest(data=data):
                (self.source / "backups.json").write_text(json.dumps(data))
                self.assert_blocked()

    def test_truncated_metadata(self):
        (self.source / "backups.json").write_text('{"backups": [')
        self.assert_blocked()

    def test_incomplete_entry_defers_entire_set(self):
        self.manifest(
            [self.archive(), self.archive("2026-11-8_12-30-0.zip", complete=False)]
        )
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("incomplete backup", result.stderr)
        self.assertFalse(self.result.exists())

    def test_ready_set_uses_snapshot_and_preserves_sync_policy(self):
        entries = [self.archive(), self.archive("2026-11-8_12-30-0.zip")]
        self.manifest(entries)
        before = {p.name: p.read_bytes() for p in self.source.iterdir()}
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.result.read_text())
        self.assertEqual(data["names"], sorted(before))
        self.assertEqual(data["metadata"], {"backups": entries})
        self.assertTrue(data["linked"])
        self.assertEqual(data["args"][0], "sync")
        self.assertEqual(data["args"][2], "fixture:backups")
        for flag in ["--check-first", "--delete-after", "--drive-use-trash=true"]:
            self.assertIn(flag, data["args"])
        self.assertEqual(data["args"][data["args"].index("--bwlimit") + 1], "2200k")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.source.iterdir()})
        self.assertFalse(Path(data["args"][1]).exists())

    def test_existing_paths_are_rebased_to_local_backup_directory(self):
        entry = self.archive()
        entry["backupLocation"] = "/previous-host/server/backups/" + Path(
            entry["backupLocation"]
        ).name
        del entry["complete"]
        self.manifest([entry])
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.result.exists())

    def test_invalid_entry_fields(self):
        entry = self.archive()
        for changes in [
            {"size": entry["size"] + 1},
            {"size": True},
            {"sha1": ""},
            {"backupFormat": "ZSTD"},
            {"backupLocation": "../outside.zip"},
            {"complete": "true"},
        ]:
            with self.subTest(changes=changes):
                self.manifest([entry | changes])
                self.assert_blocked()

    def test_invalid_zip_even_with_final_metadata(self):
        entry = self.archive()
        path = self.source / Path(entry["backupLocation"]).name
        path.write_bytes(b"incomplete zip payload")
        entry["size"] = path.stat().st_size
        self.manifest([entry])
        self.assert_blocked()

    def test_duplicate_or_missing_archive(self):
        entry = self.archive()
        self.manifest([entry, entry])
        self.assert_blocked()
        self.manifest([entry])
        (self.source / Path(entry["backupLocation"]).name).unlink()
        self.assert_blocked()

    def test_untracked_files_are_not_silently_filtered_out(self):
        self.manifest([self.archive()])
        (self.source / "untracked.zip").write_bytes(b"still being written")
        self.assert_blocked()

    def test_symlinks_are_not_followed(self):
        entry = self.archive()
        path = self.source / Path(entry["backupLocation"]).name
        outside = self.root / "outside.zip"
        path.rename(outside)
        path.symlink_to(outside)
        self.manifest([entry])
        self.assert_blocked()
        path.unlink()
        outside.rename(path)
        metadata = self.source / "backups.json"
        metadata.rename(self.root / "metadata.json")
        metadata.symlink_to(self.root / "metadata.json")
        self.assert_blocked()

    def test_rotation_during_transfer_cannot_remove_staged_archive(self):
        self.manifest([self.archive()])
        result = self.run_guard(FIXTURE_ROTATE="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.result.read_text())
        self.assertEqual(list(data["contents"].values()), ["fixture world"])
        self.assertEqual(list(self.source.glob("*.zip")), [])

    def test_metadata_change_during_preparation_defers(self):
        self.manifest([self.archive()])
        snapshot = self.root / "snapshot"
        snapshot.mkdir()
        link = os.link

        def change_metadata(*args, **kwargs):
            link(*args, **kwargs)
            with (self.source / "backups.json").open("a") as stream:
                stream.write("\n")

        with patch.object(MODULE.os, "link", side_effect=change_metadata):
            with self.assertRaises(MODULE.NotReady):
                MODULE.prepare_snapshot(self.source, snapshot)

    def test_rclone_failure_is_propagated_and_snapshot_removed(self):
        self.manifest([self.archive()])
        result = self.run_guard(FIXTURE_EXIT="7")
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertFalse((self.source.parent / ".ftb-backup-sync/snapshot").exists())
        self.assertTrue(list(self.source.glob("*.zip")))

    def test_stale_managed_snapshot_is_cleaned_after_crash(self):
        self.manifest([self.archive()])
        cache = MODULE.cache_directory(self.source)
        snapshot = cache / "snapshot"
        snapshot.mkdir()
        (snapshot / "leftover").write_text("old staging content")
        result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("leftover", json.loads(self.result.read_text())["names"])
        self.assertFalse(snapshot.exists())

    def test_unmanaged_cache_is_not_deleted(self):
        self.manifest([self.archive()])
        cache = self.source.parent / ".ftb-backup-sync"
        cache.mkdir(mode=0o700)
        sentinel = cache / "user-work"
        sentinel.write_text("preserve")
        self.assert_blocked()
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_concurrent_invocation_does_not_touch_active_snapshot(self):
        self.manifest([self.archive()])
        cache = MODULE.cache_directory(self.source)
        with (cache / "lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already running", result.stderr)
        self.assertFalse(self.result.exists())

    def test_unsupported_layout_and_empty_zip_are_blocked(self):
        entry = self.archive()
        self.manifest([entry])
        extra = self.source / "custom-backup-directory"
        extra.mkdir()
        self.assert_blocked()
        extra.rmdir()
        archive = self.source / Path(entry["backupLocation"]).name
        with zipfile.ZipFile(archive, "w"):
            pass
        entry["size"] = archive.stat().st_size
        self.manifest([entry])
        self.assert_blocked()

    def test_source_directory_link_is_blocked(self):
        self.manifest([self.archive()])
        original = self.source.with_name("original-backups")
        self.source.rename(original)
        self.source.symlink_to(original, target_is_directory=True)
        self.assert_blocked()

    def test_cache_link_and_public_cache_are_blocked(self):
        self.manifest([self.archive()])
        outside = self.root / "outside-cache"
        outside.mkdir(mode=0o700)
        sentinel = outside / "preserve"
        sentinel.write_text("untouched")
        cache = self.source.parent / ".ftb-backup-sync"
        cache.symlink_to(outside, target_is_directory=True)
        self.assert_blocked()
        self.assertEqual(sentinel.read_text(), "untouched")
        cache.unlink()
        cache = MODULE.cache_directory(self.source)
        cache.chmod(0o755)
        self.assert_blocked()

    def test_managed_cache_does_not_follow_internal_links(self):
        self.manifest([self.archive()])
        cache = MODULE.cache_directory(self.source)
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "preserve"
        sentinel.write_text("untouched")
        for name in ["owner", "lock", "snapshot"]:
            with self.subTest(name=name):
                path = cache / name
                if name == "owner":
                    path.unlink()
                    target = outside / "owner"
                    target.write_text(MODULE.MARKER)
                else:
                    target = outside
                path.symlink_to(target)
                self.assert_blocked()
                path.unlink()
                if name == "owner":
                    path.write_text(MODULE.MARKER)
                self.assertEqual(sentinel.read_text(), "untouched")

    def test_fifo_lock_is_blocked_without_hanging(self):
        self.manifest([self.archive()])
        cache = MODULE.cache_directory(self.source)
        os.mkfifo(cache / "lock")
        self.assert_blocked()

    def test_link_failure_does_not_start_transfer_and_cleans_snapshot(self):
        self.manifest([self.archive()])
        with patch.object(
            MODULE.os, "link", side_effect=OSError(errno.EXDEV, "fixture link failure")
        ):
            with patch.object(MODULE.subprocess, "run") as run:
                with self.assertRaises(OSError):
                    MODULE.sync(self.source, "fixture:backups", str(self.fake))
                run.assert_not_called()
        self.assertFalse((self.source.parent / ".ftb-backup-sync/snapshot").exists())
        self.assertTrue(list(self.source.glob("*.zip")))

    def test_archive_change_during_preparation_defers(self):
        self.manifest([self.archive()])
        snapshot = self.root / "snapshot"
        snapshot.mkdir()
        link = os.link

        def change_archive(original, staged, **kwargs):
            link(original, staged, **kwargs)
            with original.open("ab") as stream:
                stream.write(b"changed after complete")

        with patch.object(MODULE.os, "link", side_effect=change_archive):
            with self.assertRaises(MODULE.NotReady):
                MODULE.prepare_snapshot(self.source, snapshot)

    def test_orphaned_transfer_keeps_lock_until_it_exits(self):
        self.manifest([self.archive()])
        environment = os.environ.copy()
        environment.update(
            FIXTURE_SOURCE=str(self.source),
            FIXTURE_RESULT=str(self.result),
            FIXTURE_HOLD="1",
        )
        process = subprocess.Popen(
            [sys.executable, "-B", str(SCRIPT), str(self.source), "fixture:backups",
             "--rclone", str(self.fake)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            start_new_session=True,
        )

        def stop_fixture_processes():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate(timeout=10)

        self.addCleanup(stop_fixture_processes)
        self.assertEqual(process.stdout.readline(), b"fixture transfer ready\n")
        process.kill()
        process.wait(timeout=10)
        deferred = self.run_guard()
        self.assertEqual(deferred.returncode, 0, deferred.stderr)
        self.assertIn("already running", deferred.stderr)
        snapshot = self.source.parent / ".ftb-backup-sync/snapshot"
        self.assertTrue(snapshot.is_dir())
        process.communicate(input=b"x", timeout=10)
        self.assertTrue(self.result.exists())
        self.assertTrue(snapshot.is_dir())
        recovered = self.run_guard()
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertFalse(snapshot.exists())


if __name__ == "__main__":
    unittest.main()
