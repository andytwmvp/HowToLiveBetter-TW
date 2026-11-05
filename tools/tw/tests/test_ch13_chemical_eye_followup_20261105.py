"""TW-13-021 same-day correction: eye-specific chemical guidance and history."""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime
from retroactive_audit import documented_revision, validate_recheck_history
import retroactive_audit as audit


MAIN_BASE = "5b0235927b13f544aac9a46d9e618e4cae0ec120"
FIRST_RECHECK_HEAD = "a1d9d0f32a8131b2740e0ee1b68554490fd9f7fc"
FIRST_RECHECK_BASE = "1e2d6a4904123d09217c50c50107df76c7b3e80f"
SKIN_FOLLOWUP_BASE = "e9afea2e6d896400900882e278edd91b0e93c1fd"
FIRST_EVIDENCE_PATH = "localization/ch13-021-chemical-eye-followup-20261105.json"
CORRECTION_EVIDENCE_PATH = "localization/ch13-021-chemical-eye-correction-20261105.json"
CORRECTION_SOURCE_PATH = "localization/tw-edition/sources/ch13-021-chemical-eye-correction-20261105.json"
SKIN_FOLLOWUP_EVIDENCE_PATH = "localization/ch13-021-skin-exposure-followup-20261105.json"
SKIN_SOURCE_PATH = "localization/tw-edition/sources/ch13-021-skin-exposure-followup-20261105.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
ITEM_PATH = "locales/zh-TW/book/ch13/TW-13-021.md"
RUNTIME_PATH = "localization/tw-edition/runtime.json"
REVIEW_PATH = "localization/reviews/TW-13-021.json"
NEW_SOURCE_IDS = {
    "ch13_vgh_eye_penetrating_20261105",
    "ch13_vgh_chemical_burn_20261105",
    "ch13_moenv_calcium_oxide_eyes_20261105",
}
SKIN_SOURCE_IDS = {
    "ch13_poisoncenter_skin_20261105",
    "ch13_vgh_chemical_skin_burn_20261105",
}


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Chapter13ChemicalEyeFollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first_evidence = read_json(FIRST_EVIDENCE_PATH)
        cls.first_item = cls.first_evidence["item"]
        cls.prior_correction_evidence = read_json(CORRECTION_EVIDENCE_PATH)
        cls.prior_correction = cls.prior_correction_evidence["item"]
        cls.correction_evidence = read_json(SKIN_FOLLOWUP_EVIDENCE_PATH)
        cls.correction = cls.correction_evidence["item"]
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = read_json("localization/manifest.json")
        cls.manifest_item = next(
            row for row in cls.manifest["entries"] if row["id"] == "TW-13-021"
        )
        cls.review = read_json(REVIEW_PATH)
        cls.register = read_json(REGISTER_PATH)

    def test_same_day_records_are_append_only_and_hash_linked(self):
        current_register = self.register["substantive_rechecks"]
        rows = [row for row in current_register if row["id"] == "TW-13-021"]
        baseline_register = json.loads(git_bytes(FIRST_RECHECK_HEAD, REGISTER_PATH))
        baseline_rows = [
            row for row in baseline_register["substantive_rechecks"]
            if row["id"] == "TW-13-021"
        ]
        self.assertEqual(rows[:-2], baseline_rows)
        self.assertEqual(rows[-2:], [self.prior_correction, self.correction])

        same_day = [row for row in rows if row["reviewed_at"] == "2026-11-05"]
        self.assertEqual(len(same_day), 3)
        first = same_day[0]
        self.assertEqual(first, self.first_item)
        self.assertEqual(same_day[1], self.prior_correction)
        self.assertEqual(same_day[2], self.correction)
        self.assertEqual(first["prior_revision"], FIRST_RECHECK_BASE)
        self.assertEqual(self.prior_correction["prior_revision"], FIRST_RECHECK_HEAD)
        self.assertEqual(self.correction["prior_revision"], SKIN_FOLLOWUP_BASE)
        self.assertEqual(self.correction["reviewed_at"], "2026-11-05")
        self.assertEqual(self.correction["review_due_at"], "2027-02-05")
        self.assertEqual(self.correction_evidence["baseline_main_sha"], MAIN_BASE)

        old_body = git_bytes(FIRST_RECHECK_BASE, ITEM_PATH)
        first_body = git_bytes(FIRST_RECHECK_HEAD, ITEM_PATH)
        current_body = (ROOT / ITEM_PATH).read_bytes()
        self.assertEqual(first["before_sha256"], digest(old_body))
        self.assertEqual(first["after_sha256"], digest(first_body))
        self.assertEqual(first["previous_body"].encode("utf-8"), old_body)
        self.assertEqual(first["body"].encode("utf-8"), first_body)
        prior_runtime = json.loads(git_bytes(FIRST_RECHECK_BASE, RUNTIME_PATH))
        first_runtime = json.loads(git_bytes(FIRST_RECHECK_HEAD, RUNTIME_PATH))
        old_item = next(row for row in prior_runtime["items"] if row["id"] == "TW-13-021")
        first_item = next(row for row in first_runtime["items"] if row["id"] == "TW-13-021")
        self.assertTrue(audit._historical_edge_is_valid(
            ROOT, FIRST_RECHECK_HEAD, first, old_item, first_item
        ))

        first_correction_before = git_bytes(FIRST_RECHECK_HEAD, ITEM_PATH)
        first_correction_body = git_bytes(SKIN_FOLLOWUP_BASE, ITEM_PATH)
        self.assertEqual(self.prior_correction["before_sha256"], digest(first_correction_before))
        self.assertEqual(self.prior_correction["after_sha256"], digest(first_correction_body))
        self.assertEqual(self.prior_correction["previous_body"].encode("utf-8"), first_correction_before)
        self.assertEqual(self.prior_correction["body"].encode("utf-8"), first_correction_body)

        correction_before = git_bytes(SKIN_FOLLOWUP_BASE, ITEM_PATH)
        prior_review = git_bytes(SKIN_FOLLOWUP_BASE, REVIEW_PATH)
        current = self.items["TW-13-021"]
        self.assertEqual(self.correction["before_sha256"], digest(correction_before))
        self.assertEqual(self.correction["after_sha256"], digest(current_body))
        self.assertEqual(self.correction["prior_review_sha256"], digest(prior_review))
        self.assertEqual(self.correction["previous_body"].encode("utf-8"), correction_before)
        self.assertEqual(self.correction["body"].encode("utf-8"), current_body)
        self.assertEqual(current["body"], current_body.decode("utf-8"))
        self.assertEqual(self.review["target_sha256"], self.correction["after_sha256"])
        self.assertEqual(self.review["source_reviewed_sha256"], self.correction["after_sha256"])
        self.assertEqual(self.review["source_checks"], self.correction["source_checks"])
        self.assertEqual(self.manifest_item["sources"], self.correction["source_ids"])
        self.assertEqual(current["source_ids"], self.correction["source_ids"])
        self.assertEqual(self.correction["status"], "ai_source_rechecked_professional_pending")
        self.assertTrue(self.correction["question_change_reason"])
        self.assertEqual(current["limits"], self.review["limits"][0])
        validate_recheck_history(ROOT, self.correction, current)

        prior_runtime = json.loads(git_bytes(SKIN_FOLLOWUP_BASE, RUNTIME_PATH))
        prior_item = next(row for row in prior_runtime["items"] if row["id"] == "TW-13-021")
        self.assertTrue(documented_revision(prior_item, current, self.correction))
        undocumented = dict(self.correction)
        undocumented.pop("question_change_reason")
        self.assertFalse(documented_revision(prior_item, current, undocumented))
        incomplete_question = dict(current, question="我已瞭解化學品入眼要怎麼處理嗎？")
        self.assertFalse(documented_revision(prior_item, incomplete_question, self.correction))

    def test_powder_guidance_cites_specific_reactive_powder_and_keeps_unknown_limit(self):
        body = self.items["TW-13-021"]["body"]
        introduction = body.split("## 臺灣實作與下一步", 1)[0]
        self.assertIn("化學液體濺入眼睛", introduction)
        self.assertNotIn("化學液體或粉末入眼時", introduction)
        powder = body.split("成分不明的乾粉或粉狀／金屬化學品入眼時", 1)[1].split(
            "\n\n皮膚接觸要依皮膚的專屬處置", 1
        )[0]
        unresolved = powder.split("環境部化學知識地圖", 1)[0]
        self.assertIn("先離開粉塵或外洩區", powder)
        self.assertIn("不要揉眼、壓眼", powder)
        self.assertIn("沒有說明後一項如何套用到眼睛", powder)
        self.assertIn("眼睛接觸", powder)
        self.assertIn("依其「眼睛接觸」專屬指示處理", powder)
        self.assertIn("粉狀或金屬化學物質不可用水清洗", powder)
        self.assertIn("立即聯絡24小時毒藥物防治諮詢中心", unresolved)
        self.assertIn("安排就近急診", unresolved)
        self.assertIn("不要等回電", unresolved)
        self.assertNotIn("立刻以大量流動清水或生理食鹽水", unresolved)
        self.assertIn("氧化鈣（生石灰，白色粉末", powder)
        self.assertIn("30分鐘", powder)
        self.assertIn("未知粉末的處置界線仍待毒物及眼科專業確認", powder)
        self.assertIn("不要揉眼", body)
        self.assertIn("立刻以大量流動清水或生理食鹽水", body)
        self.assertIn("同步聯絡毒藥物防治諮詢中心", body)
        self.assertIn("安排急診評估", body)
        self.assertIn("02-2871-7121", body)
        self.assertIn("02-2875-7525分機85500", body)
        self.assertIn("撥119", body)
        self.assertIn("眼球穿刺傷勿沖洗、揉搓或拔除異物", body)
        self.assertNotIn("粉末一律不能碰水", body)
        self.assertNotRegex(
            body,
            r"(?:批次摘要|PR\s*#\d+|CI\s*(?:成功|通過)|(?:本次|本輪).{0,16}(?:AI|審查|再審|核對))",
        )
        self.assertNotIn("撥120", body)

    def test_skin_exposure_separates_liquid_rinse_from_dry_powder_caution(self):
        body = self.items["TW-13-021"]["body"]
        skin = body.split("皮膚接觸要依皮膚的專屬處置", 1)[1].split(
            "\n\n若尖銳物刺入眼球", 1
        )[0]
        self.assertIn("一般液體化學品沾到皮膚", skin)
        self.assertIn("立即以大量流動清水沖洗至少15分鐘", skin)
        self.assertIn("旁人同步聯絡毒物中心", skin)
        self.assertIn("化學灼傷", skin)
        self.assertIn("沖洗至少30分鐘", skin)
        self.assertIn("成分不明乾粉或粉狀／金屬化學物質", skin)
        self.assertIn("不要揉擦、揚起或自行加水測試", skin)
        self.assertIn("先去除殘留物再沖洗", skin)
        self.assertIn("這些特定皮膚處置不能套用到其他乾粉或眼睛", skin)
        self.assertIn("立即撥119", skin)

    def test_runtime_self_check_question_covers_the_same_emergency_branches(self):
        question = self.items["TW-13-021"]["question"]
        for token in (
            "液體化學品", "成分不明粉末", "避免揉挖", "立即求助", "毒物中心",
            "已知物質", "眼球穿刺傷", "立即就醫", "毒物中心", "119",
            "液體沾皮膚", "乾粉或金屬化學物質沾皮膚", "禁水指引", "化學灼傷"
        ):
            with self.subTest(token=token):
                self.assertIn(token, question)
        self.assertIn("question_change_reason", self.correction)

    def test_source_retirement_and_new_official_sources_are_synchronized(self):
        source_rows = read_json(CORRECTION_SOURCE_PATH)["sources"]
        rows_by_id = {row[0]: row for row in source_rows}
        self.assertEqual(set(rows_by_id), NEW_SOURCE_IDS)
        for source_id in NEW_SOURCE_IDS:
            source = self.sources[source_id]
            self.assertEqual(
                rows_by_id[source_id],
                [source["id"], source["title"], source["url"], source["supports"]],
            )
            self.assertEqual(source["accessed_at"], "2026-11-05")
        retired = self.prior_correction["retired_sources"][0]
        historical_runtime = json.loads(git_bytes(FIRST_RECHECK_HEAD, RUNTIME_PATH))
        old_source = next(
            row for row in historical_runtime["sources"] if row["id"] == retired["id"]
        )
        self.assertEqual(retired["id"], "ch13_eyeinjury_vghks")
        self.assertEqual(
            retired["prior_source_sha256"],
            digest(json.dumps(old_source, ensure_ascii=False, sort_keys=True).encode("utf-8")),
        )
        self.assertEqual(retired["replacement_ids"], ["ch13_vgh_eye_penetrating_20261105"])
        self.assertIn(retired["id"], self.sources)

        skin_source = read_json(SKIN_SOURCE_PATH)["sources"]
        self.assertEqual({row[0] for row in skin_source}, SKIN_SOURCE_IDS)
        self.assertEqual(set(self.correction_evidence["new_source_ids"]), SKIN_SOURCE_IDS)
        for row in skin_source:
            skin_source_id = row[0]
            self.assertEqual(
                row,
                [self.sources[skin_source_id]["id"], self.sources[skin_source_id]["title"],
                 self.sources[skin_source_id]["url"], self.sources[skin_source_id]["supports"]],
            )
            self.assertIn("皮膚", self.sources[skin_source_id]["supports"])

        source_ids = self.items["TW-13-021"]["source_ids"]
        body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", self.items["TW-13-021"]["body"]))
        runtime_urls = {self.sources[source_id]["url"] for source_id in source_ids}
        review_urls = {check["url"] for check in self.review["source_checks"]}
        self.assertEqual(body_urls, runtime_urls)
        self.assertEqual(review_urls, runtime_urls)
        self.assertIn(
            "https://topic.moenv.gov.tw/chemiknowledgemap/sp-chemical-7-20-5.html",
            body_urls,
        )
        self.assertTrue(self.correction_evidence["professional_review"]["required"])
        self.assertFalse(self.correction_evidence["professional_review"]["obtained"])

    def test_coverage_counts_include_correction_and_do_not_claim_publication_ready(self):
        coverage = json.loads(git_bytes("8591a38edaabd67fde37186a6f259ea2b8998fda", "localization/tw-edition/coverage.json"))
        runtime = json.loads(git_bytes("8591a38edaabd67fde37186a6f259ea2b8998fda", RUNTIME_PATH))
        counts = self.correction_evidence["counts_after"]
        self.assertEqual(coverage["json_files_checked"], counts["json_files"])
        self.assertEqual(coverage["registry_sources"], counts["registry_sources"])
        self.assertEqual(len(runtime["items"]), counts["runtime_items"])
        self.assertEqual(len(runtime["sources"]), counts["runtime_sources"])
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()
