import unittest

from decision_v2.contracts import SCENARIO_IDS
from decision_v2.fixtures import fixture_records, fixture_payload, operational_position


class QuantityBasisTests(unittest.TestCase):
    def test_quantity_basis_is_additive_and_matches_record_arithmetic(self):
        for scenario in SCENARIO_IDS[1:]:
            records = fixture_records(scenario)
            build, stock = records["read_build"], records["read_inventory"]
            if not build.quantity_basis:
                continue
            ordered = sum(d.quantity for d in build.deliveries)
            new_units = build.options[0].production_units if build.options else build.production_units
            with self.subTest(scenario=scenario):
                self.assertEqual(ordered, stock.released_units - stock.allocated_finished_units + new_units)
                for number in (ordered, stock.released_units, new_units, stock.released_material_units):
                    self.assertIn(str(number), build.quantity_basis)
                available = stock.released_material_units - stock.materials_reserved_other_orders
                self.assertIn(f"{available} available before consumption", build.quantity_basis) \
                    if stock.materials_reserved_other_orders else None
                self.assertNotIn("recommend", build.quantity_basis.lower())
                self.assertNotIn("prefer", build.quantity_basis.lower())

    def test_annotations_do_not_name_options_or_grant_approval(self):
        shipment = fixture_records("quality-hold-v2")["read_shipment"]
        text = (shipment.replacement_offer_status + shipment.quote_status).lower()
        self.assertIn("not a selectable plan", text)
        self.assertIn("does not approve", text)
        payload = fixture_payload(shipment)
        self.assertEqual(payload["replacement_offer_id"], "SUP-OFFER-300")
        self.assertEqual(payload["freight_cost_usd"], 3600)
        self.assertFalse(payload["incoming_accepted"])

    def test_numeric_position_is_unchanged_by_annotations(self):
        position = operational_position(fixture_records("order-pull-forward-v2"))
        self.assertEqual((position["demand_units"], position["available_stock_units"],
                          position["available_material_units"]), (400, 160, 400))


if __name__ == "__main__":
    unittest.main()
