"""第1章主題保真度再審：保留台灣規範，逐題判斷外地內容是否適用。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))

from retroactive_audit import validate_recheck_history
from review_contract import validate_runtime

BASE = "7c41a725a69f6d4dbd7b5dac614dcb4aaaab5e9c"
STAGE_SNAPSHOT = "c2d62828028a01322bb24aa77b74118a4502712f"
BATCH = "localization/topic-fidelity-dechina-recheck-20261112.json"
REGISTER = "localization/retroactive-review-register-20261019.json"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Chapter1TopicFidelityRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {x["id"]: x for x in cls.runtime["items"]}
        cls.sources = {x["id"]: x for x in cls.runtime["sources"]}
        cls.manifest = {x["id"]: x for x in read("localization/manifest.json")["entries"]}
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in ("TW-01-035", "TW-01-041")}
        cls.register = read(REGISTER)
        cls.batch = read(BATCH)

    def test_rechecks_are_append_only_hash_bound_and_source_complete(self):
        for item_id in ("TW-01-035", "TW-01-041"):
            with self.subTest(item_id=item_id):
                path = f"locales/zh-TW/book/ch01/{item_id}.md"
                prior_body = git_bytes(BASE, path)
                prior_review = git_bytes(BASE, f"localization/reviews/{item_id}.json")
                body = (ROOT / path).read_bytes()
                record = next(
                    row for row in reversed(self.register["substantive_rechecks"])
                    if row["id"] == item_id and row["reviewed_at"] == "2026-11-12"
                )
                item = self.items[item_id]
                review = self.reviews[item_id]
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["before_sha256"], sha(prior_body))
                self.assertEqual(record["previous_body"], prior_body.decode("utf-8"))
                self.assertEqual(record["prior_review_sha256"], sha(prior_review))
                self.assertEqual(record["prior_reviewed_at"], json.loads(prior_review)["reviewed_at"])
                self.assertEqual(record["after_sha256"], sha(body))
                self.assertEqual(review["target_sha256"], sha(body))
                self.assertEqual(review["source_reviewed_sha256"], sha(body))
                self.assertEqual(review["review_due_at"], "2027-02-12")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertEqual(set(item["source_ids"]) - set(self.sources), set())
                body_urls = set(re.findall(r"\]\((https://[^)]+)\)", body.decode("utf-8")))
                registered_urls = {self.sources[key]["url"] for key in item["source_ids"]}
                self.assertEqual(body_urls, registered_urls)
                if item_id == "TW-01-035":
                    self.assertEqual(self.manifest[item_id]["sources"], [self.sources[key]["url"] for key in item["source_ids"]])
                else:
                    self.assertEqual(self.manifest[item_id]["sources"], item["source_ids"])
                validate_recheck_history(ROOT, record, item)
        self.assertFalse(self.reviews["TW-01-035"]["professional_review"]["obtained"])
        self.assertFalse(self.reviews["TW-01-041"]["professional_review"]["obtained"])

    def test_paid_kidney_seller_research_is_restored_without_weakening_taiwan_law(self):
        body = self.items["TW-01-035"]["body"]
        self.assertIn("第12條要求移植器官的提供與取得無償", body)
        self.assertIn("第16條可能負刑事責任", body)
        self.assertIn("新臺幣9萬元以上45萬元以下罰鍰", body)
        self.assertIn("印度清奈", body)
        self.assertIn("305名", body)
        self.assertIn("96%", body)
        self.assertIn("1,070美元", body)
        self.assertIn("四分之三", body)
        self.assertIn("86%", body)
        self.assertIn("79%", body)
        self.assertIn("不是臺灣發生率", body)
        self.assertIn("摘要沒有列出各項結果的有效答題人數", body)
        self.assertIn("不能據此證明因果", body)
        self.assertIn("ch01_organ_india_jama_2002", self.items["TW-01-035"]["source_ids"])
        stat = self.reviews["TW-01-035"]["statistics_assessed"][0]
        self.assertEqual(stat["value"]["self_reported_health_decline_percent"], 86)
        self.assertEqual(stat["geographic_scope"], "印度清奈單一地區")
        self.assertIn("未列各題有效答題分母", stat["denominator"])
        self.assertIsNone(self.reviews["TW-01-035"]["statistics_assessed"][1]["value"])
        self.assertTrue(self.reviews["TW-01-035"]["taiwan_context_assessment"]["legal_status"])

    def test_rare_ice_topic_stays_replaced_by_taiwan_mountain_guidance(self):
        body = self.items["TW-01-041"]["body"]
        fidelity = self.reviews["TW-01-041"]["taiwan_context_assessment"]
        topic_review = self.reviews["TW-01-041"]["topic_fidelity_review"]
        self.assertEqual(fidelity["decision"], "replace_low_relevance_scenario_with_local_analogue")
        self.assertIn("可供一般民眾上冰活動的天然結冰湖面或河面", fidelity["topic_fidelity_assessment"])
        self.assertIn("臺灣高山雪地、步道或道路結冰則是不同的安全問題", fidelity["topic_fidelity_assessment"])
        self.assertEqual(topic_review["reader_content_decision"], "不恢復至讀者正文；保留臺灣登山安全與求援指引作為在地相近需求。")
        self.assertEqual(set(topic_review["reviewed_sources_not_used"]), {
            "ch01_ice_parks_banff_natural_2025",
            "ch01_ice_canada_coast_guard_20260217",
            "ch01_ice_canadian_redcross_2014",
        })
        self.assertIn("高山天候快速變化", body)
        self.assertIn("撥119或112求援", body)
        self.assertNotIn("天然冰面", body)
        self.assertNotIn("加拿大", body)
        self.assertIn("502件、695人", body)
        self.assertIn("531件、涉及727人及34人死亡", body)
        self.assertIn("兩份資料未說明差異原因", body)
        self.assertIn("不能混算或據此推估個人風險", body)
        mountain_stats = self.reviews["TW-01-041"]["statistics_assessed"][0]
        self.assertIsNone(mountain_stats["denominator"])
        self.assertIn("沒有登山暴露分母", mountain_stats["limitations"])

    def test_topic_fidelity_policy_requires_reader_value_review_not_bulk_restoration(self):
        policy = (ROOT / "localization/TAIWAN_REUSE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("### 逐題篩選順序與正文去留", policy)
        self.assertIn("來源可信只是必要條件，不代表每筆資料都要放進正文", policy)
        self.assertIn("不設單一分數或「海外研究一律收錄」規則", policy)
        self.assertIn("臺灣讀者也可能在家中或旅宿泡澡", policy)
        self.assertIn("不必把冰面操作整批搬回", policy)
        self.assertIn("不能延伸成其他主題的自動規則", policy)

    def test_retired_sources_are_preserved_and_batch_counts_remain_historical(self):
        runtime_at_base = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_sources = {x["id"]: x for x in runtime_at_base["sources"]}
        for record in self.batch["items"]:
            for retired in record["retired_sources"]:
                old = old_sources[retired["id"]]
                self.assertEqual(retired["prior_source_sha256"], sha(json.dumps(old, ensure_ascii=False, sort_keys=True).encode("utf-8")))
                self.assertEqual(self.sources[retired["id"]], old)
        # Historical completion snapshots stay tied to the main revision at the
        # end of that stage; later batches must not rewrite old counts to today's totals.
        snapshot_runtime = json.loads(git_bytes(STAGE_SNAPSHOT, "localization/tw-edition/runtime.json"))
        snapshot_manifest = json.loads(git_bytes(STAGE_SNAPSHOT, "localization/manifest.json"))
        snapshot_coverage = json.loads(git_bytes(STAGE_SNAPSHOT, "localization/tw-edition/coverage.json"))
        snapshot_register = json.loads(git_bytes(STAGE_SNAPSHOT, REGISTER))
        expected = {
            "manifest_entries": len(snapshot_manifest["entries"]),
            "verified_core_entries": sum(row.get("status") == "verified" for row in snapshot_manifest["entries"]),
            "runtime_items": len(snapshot_runtime["items"]),
            "runtime_sources": len(snapshot_runtime["sources"]),
            "source_registry": snapshot_coverage["registry_sources"],
            "review_rechecks": len(snapshot_register["substantive_rechecks"]),
            "coverage_json_files": snapshot_coverage["json_files_checked"],
            "unresolved_source_id_kinds": len(snapshot_coverage["unresolved_source_ids"]),
            "unresolved_reference_occurrences": snapshot_coverage["unresolved_reference_occurrences"],
            "publication_completed_entries": snapshot_coverage["publication_completed_entries"],
            "publication_ready": snapshot_coverage["publication_ready"],
        }
        self.assertEqual(self.batch["counts_after"], expected)


if __name__ == "__main__":
    unittest.main()
