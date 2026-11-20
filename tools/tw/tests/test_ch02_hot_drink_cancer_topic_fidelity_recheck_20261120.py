"""熱飲與食道癌研究主題保真度再審、來源及歷史紀錄契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))
sys.path.insert(0, str(ROOT / "tools/tw/tests"))

from ci_language_policy import audit_drafts
from review_contract import validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "d105a46a83f3eb16e0c6bae321571c5a6f1c83dc"
DATE = "2026-11-20"
DUE = "2027-02-20"
ITEM_ID = "TW-02-030"
ARTICLE = "locales/zh-TW/book/ch02/TW-02-030.md"
REVIEW = "localization/reviews/TW-02-030.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
BATCH = "localization/ch02-hot-drink-cancer-topic-fidelity-recheck-20261120.json"
BUNDLE = "localization/tw-edition/sources/ch02-hot-drink-cancer-topic-fidelity-recheck-20261120.json"
NEW_SOURCE_IDS = {
    "tw02_islami_golestan_hot_tea_2009",
    "tw02_papier_uk_hot_drinks_2026",
    "tw02_yu_ckb_hot_tea_interactions_2018",
    "tw02_chen_taiwan_hot_food_escc_2009",
    "tw02_hpa_esophageal_prevention_2022",
    "tw02_mohw_child_burn_prevention_firstaid_2026",
    "tw02_vghtpe_burn_care_2026",
}
EXPECTED_SOURCE_IDS = [
    "tw02_iarc_hot_drinks_2016",
    "tw02_islami_golestan_hot_tea_2009",
    "tw02_papier_uk_hot_drinks_2026",
    "tw02_yu_ckb_hot_tea_interactions_2018",
    "tw02_chen_taiwan_hot_food_escc_2009",
    "tw02_hpa_esophageal_prevention_2022",
    "tw02_mohw_child_burn_prevention_firstaid_2026",
    "tw02_vghtpe_burn_care_2026",
    "tw02_nfa_emergency_119",
]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class HotDrinkCancerTopicFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.review = read(REVIEW)
        cls.register = read(REGISTER)
        cls.batch = read(BATCH)
        cls.bundle = read(BUNDLE)
        cls.body_bytes = (ROOT / ARTICLE).read_bytes()
        cls.body = cls.body_bytes.decode("utf-8")
        cls.records = [row for row in cls.register["substantive_rechecks"] if row["id"] == ITEM_ID]
        cls.record = next(row for row in cls.records if row["reviewed_at"] == DATE)
        cls.batch_item = next(row for row in cls.batch["items"] if row["id"] == ITEM_ID)

    def test_historical_text_and_review_are_hash_bound_and_append_only(self):
        old_body = git_bytes(BASE, ARTICLE)
        old_review = git_bytes(BASE, REVIEW)
        old_register = json.loads(git_bytes(BASE, REGISTER))
        old_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        old_item = next(row for row in old_manifest["entries"] if row["id"] == ITEM_ID)

        self.assertEqual(self.record["before_sha256"], sha(old_body))
        self.assertEqual(self.record["previous_body"].encode("utf-8"), old_body)
        self.assertEqual(self.record["prior_review_sha256"], sha(old_review))
        self.assertEqual(self.record["prior_reviewed_at"], json.loads(old_review)["reviewed_at"])
        self.assertEqual(self.record["previous_source_ids"], old_item["sources"])
        retained_previous = [
            source_id for source_id in self.record["source_ids"]
            if source_id in self.record["previous_source_ids"]
        ]
        self.assertEqual(retained_previous, [
            "tw02_iarc_hot_drinks_2016", "tw02_nfa_emergency_119"
        ])
        self.assertEqual(self.record["after_sha256"], sha(self.body_bytes))
        self.assertEqual(self.record["review_sha256"], sha((ROOT / REVIEW).read_bytes()))
        self.assertEqual(self.record["source_bundle_sha256"], sha((ROOT / BUNDLE).read_bytes()))
        self.assertEqual(self.record["review_due_at"], DUE)
        self.assertEqual(self.review["review_due_at"], DUE)
        self.assertEqual(self.record["status"], "ai_source_rechecked_professional_pending")
        self.assertEqual(
            self.register["substantive_rechecks"][:len(old_register["substantive_rechecks"])],
            old_register["substantive_rechecks"],
        )
        prior_revision = subprocess.check_output(
            ["git", "log", "-1", "--format=%H", BASE, "--", ARTICLE], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(self.record["prior_revision"], prior_revision)
        self.assertTrue(self.record["prior_structured_draft_sha256"])

    def test_reader_body_and_topic_fidelity_decisions_are_current(self):
        item = self.items[ITEM_ID]
        self.assertEqual(item["body"], self.body)
        self.assertEqual(item["title"], "熱飲放涼再喝：食道癌研究與燙傷處理")
        self.assertEqual(item["review_status"], "source_checked")
        self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
        self.assertEqual(item["limits"], " ".join(self.review["limits"]))
        self.assertEqual(self.manifest[ITEM_ID]["status"], "verified")
        self.assertEqual(self.manifest[ITEM_ID]["target_path"], ARTICLE)
        self.assertEqual(self.review["target_sha256"], sha(self.body_bytes))
        self.assertEqual(self.review["source_reviewed_sha256"], sha(self.body_bytes))
        self.assertTrue(self.record["topic_fidelity_assessment"])
        self.assertTrue(self.review["topic_fidelity_assessment"])
        self.assertEqual(self.record["frequency_assessment"], self.review["frequency_assessment"])
        self.assertEqual(self.record["statistics_assessed"], self.review["statistics_assessed"])
        self.assertEqual(self.record["source_checks"], self.review["source_checks"])
        self.assertEqual(self.record["limits"], self.review["limits"])
        self.assertEqual(self.review["topic_fidelity_review"]["decision"],
                         "retain_taiwan_core_with_bounded_research_and_taiwan_safety_guidance")
        self.assertEqual(
            self.review["topic_fidelity_review"]["question_change"]["decision"],
            "restore_or_expand_original_research_question_without_replacing_it_with_a_superficially_similar_local_safety_topic",
        )
        self.assertTrue(self.review["topic_fidelity_review"]["question_change"]["previous_question"])
        self.assertTrue(self.review["topic_fidelity_review"]["question_change"]["current_question"])
        self.assertTrue(self.review["topic_fidelity_review"]["question_change"]["reason"])
        self.assertTrue(self.review["frequency_assessment"])
        self.assertFalse(self.review["professional_review"]["obtained"])
        self.assertTrue(self.review["professional_review"]["required"])
        self.assertNotRegex(
            self.body,
            r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|專業審閱仍待|fork管理)",
        )

        chapter = read("localization/tw-edition/chapters/02.json")
        row = next(row for row in chapter["entries"] if row[0] == 30)
        self.assertEqual(row[1], item["title"])
        self.assertEqual(row[5].split(), item["source_ids"])
        readme = (ROOT / "locales/zh-TW/book/ch02/README.md").read_text(encoding="utf-8")
        self.assertIn(f"[{item['title']}]({ITEM_ID}.md)", readme)

    def test_source_ids_urls_support_and_retirement_are_consistent(self):
        item = self.items[ITEM_ID]
        source_ids = item["source_ids"]
        self.assertEqual(source_ids, EXPECTED_SOURCE_IDS)
        self.assertEqual(source_ids, self.manifest[ITEM_ID]["sources"])
        self.assertEqual(source_ids, self.review["source_ids"])
        self.assertEqual(source_ids, self.record["source_ids"])
        self.assertEqual(self.record["previous_source_ids"], self.batch_item["previous_source_ids"])
        self.assertEqual(set(self.batch["new_source_ids"]), NEW_SOURCE_IDS)
        self.assertEqual(set(self.batch_item["source_ids"]) - set(self.batch_item["previous_source_ids"]), NEW_SOURCE_IDS)
        self.assertEqual(set(self.batch["source_records_reused"]), {
            "tw02_iarc_hot_drinks_2016", "tw02_nfa_emergency_119"
        })

        body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", self.body))
        expected_urls = {self.sources[source_id]["url"] for source_id in source_ids}
        checks = self.review["source_checks"]
        self.assertEqual(body_urls, expected_urls)
        self.assertEqual({row["source_id"] for row in checks}, set(source_ids))
        self.assertEqual({row["url"] for row in checks}, expected_urls)
        self.assertEqual(len(checks), len(source_ids))
        for check in checks:
            for field in ("claim", "supporting_passage", "accessed_at", "retrieval_method"):
                self.assertTrue(check[field], (check["source_id"], field))
            self.assertLessEqual(check["accessed_at"], DATE)

        bundled = {row[0]: row for row in self.bundle["sources"]}
        self.assertEqual(set(bundled), NEW_SOURCE_IDS)
        old_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        old_sources = {row["id"] for row in old_runtime["sources"]}
        added_since_baseline = set(self.sources) - old_sources
        self.assertTrue(NEW_SOURCE_IDS.isdisjoint(old_sources))
        self.assertTrue(NEW_SOURCE_IDS.issubset(added_since_baseline))
        self.assertEqual(added_since_baseline, source_bundle_ids_added_since(ROOT, BASE))
        for source_id in NEW_SOURCE_IDS:
            _, title, url, supports = bundled[source_id]
            source = self.sources[source_id]
            self.assertEqual((source["title"], source["url"], source["supports"]), (title, url, supports))
            self.assertLessEqual(source["accessed_at"], DATE)

        old_sources = {row["id"]: row for row in old_runtime["sources"]}
        for source_id, old_source in old_sources.items():
            self.assertEqual(self.sources[source_id], old_source, source_id)
        retired = self.record["retired_sources"]
        self.assertEqual([row["id"] for row in retired], ["tw02_hpa_child_burn_first_aid_2026"])
        self.assertNotIn(retired[0]["id"], source_ids)
        self.assertEqual(self.sources[retired[0]["id"]], old_sources[retired[0]["id"]])
        self.assertEqual(
            retired[0]["prior_source_sha256"],
            sha(json.dumps(old_sources[retired[0]["id"]], ensure_ascii=False, sort_keys=True).encode("utf-8")),
        )
        self.assertEqual(retired[0]["replacement_ids"], [
            "tw02_mohw_child_burn_prevention_firstaid_2026", "tw02_vghtpe_burn_care_2026"
        ])

    def test_study_statistics_keep_population_denominators_and_limits(self):
        stats = {row["topic"]: row for row in self.review["statistics_assessed"]}
        self.assertEqual(len(stats), 4)
        fields = (
            "value", "unit", "period", "geographic_scope", "population", "numerator",
            "denominator", "event_definition", "data_type", "limitations", "source_ids", "accessed_at",
        )
        for topic, stat in stats.items():
            for field in fields:
                self.assertTrue(stat[field], (topic, field))
            self.assertEqual(stat["accessed_at"], DATE)
            self.assertTrue(set(stat["source_ids"]).issubset(set(self.review["source_ids"])))

        iran = stats["伊朗Golestan茶飲溫度與食道鱗狀細胞癌病例對照"]
        self.assertIn("300", iran["numerator"])
        self.assertIn("571", iran["denominator"])
        self.assertIn("OR 8.16", iran["value"])
        uk = stats["英國兩世代熱飲偏好與食道癌亞型"]
        self.assertIn("977,282", uk["population"])
        self.assertIn("2,348", uk["numerator"])
        self.assertIn("1,045", uk["numerator"])
        self.assertIn("1,303", uk["numerator"])
        china = stats["中國茶溫、吸菸與飲酒聯合暴露及食道癌"]
        self.assertIn("456,155", china["population"])
        self.assertIn("166", china["numerator"])
        self.assertIn("775", china["numerator"])
        self.assertIn("1.55", china["value"])
        self.assertIn("0.31", china["value"])
        self.assertIn("不可歸因於茶溫單一因素", china["limitations"])
        taiwan = stats["台灣男性熱食不適與食道鱗狀細胞癌病例對照"]
        self.assertIn("343", taiwan["numerator"])
        self.assertIn("755", taiwan["denominator"])
        self.assertIn("未直接測量熱飲溫度", taiwan["event_definition"])
        self.assertIn("目前找不到能代表全台民眾飲用熱飲溫度", self.body)
        self.assertIn("不是台灣發生率或個人機率", self.body)
        self.assertIn("流動冷水沖洗15至30分鐘", self.body)
        self.assertIn("立即撥119", self.body)

    def test_batch_counts_and_live_coverage_match_without_marking_publication_ready(self):
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        base_manifest = json.loads(git_bytes(BASE, "localization/manifest.json"))
        base_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        base_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))
        base_register = json.loads(git_bytes(BASE, REGISTER))
        current_coverage = read("localization/tw-edition/coverage.json")
        live_coverage = audit_drafts()

        self.assertEqual(before["manifest_entries"], len(base_manifest["entries"]))
        self.assertEqual(before["verified_core_entries"], sum(row["status"] == "verified" for row in base_manifest["entries"]))
        self.assertEqual(before["runtime_items"], len(base_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(base_runtime["sources"]))
        self.assertEqual(before["source_registry"], base_coverage["registry_sources"])
        self.assertEqual(before["review_rechecks"], len(base_register["substantive_rechecks"]))
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["review_rechecks"], before["review_rechecks"] + 1)
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 2)
        self.assertEqual(after["unresolved_source_id_kinds"], before["unresolved_source_id_kinds"] - 1)
        self.assertEqual(after["unresolved_reference_occurrences"], before["unresolved_reference_occurrences"] - 2)
        self.assertEqual(after["publication_ready"], False)
        self.assertEqual(current_coverage, live_coverage)
        self.assertGreaterEqual(current_coverage["core_reviewed_entries"], after["verified_core_entries"])
        self.assertGreaterEqual(current_coverage["registry_sources"], after["source_registry"])
        self.assertGreaterEqual(current_coverage["json_files_checked"], after["coverage_json_files"])
        self.assertFalse(current_coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()
