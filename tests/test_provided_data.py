"""Regression expectations are deliberate review decisions, not inferred ground truth."""

import json
from pathlib import Path
import unittest
from event_sync.reconcile import reconcile, normalize_record, name_matches_email

DATA = Path(__file__).resolve().parent.parent / "data"


class ProvidedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crm = json.loads((DATA / "crm_events.json").read_text(encoding="utf-8"))
        cls.calendar = json.loads(
            (DATA / "calendar_events.json").read_text(encoding="utf-8")
        )
        cls.result = reconcile(cls.crm, cls.calendar)

    def find(self, source_id):
        return next(
            m
            for m in self.result["meetings"]
            if any(r["source_id"] == source_id for r in m["records"])
        )

    def ids(self, m):
        return {r["source_id"] for r in m["records"]}

    def test_all_original_rows_retained_once(self):
        records = [r for m in self.result["meetings"] for r in m["records"]]
        self.assertEqual(len(records), 42)
        self.assertEqual(len({(r["source"], r["row"]) for r in records}), 42)

    def test_expected_thirteen_pairs(self):
        expected = [
            ("CRM-1001", "CAL-A1"),
            ("CRM-1002", "CAL-A2"),
            ("CRM-1006", "CAL-A7"),
            ("CRM-1008", "CAL-A9"),
            ("CRM-1009", "CAL-A10"),
            ("CRM-1011", "CAL-A12"),
            ("CRM-1012", "CAL-A13"),
            ("CRM-1013", "CAL-A14"),
            ("CRM-1014", "CAL-A15"),
            ("CRM-1015", "CAL-A16"),
            ("CRM-1017", "CAL-A20"),
            ("CRM-1018", "CAL-A21"),
            ("CRM-1019", "CAL-A22"),
        ]
        self.assertEqual(self.result["summary"]["matched"], len(expected))
        for crm, cal in expected:
            with self.subTest(crm=crm):
                self.assertEqual(self.ids(self.find(crm)), {crm, cal})

    def test_source_only_meetings(self):
        for sid in (
            "CRM-1003",
            "CRM-1010",
            "CRM-1020",
            "CAL-A3",
            "CAL-A18",
            "CAL-A11",
            "CAL-A19",
        ):
            with self.subTest(sid=sid):
                self.assertEqual(self.ids(self.find(sid)), {sid})

    def test_pinnacle_ambiguity_and_possible_duplicate(self):
        for sid in ("CRM-1005", "CAL-A5", "CAL-A6"):
            m = self.find(sid)
            self.assertEqual(self.ids(m), {sid})
            self.assertTrue(m["needs_review"])
        duplicate = [
            c
            for c in self.find("CAL-A5")["candidates"]
            if c["kind"] == "possible_duplicate"
        ]
        self.assertEqual(duplicate[0]["source_id"], "CAL-A6")
        self.assertEqual(duplicate[0]["start_delta_seconds"], 1800)

    def test_timezone_mismatch_never_assumes_an_offset(self):
        m = self.find("CRM-1004")
        self.assertEqual(self.ids(m), {"CRM-1004"})
        self.assertEqual(m["candidates"][0]["source_id"], "CAL-A4")
        self.assertIsNone(m["candidates"][0]["start_delta_seconds"])
        self.assertIn("Timezone mismatch", m["candidates"][0]["review_reason"])

    def test_missing_time_is_candidate_not_midnight(self):
        m = self.find("CRM-1007")
        self.assertIsNone(m["fields"]["start"]["value"])
        self.assertEqual(m["fields"]["date"]["value"], "2025-03-18")
        self.assertEqual(m["candidates"][0]["source_id"], "CAL-A8")

    def test_two_hour_reschedule_is_review_only(self):
        m = self.find("CRM-1016")
        self.assertEqual(self.ids(m), {"CRM-1016"})
        self.assertEqual(m["candidates"][0]["source_id"], "CAL-A17")
        self.assertEqual(m["candidates"][0]["start_delta_seconds"], 7200)
        self.assertFalse(m["candidates"][0]["automatic"])

    def test_legacy_date_repair_is_auditable(self):
        m = self.find("CRM-1008")
        self.assertEqual(m["fields"]["start"]["value"], "2025-03-15T12:00:00")
        self.assertTrue(m["needs_review"])
        obs = next(
            o for o in m["fields"]["start"]["observations"] if o["source"] == "crm"
        )
        self.assertEqual(obs["raw_value"]["meeting_date"], "03-15/2025")

    def test_cancellation_is_not_overwritten(self):
        m = self.find("CRM-1009")
        self.assertEqual(m["fields"]["status"]["value"], "cancelled")
        self.assertTrue(m["fields"]["status"]["conflict"])
        self.assertTrue(m["needs_review"])
        self.assertIn("CANCELLED", m["fields"]["notes"]["value"])

    def test_virtual_vs_in_person_conflict(self):
        m = self.find("CRM-1002")
        self.assertTrue(m["fields"]["meeting_type"]["conflict"])
        self.assertEqual(m["fields"]["meeting_type"]["value"], "In-Person")
        self.assertTrue(m["fields"]["location"]["value"].startswith("Zoom"))
        obs = next(
            o
            for o in m["fields"]["meeting_type"]["observations"]
            if o["source"] == "calendar"
        )
        self.assertEqual(obs["source_field"], "location (derived modality)")

    def test_bad_attendees_retained_in_raw_only(self):
        m = self.find("CAL-A16")
        self.assertNotIn("raj.patel[at]atlasvc.com", m["fields"]["attendees"]["value"])
        r = next(r for r in m["records"] if r["source"] == "calendar")
        self.assertIn("raj.patel[at]atlasvc.com", r["raw"]["attendees"])
        self.assertTrue(m["needs_review"])

    def test_recurrence_is_not_expanded_or_merged_across_dates(self):
        self.assertNotEqual(self.find("CAL-A3")["id"], self.find("CAL-A18")["id"])
        self.assertTrue(self.find("CAL-A3")["fields"]["is_recurring"]["value"])
        self.assertFalse(self.find("CAL-A11")["fields"]["is_recurring"]["value"])

    def test_owner_and_organizer_are_different_fields(self):
        m = self.find("CRM-1013")
        self.assertEqual(m["fields"]["owner"]["value"], "Sarah Chen")
        self.assertEqual(m["fields"]["organizer"]["value"], "priya.sharma@firma.com")

    def test_reordering_preserves_decisions(self):
        other = reconcile(list(reversed(self.crm)), list(reversed(self.calendar)))
        self.assertEqual(other["summary"], self.result["summary"])
        self.assertEqual(
            [m["id"] for m in other["meetings"]],
            [m["id"] for m in self.result["meetings"]],
        )

    def test_candidate_targets_exist(self):
        ids = {m["id"] for m in self.result["meetings"]}
        for m in self.result["meetings"]:
            for c in m["candidates"]:
                self.assertIn(c["meeting_id"], ids)

    def test_names_match_whole_local_part_not_substrings(self):
        self.assertTrue(
            name_matches_email("Kevin O'Brien", ["kevin.obrien@example.com"])
        )
        self.assertFalse(name_matches_email("Ann Lee", ["joann.lee@example.com"]))
        self.assertFalse(name_matches_email("Sarah Chen", ["s.chen@example.com"]))

    def test_invalid_legacy_date_is_not_guessed(self):
        r = normalize_record(
            "crm",
            {"subject": "Test", "meeting_date": "13-45/2025", "meeting_time": "12:00"},
            0,
        )
        self.assertIsNone(r["values"]["start"])
        self.assertIsNone(r["values"]["date"])

    def test_mixed_start_end_time_basis_is_retained_as_issue(self):
        r = normalize_record(
            "calendar",
            {
                "title": "Test",
                "start_time": "2025-03-10T12:00:00",
                "end_time": "2025-03-10T13:00:00Z",
            },
            0,
        )
        self.assertIsNone(r["values"]["end"])
        self.assertTrue(any("timezone basis" in issue for issue in r["issues"]))

    def test_naive_timestamp_stays_floating(self):
        r = normalize_record(
            "calendar", {"title": "Test", "start_time": "2025-03-10T12:00"}, 0
        )
        self.assertEqual(r["values"]["start"], "2025-03-10T12:00:00")
        self.assertEqual(r["time_basis"], "local-unspecified")
        self.assertTrue(r["normalization_notes"])

    def test_time_limit_boundary_for_identity_rule(self):
        crm = self.crm[0].copy()
        cal = self.calendar[0].copy()
        for minute, matched in [("14:30:00", 1), ("14:30:01", 0)]:
            cal["start_time"] = "2025-03-10T" + minute
            with self.subTest(minute=minute):
                self.assertEqual(reconcile([crm], [cal])["summary"]["matched"], matched)
