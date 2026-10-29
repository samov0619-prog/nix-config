import importlib.util
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("report", Path(__file__).parents[1] / "scripts/task-report.py")
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

    def test_retried_steps_replace_last_message_tokens_without_double_counting(self):
        for index, n in enumerate([7, 10]):
            self.db.execute("INSERT INTO part VALUES (?,?,?,?,?)", (
                f"step{index}", "a1", "root", 10,
                json.dumps({"type": "step-finish", "tokens": self.assistant(n)["tokens"]})))
        result = module.report(self.db, "root", self.path)
        self.assertEqual(result["totals"]["input"], 17 + 20 + 30)
        self.assertEqual(result["totals"]["assistant_messages"], 3)
        self.assertEqual(result["totals"]["recorded_steps"], 4)

    def test_compaction_errors_routes_and_retry_counts(self):
        info = {**self.assistant(8), "agent": "compaction", "variant": "max", "summary": True,
                "error": {"name": "APIError"}}
        self.message("summary", "root", 120, info)
        for kind in ["compaction", "retry"]:
            self.db.execute("INSERT INTO part VALUES (?,?,?,?,?)", (
                kind, "summary", "root", 120, json.dumps({"type": kind})))
        result = module.report(self.db, "root", self.path)
        self.assertEqual(result["by_route"]["compaction|p/m|max"]["input"], 8)
        self.assertEqual(result["compactions"], 1)
        self.assertEqual(result["summary_messages"], 1)
        self.assertEqual(result["retry_parts"], 1)
        self.assertEqual(result["failed_messages"], 1)
        self.assertFalse(result["full_task_usage_complete"])

    def test_readonly_connection_rejects_writes_and_preserves_database(self):
        target = self.path / "existing.db"
        with closing(sqlite3.connect(target)) as db:
            db.execute("CREATE TABLE example(value TEXT)")
        before = target.read_bytes()
        with closing(module.connect(target)) as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("INSERT INTO example VALUES ('no')")
        self.assertEqual(target.read_bytes(), before)

    def test_v2_messages_compaction_and_children_take_precedence_over_legacy_copy(self):
        self.db.executescript("""
          CREATE TABLE session_v2(id TEXT, parent_id TEXT, time_created INTEGER);
          CREATE TABLE session_message(id TEXT, session_id TEXT, type TEXT, seq INTEGER, time_created INTEGER, data TEXT);
          INSERT INTO session_v2 VALUES ('root',NULL,0), ('child','root',11);
        """)
        def message(mid, sid, kind, seq, **data):
            self.db.execute("INSERT INTO session_message VALUES (?,?,?,?,?,?)",
                            (mid, sid, kind, seq, seq, json.dumps(data)))
        ref = {"providerID": "opencode", "id": "big-pickle"}
        message("u", "root", "user", 1, text="private prompt")
        message("a", "root", "assistant", 10, model=ref, agent="build", time={"completed": 99},
                tokens=self.assistant(10)["tokens"], cost=0,
                content=[{"type": "tool", "name": "read", "state": {
                    "status": "completed", "content": [{"type": "text", "text": "private output"}]}},
                         {"type": "text", "text": "result"}])
        message("c", "child", "assistant", 12, model=ref, agent="explore", time={"completed": 99},
                tokens=self.assistant(20)["tokens"], cost=0, content=[])
        message("compact", "root", "compaction", 14, model=ref, status="completed",
                summary="private summary", tokens=self.assistant(5)["tokens"], cost=0)
        result = module.report(self.db, "root", self.path)
        self.assertEqual(result["storage"], "v2")
        self.assertEqual(result["totals"]["input"], 35)
        self.assertEqual(result["compactions"], 1)
        self.assertEqual(result["tools"]["read"]["stored_output_chars"], 14)
        self.assertEqual(result["by_model"]["opencode/big-pickle"]["input"], 35)
        self.assertNotIn("private", json.dumps(result))

    def test_recent_sessions_merge_versions_without_duplicate_legacy_copies(self):
        self.db.executescript("""
          ALTER TABLE session ADD COLUMN version TEXT DEFAULT '1';
          ALTER TABLE session ADD COLUMN time_updated INTEGER DEFAULT 1;
          CREATE TABLE session_v2(id TEXT, parent_id TEXT, version TEXT, time_updated INTEGER);
          INSERT INTO session_v2 VALUES ('root',NULL,'2',10), ('new','root','2',20);
        """)
        rows = module.recent_sessions(self.db, 3)
        self.assertEqual([row["id"] for row in rows], ["new", "root", "native"])
        self.assertEqual(rows[1]["version"], "2")
        self.assertEqual(len(module.recent_sessions(self.db, 1)), 1)

    def test_model_calls_include_title_children_and_attempts_without_adding_tokens(self):
        calls = self.path / "calls"
        calls.mkdir()
        base = {"version": 1, "sessionID": "root", "event": "attempt", "kind": "title", "agent": "build",
                "providerID": "openai", "modelID": "alias", "wireModel": "gpt-6-luna", "variant": "low",
                "effort": "low", "transport": "http", "prompt": "PRIVATE"}
        title = {**base, "id": "title", "time": 5}
        retry = {**base, "id": "retry", "time": 6}
        rows = [title, title, {**base, "event": "response", "id": "title", "time": 101, "status": 429}, retry,
                {**base, "event": "response", "id": "retry", "time": 102, "status": 200},
                {**base, "id": "generate", "kind": "generate", "time": 110}]
        (calls / "root.jsonl").write_text("\n".join(map(json.dumps, rows)) + '\n{"partial":')
        (calls / "native.jsonl").write_text(json.dumps({**base, "id": "ws", "sessionID": "native", "time": 12,
                                                     "kind": "primary", "agent": "explore", "transport": "websocket"}))
        # Other sessions are not scanned/attributed.
        (calls / "foreign.jsonl").write_text(json.dumps({**base, "id": "foreign", "time": 8}))
        result = module.report(self.db, "root", self.path, calls_dir=calls)
        self.assertEqual(result["totals"], module.report(self.db, "root", self.path)["totals"])
        self.assertEqual(result["observed_model_attempts"], 4)
        first = result["model_calls"][0]
        self.assertEqual(first["http_status"], 429)
        self.assertEqual(first["wireModel"], "gpt-6-luna")
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertTrue(any("Unreadable/unsupported model-call" in warning for warning in result["warnings"]))
        turn = module.report(self.db, "root", self.path, "u1", calls_dir=calls)
        self.assertEqual(turn["observed_model_attempts"], 3)
        self.assertEqual(turn["model_calls"][0]["http_status"], 429, "response time must not move call into another turn")
        last = module.report(self.db, "root", self.path, "last", calls_dir=calls)
        self.assertEqual(last["observed_model_attempts"], 1)
        self.assertEqual(last["model_calls"][0]["observation"], "dispatch_hook_only")

    def test_empty_session_or_absent_journal_does_not_invent_historical_calls(self):
        self.db.execute("INSERT INTO session VALUES ('empty',NULL,0)")
        result = module.report(self.db, "empty", self.path, calls_dir=self.path / "absent")
        self.assertEqual(result["model_calls"], [])
        self.assertEqual(result["observed_model_attempts"], 0)
        self.assertTrue(any("No model-call journal" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
