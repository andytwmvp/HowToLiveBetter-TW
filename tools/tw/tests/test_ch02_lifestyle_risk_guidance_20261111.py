"""第2章五篇生活風險指引的正文、來源、統計、草稿保全及閱讀入口契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci_language_policy import audit_drafts
from review_contract import ROOT, validate_runtime


BASE = "886a47907fa0a70b9e9889357ccd2c92411ba519"
DATE = "2026-11-11"
DUE = "2027-02-11"
BATCH_PATH = "localization/ch02-lifestyle-risk-guidance-20261111.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-lifestyle-risk-guidance-20261111.json"
TOPIC_FIDELITY_BATCH = "localization/ch02-topic-fidelity-recheck-20261112.json"
DECHINA_RECHECK_BATCH = "localization/topic-fidelity-dechina-recheck-20261112.json"
CURRENT_RECHECK_BATCH = "localization/topic-fidelity-fraud-osh-recheck-20261114.json"
REMOTE_TRAVEL_RECHECK_BATCH = "localization/topic-fidelity-remote-travel-20261114.json"
ELDERCARE_RECHECK_BATCH = "localization/topic-fidelity-eldercare-prepayment-20261114.json"
REVERSE_MORTGAGE_RECHECK_BATCH = "localization/topic-fidelity-reverse-mortgage-recheck-20261114.json"
ITEM_IDS = ("TW-02-028", "TW-02-030", "TW-02-032", "TW-02-039", "TW-02-042")
PRIOR_DRAFT_HASHES = {
    "TW-02-028": "dd7f36a797b897618d4c266c88650ae24a132036b00e96733a97a80dcc848e21",
    "TW-02-030": "50b52af5f08e460feda157c3b2703b85587bf7e2a42d08cde5ead06dd18f20be",
    "TW-02-032": "ee0bc517312f78c189a6e96d27f4e8dd616f72cbfc8ccd9cdb2b3b5d9d18a7ea",
    "TW-02-039": "6951f635b900aeb64412f45c7aadb5e0fb90da26bf0737c7d7a420bcbadc2491",
    "TW-02-042": "ba87799b4f088222ba1141a6fb3492d166b2df2a6e2306ac2b028d7f0bfdf58a",
}
PRIOR_STRUCTURED_HASHES = {
    "TW-02-028": "abf3fd264c725ca3617ce12c83037a10167d39193c3f4f3c898d1c7c3d3b4bc9",
    "TW-02-030": "15a7a0ad1d53e3fbea5d4513773e104f9d957b4012b389a1e015cbd84d7163aa",
    "TW-02-032": "29e1651d0607d868fc973fa472ee9eaaa615f40dcc57e90f96a7232c7083e482",
    "TW-02-039": "6b3f156898871785ad21db7968ee4ab790ae3d31b7065bb5458a3bd54728443a",
    "TW-02-042": "753ef26d44d39ea22b01fc556db7d08d5af0e630eac8fd8713db909e1b6056aa",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def json_at(revision, path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, text=True
    ))


class Chapter2LifestyleRiskGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read_json("localization/manifest.json")["entries"]
        }
        cls.reviews = {
            item_id: read_json(f"localization/reviews/{item_id}.json")
            for item_id in ITEM_IDS
        }
        cls.batch = read_json(BATCH_PATH)
        cls.batch_items = {row["id"]: row for row in cls.batch["items"]}
        cls.bundle = read_json(SOURCE_PATH)
        cls.coverage = read_json("localization/tw-edition/coverage.json")
        cls.register = read_json("localization/retroactive-review-register-20261019.json")
        cls.chapter_readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        cls.base_runtime = json_at(BASE, "localization/tw-edition/runtime.json")
        cls.base_manifest = json_at(BASE, "localization/manifest.json")
        cls.base_coverage = json_at(BASE, "localization/tw-edition/coverage.json")
        cls.base_register = json_at(BASE, "localization/retroactive-review-register-20261019.json")
        cls.base_drafts = subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/chapters/02.json"], cwd=ROOT
        )

    def test_runtime_manifest_reviews_sources_and_hashes_match(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual((self.batch["reviewed_at"], self.batch["review_due_at"]), (DATE, DUE))
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual(len(self.batch["new_source_ids"]), 21)
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        base_source_ids = {row["id"] for row in self.base_runtime["sources"]}
        current_source_ids = {row["id"] for row in self.runtime["sources"]}
        newly_added_ids = current_source_ids - base_source_ids
        later_batch = read_json(TOPIC_FIDELITY_BATCH)
        dechina_batch = read_json(DECHINA_RECHECK_BATCH)
        current_recheck_batch = read_json(CURRENT_RECHECK_BATCH)
        remote_travel_batch = read_json(REMOTE_TRAVEL_RECHECK_BATCH)
        eldercare_recheck_batch = read_json(ELDERCARE_RECHECK_BATCH)
        reverse_mortgage_batch = read_json(REVERSE_MORTGAGE_RECHECK_BATCH)
        self.assertEqual(
            newly_added_ids,
            set(self.batch["new_source_ids"])
            | set(later_batch["new_source_ids"])
            | set(dechina_batch["new_source_ids"])
            | set(current_recheck_batch["new_source_ids"])
            | set(remote_travel_batch["new_source_ids"])
            | set(eldercare_recheck_batch["new_source_ids"])
            | set(reverse_mortgage_batch["new_source_ids"]),
        )
        bundled = {row[0]: row for row in self.bundle["sources"]}
        self.assertEqual(set(bundled), set(self.batch["new_source_ids"]))
        # 119 information was already registered and is reused rather than duplicated.
        self.assertNotIn("tw02_nfa_emergency_119", self.batch["new_source_ids"])
        self.assertIn("tw02_nfa_emergency_119", self.items["TW-02-030"]["source_ids"])

        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                entry = self.manifest[item_id]
                review = self.reviews[item_id]
                batch_item = self.batch_items[item_id]
                body_path = ROOT / entry["target_path"]
                body_bytes = body_path.read_bytes()
                body = body_bytes.decode("utf-8")
                digest = hashlib.sha256(body_bytes).hexdigest()

                self.assertEqual(entry["status"], "verified")
                self.assertEqual(entry["treatment"], "taiwan_independent_rewrite")
                self.assertEqual(entry["verified_at"], DATE)
                self.assertEqual(entry["target_path"], item["target_path"])
                self.assertEqual(entry["sources"], item["source_ids"])
                self.assertEqual(item["body"], body)
                self.assertEqual(item["review_status"], "source_checked")
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual(review["target_path"], entry["target_path"])
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertEqual(batch_item["after_sha256"], digest)
                self.assertIsNone(batch_item["before_sha256"])
                self.assertEqual(review["prior_chapter_draft_sha256"], PRIOR_DRAFT_HASHES[item_id])
                self.assertEqual(batch_item["prior_chapter_draft_sha256"], PRIOR_DRAFT_HASHES[item_id])
                self.assertEqual(review["prior_structured_draft_sha256"], PRIOR_STRUCTURED_HASHES[item_id])
                self.assertEqual(batch_item["prior_structured_draft_sha256"], PRIOR_STRUCTURED_HASHES[item_id])
                self.assertIsNone(review["prior_structured_draft_review"])
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(batch_item["source_ids"], item["source_ids"])
                self.assertEqual(review["source_checks"], batch_item["source_checks"])
                self.assertEqual(review["statistics_assessed"], batch_item["statistics_assessed"])
                self.assertEqual(review["professional_review"]["required"], True)
                self.assertEqual(review["professional_review"]["obtained"], False)

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                expected_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                self.assertEqual(body_urls, expected_urls)
                self.assertEqual({row["url"] for row in review["source_checks"]}, expected_urls)
                self.assertEqual({row["source_id"] for row in review["source_checks"]}, set(item["source_ids"]))
                for source_id in item["source_ids"]:
                    self.assertTrue(self.sources[source_id]["accessed_at"] <= DATE)
                    if source_id in bundled:
                        self.assertEqual(
                            bundled[source_id],
                            [self.sources[source_id][key] for key in ("id", "title", "url", "supports")],
                        )

                self.assertTrue(batch_item["frequency_assessment"])
                for statistic in review["statistics_assessed"]:
                    for key in (
                        "period", "geographic_scope", "population", "numerator", "denominator",
                        "event_definition", "data_type", "limitations", "source_ids",
                    ):
                        self.assertTrue(statistic[key], (item_id, statistic.get("topic"), key))
                    self.assertTrue(set(statistic["source_ids"]).issubset(item["source_ids"]))
                self.assertNotRegex(
                    body,
                    r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)",
                )
                self.assertEqual(self.chapter_readme.count(f"{item_id}.md"), 1)

    def test_statistics_taiwan_context_and_legal_dates_are_distinguished(self):
        hot_drinks = self.items["TW-02-030"]["body"]
        bmi = self.items["TW-02-032"]["body"]
        night_work = self.items["TW-02-039"]["body"]
        kitchen = self.items["TW-02-042"]["body"]
        self.assertIn("高於攝氏65度", hot_drinks)
        self.assertIn("第2A類", hot_drinks)
        self.assertIn("冷水沖洗燙傷處15至30分鐘", hot_drinks)
        self.assertIn("51.3%", bmi)
        self.assertIn("55歲以上原住民及35歲以上罹患小兒麻痺者", bmi)
        self.assertIn("每案補助880元", bmi)
        self.assertIn("8.5%", night_work)
        self.assertIn("2028年1月1日施行", night_work)
        self.assertIn("不得因此解僱、調職、不給付停止作業期間工資", night_work)
        self.assertIn("0800-068580", night_work)
        self.assertIn("脂肪分佈", bmi)
        self.assertIn("超過95%", kitchen)
        self.assertIn("不代表每個家庭都能達到相同數字", kitchen)

        bmi_stats = self.reviews["TW-02-032"]["statistics_assessed"]
        night_stats = self.reviews["TW-02-039"]["statistics_assessed"]
        self.assertEqual([row["value"] for row in bmi_stats], ["51.3%"])
        self.assertEqual([row["value"] for row in night_stats], ["8.5%"])
        self.assertIn("不是2026年每位成人的個別測量結果", bmi)
        self.assertIn("不是夜班造成疾病或事故的發生率", night_work)
        self.assertEqual(self.reviews["TW-02-028"]["statistics_assessed"], [])
        self.assertEqual(self.reviews["TW-02-030"]["statistics_assessed"], [])
        self.assertEqual(self.reviews["TW-02-042"]["statistics_assessed"], [])

    def test_existing_content_drafts_sources_and_review_history_are_preserved(self):
        current_runtime = {row["id"]: row for row in self.runtime["items"]}
        base_items = {row["id"]: row for row in self.base_runtime["items"]}
        dechina_batch = read_json(DECHINA_RECHECK_BATCH)
        dechina_items = {row["id"]: row for row in dechina_batch["items"]}
        topic_batch = read_json(TOPIC_FIDELITY_BATCH)
        topic_rows = {row["id"]: row for row in topic_batch["items"]}
        current_recheck_batch = read_json(CURRENT_RECHECK_BATCH)
        current_recheck_rows = {row["id"]: row for row in current_recheck_batch["items"]}
        remote_travel_batch = read_json(REMOTE_TRAVEL_RECHECK_BATCH)
        remote_travel_rows = {row["id"]: row for row in remote_travel_batch["items"]}
        eldercare_batch = read_json(ELDERCARE_RECHECK_BATCH)
        eldercare_rows = {row["id"]: row for row in eldercare_batch["items"]}
        reverse_mortgage_batch = read_json(REVERSE_MORTGAGE_RECHECK_BATCH)
        reverse_mortgage_rows = {row["id"]: row for row in reverse_mortgage_batch["items"]}
        rechecks = {
            row["id"]: row for row in self.register["substantive_rechecks"]
            if row["id"] in {"TW-02-025", "TW-02-047"} and row["reviewed_at"] == "2026-11-12"
        }
        for item_id, old in base_items.items():
            if item_id in {"TW-02-025", "TW-02-047"}:
                current = current_runtime[item_id]
                record = rechecks[item_id]
                self.assertEqual(hashlib.sha256(old["body"].encode("utf-8")).hexdigest(), record["before_sha256"])
                self.assertEqual(record["after_sha256"], topic_rows[item_id]["after_sha256"])
                self.assertEqual(hashlib.sha256(current["body"].encode("utf-8")).hexdigest(), record["after_sha256"])
                self.assertEqual(record["source_ids"], current["source_ids"])
            elif item_id in dechina_items:
                current = current_runtime[item_id]
                record = dechina_items[item_id]
                review = read_json(f"localization/reviews/{item_id}.json")
                self.assertEqual(
                    hashlib.sha256(current["body"].encode("utf-8")).hexdigest(),
                    record["after_sha256"],
                )
                self.assertEqual(review["target_sha256"], record["after_sha256"])
                self.assertEqual(review["reviewed_at"], dechina_batch["reviewed_at"])
                self.assertEqual(current["source_ids"], record["source_ids"])
            elif item_id in current_recheck_rows:
                current = current_runtime[item_id]
                record = current_recheck_rows[item_id]
                review = read_json(f"localization/reviews/{item_id}.json")
                self.assertEqual(
                    hashlib.sha256(old["body"].encode("utf-8")).hexdigest(),
                    record["before_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(current["body"].encode("utf-8")).hexdigest(),
                    record["after_sha256"],
                )
                self.assertEqual(review["target_sha256"], record["after_sha256"])
                self.assertEqual(review["reviewed_at"], current_recheck_batch["reviewed_at"])
                self.assertEqual(current["source_ids"], record["source_ids"])
            elif item_id in remote_travel_rows:
                current = current_runtime[item_id]
                record = remote_travel_rows[item_id]
                review = read_json(f"localization/reviews/{item_id}.json")
                self.assertEqual(
                    hashlib.sha256(old["body"].encode("utf-8")).hexdigest(),
                    record["before_sha256"],
                )
                current_sha = hashlib.sha256(current["body"].encode("utf-8")).hexdigest()
                self.assertEqual(record["after_sha256"], current_sha)
                self.assertEqual(review["target_sha256"], current_sha)
                self.assertEqual(review["reviewed_at"], remote_travel_batch["reviewed_at"])
                self.assertEqual(current["source_ids"], record["source_ids"])
            elif item_id in eldercare_rows:
                current = current_runtime[item_id]
                record = eldercare_rows[item_id]
                review = read_json(f"localization/reviews/{item_id}.json")
                current_sha = hashlib.sha256(current["body"].encode("utf-8")).hexdigest()
                self.assertEqual(
                    hashlib.sha256(old["body"].encode("utf-8")).hexdigest(),
                    record["before_sha256"],
                )
                self.assertEqual(record["after_sha256"], current_sha)
                self.assertEqual(review["target_sha256"], current_sha)
                self.assertEqual(review["reviewed_at"], eldercare_batch["reviewed_at"])
                self.assertEqual(current["source_ids"], record["source_ids"])
            elif item_id in reverse_mortgage_rows:
                current = current_runtime[item_id]
                record = reverse_mortgage_rows[item_id]
                review = read_json(f"localization/reviews/{item_id}.json")
                current_sha = hashlib.sha256(current["body"].encode("utf-8")).hexdigest()
                self.assertEqual(
                    hashlib.sha256(old["body"].encode("utf-8")).hexdigest(),
                    record["before_sha256"],
                )
                self.assertEqual(record["after_sha256"], current_sha)
                self.assertEqual(review["target_sha256"], current_sha)
                self.assertEqual(review["reviewed_at"], reverse_mortgage_batch["reviewed_at"])
                self.assertEqual(current["source_ids"], record["source_ids"])
            else:
                self.assertEqual(current_runtime[item_id], old)
        current_sources = {row["id"]: row for row in self.runtime["sources"]}
        for old in self.base_runtime["sources"]:
            self.assertEqual(current_sources[old["id"]], old)

        structured = ROOT / "localization/tw-edition/chapters/02.json"
        base_chapter = json.loads(self.base_drafts)
        current_chapter = json.loads(structured.read_bytes())
        old_rows = {row[0]: row for row in base_chapter["entries"]}
        rows = {row[0]: row for row in current_chapter["entries"]}
        self.assertEqual(set(rows), set(old_rows))
        for number, old_row in old_rows.items():
            if number not in {25, 36, 47}:
                self.assertEqual(rows[number], old_row)
        self.assertIn("日本研究有觀察到死亡率關聯", rows[25][1])
        self.assertIn("日本研究探討心血管與健康老化", rows[36][1])
        self.assertIn("生淡水魚的中華肝吸蟲風險", rows[47][1])
        for item_id, expected in PRIOR_STRUCTURED_HASHES.items():
            number = int(item_id[-3:])
            compact = json.dumps(rows[number], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.assertEqual(hashlib.sha256(compact).hexdigest(), expected)

        base_manifest = {row["id"]: row for row in self.base_manifest["entries"]}
        for item_id, old in base_manifest.items():
            if item_id in {"TW-02-025", "TW-02-047"}:
                self.assertEqual(self.manifest[item_id]["sources"], current_runtime[item_id]["source_ids"])
                self.assertEqual(self.manifest[item_id]["verified_at"], "2026-11-12")
            elif item_id == "TW-02-036":
                self.assertEqual(old["status"], "pending")
                self.assertEqual(self.manifest[item_id]["status"], "verified")
                self.assertEqual(self.manifest[item_id]["sources"], current_runtime[item_id]["source_ids"])
            elif item_id in dechina_items:
                self.assertEqual(self.manifest[item_id]["verified_at"], dechina_batch["reviewed_at"])
                expected_sources = current_runtime[item_id]["source_ids"]
                if old["sources"] and old["sources"][0].startswith("http"):
                    expected_sources = [
                        self.sources[source_id]["url"]
                        for source_id in current_runtime[item_id]["source_ids"]
                    ]
                self.assertEqual(
                    self.manifest[item_id]["sources"],
                    expected_sources,
                )
            elif item_id in current_recheck_rows:
                expected = dict(old)
                expected["sources"] = current_runtime[item_id]["source_ids"]
                expected["verified_at"] = current_recheck_batch["reviewed_at"]
                self.assertEqual(self.manifest[item_id], expected)
            elif item_id in remote_travel_rows:
                expected = dict(old)
                expected["sources"] = current_runtime[item_id]["source_ids"]
                expected["verified_at"] = remote_travel_batch["reviewed_at"]
                self.assertEqual(self.manifest[item_id], expected)
            elif item_id in eldercare_rows:
                expected = dict(old)
                expected["sources"] = current_runtime[item_id]["source_ids"]
                expected["verified_at"] = eldercare_batch["reviewed_at"]
                self.assertEqual(self.manifest[item_id], expected)
            elif item_id in reverse_mortgage_rows:
                expected = dict(old)
                expected["sources"] = current_runtime[item_id]["source_ids"]
                expected["verified_at"] = reverse_mortgage_batch["reviewed_at"]
                self.assertEqual(self.manifest[item_id], expected)
            elif item_id not in ITEM_IDS:
                self.assertEqual(self.manifest[item_id], old)
        self.assertEqual(
            len(self.register["substantive_rechecks"]),
            len(self.base_register["substantive_rechecks"])
            + len(rechecks)
            + len(dechina_items)
            + len(current_recheck_rows)
            + len(remote_travel_rows)
            + len(eldercare_rows)
            + len(reverse_mortgage_rows),
        )
        self.assertEqual(set(rechecks), {"TW-02-025", "TW-02-047"})
        self.assertTrue(set(ITEM_IDS).isdisjoint({row["id"] for row in self.register["substantive_rechecks"]}))

    def test_coverage_counts_match_batch_and_publication_remains_blocked(self):
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        live = audit_drafts()
        self.assertEqual(before, {
            "core_reviewed": sum(row["status"] == "verified" for row in self.base_manifest["entries"]),
            "runtime_items": len(self.base_runtime["items"]),
            "runtime_sources": len(self.base_runtime["sources"]),
            "source_registry": self.base_coverage["registry_sources"],
            "json_files_checked": self.base_coverage["json_files_checked"],
            "substantive_rechecks": len(self.base_register["substantive_rechecks"]),
        })
        self.assertEqual(after["core_reviewed"], before["core_reviewed"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + len(ITEM_IDS) + 2)
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"])
        self.assertEqual(after["publication_ready"], False)
        self.assertEqual(self.coverage, live)
        self.assertEqual(self.coverage["core_reviewed_entries"], live["core_reviewed_entries"])
        self.assertGreaterEqual(self.coverage["publication_completed_entries"], after["core_reviewed"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(self.coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(self.coverage["json_files_checked"], after["json_files_checked"])
        self.assertFalse(self.coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()
