import unittest

from decision_v2.agents import ROLE_INSTRUCTIONS, TWO_OPTION_INSTRUCTIONS


class CoordinatorPromptTests(unittest.TestCase):
    def test_both_coordinator_prompts_carry_flags_and_reference_rules(self):
        for prompt in (ROLE_INSTRUCTIONS["coordinator"], TWO_OPTION_INSTRUCTIONS["coordinator"]):
            self.assertIn("dependency flag", prompt)
            self.assertIn("uses_expedited_freight", prompt)
            self.assertIn("not a selectable plan", prompt.replace("rather than a selectable plan", "not a selectable plan"))
            self.assertIn("new-build", prompt)


if __name__ == "__main__":
    unittest.main()
