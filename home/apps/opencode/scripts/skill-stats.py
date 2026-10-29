"""Read-only report of local.skill-stats native V2 plugin storage."""

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3


PLUGIN = "local.skill-stats"
PREFIX = "plugin:" + "".join(f"{ord(char):04x}" for char in PLUGIN) + ":calls/"


def records(db, skill=None):
    # Plugin storage is global, namespaced by plugin ID in the native KV table.
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='kv'").fetchone():
        return []
    rows = []
    for (value,) in db.execute(
        "SELECT value FROM kv WHERE key >= ? AND key < ?", (PREFIX, PREFIX[:-1] + "0")
    ):
        row = json.loads(value)
        if row.get("version") == 1 and (skill is None or row.get("skill") == skill):
            rows.append(row)
    return sorted(rows, key=lambda row: (row["time"], row["sessionID"], row["toolCallID"]))


def summary(rows):
    counts = Counter((row["skill"], row["status"]) for row in rows)
    return [
        {"skill": skill, "count": sum(count for (name, _), count in counts.items() if name == skill),
         "completed": counts[skill, "completed"], "error": counts[skill, "error"],
         "sessions": len({row["sessionID"] for row in rows if row["skill"] == skill}),
         "unknown_query": sum(row.get("queryID") is None for row in rows if row["skill"] == skill)}
        for skill in sorted({row["skill"] for row in rows})
    ]


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def text(value):
    # Skill IDs can come from failed tool input, not only trusted definitions.
    return json.dumps(value, ensure_ascii=False)[1:-1] if isinstance(value, str) else str(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    parser.add_argument("--db", type=Path, default=data / "opencode/opencode.db")
    parser.add_argument("--skill", help="filter by exact skill ID")
    parser.add_argument("--examples", type=positive, metavar="N", help="show N newest calls INCLUDING PRIVATE QUERY TEXT")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = []
    if args.db.exists():
        with closing(sqlite3.connect(args.db.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.execute("BEGIN")
            rows = records(db, args.skill)
    report = {"skills": summary(rows)}
    if args.examples:
        report["examples"] = list(reversed(rows[-args.examples:]))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("No recorded skill calls for this selection yet.")
        return
    print("SKILL\tCOUNT\tCOMPLETED\tERROR\tSESSIONS\tUNKNOWN_QUERY")
    for row in report["skills"]:
        print("\t".join(text(row[key]) for key in ("skill", "count", "completed", "error", "sessions", "unknown_query")))
    for row in report.get("examples", []):
        stamp = datetime.fromtimestamp(row["time"] / 1000, timezone.utc).isoformat()
        print(f"\n{stamp} {text(row['skill'])} [{text(row['status'])}] {text(row['sessionID'])} {text(row['toolCallID'])}")
        # JSON quoting prevents prompt text containing terminal escapes from executing.
        print("Query:", json.dumps(row.get("lastQuery"), ensure_ascii=False))


if __name__ == "__main__":
    main()
