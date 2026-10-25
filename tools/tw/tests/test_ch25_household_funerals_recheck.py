"""第25章戶政、減免、消費申訴與殯葬業者四篇歷史再審。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from review_contract import ROOT

BASE = "392c8b990eb1d172141a61706c2392e9c384337f"
IDS = ("TW-25-005", "TW-25-006", "TW-25-007", "TW-25-008")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter25HouseholdFuneralsRecheckTests(unittest.TestCase):
    def test_each_recheck_preserves_base_body_review_and_source_contracts(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"], cwd=ROOT))
        current_runtime = read("localization/tw-edition/runtime.json")
        manifest = {entry["id"]: entry for entry in read("localization/manifest.json")["entries"]}
        register = {row["id"]: row for row in read(
            "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]}
        old_items = {item["id"]: item for item in old_runtime["items"]}
        current_items = {item["id"]: item for item in current_runtime["items"]}
        sources = {source["id"]: source for source in current_runtime["sources"]}

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                old = old_items[item_id]
                current = current_items[item_id]
                record = register[item_id]
                review_path = f"localization/reviews/{item_id}.json"
                review_bytes = subprocess.check_output(
                    ["git", "show", BASE + ":" + review_path], cwd=ROOT)
                review = read(review_path)
                markdown = (ROOT / current["target_path"]).read_bytes()
                body_sha = hashlib.sha256(current["body"].encode("utf-8")).hexdigest()

                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["prior_review_sha256"], hashlib.sha256(review_bytes).hexdigest())
                self.assertEqual(record["before_sha256"], hashlib.sha256(old["body"].encode("utf-8")).hexdigest())
                self.assertNotEqual(record["before_sha256"], body_sha)
                self.assertEqual(record["after_sha256"], body_sha)
                self.assertEqual(current["body"], markdown.decode("utf-8"))
                self.assertEqual(review["target_sha256"], hashlib.sha256(markdown).hexdigest())
                self.assertEqual(manifest[item_id]["sources"], current["source_ids"])
                self.assertEqual(
                    {sources[source_id]["url"] for source_id in current["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                self.assertEqual(record["source_checks"], review["source_checks"])
                self.assertEqual(record["limits"], review["limits"])
                for check in review["source_checks"]:
                    self.assertGreaterEqual(len(check["supporting_passage"]), 50)
                    self.assertIn("非逐字", check["supporting_passage"])
                    self.assertNotIn(check["claim"], check["supporting_passage"])
                audit.validate_recheck_history(ROOT, record, current)

    def test_death_registration_fee_relief_and_consumer_rights_are_scoped(self):
        runtime = {item["id"]: item for item in read("localization/tw-edition/runtime.json")["items"]}
        body = {item_id: runtime[item_id]["body"] for item_id in IDS}
        for phrase in ("裁定確定後30日", "「已結案」", "戶政登記完成後才會轉送", "不等於給付核准"):
            self.assertIn(phrase, body["TW-25-005"])
        for phrase in ("各直轄市、縣市政府列冊", "公立火化場", "不是全案免費", "未列冊者不因經濟困難自動適用"):
            self.assertIn(phrase, body["TW-25-006"])
        for phrase in ("1950", "線上申訴與調解", "15日內妥適處理", "不是提起消費訴訟的強制前置程序"):
            self.assertIn(phrase, body["TW-25-007"])
        for phrase in ("第42條", "第56條", "不是投資商品", "165或110查證", "所有介紹、一般服務轉介或分包"):
            self.assertIn(phrase, body["TW-25-008"])

    def test_new_official_sources_and_frequency_limits_are_registered(self):
        runtime = read("localization/tw-edition/runtime.json")
        sources = {source["id"]: source for source in runtime["sources"]}
        registry = read("localization/tw-edition/sources/17-after-death.json")["sources"]
        registry_ids = {source[0] for source in registry}
        self.assertIn("ch25_consumer_process", sources)
        self.assertIn("ch25_consumer_process", registry_ids)
        self.assertIn("ch25_funeral_sales_reporting", sources)
        self.assertIn("ch25_funeral_sales_reporting", registry_ids)
        self.assertEqual(sources["ch25_consumer_process"]["url"], "https://cpc.ey.gov.tw/Page/71E988F034956960")
        self.assertEqual(sources["ch25_funeral_sales_reporting"]["url"], "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=D0020040")
        for item_id in IDS:
            record = next(row for row in read(
                "localization/retroactive-review-register-20261019.json")["substantive_rechecks"]
                if row["id"] == item_id)
            self.assertIn("分母", record["frequency_assessment"])
            self.assertIn("不", record["frequency_assessment"])


if __name__ == "__main__":
    unittest.main()
