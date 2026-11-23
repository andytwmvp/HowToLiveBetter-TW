"""台灣痛風疾病頻率與單餐後個人發作風險的界線。"""

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime


ITEM_ID = "TW-16-010"
BATCH_PATH = "localization/tw16-gout-frequency-recheck-20261123.json"
BUNDLE_PATH = "localization/tw-edition/sources/ch16-gout-frequency-recheck-20261123.json"
STUDY_SOURCE_ID = "ch16_tw_gout_nhird_2015_20261123"


def load_json(path):
    return json.loads((ROOT / path).read_text())


def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class GoutFrequencyRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime = validate_runtime()
        cls.item = next(item for item in runtime["items"] if item["id"] == ITEM_ID)
        cls.sources = {source["id"]: source for source in runtime["sources"]}
        cls.review = load_json(f"localization/reviews/{ITEM_ID}.json")
        cls.register = load_json("localization/retroactive-review-register-20261019.json")
        cls.record = next(
            row for row in reversed(cls.register["substantive_rechecks"])
            if row["id"] == ITEM_ID
        )
        cls.batch = load_json(BATCH_PATH)
        cls.bundle = load_json(BUNDLE_PATH)
        cls.article = (ROOT / cls.item["target_path"]).read_text()

    def test_body_review_manifest_runtime_and_history_are_synchronized(self):
        manifest = load_json("localization/manifest.json")
        entry = next(row for row in manifest["entries"] if row["id"] == ITEM_ID)
        digest = sha256(self.article)
        self.assertEqual(self.article, self.item["body"])
        self.assertEqual(digest, self.review["target_sha256"])
        self.assertEqual(self.review["source_reviewed_sha256"], digest)
        self.assertEqual(self.item["source_ids"], self.review["source_ids"])
        self.assertEqual(self.item["source_ids"], entry["sources"])
        self.assertEqual(self.review["source_checks"], self.record["source_checks"])
        self.assertEqual(self.review["limits"], self.record["limits"])
        self.assertEqual(self.record["after_sha256"], digest)
        self.assertEqual(self.record["source_bundle_path"], BUNDLE_PATH)
        self.assertEqual(self.review["source_bundle_path"], BUNDLE_PATH)
        self.assertEqual(self.record["source_bundle_sha256"], self.review["source_bundle_sha256"])
        self.assertEqual(
            self.review["source_bundle_sha256"],
            sha256((ROOT / BUNDLE_PATH).read_bytes()),
        )
        validate_recheck_history(ROOT, self.record, self.item)

    def test_taiwan_rates_keep_distinct_units_and_historical_limits(self):
        by_indicator = {row["indicator"]: row for row in self.review["statistics_assessed"]}
        prevalence = by_indicator["痛風診斷盛行率"]
        incidence = by_indicator["痛風新發診斷率"]
        self.assertEqual((prevalence["numerator"], prevalence["denominator"], prevalence["value"]),
                         (1_458_569, 23_371_362, 6.24))
        self.assertEqual((incidence["numerator"], incidence["denominator"], incidence["value"]),
                         (56_595, 20_677_590, 2.74))
        self.assertEqual(incidence["unit"], "每1,000人年")
        self.assertEqual(prevalence["period"], "2010年（病例回溯至2000年中）")
        self.assertEqual(prevalence["source_id"], STUDY_SOURCE_ID)
        self.assertEqual(incidence["source_id"], STUDY_SOURCE_ID)
        self.assertIn("不是2026年現況", self.review["frequency_assessment"])
        self.assertIn("單次餐飲暴露", self.review["frequency_assessment"])
        self.assertLess(self.article.index("119"), self.article.index("發生頻率"))

    def test_reader_copy_excludes_internal_review_and_inaccessible_pdf_claims(self):
        for phrase in ("AI核對", "未重讀全部底層試驗", "仍待風濕科", "本輪"):
            self.assertNotIn(phrase, self.article)
        self.assertNotIn("499-1141224.pdf", self.article)
        active_urls = {self.sources[source_id]["url"] for source_id in self.item["source_ids"]}
        article_urls = set(re.findall(r"https://\S+", self.article))
        self.assertEqual(article_urls, active_urls)
        retired = self.record["retired_sources"][0]
        self.assertEqual(retired["id"], "next_gout_nutrition")
        self.assertEqual(retired["disposition"], "replaced")
        old_sources = {source["id"]: source for source in validate_runtime()["sources"]}
        self.assertIn(retired["id"], old_sources)
        self.assertNotIn(retired["id"], self.item["source_ids"])
        bundle_row = self.bundle["sources"][0]
        self.assertEqual(bundle_row[0], STUDY_SOURCE_ID)
        self.assertEqual(self.sources[STUDY_SOURCE_ID]["url"], bundle_row[2])

    def test_statistics_and_professional_review_remain_explicit_and_publication_blocked(self):
        self.assertEqual(self.review["statistics_assessed"], self.record["statistics_assessed"])
        self.assertEqual(self.review["professional_review"]["status"], "pending")
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertFalse(publication_report()["publication_ready"])
        coverage = load_json("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertEqual(self.batch["counts_before"]["substantive_rechecks"] + 1,
                         self.batch["counts_after"]["substantive_rechecks"])
        self.assertFalse(self.batch["publication_ready"])


if __name__ == "__main__":
    unittest.main()
