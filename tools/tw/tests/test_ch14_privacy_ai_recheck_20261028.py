"""第14章個資、臉部辨識及AI代理高風險歷史實質再審契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reader_copy_test_support import assert_body_version_matches_review_or_cleanup, assert_reader_limits_match_review_or_cleanup
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, publication_report, validate_runtime

BASE = "93966ca110b119220f3d5093c74f9f3f967b37f9"
IDS = ("TW-14-007", "TW-14-008", "TW-14-009", "TW-14-010")
NEW_SOURCE_IDS = {
    "ch14_pdpa_current_20261028",
    "ch14_pdpc_amendment_faq_20251226",
    "ch14_ai_basic_law_20260114",
    "ch14_moda_ai_risk_framework_20260707",
    "ch14_acs_agent_safety_20260325",
    "ch14_acs_agent_incident_20260813",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


class Chapter14PrivacyAIRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = read("localization/ch14-privacy-ai-recheck-20261028.json")
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.manifest = {e["id"]: e for e in read("localization/manifest.json")["entries"]}
        cls.runtime = validate_runtime()
        cls.items = {i["id"]: i for i in cls.runtime["items"]}
        cls.sources = {s["id"]: s for s in cls.runtime["sources"]}
        cls.records = {
            r["id"]: r for r in cls.register["substantive_rechecks"] if r["id"] in IDS
        }
        cls.coverage = read("localization/tw-edition/coverage.json")

    def test_dynamic_progress_and_publication_state(self):
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(self.batch["base_main_sha"], BASE)
        self.assertEqual(before["substantive_rechecks"], 256)
        self.assertEqual(after["substantive_rechecks"], 260)
        self.assertEqual(before["runtime_sources"], 910)
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        # Batch counts are immutable historical snapshots; later batches may advance live totals.
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertEqual(before["source_registry"], 991)
        self.assertGreaterEqual(self.coverage["registry_sources"], after["source_registry"])
        self.assertEqual(before["json_files_checked"], 500)
        self.assertGreaterEqual(self.coverage["json_files_checked"], after["json_files_checked"])
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + 2)
        self.assertEqual(audit_drafts(), self.coverage)
        self.assertEqual(
            (after["core_completed"], after["core_total"], after["shared_reader_items"]),
            (278, 765, 289),
        )
        self.assertEqual(
            (after["topics_with_any_content"], after["topics_without_content"]),
            (498, 267),
        )
        self.assertEqual(
            (after["unresolved_source_ids"], after["unresolved_reference_occurrences"]),
            (114, 304),
        )
        self.assertFalse(after["publication_ready"])
        self.assertFalse(self.batch["publication_ready"])
        self.assertFalse(publication_report()["publication_ready"])
        self.assertEqual(self.batch["scope"]["new_core_ids"], [])

    def test_body_manifest_runtime_review_and_history_are_synchronized(self):
        self.assertEqual(set(self.records), set(IDS))
        for key in IDS:
            with self.subTest(id=key):
                item = self.items[key]
                record = self.records[key]
                entry = self.manifest[key]
                review = read(f"localization/reviews/{key}.json")
                raw = (ROOT / entry["target_path"]).read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                self.assertEqual(raw.decode("utf-8"), item["body"])
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(entry["verified_at"], "2026-10-28")
                self.assertEqual(review["target_sha256"], digest)
                assert_body_version_matches_review_or_cleanup(self, key, record["after_sha256"], digest)
                self.assertNotEqual(record["before_sha256"], record["after_sha256"])
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(review["reviewed_at"], "2026-10-28")
                self.assertEqual(review["review_due_at"], "2027-01-31")
                self.assertEqual(record["reviewed_at"], review["reviewed_at"])
                self.assertEqual(record["review_due_at"], review["review_due_at"])
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                assert_reader_limits_match_review_or_cleanup(self, item["id"], review["limits"][0])
                self.assertEqual(
                    {c["url"] for c in review["source_checks"]},
                    {self.sources[sid]["url"] for sid in item["source_ids"]},
                )
                for check in review["source_checks"]:
                    self.assertTrue(check["supporting_passage"])
                    self.assertTrue(check["retrieval_method"])
                validate_recheck_history(ROOT, record, item)

    def test_old_sources_and_prior_review_hashes_are_preserved(self):
        prior_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        prior_sources = {s["id"]: s for s in prior_runtime["sources"]}
        current_sources = {s["id"]: s for s in self.runtime["sources"]}
        prior_items = {i["id"]: i for i in prior_runtime["items"]}
        for key in IDS:
            with self.subTest(id=key):
                old = prior_items[key]
                old_review = git_bytes(BASE, f"localization/reviews/{key}.json")
                record = self.records[key]
                self.assertEqual(record["prior_review_sha256"], hashlib.sha256(old_review).hexdigest())
                self.assertEqual(record["before_sha256"], hashlib.sha256(old["body"].encode()).hexdigest())
                self.assertEqual(record["previous_source_ids"], old["source_ids"])
                for retired in record["retired_sources"]:
                    source = prior_sources[retired["id"]]
                    self.assertEqual(current_sources[retired["id"]], source)
                    self.assertEqual(
                        retired["prior_source_sha256"],
                        hashlib.sha256(
                            json.dumps(source, ensure_ascii=False, sort_keys=True).encode()
                        ).hexdigest(),
                    )
                    self.assertTrue(retired["reason"])
                    self.assertTrue(retired["replacement_ids"])

    def test_source_catalog_and_statistics_keep_scope_and_denominators(self):
        catalog = read("localization/tw-edition/sources/ch14-privacy-ai-recheck-20261028.json")
        self.assertEqual({row[0] for row in catalog["sources"]}, NEW_SOURCE_IDS)
        self.assertTrue(NEW_SOURCE_IDS.issubset(self.sources))
        for source_id in NEW_SOURCE_IDS:
            source = self.sources[source_id]
            self.assertEqual(source["accessed_at"], "2026-10-28")
            self.assertTrue(source["retrieval_method"])
            self.assertTrue(source["supports"])
        for key in IDS:
            records = self.records[key]["statistics_assessed"]
            batch_item = next(item for item in self.batch["items"] if item["id"] == key)
            self.assertEqual(batch_item["statistics_assessed"], records)
            self.assertTrue(records)
            for statistic in records:
                self.assertEqual(statistic["accessed_at"], "2026-10-28")
                self.assertIn("numerator_definition", statistic)
                self.assertIn("denominator_definition", statistic)
                self.assertIsNone(statistic["denominator"])
                self.assertTrue(statistic["limitations"])
                self.assertTrue(statistic["search_queries"])
                self.assertTrue(all(query["searched_at"] == "2026-10-28" for query in statistic["search_queries"]))
        face_stat = self.records["TW-14-009"]["statistics_assessed"][0]
        screened_sources = face_stat["screened_sources"]
        self.assertEqual(len(screened_sources), 2)
        self.assertEqual(screened_sources[0]["dataset_url"], "https://data.gov.tw/dataset/177794")
        self.assertEqual(
            screened_sources[0]["metadata_api_url"],
            "https://data.gov.tw/api/v2/rest/dataset/177794",
        )
        self.assertEqual(
            screened_sources[0]["csv_resource_url"],
            "https://opdadm.moi.gov.tw/api/v1/no-auth/resource/api/dataset/C2E5AD78-BF72-47A8-80C8-48A75B014E8E/resource/A509E6DE-691B-480E-A466-BE7FE8B7632B/download",
        )
        self.assertIn("HTTP 200", screened_sources[0]["retrieval_status"])
        self.assertEqual(screened_sources[0]["official_context_url"], "https://data.gov.tw/news/32629")
        self.assertEqual(
            screened_sources[0]["data_fields"],
            ["序號", "年度", "使用人次", "統計日期", "提供機關"],
        )
        self.assertEqual(screened_sources[0]["data_fields"], screened_sources[0]["csv_header"])
        self.assertNotIn("驗證方式", screened_sources[0]["data_fields"])
        self.assertIn("沒有驗證方式欄位", screened_sources[0]["exclusion_reason"])
        self.assertEqual(screened_sources[1]["url"], "https://www.wra.gov.tw/epaper/Article_Detail.aspx?n=30173&s=8631&sms=9942")
        self.assertEqual(screened_sources[1]["published_at"], "2023-09-29")
        self.assertIn("僅一個機關", screened_sources[1]["scope_limit"])
        app_screen = self.records["TW-14-007"]["statistics_assessed"][0]["screened_sources"]
        self.assertEqual(app_screen[0]["url"], "https://web.moda.gov.tw/ACS/press/news/press/19790")
        self.assertIn("4款", app_screen[0]["reported_scope"])
        rights_screen = self.records["TW-14-008"]["statistics_assessed"][0]["screened_sources"]
        self.assertEqual(rights_screen[0]["url"], "https://data.gov.tw/faqs/93189")
        self.assertIn("沒有請求件數", rights_screen[0]["scope_limit"])
        agent_screen = self.records["TW-14-010"]["statistics_assessed"][0]["screened_sources"]
        self.assertEqual(agent_screen[0]["url"], "https://moda.gov.tw/ACS/press/report/20430")
        self.assertEqual(agent_screen[0]["all_incidents_including_exercises"], 145)
        self.assertEqual(agent_screen[0]["exercises"], 62)
        self.assertIn("未列AI Agent事件數", agent_screen[0]["scope_limit"])
        self.assertIsNone(self.records["TW-14-007"]["statistics_assessed"][0]["value"])
        self.assertIsNone(self.records["TW-14-008"]["statistics_assessed"][0]["value"])
        self.assertIsNone(self.records["TW-14-009"]["statistics_assessed"][0]["value"])
        agent_event = self.records["TW-14-010"]["statistics_assessed"][0]
        self.assertEqual(agent_event["value"]["officially_described_attack_waves"], 1)
        self.assertIsNone(agent_event["denominator"])
        self.assertIn("非一般民眾", agent_event["data_type"])

    def test_law_risk_and_frequency_are_separate(self):
        privacy = self.items["TW-14-007"]["body"]
        rights = self.items["TW-14-008"]["body"]
        face = self.items["TW-14-009"]["body"]
        agent = self.items["TW-14-010"]["body"]
        self.assertIn("同意」只是其中之一", privacy)
        self.assertIn("部分修正條文尚未生效", privacy)
        self.assertIn("第10條請求原則上應於15日內", rights)
        self.assertIn("第11條請求原則上於30日內", rights)
        self.assertIn("都是決定如何處理請求的期限，不是保證資料已", rights)
        self.assertIn("第14條", rights)
        self.assertIn("第6條特別列舉", face)
        self.assertIn("不代表每個場域依法都必須提供替代方式", face)
        self.assertIn("沒有一條可概括所有服務", face)
        self.assertIn("2026-01-14", agent)
        self.assertIn("第19條規範政府使用 AI", agent)
        self.assertIn("B6", agent)
        self.assertIn("多代理連鎖反應", agent)
        self.assertIn("不等於私人使用者一律被禁止", agent)
        self.assertIn("一波境外攻擊政府機關事件", agent)
        self.assertIn("個人機率", agent)
        self.assertTrue(all(self.records[key]["taiwan_context_assessment"]["independent_of_frequency"] for key in IDS))
        self.assertTrue(all(self.records[key]["reviewer_limit"] for key in IDS))
        self.assertTrue(self.batch["professional_review_pending"])


if __name__ == "__main__":
    unittest.main()
