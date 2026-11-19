"""第2章全穀與壽命研究主題保真度再審契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))
sys.path.insert(0, str(ROOT / "tools/tw/tests"))

from ci_language_policy import audit_drafts
from recheck_history_assertions import assert_chapter_entries_preserved_or_rechecked
from review_contract import validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "ccee167567b76b6c217894d6cbc19cf467b39543"
DATE = "2026-11-20"
DUE = "2027-02-20"
ITEM_ID = "TW-02-024"
ARTICLE = "locales/zh-TW/book/ch02/TW-02-024.md"
REVIEW = "localization/reviews/TW-02-024.json"
BATCH = "localization/ch02-wholegrain-topic-fidelity-recheck-20261120.json"
BUNDLE = "localization/tw-edition/sources/ch02-wholegrain-topic-fidelity-recheck-20261120.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
NEW_SOURCE_IDS = {
    "tw02_aune_wholegrain_mortality_meta_2016",
    "tw02_schwingshackl_wholegrain_mortality_meta_2017",
    "tw02_hu_wholegrain_mortality_meta_2023",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class WholegrainTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.review = read(REVIEW)
        cls.batch = read(BATCH)
        cls.bundle = read(BUNDLE)
        cls.register = read(REGISTER)
        cls.records = [row for row in cls.register["substantive_rechecks"] if row["id"] == ITEM_ID]
        cls.record = next(row for row in cls.records if row["reviewed_at"] == DATE)

    def test_recheck_is_append_only_and_hash_bound(self):
        before = git_bytes(BASE, ARTICLE)
        prior_review = git_bytes(BASE, REVIEW)
        body = (ROOT / ARTICLE).read_bytes()
        entry = self.manifest[ITEM_ID]
        review_record = self.review
        record = self.record
        digest = sha(body)

        self.assertEqual(record["before_sha256"], sha(before))
        self.assertEqual(record["previous_body"], before.decode("utf-8"))
        self.assertEqual(record["prior_review_sha256"], sha(prior_review))
        self.assertEqual(record["prior_reviewed_at"], json.loads(prior_review)["reviewed_at"])
        self.assertEqual(record["after_sha256"], digest)
        self.assertEqual(review_record["target_sha256"], digest)
        self.assertEqual(review_record["source_reviewed_sha256"], digest)
        self.assertEqual(record["review_due_at"], DUE)
        self.assertEqual(review_record["review_due_at"], DUE)
        self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
        self.assertEqual(record["prior_structured_draft_sha256"], "be0cd68c1f2f009ff0a1abff859e5e8c73deb310521d834c1ba95c9e8cb02d2c")
        self.assertTrue(record["topic_fidelity_assessment"])
        self.assertFalse(review_record["professional_review"]["obtained"])
        self.assertTrue(review_record["professional_review"]["required"])

        prior_revision = subprocess.check_output(
            ["git", "log", "-1", "--format=%H", BASE, "--", ARTICLE], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(record["prior_revision"], prior_revision)
        previous_records = [row for row in self.records if row.get("after_sha256")]
        if len(previous_records) > 1:
            self.assertEqual(record["before_sha256"], previous_records[-2]["after_sha256"])

    def test_reader_article_keeps_research_and_separates_taiwan_guidance(self):
        item = self.items[ITEM_ID]
        body = item["body"]
        self.assertEqual(item["title"], "全穀與壽命研究：白飯白麵不用一次全換")
        self.assertIn("705,253人及100,726人死亡", body)
        self.assertIn("121,141人死亡", body)
        self.assertIn("912,293人及106,112人死亡", body)
        self.assertIn("非線性關係", body)
        self.assertIn("不是每個人必須達到的目標", body)
        self.assertIn("國健署的外食建議", body)
        self.assertIn("不是已證明能延壽的特定劑量", body)
        self.assertIn("台灣現有官方飲食建議提供主食替換方向", body)
        self.assertIn("現有台灣資料不足以支持", body)
        self.assertNotRegex(body, r"(?:批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)")

        source_ids = item["source_ids"]
        self.assertEqual(source_ids, self.manifest[ITEM_ID]["sources"])
        self.assertEqual(source_ids, self.review["source_ids"])
        self.assertEqual(source_ids, self.record["source_ids"])
        urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
        self.assertEqual(urls, {self.sources[source_id]["url"] for source_id in source_ids})
        self.assertEqual({row["source_id"] for row in self.review["source_checks"]}, set(source_ids))
        self.assertEqual({row["url"] for row in self.review["source_checks"]}, urls)

    def test_source_statistics_record_units_population_and_limits(self):
        stats = {row["topic"]: row for row in self.review["statistics_assessed"]}
        self.assertEqual(len(stats), 3)
        self.assertIn("100,726", stats["Aune 2016全穀攝取與全因死亡劑量反應"]["numerator"])
        self.assertIn("705,253", stats["Aune 2016全穀攝取與全因死亡劑量反應"]["denominator"])
        self.assertIn("121,141", stats["Schwingshackl 2017全穀攝取與全因死亡"]["numerator"])
        self.assertIn("未在已核對摘要中另列該模型的參與者總數", stats["Schwingshackl 2017全穀攝取與全因死亡"]["denominator"])
        self.assertIn("106,112", stats["Hu 2023全穀攝取與全因死亡劑量反應"]["numerator"])
        self.assertIn("912,293", stats["Hu 2023全穀攝取與全因死亡劑量反應"]["denominator"])
        source_by_topic = {
            "Aune 2016全穀攝取與全因死亡劑量反應": "tw02_aune_wholegrain_mortality_meta_2016",
            "Schwingshackl 2017全穀攝取與全因死亡": "tw02_schwingshackl_wholegrain_mortality_meta_2017",
            "Hu 2023全穀攝取與全因死亡劑量反應": "tw02_hu_wholegrain_mortality_meta_2023",
        }
        for topic, stat in stats.items():
            for key in (
                "value", "unit", "period", "geographic_scope", "population", "numerator",
                "denominator", "event_definition", "data_type", "limitations", "accessed_at",
            ):
                self.assertTrue(stat[key], (stat["topic"], key))
            self.assertEqual(stat["accessed_at"], DATE)
            self.assertEqual(stat["source_ids"], [source_by_topic[topic]])

        self.assertIn("tw02_hpa_external_dining_guidance_2024", self.review["source_ids"])
        self.assertEqual(self.review["frequency_assessment"], self.record["frequency_assessment"])
        self.assertEqual(self.review["statistics_assessed"], self.record["statistics_assessed"])

    def test_runtime_manifest_chapter_and_coverage_are_consistent(self):
        item = self.items[ITEM_ID]
        entry = self.manifest[ITEM_ID]
        body = (ROOT / ARTICLE).read_text(encoding="utf-8")
        self.assertEqual(item["body"], body)
        self.assertEqual(item["review_status"], "source_checked")
        self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
        self.assertEqual((entry["status"], entry["verified_at"]), ("verified", DATE))
        self.assertEqual(entry["target_path"], ARTICLE)

        chapter = read("localization/tw-edition/chapters/02.json")
        row = next(row for row in chapter["entries"] if row[0] == 24)
        self.assertEqual(row[1], item["title"])
        readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertIn(f"[{item['title']}]({ITEM_ID}.md)", readme)

        bundle_ids = {row[0] for row in self.bundle["sources"]}
        self.assertEqual(bundle_ids, NEW_SOURCE_IDS)
        self.assertEqual(sha((ROOT / BUNDLE).read_bytes()), self.batch["items"][0]["source_bundle_sha256"])
        self.assertEqual(source_bundle_ids_added_since(ROOT, BASE), NEW_SOURCE_IDS)
        self.assertEqual({source_id for source_id in NEW_SOURCE_IDS if source_id in self.sources}, NEW_SOURCE_IDS)
        self.assertEqual(len({row["id"] for row in self.runtime["sources"]}), len(self.runtime["sources"]))
        self.assertEqual(read("localization/tw-edition/coverage.json"), audit_drafts())
        self.assertFalse(read("localization/tw-edition/coverage.json")["publication_ready"])

    def test_existing_content_and_structured_drafts_are_preserved_or_rechecked(self):
        base_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        base_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        base_register = json.loads(git_bytes(BASE, REGISTER))
        old_sources = {row["id"]: row for row in base_runtime["sources"]}
        current_sources = {row["id"]: row for row in self.runtime["sources"]}
        for source_id, source in old_sources.items():
            self.assertEqual(current_sources[source_id], source)

        old_items = {row["id"]: row for row in base_runtime["items"]}
        for item_id, old in old_items.items():
            current = self.items[item_id]
            if current == old:
                continue
            later = [row for row in self.register["substantive_rechecks"] if row["id"] == item_id and row["reviewed_at"] > "2026-11-19"]
            self.assertTrue(later, f"{item_id} changed without an append-only review")

        base_manifest_items = {row["id"]: row for row in base_manifest["entries"]}
        changed_manifest_ids = set()
        for item_id, old in base_manifest_items.items():
            if self.manifest[item_id] != old:
                changed_manifest_ids.add(item_id)
        self.assertEqual(changed_manifest_ids, {ITEM_ID})

        base_chapter = json.loads(git_bytes(BASE, "localization/tw-edition/chapters/02.json"))
        current_chapter = read("localization/tw-edition/chapters/02.json")
        assert_chapter_entries_preserved_or_rechecked(
            self,
            chapter_number=2,
            baseline_entries=base_chapter["entries"],
            current_entries=current_chapter["entries"],
            baseline_items=old_items,
            current_items=self.items,
            baseline_rechecks=base_register["substantive_rechecks"],
            current_rechecks=self.register["substantive_rechecks"],
        )

        self.assertEqual(self.batch["counts_before"]["verified_core_entries"], 322)
        self.assertEqual(self.batch["counts_after"]["verified_core_entries"], 322)
        self.assertEqual(self.batch["counts_after"]["review_rechecks"], self.batch["counts_before"]["review_rechecks"] + 1)
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], self.batch["counts_before"]["runtime_sources"] + 3)
        self.assertEqual(self.batch["counts_after"]["source_registry"], self.batch["counts_before"]["source_registry"] + 3)
        self.assertEqual(self.batch["counts_after"]["coverage_json_files"], self.batch["counts_before"]["coverage_json_files"] + 2)


if __name__ == "__main__":
    unittest.main()
