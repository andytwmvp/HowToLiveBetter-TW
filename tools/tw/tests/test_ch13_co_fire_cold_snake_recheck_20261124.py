"""第13章一氧化碳、火場、失溫與蛇咬再審的來源和歷史契約。"""
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

BASE = "0869a12e6566f65cbb13736152ca57581d309c6b"
DATE = "2026-11-24"
DUE = "2027-02-24"
IDS = ("TW-13-019", "TW-13-024", "TW-13-028", "TW-13-029")
BATCH_PATH = "localization/ch13-co-fire-cold-snake-recheck-20261124.json"
BUNDLE_PATH = "localization/tw-edition/sources/ch13-co-fire-cold-snake-recheck-20261124.json"
REGISTER_PATH = "localization/retroactive-review-register-20261019.json"
NEW_SOURCE_IDS = {"ch13_cold_nfa_112"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_at(revision, path, *, json_value=True):
    raw = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)
    return json.loads(raw) if json_value else raw


class COFireColdSnakeRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = validate_runtime()
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {row["id"]: row for row in read("localization/manifest.json")["entries"]}
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in IDS}
        cls.register = read(REGISTER_PATH)
        cls.batch = read(BATCH_PATH)
        cls.batch_items = {row["id"]: row for row in cls.batch["items"]}
        cls.bundle = read(BUNDLE_PATH)

    def test_append_only_history_hashes_and_sources_match(self):
        baseline_runtime = read_at(BASE, "localization/tw-edition/runtime.json")
        baseline_manifest = {
            row["id"]: row
            for row in read_at(BASE, "localization/manifest.json")["entries"]
        }
        baseline_register = read_at(BASE, REGISTER_PATH)["substantive_rechecks"]
        baseline_coverage = read_at(BASE, "localization/tw-edition/coverage.json")
        coverage = read("localization/tw-edition/coverage.json")
        baseline_items = {row["id"]: row for row in baseline_runtime["items"]}
        baseline_sources = {row["id"]: row for row in baseline_runtime["sources"]}

        self.assertEqual(self.batch["baseline_main_sha"], BASE)
        self.assertEqual((self.batch["reviewed_at"], self.batch["review_due_at"]), (DATE, DUE))
        self.assertEqual(set(self.batch_items), set(IDS))
        self.assertEqual(set(self.batch["new_source_ids"]), NEW_SOURCE_IDS)
        self.assertEqual(
            self.register["substantive_rechecks"][:len(baseline_register)],
            baseline_register,
        )
        self.assertEqual(self.bundle["baseline_main_sha"], BASE)
        self.assertEqual(self.bundle["checked_at"], DATE)
        self.assertEqual({row[0] for row in self.bundle["sources"]}, NEW_SOURCE_IDS)
        before = self.batch["counts_before"]
        after = self.batch["counts_after"]
        self.assertEqual(before["runtime_items"], len(baseline_runtime["items"]))
        self.assertEqual(before["runtime_sources"], len(baseline_runtime["sources"]))
        self.assertEqual(before["source_registry"], baseline_coverage["registry_sources"])
        self.assertEqual(before["coverage_json_files"], baseline_coverage["json_files_checked"])
        self.assertEqual(before["core_completed"], baseline_coverage["publication_completed_entries"])
        self.assertEqual(after["runtime_items"], before["runtime_items"])
        self.assertEqual(after["runtime_sources"], before["runtime_sources"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["source_registry"], before["source_registry"] + len(NEW_SOURCE_IDS))
        self.assertEqual(after["coverage_json_files"], before["coverage_json_files"] + 2)
        self.assertEqual(after["substantive_rechecks"], before["substantive_rechecks"] + len(IDS))
        # This historical batch predates later source registrations. Its
        # immutable count remains valid, while live coverage may have grown.
        self.assertGreaterEqual(coverage["registry_sources"], after["source_registry"])
        # Later batches add evidence JSON files; retain this batch's historical
        # count while allowing the current repository coverage to increase.
        self.assertGreaterEqual(coverage["json_files_checked"], after["coverage_json_files"])
        self.assertFalse(coverage["publication_ready"])
        self.assertFalse(self.batch["publication_ready"])
        self.assertTrue(self.batch["professional_review"]["required"])
        self.assertFalse(self.batch["professional_review"]["obtained"])
        self.assertEqual(self.batch["professional_review"]["status"], "pending")

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                row = self.batch_items[item_id]
                current = self.items[item_id]
                entry = self.manifest[item_id]
                review = self.reviews[item_id]
                body_path = entry["target_path"]
                body_bytes = (ROOT / body_path).read_bytes()
                body = body_bytes.decode("utf-8")
                body_sha = digest(body_bytes)
                histories = [
                    record for record in self.register["substantive_rechecks"]
                    if record["id"] == item_id and record["reviewed_at"] == DATE
                ]
                self.assertEqual(histories, [row])
                previous_body = read_at(BASE, body_path, json_value=False)
                self.assertEqual(row["previous_body"].encode("utf-8"), previous_body)
                self.assertEqual(row["before_sha256"], digest(previous_body))
                self.assertEqual(
                    row["prior_review_sha256"],
                    digest(read_at(BASE, f"localization/reviews/{item_id}.json", json_value=False)),
                )
                self.assertEqual(row["after_sha256"], body_sha)
                self.assertEqual(row["review_sha256"], digest((ROOT / f"localization/reviews/{item_id}.json").read_bytes()))
                self.assertEqual(row["source_bundle_sha256"], digest((ROOT / BUNDLE_PATH).read_bytes()))
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual(row["professional_review"]["status"], "pending")
                self.assertEqual(current["body"], body)
                self.assertEqual((current["reviewed_at"], current["review_due_at"]), (DATE, DUE))
                self.assertEqual(review["target_sha256"], body_sha)
                self.assertEqual(review["source_reviewed_sha256"], body_sha)
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(review["prior_review_sha256"], row["prior_review_sha256"])
                self.assertEqual(review["source_ids"], current["source_ids"])
                self.assertEqual(row["source_ids"], current["source_ids"])
                self.assertEqual(entry["sources"], current["source_ids"])
                self.assertEqual(entry["verified_at"], DATE)
                self.assertTrue(review["professional_review"]["required"])
                self.assertFalse(review["professional_review"]["obtained"])
                self.assertEqual(review["professional_review"]["status"], "pending")

                expected_urls = {self.sources[sid]["url"] for sid in current["source_ids"]}
                body_urls = set(re.findall(r"\]\((https?://[^)]+)\)", body))
                review_urls = {check["url"] for check in row["source_checks"]}
                self.assertEqual(body_urls, expected_urls)
                self.assertEqual(review_urls, expected_urls)
                self.assertEqual(
                    {check["source_id"] for check in row["source_checks"]},
                    set(current["source_ids"]),
                )
                self.assertNotRegex(body, r"(?:本批|本次再審|AI來源實質再審|專業審閱仍待取得|\bPR\s*#|CI\s*(?:成功|通過))")
                validate_recheck_history(ROOT, row, current)

        for source_id, old_source in baseline_sources.items():
            self.assertEqual(self.sources[source_id], old_source)

    def test_safety_actions_and_taiwan_call_routing_are_explicit(self):
        co = self.items["TW-13-019"]["body"]
        self.assertIn("先把自己與能自行移動的人帶到室外", co)
        self.assertIn("再立即撥119", co)
        self.assertIn("不要為了開窗、關設備、取物或查看警報來源而停留或折返", co)
        self.assertIn("不能為了關瓦斯、取物品或拉出昏迷者而冒險重返", co)

        fire = self.items["TW-13-024"]["body"]
        self.assertIn("沿仍安全的路線撤離", fire)
        self.assertIn("不延誤撤離下代為撥119", fire)
        self.assertIn("退到未起火、能關門的相對安全空間，關門後立即打119", fire)

        cold = self.items["TW-13-028"]["body"]
        self.assertIn("立即直撥119", cold)
        self.assertIn("112，依語音指示按9轉119", cold)
        self.assertIn("112需經語音轉接，可能較慢", cold)
        self.assertIn("完全無訊號時也不能保證接通", cold)

        snake = self.items["TW-13-029"]["body"]
        self.assertIn("不為辨識蛇而延誤求醫", snake)
        self.assertIn("不是即時庫存", snake)
        self.assertIn("不要為了查名單或找血清延誤就醫", snake)

    def test_statistics_keep_scope_denominators_and_data_limits(self):
        for item_id in IDS:
            rows = self.batch_items[item_id]["statistics_assessed"]
            if item_id == "TW-13-028":
                self.assertEqual(rows, [])
                self.assertIn("全國失溫病例數和暴露分母", self.batch_items[item_id]["frequency_assessment"])
                continue
            self.assertTrue(rows)
            for row in rows:
                for field in (
                    "unit", "period", "scope", "population", "numerator", "denominator_definition",
                    "event_definition", "data_type", "source_id", "accessed_at", "limitations",
                ):
                    self.assertTrue(row.get(field), (item_id, field))
                self.assertEqual(row["accessed_at"], DATE)
                self.assertIn(row["source_id"], self.items[item_id]["source_ids"])

        co = self.batch_items["TW-13-019"]["statistics_assessed"][0]
        self.assertIsNone(co["denominator"])
        self.assertIn("22件事故", co["value"])
        self.assertIn("5人死亡", co["value"])
        self.assertIn("59人送醫", co["value"])
        self.assertIn("不能換算個人發生率", co["limitations"])

        fire = self.batch_items["TW-13-024"]["statistics_assessed"][0]
        self.assertIsNone(fire["denominator"])
        self.assertIn("2021至2025年", fire["period"])
        self.assertIn("回覆403", fire["data_type"])
        self.assertIn("官方搜尋索引", fire["data_type"])

        snake = self.batch_items["TW-13-029"]["statistics_assessed"][0]
        self.assertEqual((snake["numerator"], snake["denominator"]), (9, 4893))
        self.assertIn("使用抗蛇毒血清", snake["denominator_definition"])
        self.assertIn("不能代表全部蛇咬者", snake["limitations"])


if __name__ == "__main__":
    unittest.main()
