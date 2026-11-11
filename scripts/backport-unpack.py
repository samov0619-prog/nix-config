"""Extract only allowlisted regular source files; called with an external timeout.

No links, modes, owners or archive-provided paths are installed. Limit each file
to 8 MiB and total output to 20 MiB; stream compressed archives and stop when the
requested set is complete. A mismatch/unsupported format is a review signal.
"""

import json
from pathlib import Path, PurePosixPath
import sys
import tarfile


def unpack(source, target, names):
    wanted = set(names)
    for name in wanted:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe allowlist path")
    total = 0
    with tarfile.open(source, "r|*") as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if ".." in parts or member.name.startswith("/"):
                continue
            candidates = [str(PurePosixPath(*parts))]
            if len(parts) > 1:
                candidates.append(str(PurePosixPath(*parts[1:])))
            name = next((p for p in candidates if p in wanted), None)
            if name is None or not member.isfile():
                continue
            total += member.size
            if member.size > 8 * 1024 * 1024 or total > 20 * 1024 * 1024:
                raise ValueError("Source extraction size limit exceeded")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Missing regular file payload")
            output = target / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(stream.read())
            wanted.remove(name)
            if not wanted:
                return
    raise ValueError(f"Missing source files: {sorted(wanted)}")


if __name__ == "__main__":
    unpack(Path(sys.argv[1]), Path(sys.argv[2]), json.loads(sys.argv[3]))
