import unittest

from decision_v2.contracts import SCENARIO_IDS
from decision_v2.fixtures import (
    EXAMPLES, assessment_blockers, fixture_records, operational_checks, operational_position, routing_context,
)

FEASIBLE, UNCERTAIN = "holdout-feasible-v2", "holdout-uncertain-v2"


class HoldoutFixtureTests(unittest.TestCase):
    def test_registered_as_examples_and_scenarios(self):
        self.assertEqual(EXAMPLES["holdout-feasible"], FEASIBLE)
        self.assertEqual(EXAMPLES["holdout-uncertain"], UNCERTAIN)
        self.assertIn(FEASIBLE, SCENARIO_IDS)
        self.assertIn(UNCERTAIN, SCENARIO_IDS)

    def test_feasible_case_is_resolved_with_no_blockers_or_unknowns(self):
        records = fixture_records(FEASIBLE)
        self.assertTrue(all(operational_checks(records).values()))
        self.assertEqual(assessment_blockers(FEASIBLE), [])
        context = routing_context(FEASIBLE)
        self.assertEqual(context["decision_status"]["state"], "resolved_record")
        self.assertTrue(all(not v for v in context["known_unknowns_by_role"].values()))
        shipment, policy = records["read_shipment"], records["read_approval_policy"]
        self.assertLessEqual(shipment.freight_cost_usd, policy.planner_limit_usd)
        self.assertTrue(shipment.slot_confirmed and shipment.confirmation_reference)
        self.assertEqual(operational_position(records)["arrival_at"], "2026-10-16T09:00:00-05:00")

    def test_uncertain_case_has_confirmation_unknown_and_authority_blocker(self):
        records = fixture_records(UNCERTAIN)
        shipment, policy = records["read_shipment"], records["read_approval_policy"]
        self.assertFalse(shipment.slot_confirmed)
        self.assertIsNone(shipment.confirmation_reference)
        self.assertGreater(shipment.freight_cost_usd, policy.planner_limit_usd)
        self.assertFalse(operational_checks(records)["carrier_confirmation"])
        self.assertEqual(routing_context(UNCERTAIN)["decision_status"]["state"], "business_questions_open")
        self.assertTrue(any("carrier_confirmation" in b for b in assessment_blockers(UNCERTAIN)))

    def test_holdout_identifiers_are_new(self):
        used = {"SO-6101", "SO-6102", "SO-6701", "SO-6702", "L-1061", "L-1062", "L-1063", "SH-901", "SH-902", "SH-903"}
        for scenario in (FEASIBLE, UNCERTAIN):
            records = fixture_records(scenario)
            ids = {records["read_build"].order_id, records["read_inventory"].released_lot_id,
                   records["read_shipment"].shipment_id}
            self.assertFalse(ids & used)


if __name__ == "__main__":
    unittest.main()
