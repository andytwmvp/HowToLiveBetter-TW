"""第13章嚴重過敏再審：台灣頻率證據、急救範圍與歷史雜湊契約。"""
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


BASE = "209a2c2424b5bd2bdbd0ea1bb4e471ee39e096d1"
DATE = "2026-11-24"
DUE = "2027-02-24"
ITEM_ID = "TW-13-015"
BATCH = "localization/ch13-anaphylaxis-frequency-recheck-20261124.json"
BUNDLE = "localization/tw-edition/sources/ch13-anaphylaxis-frequency-recheck-20261124.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
BODY_PATH = "locales/zh-TW/book/ch13/TW-13-015.md"
REVIEW_PATH = f"localization/reviews/{ITEM_ID}.json"
NEW_SOURCE_ID = "ch13_ana_incidence_nhi_2001_2013_20261124"
POSITION_SOURCE_ID = "ch13_ana_ascia_positioning_202604_20261124"
TSEM_SOURCE_ID = "ch13_ana_tsem_position_20230430_20261124"
SOURCE_IDS = (
    "ch13_ana_taaaci_2024",
    "ch13_ana_cch_anaphylaxis_20221026",
    "ch13_ana_nfa_20260430",
    NEW_SOURCE_ID,
    POSITION_SOURCE_ID,
    TSEM_SOURCE_ID,
)
RETIRED_SOURCE_ID = "ch13_ana_viatris_epipen_20261103"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def at_revision(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def batch_snapshot_revision(row):
    """Find this batch's immutable tree after later reviews change the live item."""
    body_path = f"locales/zh-TW/book/ch13/{row['id']}.md"
    review_path = f"localization/reviews/{row['id']}.json"
    if (
        digest((ROOT / body_path).read_bytes()) == row["after_sha256"]
        and digest((ROOT / review_path).read_bytes()) == row["review_sha256"]
    ):
        return None

    needle = f'"source_bundle_path": "{BUNDLE}"'
    revisions = subprocess.check_output(
        ["git", "log", "--all", "--format=%H", "--reverse", "-S", needle, "--", REGISTER],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for revision in revisions:
        register = json.loads(at_revision(revision, REGISTER))
        rows = [
            record for record in register["substantive_rechecks"]
            if record["id"] == row["id"]
            and record["reviewed_at"] == row["reviewed_at"]
            and record["source_bundle_path"] == BUNDLE
        ]
        if rows == [row] and (
            digest(at_revision(revision, body_path)) == row["after_sha256"]
            and digest(at_revision(revision, review_path)) == row["review_sha256"]
        ):
            return revision
    raise AssertionError(f"找不到批次 {BUNDLE} 對應的歷史正文與 review 快照")


def snapshot_bytes(revision, path):
    return (ROOT / path).read_bytes() if revision is None else at_revision(revision, path)


def digest_json(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))


class AnaphylaxisFrequencyRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.live_runtime = validate_runtime()
        cls.live_sources = {row["id"]: row for row in cls.live_runtime["sources"]}
        cls.register = read(REGISTER)
        cls.batch = read(BATCH)
        cls.batch_item = cls.batch["items"][0]
        cls.snapshot_revision = batch_snapshot_revision(cls.batch_item)
        cls.runtime = json.loads(
            snapshot_bytes(cls.snapshot_revision, "localization/tw-edition/runtime.json")
        )
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in json.loads(
                snapshot_bytes(cls.snapshot_revision, "localization/manifest.json")
            )["entries"]
        }
        cls.review_bytes = snapshot_bytes(cls.snapshot_revision, REVIEW_PATH)
        cls.review = json.loads(cls.review_bytes)
        cls.register_snapshot = json.loads(
            snapshot_bytes(cls.snapshot_revision, REGISTER)
        )
        cls.coverage = json.loads(
            snapshot_bytes(cls.snapshot_revision, "localization/tw-edition/coverage.json")
        )
        cls.bundle = read(BUNDLE)
        cls.body_bytes = snapshot_bytes(cls.snapshot_revision, BODY_PATH)
        cls.body = cls.body_bytes.decode("utf-8")

    def test_append_only_hash_source_and_runtime_edges(self):
        baseline_runtime = json.loads(at_revision(BASE, "localization/tw-edition/runtime.json"))
        baseline_manifest = json.loads(at_revision(BASE, "localization/manifest.json"))
        baseline_review_raw = at_revision(BASE, REVIEW_PATH)
        baseline_review = json.loads(baseline_review_raw)
        baseline_register = json.loads(at_revision(BASE, REGISTER))
        baseline_sources = {row["id"]: row for row in baseline_runtime["sources"]}
        baseline_item = next(row for row in baseline_runtime["items"] if row["id"] == ITEM_ID)
        baseline_entry = next(row for row in baseline_manifest["entries"] if row["id"] == ITEM_ID)
        current = self.items[ITEM_ID]
        entry = self.manifest[ITEM_ID]
        body_sha = digest(self.body_bytes)
        row = self.batch_item

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual((self.batch["reviewed_at"], self.batch["review_due_at"]), (DATE, DUE))
        self.assertEqual(self.batch["counts_before"]["core_reviewed_entries"], 351)
        self.assertEqual(self.batch["counts_after"]["core_reviewed_entries"], 351)
        self.assertEqual(self.batch["items"], [row])
        self.assertEqual(row["before_sha256"], digest(baseline_item["body"].encode("utf-8")))
        self.assertEqual(row["previous_body"], baseline_item["body"])
        self.assertEqual(row["prior_review_sha256"], digest(baseline_review_raw))
        self.assertEqual(row["after_sha256"], body_sha)
        self.assertEqual(row["review_sha256"], digest(self.review_bytes))
        self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
        self.assertEqual(current["body"], self.body)
        self.assertEqual(current["source_ids"], list(SOURCE_IDS))
        self.assertEqual(current["reviewed_at"], DATE)
        self.assertEqual(current["review_due_at"], DUE)
        self.assertEqual(self.review["target_sha256"], body_sha)
        self.assertEqual(self.review["source_reviewed_sha256"], body_sha)
        self.assertEqual(self.review["source_checks"], row["source_checks"])
        self.assertEqual(self.review["prior_review_sha256"], digest(baseline_review_raw))
        self.assertEqual(entry["sources"], list(SOURCE_IDS))
        self.assertEqual(entry["verified_at"], DATE)
        self.assertEqual(row["source_ids"], list(SOURCE_IDS))
        self.assertEqual(row["review_path"], REVIEW_PATH)
        self.assertEqual(row["source_bundle_path"], BUNDLE)
        self.assertEqual(row["source_bundle_sha256"], digest((ROOT / BUNDLE).read_bytes()))
        self.assertEqual(self.review["source_bundle_sha256"], row["source_bundle_sha256"])
        self.assertEqual(self.review["source_ids"], list(SOURCE_IDS))
        self.assertEqual(self.review["limits"], row["limits"])
        self.assertEqual(self.review["unresolved_questions"], row["unresolved_questions"])
        self.assertEqual(row["previous_source_ids"], baseline_item["source_ids"])
        self.assertEqual(row["prior_source_checks"], baseline_review["source_checks"])

        appended = [
            record for record in self.register["substantive_rechecks"]
            if record == row
        ]
        self.assertEqual(appended, [row])
        self.assertEqual(
            self.register["substantive_rechecks"][:len(baseline_register["substantive_rechecks"])],
            baseline_register["substantive_rechecks"],
        )
        self.assertEqual(
            self.register_snapshot["substantive_rechecks"][:len(baseline_register["substantive_rechecks"])],
            baseline_register["substantive_rechecks"],
        )
        if self.snapshot_revision is None:
            validate_recheck_history(ROOT, row, current)

        self.assertEqual(
            set(self.sources) - set(baseline_sources),
            {NEW_SOURCE_ID, POSITION_SOURCE_ID, TSEM_SOURCE_ID},
        )
        for source_id, old_source in baseline_sources.items():
            self.assertEqual(self.sources[source_id], old_source)
        self.assertEqual(self.live_sources[NEW_SOURCE_ID], self.sources[NEW_SOURCE_ID])
        retired = row["retired_sources"]
        self.assertEqual([source["id"] for source in retired], [RETIRED_SOURCE_ID])
        self.assertNotIn(RETIRED_SOURCE_ID, current["source_ids"])
        self.assertEqual(retired[0]["disposition"], "claim_removed_from_scope")
        self.assertEqual(retired[0]["replacement_ids"], [])
        self.assertEqual(retired[0]["prior_source_sha256"], digest_json(baseline_sources[RETIRED_SOURCE_ID]))
        self.assertEqual(self.sources[RETIRED_SOURCE_ID], baseline_sources[RETIRED_SOURCE_ID])

        urls = {self.sources[source_id]["url"] for source_id in SOURCE_IDS}
        body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", self.body))
        check_urls = {check["url"] for check in row["source_checks"]}
        self.assertEqual(body_urls, urls)
        self.assertEqual(check_urls, urls)
        self.assertEqual({check["source_id"] for check in row["source_checks"]}, set(SOURCE_IDS))
        self.assertNotIn(self.sources[RETIRED_SOURCE_ID]["url"], body_urls)
        self.assertNotRegex(self.body, r"(?:本批|本次再審|AI來源實質再審|專業審閱仍待取得|\bPR\s*#|CI\s*(?:成功|通過))")

    def test_historical_taiwan_rate_has_correct_definition_and_limits(self):
        stats = self.batch_item["statistics_assessed"]
        self.assertEqual(len(stats), 1)
        row = stats[0]
        self.assertEqual(row["source_id"], NEW_SOURCE_ID)
        self.assertEqual(row["numerator"], 2496)
        self.assertEqual(row["denominator"], 34430000)
        self.assertIn("2001", row["period"])
        self.assertIn("2013", row["period"])
        self.assertIn("申報", row["data_type"])
        self.assertIn("首次", row["event_definition"])
        self.assertIn("門診、急診或住院", row["event_definition"])
        self.assertIn("每10萬人年7.25例", self.body)
        self.assertIn("2,496名首次診斷患者及34,430,000人年", self.body)
        self.assertIn("不代表2026年現況", self.body)
        self.assertIn("研究也沒有詳細記錄每個病例的誘因", self.body)
        self.assertIn("不能用來推算所有成因的發生率", self.body)
        self.assertIn("全國推估的歷史資料", self.batch_item["frequency_assessment"])
        self.assertNotIn("沒有可比的全國嚴重過敏反應發生率", self.batch_item["frequency_assessment"])
        for field in (
            "unit", "period", "scope", "population", "numerator", "denominator",
            "denominator_definition", "event_definition", "data_type", "source_id",
            "accessed_at", "limitations",
        ):
            self.assertTrue(row.get(field), field)
        self.assertIn("誘因", row["limitations"])
        self.assertIn("個人風險", row["limitations"])

    def test_emergency_actions_and_food_guideline_scope_are_preserved(self):
        for phrase in (
            "立即撥119",
            "依個人急救計畫及裝置說明立即使用",
            "旁人可同時通報119",
            "不要等救護車到場",
            "使用自動注射器後仍須儘速送急診",
            "不要共用他人的處方藥",
            "不要自行抽取或注射其他藥物",
            "先讓其平躺",
            "若呼吸困難或平躺會更不舒服",
            "懷孕者左側臥",
            "刻意抬高下肢的效益仍有爭議",
            "不要讓患者站起或走動",
            "依119派遣員指示開始CPR並取得AED",
            "此指引以食物過敏為主",
        ):
            self.assertIn(phrase, self.body)
        self.assertIn("只直接支持其適用範圍內的食物過敏處置", self.review["limits"][2])
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertEqual(self.review["professional_review"]["status"], "pending")
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.coverage["core_reviewed_entries"], 351)

    def test_new_source_bundle_and_dynamic_counts_match(self):
        source = self.sources[NEW_SOURCE_ID]
        self.assertEqual(source["accessed_at"], DATE)
        self.assertEqual(source["published_at"], "2018-10-10")
        position_source = self.sources[POSITION_SOURCE_ID]
        self.assertEqual(position_source["accessed_at"], DATE)
        self.assertIsNone(position_source["published_at"])
        self.assertIn("2026年4月更新", position_source["title"])
        self.assertIn("避免站立或步行", position_source["supports"])
        tsem_source = self.sources[TSEM_SOURCE_ID]
        self.assertEqual(tsem_source["accessed_at"], DATE)
        self.assertEqual(tsem_source["published_at"], "2023-04-30")
        self.assertIn("抬高下肢", tsem_source["supports"])
        self.assertIn("效益有爭議", tsem_source["supports"])
        self.assertEqual(self.bundle["baseline_main_sha"], BASE)
        self.assertEqual(
            [row[0] for row in self.bundle["sources"]],
            [NEW_SOURCE_ID, POSITION_SOURCE_ID, TSEM_SOURCE_ID],
        )
        self.assertEqual(
            self.bundle["sources"][0],
            [source["id"], source["title"], source["url"], source["supports"]],
        )
        self.assertEqual(
            self.bundle["sources"][1],
            [position_source["id"], position_source["title"], position_source["url"], position_source["supports"]],
        )
        self.assertEqual(
            self.bundle["sources"][2],
            [tsem_source["id"], tsem_source["title"], tsem_source["url"], tsem_source["supports"]],
        )
        coverage = self.coverage
        live_coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage["core_reviewed_entries"], 351)
        self.assertEqual(coverage["registry_sources"], 1607)
        self.assertEqual(coverage["json_files_checked"], 741)
        self.assertEqual(coverage["topics_with_any_content"], 520)
        self.assertEqual(coverage["topics_with_unreviewed_content"], 169)
        self.assertEqual(coverage["topics_without_content"], 245)
        self.assertEqual(coverage["unresolved_reference_occurrences"], 239)
        self.assertEqual(len(coverage["unresolved_source_ids"]), 100)
        self.assertGreaterEqual(live_coverage["core_reviewed_entries"], self.batch["counts_after"]["core_reviewed_entries"])
        self.assertGreaterEqual(live_coverage["registry_sources"], self.batch["counts_after"]["source_registry"])
        self.assertGreaterEqual(live_coverage["json_files_checked"], self.batch["counts_after"]["json_files_checked"])
        self.assertEqual(self.batch["counts_after"]["runtime_items"], len(self.runtime["items"]))
        self.assertEqual(self.batch["counts_after"]["runtime_sources"], len(self.runtime["sources"]))
        self.assertEqual(self.batch["counts_after"]["source_registry"], coverage["registry_sources"])
        self.assertEqual(self.batch["counts_after"]["json_files_checked"], coverage["json_files_checked"])
        self.assertEqual(
            self.batch["counts_after"]["substantive_rechecks"],
            len(self.register_snapshot["substantive_rechecks"]),
        )
        self.assertTrue(self.batch["professional_review_pending"])
        self.assertFalse(self.batch["publication_ready"])


if __name__ == "__main__":
    unittest.main()
