"""Cheap unit checks of the scripted fixture, not native OpenCode execution."""

import unittest
from unittest.mock import patch

from test_delegated_review_runtime import RecoveryMock, main


def parent(text=""):
    return {
        "tools": [{"name": "subagent"}],
        "input": "Orchestrate an independent review of fixture.txt " + text,
    }


def child():
    return {
        "tools": [{"name": "read"}],
        "input": "DR_CHILD_SCOPE_V1 DR_PRESERVED_READ_EVIDENCE",
    }


class FixtureTests(unittest.TestCase):
    def test_setup_failure_closes_provider_without_starting_it(self):
        with (
            patch("test_delegated_review_runtime.ThreadingHTTPServer") as server,
            patch("test_delegated_review_runtime.run_fixture", side_effect=KeyError("setup")),
        ):
            with self.assertRaisesRegex(KeyError, "setup"):
                main(__file__)
            server.return_value.__exit__.assert_called_once()
            server.return_value.__enter__.return_value.serve_forever.assert_not_called()

    def test_one_native_retry_does_not_create_an_orchestration_retry(self):
        RecoveryMock.reset("native", "/fixture.txt")
        RecoveryMock.decide(parent())
        self.assertEqual(RecoveryMock.next_tool[0], "subagent")
        RecoveryMock.decide(child())
        self.assertEqual(RecoveryMock.next_tool[0], "read")
        RecoveryMock.decide(child())
        self.assertTrue(RecoveryMock.fail_next)
        self.assertEqual(RecoveryMock.fail_status, 429)
        RecoveryMock.decide(child())
        self.assertIn("DR_CHILD_COMPLETE", RecoveryMock.reply)
        RecoveryMock.decide(parent("DR_CHILD_COMPLETE"))
        self.assertIn("DR_PARENT_COMPLETE", RecoveryMock.reply)
        self.assertEqual(RecoveryMock.parent_step, 2)

    def test_terminal_fixture_waits_then_uses_the_error_child_id(self):
        RecoveryMock.reset("terminal", "/fixture.txt")
        RecoveryMock.decide(parent())
        RecoveryMock.decide(child())
        for _ in range(11):
            RecoveryMock.decide(child())
            self.assertTrue(RecoveryMock.fail_next)
        with patch("test_delegated_review_runtime.time.monotonic", return_value=100):
            RecoveryMock.decide(parent("Subagent failed (sessionID: ses_fixture123): 429"))
        self.assertEqual(RecoveryMock.next_tool[1]["command"], "sleep 20")
        with patch("test_delegated_review_runtime.time.monotonic", return_value=120):
            RecoveryMock.decide(parent("Subagent failed (sessionID: ses_fixture123): 429"))
        self.assertEqual(RecoveryMock.next_tool[1]["sessionID"], "ses_fixture123")
        RecoveryMock.decide(child())
        self.assertIn("DR_CHILD_COMPLETE", RecoveryMock.reply)
        RecoveryMock.decide(parent("DR_CHILD_COMPLETE"))
        self.assertIn("DR_PARENT_COMPLETE", RecoveryMock.reply)

    def test_premature_parent_retry_is_a_fixture_failure(self):
        RecoveryMock.reset("terminal", "/fixture.txt")
        RecoveryMock.decide(parent())
        RecoveryMock.failures = 3
        with self.assertRaisesRegex(AssertionError, "native retries exhausted"):
            RecoveryMock.decide(parent("Subagent failed (sessionID: ses_fixture123): 429"))


if __name__ == "__main__":
    unittest.main()
