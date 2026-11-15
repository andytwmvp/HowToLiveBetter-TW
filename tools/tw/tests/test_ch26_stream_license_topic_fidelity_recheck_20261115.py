"""第26章直播與影音服務許可範圍主題忠實度再審契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from retroactive_audit import validate_recheck_history
from review_contract import ROOT, validate_runtime


BASELINE = "c8f2f077593b42e95fda65c9a1d8ff1326e54535"
ITEM_ID = "TW-26-003"
BATCH_PATH = "localization/topic-fidelity-stream-licensing-recheck-20261115.json"
REGISTRY_PATH = "localization/tw-edition/sources/ch26-stream-licensing-recheck-20261115.json"
NEW_SOURCE_IDS = {
    "ch26_broadcast_act_20261115",
    "ch26_cable_act_20261115",
    "ch26_satellite_act_20261115",
    "ch26_ncc_entry_20261115",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class StreamLicenseTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {item["id"]: item for item in cls.runtime["items"]}
        cls.sources = {source["id"]: source for source in cls.runtime["sources"]}
        cls.manifest = {
            item["id"]: item for item in read("localization/manifest.json")["entries"]
        }
        cls.review = read(f"localization/reviews/{ITEM_ID}.json")
        cls.register = read("localization/retroactive-review-register-20261019.json")
        cls.records = [
            item for item in cls.register["substantive_rechecks"]
            if item["id"] == ITEM_ID
        ]
        cls.record = next(item for item in cls.records if item["reviewed_at"] == "2026-11-15")
        cls.batch = read(BATCH_PATH)

    def test_article_history_is_append_only_and_hash_bound(self):
        item = self.items[ITEM_ID]
        manifest = self.manifest[ITEM_ID]
        body_bytes = (ROOT / manifest["target_path"]).read_bytes()
        body = body_bytes.decode("utf-8")
        body_sha = sha(body_bytes)
        baseline_runtime = json.loads(git_bytes(BASELINE, "localization/tw-edition/runtime.json"))
        baseline_item = next(x for x in baseline_runtime["items"] if x["id"] == ITEM_ID)
        prior_revision = self.record["prior_revision"]
        prior_item = next(
            x for x in json.loads(git_bytes(prior_revision, "localization/tw-edition/runtime.json"))["items"]
            if x["id"] == ITEM_ID
        )
        prior_review = git_bytes(prior_revision, f"localization/reviews/{ITEM_ID}.json")
        baseline_register = json.loads(
            git_bytes(BASELINE, "localization/retroactive-review-register-20261019.json")
        )
        historical_records = [
            row for row in baseline_register["substantive_rechecks"] if row["id"] == ITEM_ID
        ]

        self.assertEqual(self.batch["baseline_main_sha"], BASELINE)
        self.assertEqual(self.record["prior_revision"], "b0367db7a5f817462020670bfafdfef3dd020fab")
        self.assertEqual(self.record["previous_body"], prior_item["body"])
        self.assertEqual(self.record["before_sha256"], sha(prior_item["body"].encode("utf-8")))
        self.assertEqual(self.record["before_sha256"], sha(baseline_item["body"].encode("utf-8")))
        self.assertEqual(self.record["previous_review_snapshot"], json.loads(prior_review))
        self.assertEqual(self.record["prior_review_sha256"], sha(prior_review))
        self.assertEqual(self.records[:-1], historical_records)
        self.assertEqual(self.record["after_sha256"], body_sha)
        self.assertEqual(self.record["new_body"], body)
        self.assertEqual(item["body"], body)
        self.assertEqual(item["title"], self.record["new_body"].split("\n", 3)[2][2:])
        self.assertEqual(self.review["target_sha256"], body_sha)
        self.assertEqual(self.review["source_reviewed_sha256"], body_sha)
        self.assertEqual(manifest["verified_at"], "2026-11-15")
        self.assertEqual(self.review["review_due_at"], "2027-02-15")
        self.assertEqual(self.record["review_due_at"], self.review["review_due_at"])
        self.assertEqual(self.record["status"], "ai_source_rechecked_professional_pending")
        validate_recheck_history(ROOT, self.record, item)

    def test_taiwan_license_scope_is_restored_without_china_specific_rules(self):
        body = self.items[ITEM_ID]["body"]
        for phrase in (
            "既有影音平台使用個人帳號直播",
            "廣播電視法》第2條",
            "第10條規定經營該法所稱廣播、電視事業須先取得許可及執照",
            "有線廣播電視法》第2條、第5條",
            "衛星廣播電視法》第2條、第6條",
            "向[國家通訊傳播委員會（NCC）]",
            "不能只看到「直播」就推定每個人都要申請",
            "兒童及少年福利與權益保障法》第46條",
            "網路平台提供者",
            "目前沒有可用來估算臺灣未授權直播或回放個人發生機率的全國同口徑統計",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)
        for china_specific in ("網絡文化經營許可證", "民營視聽節目許可", "百萬註冊資金"):
            self.assertNotIn(china_specific, body)
        self.assertNotRegex(body, r"個人直播(?:都|一律)須申請")
        self.assertNotRegex(body, r"所有網路影音服務(?:都|一律)免許可")
        for internal in ("本批", "累計", "實質再審", "AI來源實質再審", "下方為原作", "專業審閱仍待"):
            self.assertNotIn(internal, body)

    def test_sources_runtime_manifest_review_and_registry_reconcile(self):
        item = self.items[ITEM_ID]
        manifest = self.manifest[ITEM_ID]
        article_urls = set(re.findall(r"\]\((https?://[^)]+)\)", item["body"]))
        expected_urls = {self.sources[source_id]["url"] for source_id in item["source_ids"]}
        checked_urls = {check["url"] for check in self.review["source_checks"]}
        registry = read(REGISTRY_PATH)
        registry_ids = {row[0] for row in registry["sources"]}
        self.assertEqual(item["source_ids"][:3], self.record["previous_source_ids"])
        self.assertEqual(set(item["source_ids"]) - set(self.record["previous_source_ids"]), NEW_SOURCE_IDS)
        self.assertEqual(manifest["sources"], [self.sources[x]["url"] for x in item["source_ids"]])
        self.assertEqual(article_urls, expected_urls)
        self.assertEqual(checked_urls, expected_urls)
        self.assertEqual(self.record["source_checks"], self.review["source_checks"])
        self.assertEqual(self.record["limits"], self.review["limits"])
        self.assertEqual(registry_ids, NEW_SOURCE_IDS)
        for source_id in item["source_ids"]:
            self.assertTrue(self.sources[source_id]["supports"])
        registry_rows = {row[0]: row for row in registry["sources"]}
        for source_id in NEW_SOURCE_IDS:
            self.assertEqual(registry_rows[source_id][2], self.sources[source_id]["url"])
            self.assertEqual(registry_rows[source_id][3], self.sources[source_id]["supports"])
        self.assertTrue(all(check["accessed_at"] == "2026-11-15" for check in self.review["source_checks"]))
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])

    def test_legal_history_separates_promulgation_effective_dates_and_pending_amendments(self):
        legal = self.review["legal_status_assessment"]
        self.assertEqual(legal["as_of"], "2026-11-15")
        self.assertEqual(legal["effective_date_rule_url"], "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030133")
        laws = {row["name"]: row for row in legal["laws"]}

        copyright = laws["著作權法"]
        copyright_articles = {
            article: provision
            for provision in copyright["provisions"]
            for article in provision["articles"]
        }
        self.assertEqual(copyright_articles["第22條"]["promulgated_or_amended_at"], "2004-09-01")
        self.assertEqual(copyright_articles["第22條"]["effective_at"], "2004-09-03")
        self.assertEqual(copyright_articles["第26條之1"]["promulgated_or_amended_at"], "2003-07-09")
        self.assertEqual(copyright_articles["第26條之1"]["effective_at"], "2003-07-11")
        pending = copyright["pending_amendment_distinction"]
        self.assertEqual(pending["promulgated_at"], "2022-05-04")
        self.assertIn("第91條", pending["articles_amended"])
        self.assertIn("第46、47、48條", pending["separate_amendment_on_2022_06_15"])
        self.assertNotIn("2022-06-15修正的第91條", self.review["source_checks"][0]["supporting_passage"])

        broadcast_articles = {
            article: provision
            for provision in laws["廣播電視法"]["provisions"]
            for article in provision["articles"]
        }
        self.assertEqual(broadcast_articles["第2條"]["effective_at"], "2016-01-08")
        self.assertEqual(broadcast_articles["第10條"]["effective_at"], "2011-07-01")
        for name in ("有線廣播電視法", "衛星廣播電視法"):
            self.assertEqual(laws[name]["provisions"][0]["effective_at"], "2016-01-08")
        self.assertEqual(laws["兒童及少年福利與權益保障法"]["provisions"][0]["effective_at"], "2011-12-02")

        self.assertEqual(self.record["legal_status_assessment"], legal)
        self.assertEqual(self.batch["items"][0]["legal_status_assessment"], legal)
        review_bytes = (ROOT / f"localization/reviews/{ITEM_ID}.json").read_bytes()
        self.assertEqual(self.record["review_sha256"], sha(review_bytes))
        self.assertEqual(self.batch["items"][0]["review_sha256"], sha(review_bytes))

    def test_coverage_remains_dynamic_and_does_not_mark_publication_ready(self):
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertEqual(
            self.batch["counts_after"]["publication_completed_entries"], 315
        )
        self.assertGreaterEqual(
            coverage["publication_completed_entries"],
            self.batch["counts_after"]["publication_completed_entries"],
        )
        self.assertEqual(coverage["publication_total_entries"], 765)
        self.assertFalse(coverage["publication_ready"])
        self.assertEqual(len(self.records), 2)
        self.assertEqual(len(self.batch["new_source_ids"]), 4)
        self.assertEqual(len(read(REGISTRY_PATH)["sources"]), 4)
        self.assertEqual(self.batch["counts_after"]["review_rechecks"], self.batch["counts_before"]["review_rechecks"] + 1)
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], self.batch["counts_before"]["runtime_sources"] + 4)


if __name__ == "__main__":
    unittest.main()
