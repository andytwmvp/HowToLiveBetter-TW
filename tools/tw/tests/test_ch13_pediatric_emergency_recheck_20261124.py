"""第13章兒少急救再審：急救步驟、統計範圍與歷史雜湊契約。"""
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


BASE = "915ab7ac3c8eecba8221facfa182bdaf8f54f281"
DATE = "2026-11-24"
DUE = "2027-02-24"
BATCH = "localization/ch13-pediatric-emergency-recheck-20261124.json"
BUNDLE = "localization/tw-edition/sources/ch13-pediatric-emergency-recheck-20261124.json"
REGISTER = "localization/retroactive-review-register-20261019.json"
IDS = ("TW-13-026", "TW-13-043", "TW-13-044", "TW-13-045")
NEW_SOURCE_IDS = {
    "ch13_choke_ntpc_114_20261124",
    "ch13_infant_choke_faq_tpe_20261124",
    "ch13_battery_ncpc_20261124",
    "ch13_battery_tsem_canonical_20261124",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def at_revision(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


class PediatricEmergencyRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in IDS}
        cls.register = read(REGISTER)
        cls.batch = read(BATCH)
        cls.batch_items = {row["id"]: row for row in cls.batch["items"]}
        cls.bundle = read(BUNDLE)

    def test_append_only_hash_and_source_edges_are_exact(self):
        baseline_runtime = json.loads(at_revision(BASE, "localization/tw-edition/runtime.json"))
        baseline_register = json.loads(at_revision(BASE, REGISTER))
        baseline_sources = {row["id"]: row for row in baseline_runtime["sources"]}
        baseline_items = {row["id"]: row for row in baseline_runtime["items"]}
        baseline_entries = {
            row["id"]: row
            for row in json.loads(at_revision(BASE, "localization/manifest.json"))["entries"]
        }
        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual(self.batch["reviewed_at"], DATE)
        self.assertEqual(self.batch["review_due_at"], DUE)
        self.assertEqual(set(self.batch_items), set(IDS))
        self.assertEqual(
            self.register["substantive_rechecks"][:len(baseline_register["substantive_rechecks"])],
            baseline_register["substantive_rechecks"],
        )
        self.assertEqual(self.bundle["baseline_main_sha"], BASE)
        self.assertEqual({row[0] for row in self.bundle["sources"]}, NEW_SOURCE_IDS)
        self.assertTrue(self.batch["professional_review_pending"])
        self.assertFalse(self.batch["publication_ready"])

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                row = self.batch_items[item_id]
                current = self.items[item_id]
                review = self.reviews[item_id]
                entry = self.manifest[item_id]
                body_bytes = (ROOT / current["target_path"]).read_bytes()
                body = body_bytes.decode("utf-8")
                body_sha = digest(body_bytes)
                history = [
                    record for record in self.register["substantive_rechecks"]
                    if record["id"] == item_id and record["reviewed_at"] == DATE
                ]
                self.assertEqual(history, [row])
                self.assertEqual(row["before_sha256"], digest(baseline_items[item_id]["body"].encode()))
                self.assertEqual(row["previous_body"], baseline_items[item_id]["body"])
                self.assertEqual(row["prior_review_sha256"], digest(at_revision(BASE, f"localization/reviews/{item_id}.json")))
                self.assertEqual(row["after_sha256"], body_sha)
                self.assertEqual(row["review_sha256"], digest((ROOT / f"localization/reviews/{item_id}.json").read_bytes()))
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(current["body"], body)
                self.assertEqual((current["reviewed_at"], current["review_due_at"]), (DATE, DUE))
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(review["prior_review_sha256"], row["prior_review_sha256"])
                self.assertEqual(entry["sources"], current["source_ids"])
                self.assertEqual(entry["verified_at"], DATE)
                self.assertEqual(row["source_ids"], current["source_ids"])
                self.assertEqual(review["source_ids"], current["source_ids"])
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertEqual(review["unresolved_questions"], row["unresolved_questions"])
                urls = {self.sources[sid]["url"] for sid in current["source_ids"]}
                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                review_urls = {check["url"] for check in row["source_checks"]}
                self.assertEqual(body_urls, urls)
                self.assertEqual(review_urls, urls)
                self.assertEqual(
                    {check["source_id"] for check in row["source_checks"]},
                    set(current["source_ids"]),
                )
                self.assertNotRegex(body, r"(?:本批|本次再審|AI來源實質再審|專業審閱仍待取得|\bPR\s*#|CI\s*(?:成功|通過))")
                validate_recheck_history(ROOT, row, current)
                for retired in row["retired_sources"]:
                    old = baseline_sources[retired["id"]]
                    self.assertEqual(self.sources[retired["id"]], old)
                    self.assertEqual(
                        retired["prior_source_sha256"],
                        digest(json.dumps(old, ensure_ascii=False, sort_keys=True).encode()),
                    )
        for sid, source in baseline_sources.items():
            self.assertEqual(self.sources[sid], source)

    def test_scope_and_frequency_language_do_not_turn_counts_into_rates(self):
        adult = self.items["TW-13-026"]["body"]
        for phrase in ("W79）死亡138人", "W80）死亡107人", "兒少窒息事故24件", "食物哽塞21件", "受傷者年齡分組為未滿2歲12人", "不能當成全國件數", "個人機率"):
            self.assertIn(phrase, adult)
        infant = self.items["TW-13-043"]["body"]
        self.assertIn("2026年11月12日更新", infant)
        self.assertIn("兩指", infant)
        self.assertIn("掌根", infant)
        self.assertIn("無法分出嬰兒", infant)
        stats = self.batch_items["TW-13-026"]["statistics_assessed"]
        self.assertEqual([row["value"] for row in stats], [138, 107, 24])
        local = next(row for row in stats if row["source_id"] == "ch13_choke_ntpc_114_20261124")
        self.assertEqual((local["value"], local["unit"], local["numerator"]), (24, "行政通報事故件數（件）", 24))
        self.assertEqual(local["related_injury_counts"], {"unit": "受傷人數（人）", "under_2": 12, "age_2_to_under_6": 6, "age_6_to_under_12": 6, "age_12_to_under_18": 0, "deaths": 0})
        self.assertIn("受傷人數", local["limitations"])
        for row in stats:
            self.assertIsNone(row["denominator"])
            for field in ("unit", "period", "scope", "population", "numerator", "denominator_definition", "event_definition", "data_type", "source_id", "accessed_at", "limitations"):
                self.assertTrue(row.get(field), field)
            self.assertRegex(row["limitations"], r"分母|率")

    def test_pediatric_resuscitation_and_battery_advice_are_qualified(self):
        cpr = self.items["TW-13-044"]["body"]
        self.assertIn("包含吹氣的CPR", cpr)
        self.assertIn("單人", cpr)
        self.assertIn("30次按壓、2次吹氣", cpr)
        self.assertIn("兩名受訓施救者採15:2", cpr)
        self.assertIn("仍比完全不急救好", cpr)
        battery = self.items["TW-13-045"]["body"]
        for phrase in ("年滿一歲", "未超過12小時", "不能為了準備蜂蜜而延誤出發", "不是台灣通用標準", "依X光位置、吞入時間與症狀決定"):
            self.assertIn(phrase, battery)
        self.assertNotIn("tsem.azurewebsites.net", battery)
        self.assertIn("www.sem.org.tw", battery)

    def test_source_counts_and_current_coverage_are_consistent(self):
        baseline_runtime = json.loads(at_revision(BASE, "localization/tw-edition/runtime.json"))
        baseline_source_ids = {row["id"] for row in baseline_runtime["sources"]}
        current_source_ids = set(self.sources)
        self.assertEqual(self.batch["counts_before"]["runtime_sources"], len(baseline_source_ids))
        self.assertEqual(
            self.batch["counts_after"]["runtime_sources"],
            len(baseline_source_ids) + len(NEW_SOURCE_IDS),
        )
        self.assertTrue(NEW_SOURCE_IDS.issubset(current_source_ids - baseline_source_ids))
        self.assertGreaterEqual(len(current_source_ids), self.batch["counts_after"]["runtime_sources"])
        source_rows = {row[0]: row for row in self.bundle["sources"]}
        for sid in NEW_SOURCE_IDS:
            source = self.sources[sid]
            self.assertEqual(source_rows[sid], [source["id"], source["title"], source["url"], source["supports"]])
            self.assertEqual(source["accessed_at"], DATE)
        self.assertEqual(self.batch["counts_after"]["core_reviewed_entries"], self.batch["counts_before"]["core_reviewed_entries"])
        self.assertEqual(self.batch["counts_after"]["substantive_rechecks"], self.batch["counts_before"]["substantive_rechecks"] + 4)


if __name__ == "__main__":
    unittest.main()
