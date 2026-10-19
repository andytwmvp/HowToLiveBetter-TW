"""回溯稽核：既有正式正文、導航和原作 765 條均須動態覆蓋。"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit


class RetroactiveAuditTests(unittest.TestCase):
    def test_all_existing_and_future_core_and_navigation_are_included(self):
        result = audit.audit()
        root = audit.ROOT
        manifest = json.loads((root / "localization/manifest.json").read_text(encoding="utf-8"))
        runtime = json.loads((root / "localization/tw-edition/runtime.json").read_text(encoding="utf-8"))
        current = {e["id"] for e in manifest["entries"]}
        tracked = {e["id"] for e in result["core"]}
        self.assertEqual(tracked, current)
        self.assertEqual(len(tracked), len(result["core"]))
        self.assertEqual(
            {i["id"] for i in runtime["items"] if i["id"].startswith("TW-NAV-")},
            {i["id"] for i in result["navigation"]},
        )
        self.assertEqual(
            result["summary"]["published_core_retroactively_screened"],
            sum(e["status"] == "verified" for e in manifest["entries"]),
        )
        self.assertFalse(result["summary"]["publication_ready"])

    def test_prior_verified_status_never_automatically_certifies_new_standard(self):
        result = audit.audit()
        for page in result["core"]:
            if page["prior_status"] == "verified":
                self.assertEqual(
                    page["new_standard_review"],
                    "pending_substantive_taiwan_context_and_frequency_recheck",
                )
                self.assertIn("content_sha256", page)
            else:
                self.assertEqual(page["new_standard_review"], "not_published_research_pending")
                self.assertNotIn("evidence_markers_only", page)
        for page in result["navigation"]:
            self.assertEqual(
                page["new_standard_review"],
                "pending_substantive_taiwan_context_and_frequency_recheck",
            )

    def test_heuristic_is_a_marker_not_an_incidence_certificate(self):
        sample = "臺灣2025年資料顯示，2025年事件統計100件，但母數未知。"
        marks = audit.cues(sample)
        self.assertTrue(marks["frequency_term_marker"])
        self.assertTrue(marks["tw_context_marker"])
        self.assertTrue(marks["statistic_year_marker"])
        # 只有審閱者取得該年該地的母數與統計定義才可提供真正發生率。

    def test_review_date_or_medical_number_is_not_a_frequency_claim(self):
        markers = audit.cues("臺灣急救先撥119。AI輔助查閱2026-10-19。")
        self.assertTrue(markers["tw_context_marker"])
        self.assertFalse(markers["frequency_term_marker"])
        self.assertFalse(markers["statistic_year_marker"])
        self.assertFalse(markers["numeric_claim_marker"])

    def test_critical_event_prioritization_is_independent_of_frequency(self):
        self.assertEqual(audit.risk(13, "TW-13-001"), "P0")
        self.assertEqual(audit.risk(1, "TW-01-001"), "P0")
        self.assertEqual(audit.risk(14, "TW-14-001"), "P2")
        self.assertEqual(audit.risk(None, "TW-NAV-010"), "P0")


if __name__ == "__main__":
    unittest.main()
