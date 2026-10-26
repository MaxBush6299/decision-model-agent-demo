import unittest

from decision_v2 import prose
from decision_v2.contracts import DemoError

THU, FRI = "2027-03-04T16:30:00-06:00", "2027-03-05T09:00:00-06:00"
EVENTS = {
    "alpha-one": {"booking": [(THU, "ship")], "pickup": [("2027-03-04T18:00:00-06:00", "ship")],
                  "arrival": [(FRI, "ship")], "delivery": [("2027-03-05T08:00:00-06:00", "ship")]},
    "beta-two": {"booking": [(THU, "ship"), (FRI, "ship")], "pickup": [("2027-03-04T17:00:00-06:00", "ship"),
                 ("2027-03-05T10:00:00-06:00", "ship")], "arrival": [(FRI, "ship")],
                 "delivery": [("2027-03-05T08:00:00-06:00", "ship")]},
}


def violations(text, explicit=None):
    try:
        prose.check_calendar(text, "actor", "field", EVENTS, explicit)
    except DemoError as error:
        return str(error)
    return None


class LegAwareCalendarTests(unittest.TestCase):
    def test_trailing_option_label_owns_the_date(self):
        text = ("Booking cutoffs are Thursday 2027-03-04 16:30 UTC-06:00 for alpha-one and "
                "Thursday 2027-03-04 16:30 UTC-06:00 / Friday 2027-03-05 09:00 UTC-06:00 for beta-two.")
        self.assertIsNone(violations(text))

    def test_date_followed_by_window_binds_to_window_not_prior_pickup(self):
        text = ("Pickup is Thursday 2027-03-04 18:00 UTC-06:00 and the Friday 08:00-10:00 window is supported "
                "by arrival Friday 2027-03-05 09:00 UTC-06:00", )
        self.assertIsNone(violations(text[0], "alpha-one"))

    def test_clear_contradiction_with_the_single_leg_still_warns(self):
        self.assertIsNotNone(violations("Booking cutoff Friday 2027-03-05 09:00 UTC-06:00 for alpha-one."))

    def test_multi_leg_option_with_distinct_days_is_not_flagged(self):
        self.assertIsNone(violations("Booking cutoff Friday 2027-03-05 09:00 UTC-06:00 for beta-two."))

    def test_wrong_weekday_for_the_named_leg_still_warns(self):
        self.assertIsNotNone(violations("Pickup is Saturday 2027-03-06 18:00 UTC-06:00 for alpha-one."))

    def test_warn_mode_collects_instead_of_raising(self):
        sink = []
        token = prose.PROSE_SINK.set(sink)
        try:
            prose.check_calendar("Booking cutoff Friday 2027-03-05 09:00 UTC-06:00 for alpha-one.",
                                 "actor", "field", EVENTS, None)
        finally:
            prose.PROSE_SINK.reset(token)
        self.assertTrue(sink)
        self.assertEqual({w.rule_id for w in sink}, {"prose.booking"})


if __name__ == "__main__":
    unittest.main()
