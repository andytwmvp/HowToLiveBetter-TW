"""第2章電子煙再審：主題保真、台灣法規、研究證據與歷史追溯契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from review_contract import ROOT, publication_report, validate_runtime

BASE = "463559ba83a4212480e793780ec669b11f4468dc"
DATE = "2026-11-18"
ITEM_ID = "TW-02-006"
BATCH_PATH = "localization/ch02-ecig-topic-fidelity-recheck-20261118.json"
SOURCE_BUNDLE_PATH = "localization/tw-edition/sources/ch02-ecig-topic-fidelity-recheck-20261118.json"
ARTICLE_PATH = "locales/zh-TW/book/ch02/TW-02-006.md"
REVIEW_PATH = "localization/reviews/TW-02-006.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def git_json(revision, path):
    return json.loads(git_bytes(revision, path))


class EcigTopicFidelityRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read_json("localization/manifest.json")
        cls.manifest_items = {row["id"]: row for row in cls.manifest["entries"]}
        cls.runtime = validate_runtime()
        cls.runtime_items = {row["id"]: row for row in cls.runtime["items"]}
        cls.runtime_sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.review = read_json(REVIEW_PATH)
        cls.register = read_json(REGISTER_PATH)
        cls.batch = read_json(BATCH_PATH)
        cls.batch_item = next(row for row in cls.batch["items"] if row["id"] == ITEM_ID)
        cls.source_bundle = read_json(SOURCE_BUNDLE_PATH)
        cls.chapter = read_json("localization/tw-edition/chapters/02.json")
        cls.chapter_readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        cls.article_bytes = (ROOT / ARTICLE_PATH).read_bytes()
        cls.article = cls.article_bytes.decode("utf-8")
        cls.article_sha = hashlib.sha256(cls.article_bytes).hexdigest()
        cls.latest_recheck = next(
            row for row in reversed(cls.register["substantive_rechecks"])
            if row["id"] == ITEM_ID and row["reviewed_at"] == DATE
        )

    def test_article_restores_the_research_question_and_keeps_taiwan_actions_clear(self):
        item = self.runtime_items[ITEM_ID]
        self.assertEqual(item["body"], self.article)
        self.assertEqual(item["title"], "電子煙與戒菸研究：台灣規範和合法戒菸協助")
        self.assertIn("2026年更新的Cochrane系統性回顧", self.article)
        self.assertIn("不是在台灣使用電子煙的建議", self.article)
        self.assertIn("合法的協助方式", self.article)
        self.assertNotIn("AI輔助", self.article)
        self.assertNotIn("本批", self.article)
        self.assertNotIn("工作分支", self.article)
        chapter_row = next(row for row in self.chapter["entries"] if row[0] == 6)
        self.assertEqual(chapter_row[1], item["title"])
        self.assertIn("RR為1.61", chapter_row[2])
        self.assertIn("在學樣本", chapter_row[4])
        self.assertIn("TW-02-006.md", self.chapter_readme)
        self.assertIn(item["title"], self.chapter_readme)

    def test_research_statistics_are_bound_to_the_fixed_pub11_version(self):
        statistics = {row["topic"]: row for row in self.review["statistics_assessed"]}
        nrt = statistics["含尼古丁電子煙相較尼古丁替代療法的戒菸成效"]
        self.assertEqual(nrt["value"]["studies"], 11)
        self.assertEqual(nrt["value"]["participants"], 4114)
        self.assertEqual(nrt["value"]["relative_risk"], 1.61)
        self.assertEqual(nrt["value"]["95_CI"], [1.23, 2.12])
        self.assertEqual(nrt["value"]["certainty"], "高")
        self.assertIn("2026年1月1日", nrt["period"])
        self.assertIn("不是台灣療效或個人成功率", nrt["limitations"])

        support = statistics["含尼古丁電子煙相較單獨行為支持或沒有支持的戒菸成效"]
        self.assertEqual(support["value"]["studies"], 11)
        self.assertEqual(support["value"]["participants"], 7214)
        self.assertEqual(support["value"]["relative_risk"], 1.75)
        self.assertEqual(support["value"]["95_CI"], [1.39, 2.2])
        self.assertEqual(support["value"]["certainty"], "低")
        self.assertIn("偏差風險", support["limitations"])
        self.assertIn("7,214人", self.article)
        self.assertIn("相對風險1.75", self.article)

        sae = statistics["含尼古丁電子煙相較尼古丁替代療法的嚴重不良事件"]
        self.assertEqual(sae["value"]["studies"], 10)
        self.assertEqual(sae["value"]["participants"], 4045)
        self.assertEqual(sae["value"]["risk_difference"], 0.01)
        self.assertEqual(sae["value"]["95_CI"], [-0.01, 0.02])
        self.assertIn("約1個百分點", self.article)

        source = next(
            row for row in self.review["source_checks"]
            if row["source_id"] == "tw02_cochrane_ecig_cessation_20261118"
        )
        self.assertIn("CD010216.pub11", source["retrieval_method"])
        self.assertIn("Flinders University ResearchNow", source["retrieval_method"])
        self.assertIn("不是 DOI 固定版 pub11", source["retrieval_method"])

    def test_law_and_proposal_are_separated_and_claims_stay_in_scope(self):
        checks = {row["source_id"]: row for row in self.review["source_checks"]}
        law = checks["tw02_moj_tobacco_hazards_act_20261107"]
        self.assertIn("第15條", law["supporting_passage"])
        self.assertIn("第40條", law["supporting_passage"])
        self.assertIn("不對其他法律或個案作擴張判斷", law["retrieval_method"])
        proposal = checks["tw02_hpa_ecig_amendment_20261118"]
        self.assertIn("由立法院審議中", proposal["supporting_passage"])
        self.assertIn("由立法院審議", self.article)
        self.assertIn("草案不能當成已公布施行的法律", self.article)
        self.assertIn("產品若涉及其他法規，仍須另外判斷", self.article)
        self.assertIn("2023年2月15日公布", self.article)
        self.assertIn("3月22日起施行", self.article)
        self.assertIn("新臺幣2,000元以上、1萬元以下", self.article)
        self.assertIn("432處回收桶", self.article)
        self.assertIn("tw02_hpa_ecig_return_20261118", self.runtime_items[ITEM_ID]["source_ids"])

    def test_review_hashes_sources_and_history_are_append_only(self):
        manifest = self.manifest_items[ITEM_ID]
        item = self.runtime_items[ITEM_ID]
        review_sha = hashlib.sha256((ROOT / REVIEW_PATH).read_bytes()).hexdigest()
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.latest_recheck["prior_revision"], "e2f0fe13bc91606ebde866fb9996e638dacabf42")
        self.assertEqual(self.latest_recheck["before_sha256"], self.batch_item["before_sha256"])
        self.assertEqual(self.latest_recheck["after_sha256"], self.article_sha)
        self.assertEqual(self.review["target_sha256"], self.article_sha)
        self.assertEqual(self.review["source_reviewed_sha256"], self.article_sha)
        self.assertEqual(self.latest_recheck["review_sha256"], review_sha)
        self.assertEqual(self.batch_item["review_sha256"], review_sha)
        self.assertEqual(manifest["status"], "verified")
        self.assertEqual(manifest["verified_at"], DATE)
        self.assertEqual(item["reviewed_at"], DATE)
        self.assertEqual(item["review_due_at"], "2027-02-18")

        previous_body = self.latest_recheck["previous_body"].encode("utf-8")
        self.assertEqual(hashlib.sha256(previous_body).hexdigest(), self.latest_recheck["before_sha256"])
        self.assertEqual(previous_body, git_bytes(BASE, ARTICLE_PATH))
        previous_review = self.latest_recheck["previous_review_snapshot"]
        self.assertEqual(previous_review, git_json(BASE, REVIEW_PATH))
        self.assertEqual(
            hashlib.sha256(json.dumps(previous_review, ensure_ascii=False, indent=2).encode("utf-8") + b"\n").hexdigest(),
            self.latest_recheck["prior_review_sha256"],
        )

        base_register = git_json(BASE, REGISTER_PATH)
        current_rows = self.register["substantive_rechecks"]
        base_rows = base_register["substantive_rechecks"]
        self.assertEqual(current_rows[:len(base_rows)], base_rows)
        self.assertEqual(len(current_rows) - len(base_rows), 1)
        self.assertEqual(self.review["professional_review"]["required"], True)
        self.assertEqual(self.review["professional_review"]["obtained"], False)
        self.assertEqual(self.latest_recheck["status"], "ai_source_rechecked_professional_pending")

    def test_manifest_runtime_source_bundle_and_reader_navigation_match(self):
        manifest = self.manifest_items[ITEM_ID]
        item = self.runtime_items[ITEM_ID]
        bundled = {row[0]: row for row in self.source_bundle["sources"]}
        new_ids = set(self.batch["new_source_ids"])
        self.assertEqual(set(bundled), new_ids)
        self.assertEqual(self.source_bundle["checked_at"], DATE)
        self.assertEqual(set(self.batch_item["new_source_ids"]), new_ids)
        self.assertTrue(new_ids.issubset(self.runtime_sources))
        self.assertTrue(set(item["source_ids"]).issubset(self.runtime_sources))
        self.assertEqual(manifest["sources"], item["source_ids"])
        self.assertEqual(self.review["source_ids"], item["source_ids"])
        self.assertEqual(self.batch_item["source_ids"], item["source_ids"])
        self.assertEqual(self.review["source_bundle_sha256"], hashlib.sha256((ROOT / SOURCE_BUNDLE_PATH).read_bytes()).hexdigest())
        self.assertEqual(self.latest_recheck["source_bundle_sha256"], self.review["source_bundle_sha256"])
        for source_id, row in bundled.items():
            with self.subTest(source_id=source_id):
                source = self.runtime_sources[source_id]
                self.assertEqual(row, [source[key] for key in ("id", "title", "url", "supports")])
        self.assertEqual(set(item["source_ids"]), {row["source_id"] for row in self.review["source_checks"]})
        self.assertIn("tw02_cochrane_ecig_cessation_20261118", item["source_ids"])

    def test_counts_match_current_data_without_promoting_publication_gate(self):
        baseline_coverage = git_json(BASE, "localization/tw-edition/coverage.json")
        baseline_runtime = git_json(BASE, "localization/tw-edition/runtime.json")
        baseline_manifest = git_json(BASE, "localization/manifest.json")
        baseline_register = git_json(BASE, REGISTER_PATH)
        coverage = read_json("localization/tw-edition/coverage.json")
        report = audit_drafts()
        counts_before = self.batch["counts_before"]
        counts_after = self.batch["counts_after"]
        self.assertEqual(coverage, report)
        self.assertEqual(counts_before["manifest_entries"], len(baseline_manifest["entries"]))
        self.assertEqual(counts_before["verified_core_entries"], sum(row["status"] == "verified" for row in baseline_manifest["entries"]))
        self.assertEqual(counts_before["publication_completed_entries"], baseline_coverage["publication_completed_entries"])
        self.assertEqual(counts_before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(counts_before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(counts_before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(counts_before["coverage_json_files"], baseline_coverage["json_files_checked"])
        self.assertEqual(counts_before["review_rechecks"], len(baseline_register["substantive_rechecks"]))
        self.assertEqual(counts_before["publication_ready"], False)

        self.assertEqual(counts_after["manifest_entries"], counts_before["manifest_entries"])
        self.assertEqual(counts_after["verified_core_entries"], counts_before["verified_core_entries"])
        self.assertEqual(counts_after["publication_completed_entries"], counts_before["publication_completed_entries"])
        self.assertEqual(counts_after["runtime_items"], counts_before["runtime_items"])
        self.assertEqual(counts_after["runtime_sources"], counts_before["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(counts_after["source_registry"], counts_before["source_registry"] + len(self.batch["new_source_ids"]))
        self.assertEqual(counts_after["coverage_json_files"], counts_before["coverage_json_files"] + 2)
        self.assertEqual(counts_after["review_rechecks"], counts_before["review_rechecks"] + 1)
        # counts_after is the snapshot at this batch. Later batches may add
        # sources; the current coverage/report pair remains the live contract.
        self.assertGreaterEqual(coverage["registry_sources"], counts_after["source_registry"])
        self.assertGreaterEqual(coverage["json_files_checked"], counts_after["coverage_json_files"])
        current_verified_entries = sum(row["status"] == "verified" for row in self.manifest["entries"])
        self.assertEqual(coverage["publication_completed_entries"], current_verified_entries)
        self.assertGreaterEqual(
            coverage["publication_completed_entries"],
            counts_after["publication_completed_entries"],
        )
        self.assertEqual(coverage["publication_ready"], False)
        self.assertEqual(publication_report()["publication_ready"], False)


if __name__ == "__main__":
    unittest.main()
