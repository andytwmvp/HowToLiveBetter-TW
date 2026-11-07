"""2026-11-07 Taiwan travel, housing finance, and subscription recheck."""
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


BASE = "3cac9b35a0a3079c66b92c223a460cd6238e4e81"
IDS = ("TW-15-016", "TW-21-008", "TW-21-009", "TW-21-010", "TW-26-013")
NEW_SOURCES = {
    "thb_idp_application_20261107",
    "nia_immigration_act_20261107",
    "nia_immigration_agencies_20261106",
    "moe_overseas_study_contract_20240613",
    "passport_act_20210120",
    "nta_youthloan3_faq_20260728",
    "nta_youthloan3_release_20260728",
    "moda_online_retail_terms_20160715",
    "moda_internet_teaching_terms_20191115",
    "moda_retail_subscription_draft_20260116",
    "cpc_app_subscription_cancel_2026",
}
EXPECTED_GEOGRAPHIC_SCOPE = {
    "TW-15-016": "臺灣青年安心成家購屋優惠貸款3.0申貸制度；房價上限依臺北市、新北市及新竹縣市、其他縣市區分，不代表其他住宅貸款方案。",
    "TW-21-008": "臺灣駕照申領程序及各目的地道路交通規則；境外事故發生地依旅客實際駕駛的國家或地區而異。",
    "TW-21-009": "臺灣移民法規所管制的境內移民代辦業務及臺灣留學服務契約；簽證與入學結果另依目的地及學校規則。",
    "TW-21-010": "臺灣居民出具海外邀請或費用文件及臺灣護照的合法使用；簽證申請規則依目的地國家和簽證類別。",
    "TW-26-013": "臺灣消費者使用的網路訂閱服務；應依服務產業、付款平台、交易方式及個別契約例外分層。",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class TravelHousingSubscriptionRecheckTests(unittest.TestCase):
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
            if item.get("reviewed_at") == "2026-11-07" and item.get("id") in IDS
        }
        cls.batch = read("localization/travel-visa-housing-subscription-recheck-20261107.json")

    def test_articles_sources_reviews_manifest_and_append_only_history_match(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(set(self.batch["rechecked_ids"]), set(IDS))
        self.assertEqual(self.batch["new_core_ids"], [])
        self.assertEqual(set(self.records), set(IDS))

        for key in IDS:
            with self.subTest(id=key):
                item = self.items[key]
                review = read(f"localization/reviews/{key}.json")
                record = self.records[key]
                body = (ROOT / item["target_path"]).read_text(encoding="utf-8")
                body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
                batch_item = next(row for row in self.batch["items"] if row["id"] == key)

                self.assertEqual(item["body"], body)
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(batch_item["after_sha256"], body_sha)
                self.assertNotEqual(record["before_sha256"], body_sha)
                self.assertEqual(review["reviewed_at"], "2026-11-07")
                self.assertEqual(review["review_due_at"], "2027-02-07")
                self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["statistics_assessed"], review["statistics_assessed"])
                self.assertTrue(record["previous_review_claims"])
                self.assertTrue(record["prior_review_sha256"])
                self.assertTrue(record["prior_revision"])

                previous_review = subprocess.check_output(
                    ["git", "show", f"{BASE}:localization/reviews/{key}.json"], cwd=ROOT
                )
                self.assertEqual(
                    record["prior_review_sha256"], hashlib.sha256(previous_review).hexdigest()
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
                for stat in review["statistics_assessed"]:
                    self.assertIsNone(stat["value"])
                    self.assertIsNone(stat["denominator"])
                    self.assertTrue(stat["population"])
                    self.assertTrue(stat["numerator"])
                    self.assertTrue(stat["event_definition"])
                    self.assertTrue(stat["sources_examined_for_frequency"])
                    self.assertEqual(stat["accessed_at"], "2026-11-07")
                    self.assertEqual(stat["geographic_scope"], EXPECTED_GEOGRAPHIC_SCOPE[key])
                validate_recheck_history(ROOT, record, item)

    def test_reader_articles_and_chapter_navigation_use_taiwan_copy(self):
        bodies = {key: self.items[key]["body"] for key in IDS}
        combined = "\n".join(bodies.values())
        for phrase in ("AI輔助", "本批", "累計", "臺灣版尚在", "僅在此 fork", "編者摘要"):
            self.assertNotIn(phrase, combined)

        loan = bodies["TW-15-016"]
        for phrase in ("不是只給第一次買房的人", "曾經持有房屋", "2026年8月1日", "一段式機動利率", "不代表銀行會核准到上限"):
            self.assertIn(phrase, loan)
        chapter15 = (ROOT / "locales/zh-TW/book/ch15/README.md").read_text(encoding="utf-8")
        self.assertIn("申辦青安3.0前先核對資格、月付與自備款", chapter15)
        self.assertNotIn("首購優惠", chapter15)

        driving = bodies["TW-21-008"]
        for phrase in ("新臺幣250元", "2吋照片2張", "日本", "不能拿臺灣申領的國際駕照直接替代", "不能據此估算個人事故機率"):
            self.assertIn(phrase, driving)

        agents = bodies["TW-21-009"]
        for phrase in ("第55、56條", "新臺幣20萬元以上、100萬元以下", "不是同一件事", "至少有5日契約審閱期", "不能直接套用到所有旅行社或留學服務"):
            self.assertIn(phrase, agents)

        invitation = bodies["TW-21-010"]
        for phrase in ("《護照條例》第5條", "第31條", "不等同於邀請函寫錯", "美國B類訪客簽證", "不能估算個人遭遇機率"):
            self.assertIn(phrase, invitation)

        subscription = bodies["TW-26-013"]
        for phrase in ("7日內解除契約", "事先同意開始提供", "刪除應用程式通常不會終止訂閱", "草案不能單憑預告", "不能換算成個人被扣款機率"):
            self.assertIn(phrase, subscription)
        self.assertIn("不是所有網路服務的通用規則", subscription)

    def test_source_inventory_coverage_and_batch_counts_are_truthful(self):
        catalog = read("localization/tw-edition/sources/travel-visa-housing-subscription-recheck-20261107.json")
        catalog_sources = {row[0]: row for row in catalog["sources"]}
        self.assertEqual(set(catalog_sources), NEW_SOURCES)
        self.assertTrue(NEW_SOURCES.issubset(self.sources))
        for source_id in NEW_SOURCES:
            self.assertEqual(catalog_sources[source_id][2], self.sources[source_id]["url"])

        self.assertEqual(self.batch["runtime_sources_before"], 1135)
        self.assertEqual(self.batch["runtime_sources_after"], len(self.runtime["sources"]))
        self.assertEqual(self.batch["source_registry_before"], 1218)
        self.assertEqual(self.batch["formal_rechecks_before"], 371)
        self.assertEqual(self.batch["formal_rechecks_after"], len(self.register["substantive_rechecks"]))
        self.assertEqual(self.batch["json_files_checked_before"], 567)

        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertEqual(self.batch["source_registry_after"], coverage["registry_sources"])
        self.assertEqual(self.batch["json_files_checked_after"], coverage["json_files_checked"])
        self.assertEqual(self.batch["core_verified_before"], 282)
        self.assertEqual(self.batch["core_verified_after"], 282)
        self.assertEqual(self.batch["core_verified_after"], coverage["publication_completed_entries"])
        self.assertFalse(coverage["publication_ready"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        self.assertEqual(self.batch["retired_source_ids"], ["renewaldraft"])
        self.assertIn("renewaldraft", self.sources)
        self.assertNotIn("renewaldraft", self.items["TW-26-013"]["source_ids"])
        prior_runtime = json.loads(subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/runtime.json"], cwd=ROOT
        ))
        prior_renewaldraft = next(source for source in prior_runtime["sources"]
                                  if source["id"] == "renewaldraft")
        self.assertEqual(self.sources["renewaldraft"], prior_renewaldraft)


if __name__ == "__main__":
    unittest.main()
