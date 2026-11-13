"""第2章六篇飲食指引的正文、來源、草稿保全及讀者出口契約。"""
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


BASE = "ce2bc87f94ccad5421d7dc8a2b9d6dcf008dbff1"
COMPLETED_HEAD = "a5482a74c68ef521a3f306bd758398053436b8b9"
DATE = "2026-11-10"
DUE = "2027-02-10"
ITEM_IDS = tuple(f"TW-02-{number:03}" for number in range(22, 28))
BATCH_PATH = "localization/ch02-nutrition-guidance-20261110.json"
SOURCE_PATH = "localization/tw-edition/sources/ch02-nutrition-guidance-20261110.json"
DRAFT_ROW_SHA256 = {
    "TW-02-022": "86ab16285a993a038bdc57297fa8d9b131bc28542d6619c8aba85808f279e231",
    "TW-02-023": "ad83f8f5be915d67af7dc6666022cd931cdd970afc551ef96b0f71b2319478ce",
    "TW-02-024": "be0cd68c1f2f009ff0a1abff859e5e8c73deb310521d834c1ba95c9e8cb02d2c",
    "TW-02-025": "8353a3e2b02b00843827b86d086c359fdcc16ee818a057c802810a09f40bd946",
    "TW-02-026": "32ea9bef1c91bb6e477ab02e1608da245073aad938184071ea2628a106844339",
    "TW-02-027": "dc60662d95846fd3853715dad586bd9747736b07116e9b0ba47a0937b3288391",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def base_json(path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True
    ))


def json_at(revision, path):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, text=True
    ))


