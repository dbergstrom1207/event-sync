import copy
import unittest
from event_sync.reconcile import reconcile


def row(**changes):
    return {
        "id": "a",
        "title": "Acme review",
        "start": "2026-11-02T15:00:00Z",
        "client": "Acme",
        "attendees": ["alex@acme.example"],
        "location": "Office",
        **changes,
    }


class ReconciliationTests(unittest.TestCase):
    def test_match_and_field_provenance(self):
        result = reconcile(
            [row(owner="Jordan")],
            [row(id="b", start="2026-11-02T15:05:00Z", location="Zoom")],
        )
        m = result["meetings"][0]
        self.assertEqual(result["summary"]["matched"], 1)
        self.assertEqual(m["fields"]["location"]["value"], "Zoom")
        self.assertTrue(m["fields"]["location"]["conflict"])
        self.assertEqual(m["fields"]["owner"]["selected_source"], "crm")
        self.assertEqual(len(m["fields"]["location"]["observations"]), 2)
        self.assertEqual(m["match"]["start_delta_seconds"], 300)

    def test_timezone_equivalence(self):
        m = reconcile([row(start="2026-11-02T10:00:00-05:00")], [row()])["meetings"][0]
        self.assertFalse(m["fields"]["start"]["conflict"])

    def test_window_inclusive_and_outside(self):
        for time, expected in [("15:10:00", 1), ("15:10:01", 2)]:
            with self.subTest(time=time):
                self.assertEqual(
                    len(
                        reconcile([row()], [row(start=f"2026-11-02T{time}Z")])[
                            "meetings"
                        ]
                    ),
                    expected,
                )

    def test_same_title_and_time_not_enough(self):
        self.assertEqual(
            len(
                reconcile(
                    [row(client=None, attendees=[])], [row(client=None, attendees=[])]
                )["meetings"]
            ),
            2,
        )

    def test_conflicting_clients_veto(self):
        self.assertEqual(len(reconcile([row()], [row(client="Other")])["meetings"]), 2)

    def test_ambiguous_many_to_one_is_not_greedily_merged(self):
        r = reconcile([row()], [row(id="b"), row(id="c", start="2026-11-02T15:01:00Z")])
        self.assertEqual(r["summary"]["matched"], 0)
        self.assertEqual(r["summary"]["review"], 3)
        self.assertTrue(all(m["candidate_refs"] for m in r["meetings"]))

    def test_exact_duplicate_keeps_raw_records(self):
        r = reconcile([row(), row(id="copy")], [])
        self.assertEqual(r["summary"]["duplicates_collapsed"], 1)
        self.assertEqual(len(r["meetings"][0]["records"]), 2)

    def test_near_duplicate_not_silently_removed(self):
        r = reconcile([row(), row(id="copy", start="2026-11-02T15:01:00Z")], [])
        self.assertEqual(r["summary"]["meetings"], 2)

    def test_invalid_and_scalar_records_retained(self):
        r = reconcile([row(start="bad"), row(start="2026-11-02T99:00:00"), 42], [])
        self.assertEqual(r["summary"]["review"], 3)
        self.assertEqual(r["summary"]["input_records"], 3)
        self.assertTrue(
            all(m["fields"]["start"]["value"] is None for m in r["meetings"])
        )

    def test_empty_inputs(self):
        self.assertEqual(reconcile([], [])["meetings"], [])

    def test_invalid_root(self):
        with self.assertRaises(ValueError):
            reconcile({}, [])

    def test_recurrence_occurrences_remain_separate(self):
        r = reconcile(
            [row()],
            [row(start="2026-11-09T15:00:00Z", recurrence=["RRULE:FREQ=WEEKLY"])],
        )
        self.assertEqual(r["summary"]["meetings"], 2)

    def test_missing_fields_not_conflicts(self):
        m = reconcile([row(owner="Jordan")], [row()])["meetings"][0]
        self.assertFalse(m["fields"]["owner"]["conflict"])

    def test_invalid_end_and_partial_attendees(self):
        m = reconcile(
            [row(end="2026-11-02T14:00:00Z", attendees=["bad", "alex@acme.example"])],
            [],
        )["meetings"][0]
        self.assertIsNone(m["fields"]["end"]["value"])
        self.assertEqual(m["fields"]["attendees"]["value"], ["alex@acme.example"])
        self.assertTrue(m["needs_review"])

    def test_fractional_end_order(self):
        m = reconcile([row(end="2026-11-02T15:00:00.500Z")], [])["meetings"][0]
        self.assertIsNotNone(m["fields"]["end"]["value"])

    def test_stable_ids_under_reordering_and_no_mutation(self):
        a = [row(), row(id="c", title="Another")]
        b = [row(id="calendar")]
        original = copy.deepcopy(a)
        first = reconcile(a, b)
        second = reconcile(list(reversed(a)), b)
        self.assertEqual(
            [m["id"] for m in first["meetings"]], [m["id"] for m in second["meetings"]]
        )
        self.assertEqual(a, original)

    def test_same_source_conflicting_ids_do_not_overwrite(self):
        r = reconcile([row(), row(location="Zoom")], [])
        self.assertEqual(r["summary"]["meetings"], 2)

    def test_whitespace_case_and_attendee_order(self):
        m = reconcile(
            [
                row(
                    title="  ACME   review ",
                    attendees=["B@acme.example", "alex@acme.example"],
                )
            ],
            [row(attendees=["alex@acme.example", "b@acme.example"])],
        )["meetings"][0]
        self.assertFalse(m["fields"]["title"]["conflict"])
        self.assertFalse(m["fields"]["attendees"]["conflict"])

    def test_row_accounting(self):
        a = [row(), row(id="copy"), None]
        b = [row(id="calendar"), row(title="Other")]
        r = reconcile(a, b)
        self.assertEqual(sum(len(m["records"]) for m in r["meetings"]), len(a) + len(b))
