import unittest

from decision_v2.contracts import PROSE_REVIEW_PREFIX, DemoError, FinalResult, ProseWarning, RunState
from decision_v2 import prose


class ProseWarningContractTests(unittest.TestCase):
    def test_warning_is_frozen_record(self):
        w = ProseWarning("production", "assessment", "2026-10-16", "prose.ready", "ready=x")
        with self.assertRaises(Exception):
            w.actor = "other"

    def test_fail_raises_without_sink(self):
        with self.assertRaises(DemoError):
            prose.fail("supply-chain", "assessment", "claim", "ready", [("18:00", "fixture")])

    def test_fail_collects_with_sink(self):
        sink = []
        token = prose.PROSE_SINK.set(sink)
        try:
            prose.fail("supply-chain", "assessment", "claim", "ready", [("18:00", "fixture")])
        finally:
            prose.PROSE_SINK.reset(token)
        self.assertEqual(len(sink), 1)
        self.assertEqual(sink[0].rule_id, "prose.ready")

    def test_final_result_defaults_to_no_warnings(self):
        self.assertEqual(FinalResult("pending", 2, (), None).warnings, ())
        self.assertTrue(PROSE_REVIEW_PREFIX.startswith("Prose review"))


if __name__ == "__main__":
    unittest.main()