class Chapter2NutritionGuidanceTests(unittest.TestCase):
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
        cls.readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        cls.base_runtime = base_json("localization/tw-edition/runtime.json")
        cls.base_manifest = base_json("localization/manifest.json")
        cls.completed_runtime = json_at(COMPLETED_HEAD, "localization/tw-edition/runtime.json")
        cls.completed_manifest = json_at(COMPLETED_HEAD, "localization/manifest.json")
        cls.completed_coverage = json_at(COMPLETED_HEAD, "localization/tw-edition/coverage.json")
        cls.completed_register = json_at(
            COMPLETED_HEAD, "localization/retroactive-review-register-20261019.json"
        )
        base_register = base_json("localization/retroactive-review-register-20261019.json")
        cls.later_rechecks = cls.register["substantive_rechecks"][
            len(base_register["substantive_rechecks"]):
        ]
        cls.later_first_publication_ids = set()
        cls.later_first_publication_source_ids = set()
        cls.completed_or_later_main_shas = set(subprocess.check_output(
            ["git", "rev-list", f"{COMPLETED_HEAD}..HEAD"], cwd=ROOT, text=True
        ).splitlines()) | {COMPLETED_HEAD}
        for path in (ROOT / "localization").glob("ch*.json"):
            try:
                later_batch = read_json(path.relative_to(ROOT).as_posix())
            except (json.JSONDecodeError, OSError):
                continue
            batch_base = later_batch.get("baseline_main_sha")
            if batch_base not in cls.completed_or_later_main_shas:
                continue
            for row in later_batch.get("items", []):
                if isinstance(row, dict) and row.get("before_sha256") is None:
                    cls.later_first_publication_ids.add(row["id"])
            cls.later_first_publication_source_ids.update(later_batch.get("new_source_ids", []))

    def test_articles_runtime_manifest_review_and_sources_match(self):
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual((self.batch["reviewed_at"], self.batch["review_due_at"]), (DATE, DUE))
        self.assertEqual(set(self.batch_items), set(ITEM_IDS))
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])

        bundled_sources = {row[0]: row for row in self.bundle["sources"]}
        self.assertEqual(set(bundled_sources), set(self.batch["new_source_ids"]))
        for item_id in ITEM_IDS:
            with self.subTest(item_id=item_id):
                item = self.items[item_id]
                entry = self.manifest[item_id]
                review = self.reviews[item_id]
                record = self.batch_items[item_id]
                current_item = item
                current_entry = entry
                current_review = review
                current_body_path = ROOT / current_entry["target_path"]
                current_body = current_body_path.read_text(encoding="utf-8")
                current_digest = hashlib.sha256(current_body_path.read_bytes()).hexdigest()

                later_rechecks = [row for row in self.later_rechecks if row["id"] == item_id]
                if later_rechecks:
                    # Validate the 11/10 batch against its exact merged snapshot, then
                    # validate the append-only review chain to the current article.
                    completed_items = {
                        row["id"]: row for row in self.completed_runtime["items"]
                    }
                    completed_entries = {
                        row["id"]: row for row in self.completed_manifest["entries"]
                    }
                    item = completed_items[item_id]
                    entry = completed_entries[item_id]
                    review = json.loads(subprocess.check_output(
                        ["git", "show", f"{COMPLETED_HEAD}:localization/reviews/{item_id}.json"],
                        cwd=ROOT,
                        text=True,
                    ))
                    body = item["body"]
                    body_bytes = body.encode("utf-8")
                    digest = hashlib.sha256(body_bytes).hexdigest()
                    self.assertEqual(record["after_sha256"], digest)
                    self.assertEqual(later_rechecks[0]["before_sha256"], digest)
                    for previous, following in zip(later_rechecks, later_rechecks[1:]):
                        self.assertEqual(following["before_sha256"], previous["after_sha256"])
                    self.assertEqual(later_rechecks[-1]["after_sha256"], current_digest)
                    self.assertEqual(current_item["body"], current_body)
                    self.assertEqual(current_review["target_sha256"], current_digest)
                    self.assertEqual(current_review["source_reviewed_sha256"], current_digest)
                    self.assertEqual(current_review["reviewed_at"], later_rechecks[-1]["reviewed_at"])
                    self.assertEqual(current_item["reviewed_at"], later_rechecks[-1]["reviewed_at"])
                    self.assertEqual(current_entry["verified_at"], later_rechecks[-1]["reviewed_at"])
                    self.assertIn("日本研究", current_body)
                else:
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
                self.assertEqual(review["reviewed_at"], DATE)
                self.assertEqual(review["review_due_at"], DUE)
                self.assertEqual(review["target_sha256"], digest)
                self.assertEqual(review["source_reviewed_sha256"], digest)
                self.assertEqual(record["after_sha256"], digest)
                self.assertIsNone(record["before_sha256"])
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(record["source_ids"], item["source_ids"])
                self.assertEqual(review["source_checks"], record["source_checks"])
                self.assertEqual(review["statistics_assessed"], record["statistics_assessed"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertEqual(review["prior_structured_draft_sha256"], DRAFT_ROW_SHA256[item_id])
                self.assertEqual(record["prior_structured_draft_sha256"], DRAFT_ROW_SHA256[item_id])
                self.assertIsNone(review["prior_structured_draft_review"])

                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                expected_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                self.assertEqual(body_urls, expected_urls)
                self.assertEqual({row["url"] for row in review["source_checks"]}, expected_urls)
                self.assertEqual({row["source_id"] for row in review["source_checks"]}, set(item["source_ids"]))
                for source_id in item["source_ids"]:
                    source = self.sources[source_id]
                    self.assertTrue(source["accessed_at"] <= DATE)
                    if source_id in bundled_sources:
                        self.assertEqual(source["accessed_at"], DATE)
                    if source_id in bundled_sources:
                        row = bundled_sources[source_id]
                        self.assertEqual(row, [source[key] for key in ("id", "title", "url", "supports")])

                self.assertTrue(record["frequency_assessment"])
                for stat in review["statistics_assessed"]:
                    for key in (
                        "period", "geographic_scope", "population", "numerator", "denominator",
                        "event_definition", "data_type", "limitations", "source_ids",
                    ):
                        self.assertTrue(stat[key], (item_id, stat.get("topic"), key))
                    self.assertTrue(set(stat["source_ids"]).issubset(item["source_ids"]))
                self.assertNotRegex(
                    body,
                    r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)",
                )
                self.assertEqual(self.readme.count(f"{item_id}.md"), 1)

    def test_topic_claims_and_statistics_limits_are_explicit(self):
        bodies = {item_id: self.items[item_id]["body"] for item_id in ITEM_IDS}
        self.assertIn("不代表人人每天都要另外加吃一份", bodies["TW-02-022"])
        self.assertIn("2020年7月1日施行", bodies["TW-02-022"])
        self.assertIn("不要把整顆堅果當零食", bodies["TW-02-022"])
        self.assertIn("不用把某種食物列為禁品", bodies["TW-02-023"])
        self.assertIn("至少約三分之一", bodies["TW-02-024"])
        self.assertIn("不是喝茶就能延壽", bodies["TW-02-025"])
        self.assertIn("兩種說法的族群與文字不同", bodies["TW-02-026"])
        self.assertIn("不能用成人每日300毫克建議取代孕期評估", bodies["TW-02-026"])
        self.assertIn("22.8%", bodies["TW-02-027"])
        self.assertIn("11.2%", bodies["TW-02-027"])
        self.assertIn("未加權樣本6,537人", bodies["TW-02-027"])
        self.assertIn("不是2026年現況、疾病盛行率或個人罹病機率", bodies["TW-02-027"])
        stats = self.reviews["TW-02-027"]["statistics_assessed"]
        self.assertEqual({row["value"] for row in stats}, {"22.8%", "11.2%"})
        self.assertEqual({row["period"] for row in stats}, {"2017至2020年"})
        self.assertEqual({row["population"] for row in stats}, {"19歲以上成人；未加權樣本6,537人"})

    def test_existing_runtime_manifest_and_structured_drafts_are_preserved(self):
        base_sources = {row["id"]: row for row in self.base_runtime["sources"]}
        base_items = {row["id"]: row for row in self.base_runtime["items"]}
        for source_id, old in base_sources.items():
            self.assertEqual(self.sources[source_id], old)
        for item_id, old in base_items.items():
            current = self.items[item_id]
            if current == old:
                continue
            rechecks = [row for row in self.later_rechecks if row["id"] == item_id]
            self.assertTrue(rechecks, f"{item_id} changed without a later recorded recheck")
            old_sha = hashlib.sha256(old["body"].encode("utf-8")).hexdigest()
            current_sha = hashlib.sha256(current["body"].encode("utf-8")).hexdigest()
            self.assertEqual(rechecks[0]["before_sha256"], old_sha)
            for previous, following in zip(rechecks, rechecks[1:]):
                self.assertEqual(following["before_sha256"], previous["after_sha256"])
            self.assertEqual(rechecks[-1]["after_sha256"], current_sha)

        base_manifest = {row["id"]: row for row in self.base_manifest["entries"]}
        later_recheck_ids = {row["id"] for row in self.later_rechecks}
        for item_id, old in base_manifest.items():
            if item_id not in set(ITEM_IDS) | self.later_first_publication_ids:
                if self.manifest[item_id] != old:
                    self.assertIn(item_id, later_recheck_ids)

        base_drafts = subprocess.check_output(
            ["git", "show", f"{BASE}:localization/tw-edition/chapters/02.json"], cwd=ROOT
        )
        current_drafts = (ROOT / "localization/tw-edition/chapters/02.json").read_bytes()
        base_draft_data = json.loads(base_drafts)
        draft_data = json.loads(current_drafts)
        base_rows = {f"TW-02-{row[0]:03}": row for row in base_draft_data["entries"]}
        rows = {f"TW-02-{row[0]:03}": row for row in draft_data["entries"]}
        self.assertEqual(set(rows), set(base_rows))
        for item_id, old_row in base_rows.items():
            if item_id not in {"TW-02-025", "TW-02-036", "TW-02-047"}:
                self.assertEqual(rows[item_id], old_row)
        self.assertIn("日本研究", rows["TW-02-025"][1])
        self.assertIn("日本研究探討心血管與健康老化", rows["TW-02-036"][1])
        self.assertIn("生淡水魚的中華肝吸蟲風險", rows["TW-02-047"][1])
        self.assertIn("喝茶、泡澡等健康研究", draft_data["intro"])
        for item_id, expected_sha in DRAFT_ROW_SHA256.items():
            if item_id == "TW-02-025":
                # The former draft hash remains in the immutable 11/10 batch record;
                # the current row reflects the later source-backed re-review.
                original = base_rows[item_id]
                value = json.dumps(original, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.assertEqual(hashlib.sha256(value).hexdigest(), expected_sha)
                continue
            value = json.dumps(rows[item_id], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.assertEqual(hashlib.sha256(value).hexdigest(), expected_sha)

        new_source_ids = {row["id"] for row in self.runtime["sources"]} - set(base_sources)
        sources_added_by_later_rechecks = {
            source_id
            for row in self.later_rechecks
            for source_id in set(row["source_ids"]) - set(row["previous_source_ids"])
        }
        topic_fidelity_batch = json.loads(
            (ROOT / "localization/topic-fidelity-dechina-recheck-20261112.json").read_text(encoding="utf-8")
        )
        current_recheck_batch = read_json("localization/topic-fidelity-fraud-osh-recheck-20261114.json")
        reviewed_sources_not_used = {
            source_id
            for row in topic_fidelity_batch["items"]
            for source_id in row.get("reviewed_sources_not_used", [])
        }
        registered_source_ids = {row["id"] for row in self.runtime["sources"]}
        cited_source_ids = {source_id for row in self.runtime["items"] for source_id in row["source_ids"]}
        self.assertTrue(reviewed_sources_not_used.issubset(registered_source_ids))
        self.assertTrue(reviewed_sources_not_used.isdisjoint(cited_source_ids))
        self.assertEqual(
            new_source_ids,
            set(self.batch["new_source_ids"])
            | sources_added_by_later_rechecks
            | self.later_first_publication_source_ids
            | reviewed_sources_not_used
            | set(current_recheck_batch["new_source_ids"]),
        )
        self.assertGreaterEqual(
            len(self.register["substantive_rechecks"]),
            self.batch["counts_before"]["substantive_rechecks"],
        )
        reviewed_ids = {row["id"] for row in self.register["substantive_rechecks"]}
        self.assertEqual(set(ITEM_IDS) & reviewed_ids, {"TW-02-025"})
        self.assertTrue(any(
            row["id"] == "TW-02-025" and row["reviewed_at"] == "2026-11-12"
            for row in self.later_rechecks
        ))

    def test_coverage_and_recorded_counts_match_the_current_data(self):
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        live = audit_drafts()
        self.assertEqual(before, {
            "core_reviewed": 303,
            "runtime_items": 314,
            "runtime_sources": 1218,
            "source_registry": 1301,
            "json_files_checked": 602,
            "substantive_rechecks": 379,
        })
        self.assertEqual(after, {
            "core_reviewed": self.completed_coverage["publication_completed_entries"],
            "runtime_items": len(self.completed_runtime["items"]),
            "runtime_sources": len(self.completed_runtime["sources"]),
            "source_registry": self.completed_coverage["registry_sources"],
            "json_files_checked": self.completed_coverage["json_files_checked"],
            "substantive_rechecks": len(self.completed_register["substantive_rechecks"]),
            "unresolved_source_ids": len(self.completed_coverage["unresolved_source_ids"]),
            "unresolved_reference_occurrences": self.completed_coverage["unresolved_reference_occurrences"],
            "topics_with_any_content": self.completed_coverage["topics_with_any_content"],
            "topics_without_content": self.completed_coverage["topics_without_content"],
            "publication_ready": self.completed_coverage["publication_ready"],
        })
        self.assertEqual(after["core_reviewed"], before["core_reviewed"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + len(ITEM_IDS))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(self.batch["new_source_ids"]))
        self.assertEqual(after["json_files_checked"], before["json_files_checked"] + len(ITEM_IDS) + 2)
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"])
        self.assertFalse(after["publication_ready"])
        self.assertGreaterEqual(live["core_reviewed_entries"], after["core_reviewed"])
        self.assertGreaterEqual(len(self.runtime["items"]), after["runtime_items"])
        self.assertGreaterEqual(len(self.runtime["sources"]), after["runtime_sources"])
        self.assertGreaterEqual(live["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(live["json_files_checked"], after["json_files_checked"])
        self.assertGreaterEqual(len(self.register["substantive_rechecks"]), after["substantive_rechecks"])
        self.assertEqual(self.coverage, live)
        self.assertFalse(self.coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()
