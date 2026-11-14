"""逐題保留有用海外研究，補回台灣職安長期暴露及追蹤檢查。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))

from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import validate_runtime

BASE = "c2d62828028a01322bb24aa77b74118a4502712f"
BATCH = "localization/topic-fidelity-fraud-osh-recheck-20261114.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
SOURCE_FILE = "localization/tw-edition/sources/topic-fidelity-fraud-osh-recheck-20261114.json"
ITEMS = ("TW-17-004", "TW-19-009", "TW-19-010")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class TopicFidelityFraudOshRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        cls.reviews = {item_id: read(f"localization/reviews/{item_id}.json") for item_id in ITEMS}
        cls.register = read(REGISTER)
        cls.batch = read(BATCH)

    def test_reviews_are_hash_bound_and_append_only(self):
        for item_id in ITEMS:
            with self.subTest(item_id=item_id):
                target = self.items[item_id]["target_path"]
                before_body = git_bytes(BASE, target)
                before_review = git_bytes(BASE, f"localization/reviews/{item_id}.json")
                body = (ROOT / target).read_bytes()
                review = self.reviews[item_id]
                record = next(
                    row for row in reversed(self.register["substantive_rechecks"])
                    if row["id"] == item_id and row["reviewed_at"] == "2026-11-14"
                )
                item = next(row for row in self.batch["items"] if row["id"] == item_id)
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["before_sha256"], sha(before_body))
                self.assertEqual(record["previous_body"].encode("utf-8"), before_body)
                self.assertEqual(record["prior_review_sha256"], sha(before_review))
                self.assertEqual(record["after_sha256"], sha(body))
                self.assertEqual(item["after_sha256"], sha(body))
                self.assertEqual(item["review_sha256"], sha((ROOT / f"localization/reviews/{item_id}.json").read_bytes()))
                self.assertEqual(review["target_sha256"], sha(body))
                self.assertEqual(review["source_reviewed_sha256"], sha(body))
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["source_ids"], self.items[item_id]["source_ids"])
                self.assertEqual(self.manifest[item_id]["sources"], self.items[item_id]["source_ids"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertEqual(set(self.items[item_id]["source_ids"]) - set(self.sources), set())
                body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body.decode("utf-8")))
                registered_urls = {self.sources[key]["url"] for key in self.items[item_id]["source_ids"]}
                self.assertEqual(body_urls, registered_urls)
                validate_recheck_history(ROOT, record, self.items[item_id])

    def test_foreign_fraud_research_is_scoped_and_not_used_as_taiwan_rate(self):
        body = self.items["TW-17-004"]["body"]
        review = self.reviews["TW-17-004"]
        self.assertIn("我現在不決定，會自己查證後再回覆", body)
        self.assertIn("116名65至85歲成人及115名30至40歲成人", body)
        self.assertIn("511人接到後續模擬電話詐騙", body)
        self.assertIn("沒有實際付款或財損", body)
        self.assertIn("不代表台灣受騙率", body)
        self.assertIn("不必把是否決定交由家人代替", body)
        self.assertEqual(len(review["statistics_assessed"]), 3)
        self.assertIn("未測試文中建議句", review["statistics_assessed"][1]["limitations"])
        self.assertIsNone(review["statistics_assessed"][0]["denominator"])

    def test_occupational_followup_is_limited_to_listed_work_and_approved_claims(self):
        body = self.items["TW-19-009"]["body"]
        self.assertIn("附表二所列追蹤檢查作業", body)
        self.assertIn("加保年資連續滿1年", body)
        self.assertIn("離職或退保後", body)
        self.assertIn("先向勞保局提出申請並等審查", body)
        self.assertIn("不是每位離職或轉職者都有的「離職健檢」", body)
        self.assertIn("2028-01-01", body)
        self.assertEqual(self.reviews["TW-19-009"]["taiwan_context_assessment"]["decision"],
                         "preserve_original_health_topic_with_taiwan_exposure_and_followup")

    def test_workplace_article_restores_chronic_topic_and_keeps_immediate_exit_rule(self):
        body = self.items["TW-19-010"]["body"]
        review = self.reviews["TW-19-010"]
        self.assertIn("長期接觸粉塵、噪音、溶劑或化學品", body)
        self.assertIn("第18條的自行停工退避權，適用於有立即發生危險之虞", body)
        for criterion in ("死亡", "罹災3人以上", "至少1人需住院治療", "中央主管機關另行公告"):
            self.assertIn(criterion, body)
        self.assertIn("未經司法機關或勞動檢查機構許可，不得移動或破壞現場", body)
        osh_act_check = next(
            check for check in review["source_checks"]
            if check["url"] == "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0060001"
        )
        self.assertIn("第37條第2項限定", osh_act_check["claim"])
        self.assertIn("罹災人數3人以上", osh_act_check["supporting_passage"])
        self.assertIn("第39條允許工作者", review["taiwan_context_assessment"]["legal_status"])
        self.assertIn("全產業重大職災死亡193人，其中營造業102人", body)
        self.assertIn("營造業死亡事故約62%屬墜落", body)
        self.assertIn("走訪60家事業單位", body)
        self.assertIn("305名粉塵作業勞工", body)
        self.assertIn("4人經評估有疑似與工作相關的肺部健康異常", body)
        self.assertIn("不能據此計算台灣矽肺症盛行率", body)
        self.assertIn("osha_2026h1_fatality_stats", review["retired_sources"][0]["id"])
        self.assertEqual(review["retired_sources"][0]["replacement_ids"], ["osha_2026q3_fatality_stats"])

    def test_policy_batch_and_live_coverage_counts_are_consistent(self):
        policy = (ROOT / "localization/TAIWAN_REUSE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("### 逐題篩選順序與正文去留", policy)
        self.assertIn("不要從「這個資料是外國的」直接跳到保留或刪除", policy)
        self.assertIn("不設單一分數或「海外研究一律收錄」規則", policy)
        self.assertIn("每一題都要重新判斷", policy)
        # This batch snapshot is immutable. Reconcile it with the next append-only
        # batch, then compare the live state with that later batch's recorded result.
        remote_travel_batch = read("localization/topic-fidelity-remote-travel-20261114.json")
        eldercare_batch = read("localization/topic-fidelity-eldercare-prepayment-20261114.json")
        reverse_mortgage_batch = read("localization/topic-fidelity-reverse-mortgage-recheck-20261114.json")
        later_before = remote_travel_batch["counts_before"]
        for old_key, later_key in (
            ("runtime_items", "runtime_items"),
            ("runtime_sources", "runtime_sources"),
            ("source_registry", "registry_sources"),
            ("review_rechecks", "review_rechecks"),
            ("coverage_json_files", "coverage_json_files"),
            ("publication_completed_entries", "publication_completed_entries"),
            ("publication_ready", "publication_ready"),
        ):
            self.assertEqual(self.batch["counts_after"][old_key], later_before[later_key])
        eldercare_before = eldercare_batch["counts_before"]
        for remote_key, eldercare_key in (
            ("runtime_items", "runtime_items"),
            ("runtime_sources", "runtime_sources"),
            ("registry_sources", "source_registry"),
            ("review_rechecks", "review_rechecks"),
            ("coverage_json_files", "coverage_json_files"),
            ("publication_completed_entries", "publication_completed_entries"),
            ("publication_ready", "publication_ready"),
        ):
            self.assertEqual(remote_travel_batch["counts_after"][remote_key], eldercare_before[eldercare_key])
        # Preserve the eldercare batch as an immutable historical snapshot and
        # reconcile it with the next batch's recorded starting point. The newest
        # batch is responsible for comparing current runtime/coverage to live data.
        later_counts = eldercare_batch["counts_after"]
        current_before = reverse_mortgage_batch["counts_before"]
        for key in (
            "runtime_items", "runtime_sources", "source_registry", "review_rechecks",
            "coverage_json_files", "publication_completed_entries", "publication_ready",
        ):
            self.assertEqual(later_counts[key], current_before[key])
        self.assertFalse(self.batch["counts_after"]["publication_ready"])
        catalog = read(SOURCE_FILE)["sources"]
        self.assertEqual(len(catalog), len(self.batch["new_source_ids"]))
        self.assertEqual({row[0] for row in catalog}, set(self.batch["new_source_ids"]))

    def test_retired_stat_source_object_is_unchanged(self):
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_sources = {source["id"]: source for source in old_runtime["sources"]}
        retired = self.reviews["TW-19-010"]["retired_sources"][0]
        old = old_sources[retired["id"]]
        self.assertEqual(self.sources[retired["id"]], old)
        self.assertEqual(retired["prior_source_sha256"], sha(json.dumps(old, ensure_ascii=False, sort_keys=True).encode("utf-8")))
        self.assertFalse(self.batch["counts_after"]["publication_ready"])


if __name__ == "__main__":
    unittest.main()
