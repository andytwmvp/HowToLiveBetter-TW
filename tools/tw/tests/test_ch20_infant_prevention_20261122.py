"""第20章嬰幼兒補種、蜂蜜、維生素K及洗澡防燙首次發布契約。"""
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

BASE = "40f82aac2e0b0b88f11fa3b1edae119df2a3f8ec"
DATE = "2026-11-22"
DUE = "2027-02-22"
BUNDLE = "localization/tw-edition/sources/ch20-infant-prevention-20261122.json"
STAGE = "localization/ch20-infant-prevention-20261122.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
ARTICLES = {
    "TW-20-003": {
        "title": "嬰幼兒疫苗漏打或延遲，帶著紀錄請接種院所安排補種",
        "path": "locales/zh-TW/book/ch20/TW-20-003.md",
        "sources": ["tw20_cdc_schedule_11509", "tw20_cdc_vaccine_catchup_guide", "tw20_cdc_vaccine_record_query", "tw20_cdc_selfpaid_vaccines_2025"],
    },
    "TW-20-006": {
        "title": "未滿1歲的嬰兒不要餵蜂蜜",
        "path": "locales/zh-TW/book/ch20/TW-20-006.md",
        "sources": ["tw20_cdc_botulism_guidance_2026", "tw20_cdc_infant_botulism_case_2024"],
    },
    "TW-20-007": {
        "title": "新生兒維生素K預防，和醫療團隊確認適合的給藥安排",
        "path": "locales/zh-TW/book/ch20/TW-20-007.md",
        "sources": ["tw20_tsn_vitamin_k_2025", "tw20_tfda_phytomenadione_label", "tw20_mohw_phytomenadione_notice_2022"],
    },
    "TW-20-017": {
        "title": "幫嬰兒洗澡先放冷水再加熱水，水溫不超過40°C並全程看護",
        "path": "locales/zh-TW/book/ch20/TW-20-017.md",
        "sources": ["tw20_hpa_child_burn_prevention_2026", "tw20_hpa_infant_bath_preparation"],
    },
}
NEW_SOURCES = {source for row in ARTICLES.values() for source in row["sources"]} - {"tw20_cdc_schedule_11509"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Chapter20InfantPreventionPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in ARTICLES}
        cls.bodies = {key: (ROOT / spec["path"]).read_text(encoding="utf-8") for key, spec in ARTICLES.items()}
        cls.bundle = read(BUNDLE)
        cls.stage = read(STAGE)
        cls.register = read(REGISTER)
        cls.base_register = json.loads(git_bytes(BASE, REGISTER))
        cls.base_runtime = json.loads(git_bytes(BASE, "localization/tw-edition/runtime.json"))
        cls.base_coverage = json.loads(git_bytes(BASE, "localization/tw-edition/coverage.json"))

    def test_first_publication_preserves_ids_upstream_hashes_and_history(self):
        self.assertEqual(self.stage["baseline_main_sha"], BASE)
        baseline = {row["id"]: row for row in json.loads(git_bytes(BASE, "localization/manifest.json"))["entries"]}
        for key, spec in ARTICLES.items():
            old = baseline[key]
            self.assertEqual((old["status"], old["target_path"], old["sources"]), ("pending", None, []))
            self.assertIsNone(git_bytes(BASE, spec["path"]))
            current = self.manifest[key]
            self.assertEqual((current["status"], current["treatment"], current["verified_at"]), ("verified", "taiwan_independent_rewrite", DATE))
            self.assertEqual((current["upstream_commit"], current["upstream_text_sha256"]), (old["upstream_commit"], old["upstream_text_sha256"]))
            self.assertEqual((current["target_path"], current["sources"]), (spec["path"], spec["sources"]))
        baseline_rows = self.base_register["substantive_rechecks"]
        self.assertEqual(
            self.register["substantive_rechecks"][:len(baseline_rows)],
            baseline_rows,
            "較新的歷史再審只能追加，不能改寫本批之前的紀錄",
        )
        self.assertEqual(self.stage["counts_before"]["review_rechecks"], len(baseline_rows))
        self.assertEqual(
            self.stage["counts_after"]["review_rechecks"],
            self.stage["counts_before"]["review_rechecks"],
        )
        self.assertGreaterEqual(
            len(self.register["substantive_rechecks"]),
            self.stage["counts_after"]["review_rechecks"],
        )
        baseline_cleanups = self.base_register.get("reader_copy_cleanups", [])
        current_cleanups = self.register.get("reader_copy_cleanups", [])
        self.assertEqual(current_cleanups[:len(baseline_cleanups)], baseline_cleanups)
        self.assertEqual(
            {key: value for key, value in self.register.items()
             if key not in {"substantive_rechecks", "reader_copy_cleanups"}},
            {key: value for key, value in self.base_register.items()
             if key not in {"substantive_rechecks", "reader_copy_cleanups"}},
        )
        base_item_ids = [row["id"] for row in self.base_runtime["items"]]
        current_item_ids = [row["id"] for row in self.runtime["items"]]
        self.assertEqual([key for key in current_item_ids if key in set(base_item_ids)], base_item_ids)
        self.assertTrue(set(ARTICLES).issubset(set(current_item_ids)))
        self.assertGreaterEqual(len(self.runtime["items"]), len(self.base_runtime["items"]) + len(ARTICLES))
        base_sources = {row["id"]: row for row in self.base_runtime["sources"]}
        self.assertEqual(
            [self.sources[key] for key in base_sources],
            list(base_sources.values()),
            "既有來源必須保留原順序和內容",
        )
        self.assertTrue(NEW_SOURCES.issubset(set(self.sources) - set(base_sources)))
        self.assertGreaterEqual(len(self.runtime["sources"]), len(self.base_runtime["sources"]) + len(NEW_SOURCES))

    def test_reader_body_runtime_review_sources_and_sha_are_consistent(self):
        base_ids = [row["id"] for row in self.base_runtime["items"]]
        current_ids = [row["id"] for row in self.runtime["items"]]
        self.assertEqual([key for key in current_ids if key in set(base_ids)], base_ids)
        chapter = (ROOT / "locales/zh-TW/book/ch20/README.md").read_text(encoding="utf-8")
        chapter_ids = [int(n) for n in re.findall(r"TW-20-(\d{3})\.md", chapter)]
        runtime_chapter_ids = sorted(
            int(item["id"].rsplit("-", 1)[1])
            for item in self.runtime["items"]
            if item["id"].startswith("TW-20-")
            and item.get("target_path", "").startswith("locales/zh-TW/book/ch20/")
        )
        self.assertEqual(chapter_ids, runtime_chapter_ids)
        for key, spec in ARTICLES.items():
            with self.subTest(id=key):
                body = self.bodies[key]
                raw = body.encode("utf-8")
                digest = sha(raw)
                item, entry, review = self.items[key], self.manifest[key], self.reviews[key]
                self.assertEqual((item["body"], item["target_path"], item["title"]), (body, spec["path"], spec["title"]))
                self.assertEqual((item["source_ids"], item["review_status"]), (spec["sources"], "source_checked"))
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual((review["target_sha256"], review["source_reviewed_sha256"], review["after_sha256"]), (digest, digest, digest))
                self.assertIsNone(review["before_sha256"])
                self.assertEqual(review["source_bundle_path"], BUNDLE)
                self.assertEqual(review["source_bundle_sha256"], sha((ROOT / BUNDLE).read_bytes()))
                self.assertEqual(review["source_ids"], spec["sources"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertTrue(review["professional_review"]["scope"])
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual({row["source_id"] for row in review["source_checks"]}, set(spec["sources"]))
                linked_urls = set(re.findall(r"\]\((https://[^)]+)\)", body))
                self.assertEqual(linked_urls, {self.sources[sid]["url"] for sid in spec["sources"]})
                self.assertNotRegex(body, r"(批次摘要|AI協助|本次.{0,12}(?:審查|再審|核對)|CI\s*(?:成功|通過)|PR\s*#\d+|待專業審閱|fork管理|原作固定ID|本輪|本批)")
                self.assertNotRegex(body, r"(繁體字形轉換稿|臺灣改寫與來源重核|管理說明|內部審閱)")

    def test_frequency_statistics_and_substantive_content_are_supported(self):
        vaccines = self.bodies["TW-20-003"]
        self.assertIn("查不到紀錄不一定代表沒有接種", vaccines)
        self.assertIn("最小接種年齡、劑次和間隔可能不同", vaccines)
        self.assertIn("非公費疫苗需自費", vaccines)
        self.assertEqual(self.reviews["TW-20-003"]["statistics_assessed"], [])
        self.assertIn("未找到", self.reviews["TW-20-003"]["frequency_assessment"])

        honey = self.bodies["TW-20-006"]
        self.assertIn("未滿1歲", honey)
        self.assertIn("不能換算個人發生機率", honey)
        self.assertIn("呼吸困難或反應變差時立即撥119", honey)
        stat = self.reviews["TW-20-006"]["statistics_assessed"][0]
        self.assertEqual((stat["numerator"], stat["denominator"], stat["unit"]), (3, None, "確診病例數"))
        self.assertIn("病例累計數不含適當人口或暴露分母", stat["limitations"][0])
        self.assertIn("不能推論病例是由蜂蜜造成", stat["limitations"][1])

        vitamin = self.bodies["TW-20-007"]
        self.assertIn("預防性補充", vitamin)
        self.assertIn("嚴重甚至致命過敏反應", vitamin)
        self.assertIn("有警語不等於該反應常見", vitamin)
        self.assertIn("2022年5月9日", vitamin)
        self.assertEqual(self.reviews["TW-20-007"]["statistics_assessed"], [])

        bath = self.bodies["TW-20-017"]
        self.assertIn("先放冷水，再加入熱水", bath)
        self.assertIn("不得超過攝氏40度", bath)
        self.assertIn("全程看護", bath)
        self.assertIn("../ch13/TW-13-014.md", bath)
        self.assertNotIn("50°C", bath)
        self.assertEqual(self.reviews["TW-20-017"]["statistics_assessed"], [])

    def test_bundle_coverage_counts_and_nonpublication_state_are_live(self):
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual({row[0] for row in self.bundle["sources"]}, NEW_SOURCES)
        self.assertEqual(len([row[0] for row in self.bundle["sources"]]), len(NEW_SOURCES), "來源 bundle 不得重複登錄相同 ID")
        current_source_ids = set(self.sources)
        base_source_ids = {row["id"] for row in self.base_runtime["sources"]}
        self.assertTrue(NEW_SOURCES.issubset(current_source_ids - base_source_ids))
        self.assertTrue(NEW_SOURCES.issubset(source_bundle_ids_added_since(ROOT, BASE)))
        bundled = {row[0]: row for row in self.bundle["sources"]}
        for sid in NEW_SOURCES:
            source = self.sources[sid]
            self.assertEqual(bundled[sid], [source[k] for k in ("id", "title", "url", "supports")])
        from ci_language_policy import audit_drafts
        coverage = read("localization/tw-edition/coverage.json")
        self.assertEqual(coverage, audit_drafts())
        self.assertFalse(coverage["publication_ready"])
        publication = publication_report(ROOT)
        self.assertEqual(publication["publication_completed_entries"], coverage["publication_completed_entries"])
        self.assertFalse(publication["publication_ready"])
        self.assertEqual(self.stage["counts_before"]["publication_completed_entries"], self.base_coverage["publication_completed_entries"])
        self.assertEqual(self.stage["counts_after"]["publication_completed_entries"], 344)
        self.assertEqual(self.stage["counts_before"]["review_rechecks"], self.stage["counts_after"]["review_rechecks"])
        self.assertEqual(self.stage["counts_before"]["runtime_items"], 351)
        self.assertEqual(self.stage["counts_after"]["runtime_items"], 355)


if __name__ == "__main__":
    unittest.main()
