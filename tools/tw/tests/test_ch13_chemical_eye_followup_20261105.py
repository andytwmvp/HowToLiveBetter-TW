"""TW-13-021 follow-up: unknown powder, urgent decontamination and provenance."""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, validate_runtime
from retroactive_audit import validate_recheck_history


MAIN_BASE = "5b0235927b13f544aac9a46d9e618e4cae0ec120"
PRIOR_HEAD = "1e2d6a4904123d09217c50c50107df76c7b3e80f"
EVIDENCE_PATH = "localization/ch13-021-chemical-eye-followup-20261105.json"
SOURCE_PATH = "localization/tw-edition/sources/ch13-021-chemical-eye-followup-20261105.json"
ITEM_PATH = "locales/zh-TW/book/ch13/TW-13-021.md"
SOURCE_ID = "ch13_poisoncenter_eye_20261105"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Chapter13ChemicalEyeFollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = read_json(EVIDENCE_PATH)
        cls.item = cls.evidence["item"]
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = read_json("localization/manifest.json")
        cls.manifest_item = next(
            row for row in cls.manifest["entries"] if row["id"] == "TW-13-021"
        )
        cls.review = read_json("localization/reviews/TW-13-021.json")
        cls.register = read_json("localization/retroactive-review-register-20261019.json")

    def test_followup_is_append_only_and_hash_linked(self):
        rows = [
            row
            for row in self.register["substantive_rechecks"]
            if row["id"] == "TW-13-021"
        ]
        prior = next(row for row in rows if row["reviewed_at"] == "2026-11-04")
        current = [row for row in rows if row["reviewed_at"] == "2026-11-05"]
        self.assertEqual(len(current), 1)
        record = current[0]
        self.assertEqual(record, self.item)
        self.assertEqual(record, self.evidence["item"])
        self.assertEqual(rows[-1], record)
        self.assertEqual(self.evidence["reviewed_at"], "2026-11-05")
        self.assertEqual(self.evidence["prior_revision"], PRIOR_HEAD)
        self.assertEqual(record["prior_revision"], PRIOR_HEAD)
        self.assertEqual(record["reviewed_at"], "2026-11-05")
        self.assertEqual(record["review_due_at"], "2027-02-05")
        self.assertEqual(prior["reviewed_at"], "2026-11-04")

        previous = subprocess.check_output(
            ["git", "show", f"{PRIOR_HEAD}:{ITEM_PATH}"], cwd=ROOT
        )
        body_path = ROOT / ITEM_PATH
        body_bytes = body_path.read_bytes()
        body = body_bytes.decode("utf-8")
        self.assertEqual(record["before_sha256"], hashlib.sha256(previous).hexdigest())
        self.assertEqual(record["after_sha256"], hashlib.sha256(body_bytes).hexdigest())
        self.assertEqual(record["body"], body)
        self.assertEqual(record["previous_body"], previous.decode("utf-8"))
        self.assertEqual(self.items["TW-13-021"]["body"], body)
        self.assertEqual(self.review["target_sha256"], record["after_sha256"])
        self.assertEqual(self.review["source_reviewed_sha256"], record["after_sha256"])
        self.assertEqual(self.review["source_checks"], record["source_checks"])
        self.assertEqual(self.review["reviewed_at"], "2026-11-05")
        self.assertEqual(self.review["review_due_at"], "2027-02-05")
        self.assertEqual(self.manifest_item["sources"], record["source_ids"])
        self.assertEqual(self.items["TW-13-021"]["source_ids"], record["source_ids"])
        self.assertEqual(record["status"], "ai_source_rechecked_professional_pending")
        self.assertEqual(record["source_ids"], self.evidence["item"]["source_ids"])
        validate_recheck_history(ROOT, record, self.items["TW-13-021"])

    def test_unknown_powder_gets_immediate_action_and_known_water_reactive_exception(self):
        body = self.items["TW-13-021"]["body"]
        self.assertIn("不明粉末", body)
        self.assertIn("立即", body)
        self.assertIn("沖洗", body)
        self.assertIn("沖洗同時", body)
        self.assertIn("不要揉眼", body)
        self.assertIn("禁水", body)
        self.assertIn("生石灰", body)
        self.assertIn("02-2871-7121", body)
        self.assertIn("02-2875-7525分機85500", body)
        self.assertNotIn("粉末一律不能碰水", body)
        self.assertNotRegex(
            body,
            r"(?:批次摘要|PR\s*#\d+|CI\s*(?:成功|通過)|(?:本次|本輪).{0,16}(?:AI|審查|再審|核對))",
        )
        self.assertNotIn("撥120", body)

    def test_taiwan_poison_center_source_and_runtime_outputs_are_synchronized(self):
        catalog = read_json(SOURCE_PATH)["sources"]
        row = next(source for source in catalog if source[0] == SOURCE_ID)
        source = self.sources[SOURCE_ID]
        self.assertEqual(row, [source["id"], source["title"], source["url"], source["supports"]])
        self.assertEqual(source["accessed_at"], "2026-11-05")
        self.assertEqual(source["url"], "https://www.pcc-vghtpe.tw/active-detail1260.htm")
        self.assertIn("由內往外沖洗15分鐘", source["supports"])
        self.assertIn(SOURCE_ID, self.manifest_item["sources"])
        self.assertIn(SOURCE_ID, self.items["TW-13-021"]["source_ids"])
        check = next(item for item in self.review["source_checks"] if item["source_id"] == SOURCE_ID)
        self.assertEqual(check["accessed_at"], "2026-11-05")
        self.assertIn("眼睛暴露", check["supporting_passage"])
        body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", self.items["TW-13-021"]["body"]))
        runtime_urls = {
            self.sources[source_id]["url"]
            for source_id in self.items["TW-13-021"]["source_ids"]
        }
        review_urls = {check["url"] for check in self.review["source_checks"]}
        self.assertEqual(body_urls, runtime_urls)
        self.assertEqual(review_urls, runtime_urls)
        self.assertTrue(self.evidence["professional_review"]["required"])
        self.assertFalse(self.evidence["professional_review"]["obtained"])

    def test_coverage_counts_include_followup_and_do_not_claim_publication_ready(self):
        coverage = read_json("localization/tw-edition/coverage.json")
        self.assertEqual(coverage["json_files_checked"], self.evidence["counts_after"]["json_files"])
        self.assertEqual(coverage["registry_sources"], self.evidence["counts_after"]["registry_sources"])
        self.assertEqual(len(self.runtime["items"]), self.evidence["counts_after"]["runtime_items"])
        self.assertEqual(len(self.runtime["sources"]), self.evidence["counts_after"]["runtime_sources"])
        self.assertFalse(coverage["publication_ready"])


if __name__ == "__main__":
    unittest.main()
