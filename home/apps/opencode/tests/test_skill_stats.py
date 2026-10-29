import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "scripts/skill-stats.py"
spec = importlib.util.spec_from_file_location("skill_stats", SOURCE)
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


class SkillStats(unittest.TestCase):
    def test_failed_skill_ids_cannot_emit_terminal_controls(self):
        self.assertEqual(stats.text("skill\x1b[2J\nname"), "skill\\u001b[2J\\nname")

    def test_native_namespace_filter_summary_and_private_examples(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            path = Path(tmp) / "opencode.db"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)")
                for index, (skill, status, sid, query) in enumerate([
                    ("discussion-map", "completed", "root", "PRIVATE\x1b[2J query"),
                    ("discussion-map", "error", "child", None),
                    ("opencode", "completed", "root", "another PRIVATE query"),
                ]):
                    row = {"version": 1, "time": index, "skill": skill, "status": status,
                           "sessionID": sid, "toolCallID": str(index), "queryID": "query" if query else None,
                           "lastQuery": query}
                    db.execute("INSERT INTO kv VALUES (?, ?)", (stats.PREFIX + str(index), json.dumps(row)))
                for key in [stats.PREFIX[:-1], stats.PREFIX[:-1] + "0", "other-plugin"]:
                    db.execute("INSERT INTO kv VALUES (?, ?)", (key, "{}"))
            before = path.read_bytes()
            def run(*args):
                return subprocess.check_output([sys.executable, str(SOURCE), "--db", str(path), *args], text=True)
            report = json.loads(run("--json"))
            self.assertNotIn("PRIVATE", json.dumps(report))
            self.assertEqual(report["skills"][0], {"skill": "discussion-map", "count": 2,
                             "completed": 1, "error": 1, "sessions": 2, "unknown_query": 1})
            selected = json.loads(run("--skill", "discussion-map", "--examples", "1", "--json"))
            self.assertEqual(len(selected["examples"]), 1)
            self.assertEqual(selected["examples"][0]["sessionID"], "child")
            text = run("--skill", "discussion-map", "--examples", "2")
            self.assertIn("PRIVATE", text)
            self.assertNotIn("\x1b", text, "query text must not emit terminal control sequences")
            self.assertEqual(path.read_bytes(), before, "report must not mutate the database")

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            path = Path(tmp) / "absent.db"
            text = subprocess.check_output([sys.executable, str(SOURCE), "--db", str(path), "--json"], text=True)
            self.assertEqual(json.loads(text), {"skills": []})
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
