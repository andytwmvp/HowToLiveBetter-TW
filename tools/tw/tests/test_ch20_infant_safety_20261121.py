"""第20章嬰兒安全六篇首次正式發布契約。"""
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
from review_contract import publication_report, validate_runtime
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "b2c31fe1eb414e7f9bf869d2044022823bce1ceb"
DATE = "2026-11-21"
DUE = "2027-02-21"
REGISTER = "localization/retroactive-review-register-20261019.json"
BUNDLE = "localization/tw-edition/sources/ch20-infant-safety-20261121.json"
STAGE = "localization/ch20-infant-safety-20261121.json"
ARTICLES = {
    "TW-20-001": {"title": "嬰兒每次睡覺都仰睡，使用平坦堅實且淨空的睡眠空間", "path": "locales/zh-TW/book/ch20/TW-20-001.md", "sources": ["tw20_hpa_safe_sleep_5steps", "tw20_hpa_safe_sleep_5ng", "tw20_mohw_child_death_review"]},
    "TW-20-002": {"title": "新生兒B型肝炎疫苗，依台灣時程在出生後儘速接種", "path": "locales/zh-TW/book/ch20/TW-20-002.md", "sources": ["tw20_cdc_schedule_11509", "tw20_cdc_hepb_vaccine", "tw20_cdc_hbig_eligibility", "tw20_cdc_hbig_qna"]},
    "TW-20-005": {"title": "沖泡嬰兒配方奶粉，遵照標示並注意70°C與保存時間", "path": "locales/zh-TW/book/ch20/TW-20-005.md", "sources": ["tw20_hpa_formula_preparation", "tw20_hpa_newborn_feeding", "tw20_vghtc_formula_guide_2026"]},
    "TW-20-008": {"title": "未滿3個月嬰兒發燒，儘速到醫院接受評估", "path": "locales/zh-TW/book/ch20/TW-20-008.md", "sources": ["tw20_hpa_infant_health", "tw34_pids_fever_2019"]},
    "TW-20-009": {"title": "寶寶哭鬧時先求援，絕不劇烈搖晃或拋接", "path": "locales/zh-TW/book/ch20/TW-20-009.md", "sources": ["tw20_hpa_infant_health", "tw20_hpa_no_shake", "tw20_mohw_3hearts", "tw20_hpa_calm_baby"]},
    "TW-20-013": {"title": "新生兒黃疸要看精神、吃奶與大便顏色，異常時儘速就醫", "path": "locales/zh-TW/book/ch20/TW-20-013.md", "sources": ["tw20_hpa_stool_color_2026", "tw20_hpa_jaundice_care", "tw20_hpa_jaundice_leaflet_2019"]},
}
NEW_SOURCE_IDS = {sid for item in ARTICLES.values() for sid in item["sources"]} - {"tw34_pids_fever_2019"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Chapter20InfantSafetyPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in ARTICLES}
        cls.articles = {key: (ROOT / spec["path"]).read_bytes() for key, spec in ARTICLES.items()}
        cls.bodies = {key: raw.decode("utf-8") for key, raw in cls.articles.items()}
        cls.bundle = read(BUNDLE)
        cls.stage = read(STAGE)
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.register = read(REGISTER)
        cls.batch_items = {row["id"]: row for row in cls.stage["items"]}

    def test_fixed_ids_and_first_publication_preserve_history(self):
        self.assertEqual(self.stage["baseline_main_sha"], BASE)
        baseline_manifest = {row["id"]: row for row in json.loads(git_bytes(BASE, "localization/manifest.json"))["entries"]}
        baseline_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        for key, spec in ARTICLES.items():
            old = baseline_manifest[key]
            self.assertEqual((old["status"], old["target_path"], old["sources"]), ("pending", None, []))
            self.assertIsNone(git_bytes(BASE, spec["path"]))
            current = self.manifest[key]
            self.assertEqual((current["status"], current["treatment"], current["verified_at"]), ("verified", "taiwan_independent_rewrite", DATE))
            self.assertEqual((current["upstream_commit"], current["upstream_text_sha256"]), (old["upstream_commit"], old["upstream_text_sha256"]))
            self.assertEqual((current["target_path"], current["sources"]), (spec["path"], spec["sources"]))
        self.assertEqual(self.register["unpublished_core_inventory"], baseline_register["unpublished_core_inventory"])
        self.assertEqual(self.register["substantive_rechecks"], baseline_register["substantive_rechecks"])
        current_items = {row["id"]: row for row in self.runtime["items"]}
        self.assertEqual([current_items[row["id"]] for row in baseline_runtime["items"]], baseline_runtime["items"])
        self.assertTrue(set(ARTICLES).issubset(current_items))
        self.assertGreaterEqual(len(self.runtime["items"]), len(baseline_runtime["items"]) + len(ARTICLES))
        baseline_source_ids = [row["id"] for row in baseline_runtime["sources"]]
        self.assertEqual([self.sources[source_id] for source_id in baseline_source_ids], baseline_runtime["sources"])
        self.assertTrue(NEW_SOURCE_IDS.issubset(set(self.sources) - set(baseline_source_ids)))
        self.assertGreaterEqual(len(self.runtime["sources"]), len(baseline_runtime["sources"]) + len(NEW_SOURCE_IDS))
        self.assertEqual(self.stage["counts_before"]["review_rechecks"], len(baseline_register["substantive_rechecks"]))
        self.assertEqual(self.stage["counts_after"]["review_rechecks"], self.stage["counts_before"]["review_rechecks"])

    def test_markdown_runtime_reviews_sources_and_hashes_match(self):
        base_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        base_ids = [row["id"] for row in base_runtime["items"]]
        current_ids = [row["id"] for row in self.runtime["items"]]
        self.assertEqual([key for key in current_ids if key in set(base_ids)], base_ids)
        chapter = (ROOT / "locales/zh-TW/book/ch20/README.md").read_text(encoding="utf-8")
        index = (ROOT / "locales/zh-TW/README.md").read_text(encoding="utf-8")
        chapter_ids = [int(n) for n in re.findall(r"TW-20-(\d{3})\.md", chapter)]
        earlier_batch_ids = [1, 2, 5, 8, 9, 13]
        self.assertTrue(set(earlier_batch_ids).issubset(chapter_ids))
        self.assertEqual([number for number in chapter_ids if number in set(earlier_batch_ids)], earlier_batch_ids)
        self.assertEqual(index.count("[第20章：新生兒與嬰兒照護](book/ch20/README.md)"), 1)
        for key, spec in ARTICLES.items():
            with self.subTest(id=key):
                body, digest = self.bodies[key], sha(self.articles[key])
                item, entry, review, batch = self.items[key], self.manifest[key], self.reviews[key], self.batch_items[key]
                self.assertEqual(item["body"], body)
                self.assertEqual(item["title"], spec["title"])
                self.assertEqual(re.search(r"^# (.+)$", body, re.MULTILINE).group(1), spec["title"])
                self.assertEqual((item["target_path"], item["source_ids"], item["review_status"]), (spec["path"], spec["sources"], "source_checked"))
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual((review["target_sha256"], review["source_reviewed_sha256"], review["after_sha256"]), (digest, digest, digest))
                self.assertIsNone(review["before_sha256"])
                self.assertEqual((batch["after_sha256"], batch["target_sha256"]), (digest, digest))
                self.assertEqual(review["source_bundle_path"], BUNDLE)
                self.assertEqual(review["source_bundle_sha256"], sha((ROOT / BUNDLE).read_bytes()))
                self.assertEqual(review["source_ids"], spec["sources"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertTrue(review["professional_review"]["scope"])
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual({row["source_id"] for row in review["source_checks"]}, set(spec["sources"]))
                self.assertEqual({url for url in re.findall(r"\]\((https://[^)]+)\)", body)}, {self.sources[sid]["url"] for sid in spec["sources"]})
                self.assertNotRegex(body, r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理)")

    def test_taiwan_safety_content_frequency_and_topic_fidelity(self):
        safe = self.bodies["TW-20-001"]
        self.assertIn("仰睡", safe)
        self.assertIn("同室不同床", safe)
        self.assertIn("不是所有嬰兒的出生世代或睡眠暴露調查", safe)
        stat = self.reviews["TW-20-001"]["statistics_assessed"]
        self.assertEqual([(x["numerator"], x["denominator"]) for x in stat], [(43, 344), (41, 344)])
        self.assertTrue(all("睡眠暴露" in x["limitations"] for x in stat))
        vaccine = self.bodies["TW-20-002"]
        self.assertIn("出生24小時內", vaccine)
        self.assertIn("未滿600公克", vaccine)
        self.assertIn("出生劑次不列入後續完整3劑", vaccine)
        formula = self.bodies["TW-20-005"]
        self.assertIn("水溫至少70°C", formula)
        self.assertIn("兩小時", formula)
        fever = self.bodies["TW-20-008"]
        self.assertIn("儘速由醫療人員評估", fever)
        crying = self.bodies["TW-20-009"]
        self.assertIn("TW-20-001.md", crying)
        jaundice = self.bodies["TW-20-013"]
        self.assertIn("第14天", jaundice)
        self.assertIn("1至6號", jaundice)
        for key, review in self.reviews.items():
            self.assertTrue(review["frequency_assessment"])
            self.assertTrue(review["limits"])
            if key != "TW-20-001":
                self.assertEqual(review["statistics_assessed"], [])

    def test_new_source_bundle_coverage_and_counts_are_live(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual({row[0] for row in self.bundle["sources"]}, NEW_SOURCE_IDS)
        base_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        base_source_ids = {row["id"] for row in base_runtime["sources"]}
        self.assertIn("tw34_pids_fever_2019", base_source_ids)
        self.assertTrue(NEW_SOURCE_IDS.issubset(set(self.sources) - base_source_ids))
        self.assertTrue(NEW_SOURCE_IDS.issubset(source_bundle_ids_added_since(ROOT, BASE)))
        bundled = {row[0]: row for row in self.bundle["sources"]}
        for sid in NEW_SOURCE_IDS:
            source = self.sources[sid]
            self.assertEqual(bundled[sid], [source["id"], source["title"], source["url"], source["supports"]])
        self.assertEqual(self.coverage, audit_drafts())
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.coverage["publication_completed_entries"], publication_report()["publication_completed_entries"])
        self.assertTrue(set(ARTICLES).isdisjoint({row.split(":")[0] for row in self.coverage["publication_blockers"]}))
        before, after = self.stage["counts_before"], self.stage["counts_after"]
        self.assertEqual(after["manifest_entries"], before["manifest_entries"])
        self.assertEqual(after["verified_core_entries"], before["verified_core_entries"] + len(ARTICLES))
        self.assertEqual(after["runtime_items"], before["runtime_items"] + len(ARTICLES))
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + len(ARTICLES) + 2)
        self.assertEqual(after["review_rechecks"], before["review_rechecks"])
        self.assertFalse(after["publication_ready"])


if __name__ == "__main__":
    unittest.main()
