#!/usr/bin/env python3
"""Sync a completed FTB Backups 2 ZIP set, never a live or empty directory."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import zipfile


MARKER = "minecraft-ftb-backup-sync-v1\n"


class UnsafeSource(Exception):
    pass


class NotReady(Exception):
    pass


def regular_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise UnsafeSource("source files must be regular files, not links")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_manifest(source):
    manifest = source / "backups.json"
    identity = regular_file(manifest)
    raw = manifest.read_bytes()
    if regular_file(manifest) != identity:
        raise NotReady("backup metadata changed while reading")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise UnsafeSource("backups.json is not valid JSON") from error
    if not isinstance(data, dict) or not isinstance(data.get("backups"), list):
        raise UnsafeSource("backups.json must contain an FTB backups list")
    if not data["backups"]:
        raise UnsafeSource("no completed archives; refusing to sync")

    archives = {}
    for entry in data["backups"]:
        if not isinstance(entry, dict):
            raise UnsafeSource("invalid backup entry")
        # FTB 1.0.29 defaults missing complete fields to true for older entries.
        complete = entry.get("complete", True)
        if complete is False:
            raise NotReady("FTB has an incomplete backup; waiting for completion")
        if complete is not True or entry.get("backupFormat") != "ZIP":
            raise UnsafeSource("only completed ZIP backups are supported")
        location = entry.get("backupLocation")
        if (
            not isinstance(location, str)
            or not location
            or "\\" in location
            or any(ord(character) < 32 for character in location)
            or ".." in Path(location).parts
        ):
            raise UnsafeSource("invalid backup location")
        # Rebase paths from a previous host, never open a path from the JSON.
        name = Path(location).name
        if not name.endswith(".zip") or name in archives:
            raise UnsafeSource("invalid or duplicate archive name")
        size = entry.get("size")
        checksum = entry.get("sha1")
        if type(size) is not int or size <= 0:
            raise UnsafeSource("archive size is missing or invalid")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", checksum):
            raise UnsafeSource("completed archive SHA-1 is missing or invalid")
        archives[name] = size
    return raw, identity, archives


def prepare_snapshot(source, snapshot):
    raw, manifest_identity, archives = read_manifest(source)
    expected = set(archives) | {"backups.json"}
    if {path.name for path in source.iterdir()} != expected:
        raise UnsafeSource("directory and metadata disagree; refusing partial sync")

    identities = {}
    for name, expected_size in archives.items():
        original = source / name
        identity = regular_file(original)
        if identity[2] != expected_size:
            raise UnsafeSource("archive size does not match completed metadata")
        staged = snapshot / name
        os.link(original, staged, follow_symlinks=False)
        if regular_file(staged) != identity:
            raise NotReady("archive changed while preparing snapshot")
        try:
            # Read the central directory, not every compressed world byte.
            with zipfile.ZipFile(staged) as archive:
                if not archive.infolist():
                    raise UnsafeSource("empty ZIP is not a world backup")
        except zipfile.BadZipFile as error:
            raise UnsafeSource("archive has no valid ZIP central directory") from error
        identities[name] = identity

    if (
        regular_file(source / "backups.json") != manifest_identity
        or (source / "backups.json").read_bytes() != raw
        or {path.name for path in source.iterdir()} != expected
        or any(regular_file(source / name) != identity for name, identity in identities.items())
        or any(regular_file(snapshot / name) != identity for name, identity in identities.items())
    ):
        raise NotReady("backup set changed while preparing snapshot")
    (snapshot / "backups.json").write_bytes(raw)


def cache_directory(source):
    cache = source.parent / ".ftb-backup-sync"
    try:
        cache.mkdir(mode=0o700)
    except FileExistsError:
        pass
    else:
        (cache / "owner").write_text(MARKER)
    info = cache.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
        or not stat.S_ISREG((cache / "owner").lstat().st_mode)
        or (cache / "owner").read_text() != MARKER
    ):
        raise UnsafeSource("staging cache is not a private, owned sync directory")
    return cache


def sync(source, destination, rclone):
    if not stat.S_ISDIR(source.lstat().st_mode):
        raise UnsafeSource("backup source must be a directory, not a link")
    cache = cache_directory(source)
    descriptor = os.open(
        cache / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600
    )
    with os.fdopen(descriptor, "w") as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise UnsafeSource("staging lock must be a regular file")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise NotReady("another backup sync is already running") from error
        snapshot = cache / "snapshot"
        # Recover only our marked cache after a killed transfer; never touch source.
        if snapshot.exists() or snapshot.is_symlink():
            if not stat.S_ISDIR(snapshot.lstat().st_mode):
                raise UnsafeSource("staging snapshot is not a directory")
            shutil.rmtree(snapshot)
        snapshot.mkdir(mode=0o700)
        try:
            prepare_snapshot(source, snapshot)
            result = subprocess.run(
                [
                    rclone,
                    "sync",
                    str(snapshot),
                    destination,
                    "--bwlimit",
                    "2200k",
                    "--quiet",
                    "--check-first",
                    "--delete-after",
                    "--drive-use-trash=true",
                ],
                check=False,
                # Keep staging locked if only the wrapper is killed during upload.
                pass_fds=(lock.fileno(),),
            )
            return result.returncode
        finally:
            shutil.rmtree(snapshot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination")
    parser.add_argument("--rclone", required=True)
    args = parser.parse_args()
    try:
        return sync(args.source.absolute(), args.destination, args.rclone)
    except NotReady as error:
        print(f"Backup sync deferred: {error}", file=sys.stderr)
        return 0
    except (UnsafeSource, OSError) as error:
        print(f"Backup sync blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
