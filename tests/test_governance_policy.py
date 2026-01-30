import unittest

from governance_policy import Action, decide


class TestGovernancePolicy(unittest.TestCase):
    def test_low_signals_continue(self):
        report = {
            "loop_pattern_hits": {"total": 1},
            "invert_nesting_max": 0,
            "dedup_saved": 0.0,
            "avg_novelty_to_ground": 0.6,
            "ground_reached": True,
        }
        decision = decide(report)
        self.assertEqual(decision.action, Action.CONTINUE)

    def test_moderate_loop_prune(self):
        report = {
            "loop_pattern_hits": {"total": 6},
            "invert_nesting_max": 0,
            "dedup_saved": 0.0,
            "avg_novelty_to_ground": 0.6,
            "ground_reached": True,
        }
        decision = decide(report)
        self.assertEqual(decision.action, Action.PRUNE)

    def test_high_invert_ground_now(self):
        report = {
            "loop_pattern_hits": {"total": 0},
            "invert_nesting_max": 2,
            "dedup_saved": 0.0,
            "avg_novelty_to_ground": 0.6,
            "ground_reached": False,
        }
        decision = decide(report)
        self.assertEqual(decision.action, Action.GROUND_NOW)

    def test_invalid_report_defer(self):
        report = {"loop_pattern_hits": None}
        decision = decide(report)
        self.assertEqual(decision.action, Action.DEFER)
        self.assertIn("INVALID_REPORT", decision.reason_codes)

    def test_severity_clamped(self):
        report = {
            "loop_pattern_hits": {"total": 999},
            "invert_nesting_max": 999,
            "dedup_saved": 999,
            "avg_novelty_to_ground": 0.6,
            "ground_reached": True,
        }
        decision = decide(report)
        self.assertGreaterEqual(decision.severity, 0.0)
        self.assertLessEqual(decision.severity, 1.0)


if __name__ == "__main__":
    unittest.main()
