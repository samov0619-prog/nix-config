import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("report", Path(__file__).parents[1] / "task-report.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE session(id TEXT, parent_id TEXT, time_created INTEGER);
          CREATE TABLE message(id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
          CREATE TABLE part(id TEXT, message_id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
          INSERT INTO session VALUES ('root',NULL,0), ('native','root',11);
        """)
        self.message("u1", "root", 1, {"role": "user"})
        self.message("a1", "root", 10, self.assistant(10))
        self.message("n1", "native", 12, self.assistant(20))
        self.message("u2", "root", 100, {"role": "user"})
        self.message("a2", "root", 110, self.assistant(30))
        for pid, mid, output, tool in [("p1", "a1", "same", "read"), ("p2", "a1", "same", "read"),
                                       ("p3", "a1", "answer", "rlm_subquery")]:
            self.db.execute("INSERT INTO part VALUES (?,?,?,?,?)", (pid, mid, "root", 10, json.dumps({
                "type": "tool", "tool": tool, "state": {"status": "completed", "output": output}})))

    @staticmethod
    def assistant(n):
        return {"role": "assistant", "providerID": "p", "modelID": "m", "time": {"completed": 99},
                "tokens": {"input": n, "output": 2, "reasoning": 3, "cache": {"read": 100, "write": 4}}, "cost": 0}

    def message(self, mid, sid, ts, info):
        self.db.execute("INSERT INTO message VALUES (?,?,?,?)", (mid, sid, ts, json.dumps(info)))

    def ledger(self):
        (self.path / "child.json").write_text(json.dumps({"version": 1, "parentSessionID": "root",
            "childSessionID": "child", "started": 15, "messages": [{"id": "c1", **self.assistant(40)}]}))

    def test_counts_children_and_cache_without_double_counting_step_parts(self):
        self.ledger()
        result = module.report(self.db, "root", self.path)
        self.assertEqual(result["totals"]["input"], 100)
        self.assertEqual(result["processed_input_tokens"], 100 + 4 * 104)
        self.assertEqual(result["processed_total_tokens"], 100 + 4 * 109)
        self.assertEqual(result["root_tokens"]["input"], 40)
        self.assertEqual(result["tools"]["read"]["exact_repeat_chars"], 4)
        self.assertEqual(result["unaccounted_rlm_calls"], 0)

    def test_retained_child_and_ledger_not_double_counted(self):
        self.ledger()
        self.db.execute("INSERT INTO session VALUES ('child',NULL,15)")
        self.message("c1", "child", 16, self.assistant(40))
        self.assertEqual(module.report(self.db, "root", self.path)["totals"]["input"], 100)

    def test_turn_bounds_and_missing_historical_subquery(self):
        first = module.report(self.db, "root", self.path, "u1")
        self.assertEqual(first["totals"]["input"], 30)
        self.assertEqual(first["unaccounted_rlm_calls"], 1)
        last = module.report(self.db, "root", self.path, "last")
        self.assertEqual(last["totals"]["input"], 30)
        self.assertEqual(last["sessions"], ["root"])

    def test_readonly_missing_database_not_created(self):
        target = self.path / "absent.db"
        with self.assertRaises(sqlite3.OperationalError):
            module.connect(target)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
