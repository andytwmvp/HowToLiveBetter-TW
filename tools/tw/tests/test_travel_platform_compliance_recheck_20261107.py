"""2026-11-07 旅外安全與臺灣網路交易法規實質再審。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime


BASE = "dbacb6c37f0ec6e358923da0fb456f3f92bdfe42"
IDS = ("TW-21-002", "TW-21-001", "TW-21-007", "TW-26-005", "TW-26-004", "TW-26-002")
NEW_SOURCES = {
    "ch26_tax_registration_display_20261107",
    "ch26_platform_accounting_records_20261107",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class TravelPlatformRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.records = {
            item["id"]: item
            for item in cls.register["substantive_rechecks"]
            if item.get("reviewed_at") == "2026-11-07"
        }
        cls.batch = read("localization/travel-platform-compliance-recheck-20261107.json")

    def test_articles_sources_reviews_manifest_and_history_are_synchronized(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(set(self.batch["rechecked_ids"]), set(IDS))
        for key in IDS:
            with self.subTest(id=key):
                item = self.items[key]
                review = read(f"localization/reviews/{key}.json")
                record = self.records[key]
                body = (ROOT / item["target_path"]).read_text(encoding="utf-8")
                body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
                self.assertEqual(item["body"], body)
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(record["after_sha256"], body_sha)
                batch_item = next(row for row in self.batch["items"] if row["id"] == key)
                self.assertEqual(batch_item["after_sha256"], body_sha)
                self.assertNotEqual(record["before_sha256"], body_sha)
                self.assertEqual(review["reviewed_at"], "2026-11-07")
                self.assertEqual(review["review_due_at"], "2027-02-07")
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["statistics_assessed"], review["statistics_assessed"])
                self.assertTrue(record["previous_review_claims"])
                self.assertEqual(record["prior_reviewed_at"], "2026-10-17")
                self.assertEqual(record["prior_review_due_at"], "2026-12-31")
                previous_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{key}.json"],
                    cwd=ROOT,
                )
                self.assertEqual(
                    record["prior_review_sha256"],
                    hashlib.sha256(previous_review).hexdigest(),
                )
                self.assertTrue(record["taiwan_context_assessment"]["independent_of_frequency"])
                self.assertTrue(all(self.sources[source_id]["url"] in body
                                    for source_id in item["source_ids"]))
                self.assertEqual(
                    self.manifest[key]["sources"],
                    [self.sources[source_id]["url"] for source_id in item["source_ids"]],
                )
                self.assertEqual(
                    {source["url"] for source in review["source_checks"]},
                    {self.sources[source_id]["url"] for source_id in item["source_ids"]},
                )
                self.assertTrue(all(
                    check["supporting_passage"].startswith("編者摘要（非逐字）：")
                    and check["supporting_passage"] != check["claim"]
                    for check in review["source_checks"]
                ))
                self.assertIsNone(review["statistics_assessed"][0]["value"])
                self.assertIsNone(review["statistics_assessed"][0]["denominator"])
                self.assertTrue(review["statistics_assessed"][0]["population"])
                self.assertTrue(review["statistics_assessed"][0]["event_definition"])
                self.assertTrue(review["statistics_assessed"][0]["sources_examined_for_frequency"])
                validate_recheck_history(ROOT, record, item)

    def test_reading_text_uses_verified_taiwan_context_and_has_no_batch_editorial_copy(self):
        bodies = {key: self.items[key]["body"] for key in IDS}
        combined = "\n".join(bodies.values())
        for phrase in ("AI輔助", "本批", "累計", "臺灣版尚在", "僅在此 fork", "編者摘要"):
            self.assertNotIn(phrase, combined)

        alerts = bodies["TW-21-001"]
        for phrase in ("灰色提醒", "黃色注意", "橙色避免前往", "紅色儘速離境", "不會自動決定"):
            self.assertIn(phrase, alerts)

        emergency = bodies["TW-21-002"]
        for phrase in ("0800-085-095", "+886-800-085-095", "22個國家或地區", "另付國際漫遊電話費"):
            self.assertIn(phrase, emergency)
        self.assertNotIn("12308", emergency)
        self.assertNotIn("並補上國內免費", emergency)

        passport = bodies["TW-21-007"]
        for phrase in ("遺失護照說明書", "入國證明書", "最近6個月內", "不自行使用已註銷護照"):
            self.assertIn(phrase, passport)

        tax = bodies["TW-26-002"]
        for phrase in ("新臺幣10萬元", "5萬元（勞務）", "2025年1月1日", "第4-1條"):
            self.assertIn(phrase, tax)
        self.assertIn("https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=G0340087", tax)

        privacy = bodies["TW-26-004"]
        for phrase in ("2025年11月11日", "尚未施行", "112年5月31日", "準備、偵測與應變"):
            self.assertIn(phrase, privacy)

        platform = bodies["TW-26-005"]
        for phrase in ("第21條第3項", "第27條", "至少保存五年", "不代表所有使用者資料都要保存五年"):
            self.assertIn(phrase, platform)
        self.assertIn("最新修正及施行狀態", platform)
        self.assertNotIn("保存三年", platform)
        self.assertNotIn("每個平台都必須永久保存所有會員資料", platform)

    def test_new_source_catalog_and_live_coverage_match_batch_snapshot(self):
        catalog = read("localization/tw-edition/sources/travel-platform-compliance-recheck-20261107.json")
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCES)
        self.assertTrue(NEW_SOURCES.issubset(self.sources))
        coverage = read("localization/tw-edition/coverage.json")
        live = audit_drafts()
        self.assertEqual(coverage, live)
        self.assertFalse(self.batch.get("publication_ready", False))
        self.assertFalse(self.batch["professional_review"]["obtained"])


if __name__ == "__main__":
    unittest.main()
