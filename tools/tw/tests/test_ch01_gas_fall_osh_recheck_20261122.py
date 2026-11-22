"""2026-11-22 家用瓦斯、高處墜落及職安導航歷史實質再審契約。"""
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/tw"))
import retroactive_audit as audit
from ci_language_policy import audit_drafts
from source_bundle_test_support import source_bundle_ids_added_since

BASE = "91c74820f6e0230b0b527d4ef11b27b4a180ef59"
DATE = "2026-11-22"
DUE = "2027-02-22"
REGISTER = "localization/retroactive-review-register-20261019.json"
BUNDLE = "localization/tw-edition/sources/ch01-gas-fall-osh-recheck-20261122.json"
EVIDENCE = "localization/ch01-gas-fall-osh-recheck-20261122.json"
IDS = ("TW-01-004", "TW-01-034", "TW-NAV-011")
PATHS = {
    "TW-01-004": "locales/zh-TW/book/ch01/TW-01-004.md",
    "TW-01-034": "locales/zh-TW/book/ch01/TW-01-034.md",
    "TW-NAV-011": "locales/zh-TW/guides/職業安全與健康.md",
}
NEW_SOURCE_IDS = {
    "ch01_nfa_co_latest_20261120",
    "ch01_nfa_gas_stove_safety_20261122",
    "ch01_bsmi_plastic_hose_use_20260309",
    "ch01_bsmi_plastic_hose_marking_2024",
    "ch01_tpe_gas_leak_20261112",
    "ch01_tainan_fire_gas_leak_response_20261122",
    "ch01_osha_fall_2026q3_pdf",
    "ch01_fall_icu_south_xinjiang_2025",
    "ch01_taiwan_trauma_rtw_2025",
    "ch01_germany_trauma_rtw_2020",
    "ch01_bli_rtw_service_2025",
    "nav11_confined_osha_current_20261122",
    "nav11_osh_bullying_local_complaint_20260623",
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def git_bytes(revision, path):
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True
    )
    return result.stdout if result.returncode == 0 else None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Ch01GasFallOshRecheck20261122Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = read("localization/tw-edition/runtime.json")
        cls.items = {row["id"]: row for row in cls.runtime["items"]}
        cls.sources = {row["id"]: row for row in cls.runtime["sources"]}
        cls.manifest = {
            row["id"]: row for row in read("localization/manifest.json")["entries"]
        }
        cls.reviews = {key: read(f"localization/reviews/{key}.json") for key in IDS}
        cls.register = read(REGISTER)
        cls.rows = cls.register["substantive_rechecks"]
        cls.batch_rows = {
            key: next(
                row for row in reversed(cls.rows)
                if row["id"] == key and row["prior_revision"] == BASE
            )
            for key in IDS
        }
        cls.coverage = read("localization/tw-edition/coverage.json")
        cls.evidence = read(EVIDENCE)
        cls.bundle = read(BUNDLE)

    def test_append_only_history_sources_and_hashes(self):
        baseline_register = json.loads(git_bytes(BASE, REGISTER))
        baseline_runtime = json.loads(
            git_bytes(BASE, "localization/tw-edition/runtime.json")
        )
        baseline_manifest = json.loads(
            git_bytes(BASE, "localization/manifest.json")
        )
        baseline_rows = baseline_register["substantive_rechecks"]
        self.assertEqual(self.rows[:len(baseline_rows)], baseline_rows)
        baseline_items = {row["id"]: row for row in baseline_runtime["items"]}
        baseline_sources = {row["id"]: row for row in baseline_runtime["sources"]}
        baseline_entries = {row["id"]: row for row in baseline_manifest["entries"]}

        for key in IDS:
            with self.subTest(id=key):
                row = self.batch_rows[key]
                review = self.reviews[key]
                old = baseline_items[key]
                item = self.items[key]
                raw = (ROOT / PATHS[key]).read_bytes()
                prior_review = git_bytes(BASE, f"localization/reviews/{key}.json")

                self.assertEqual(row["before_sha256"], digest(old["body"].encode()))
                self.assertEqual(row["previous_body"], old["body"])
                self.assertEqual(row["prior_review_sha256"], digest(prior_review))
                self.assertEqual(row["after_sha256"], digest(raw))
                self.assertEqual(row["review_sha256"], digest(
                    (ROOT / f"localization/reviews/{key}.json").read_bytes()
                ))
                self.assertEqual(row["status"], "ai_source_rechecked_professional_pending")
                self.assertEqual((item["reviewed_at"], item["review_due_at"]), (DATE, DUE))
                self.assertEqual(item["body"].encode(), raw)
                self.assertEqual(review["target_sha256"], digest(raw))
                self.assertEqual(review["source_reviewed_sha256"], digest(raw))
                self.assertEqual(review["prior_review_sha256"], digest(prior_review))
                self.assertEqual(review["source_checks"], row["source_checks"])
                self.assertEqual(review["statistics_assessed"], row["statistics_assessed"])
                self.assertEqual(review["legal_temporal_checks"], row.get("legal_temporal_checks", []))
                self.assertEqual(review["limits"], row["limits"])
                self.assertEqual(item["limits"], " ".join(review["limits"]))
                self.assertNotIn("AI輔助", item["limits"])
                self.assertEqual(review["source_ids"], item["source_ids"])
                self.assertEqual(review["source_ids"], self.manifest.get(key, {}).get("sources", item["source_ids"]))
                self.assertEqual(review["professional_review"]["required"], True)
                self.assertEqual(review["professional_review"]["obtained"], False)
                self.assertTrue(review["unresolved_questions"])
                self.assertEqual(row["source_bundle_path"], BUNDLE)
                self.assertEqual(row["source_bundle_sha256"], digest((ROOT / BUNDLE).read_bytes()))

                body_urls = {
                    url.rstrip(".,;，。；")
                    for url in re.findall(r"https://[^\s)>]+", raw.decode("utf-8"))
                }
                source_urls = {self.sources[sid]["url"] for sid in item["source_ids"]}
                review_urls = {check["url"] for check in review["source_checks"]}
                self.assertEqual(body_urls, source_urls)
                self.assertEqual(review_urls, source_urls)
                self.assertEqual(
                    {check["source_id"] for check in review["source_checks"]},
                    set(item["source_ids"]),
                )
                for check in review["source_checks"]:
                    self.assertTrue(check["supporting_passage"])
                    self.assertLessEqual(check["accessed_at"], DATE)
                    self.assertTrue(check["retrieval_method"])
                audit.validate_recheck_history(ROOT, row, item)

                if key != "TW-NAV-011":
                    self.assertEqual(self.manifest[key]["verified_at"], DATE)
                    self.assertEqual(
                        self.manifest[key]["sources"], item["source_ids"]
                    )

        self.assertEqual(
            self.runtime["sources"][:len(baseline_runtime["sources"])],
            baseline_runtime["sources"],
        )
        added = set(self.sources) - set(baseline_sources)
        self.assertTrue(NEW_SOURCE_IDS <= added)
        self.assertEqual(
            {source[0] for source in self.bundle["sources"]}, NEW_SOURCE_IDS
        )
        self.assertTrue(NEW_SOURCE_IDS <= source_bundle_ids_added_since(ROOT, BASE))

    def test_taiwan_context_and_frequency_limits_are_specific(self):
        gas = self.items["TW-01-004"]["body"]
        self.assertIn("2026年截至11月19日", gas)
        self.assertIn("12件事故、死亡1人、送醫48人", gas)
        self.assertIn("10件與屋外型熱水器設於通風不足處有關", gas)
        self.assertIn("沒有找到可信的全國家戶分母", gas)
        self.assertIn("不能換算個人機率、致死率或趨勢", gas)
        self.assertIn("不能把塑膠軟管的標示要求或期限套用到橡膠管、金屬可撓管", gas)
        self.assertIn("不是適用所有爐具的法定到期日", gas)
        self.assertNotIn("f1729737563517.pdf", gas)
        self.assertIn("f1727772370076.pdf", gas)
        gas_stats = self.reviews["TW-01-004"]["statistics_assessed"]
        self.assertEqual([row["period"] for row in gas_stats], [
            "2024-01-01至2024-12-31",
            "2025-01-01至2025-12-31",
            "2026-01-01至2026-11-19",
        ])
        self.assertTrue(all(row["denominator"] is None for row in gas_stats))

        fall = self.items["TW-01-034"]["body"]
        self.assertIn("臺灣全民健保資料庫", fall)
        self.assertIn("4,741人（79.5%）", fall)
        self.assertIn("不是高處墜落專屬統計", fall)
        self.assertIn("不能預測目前個別傷者", fall)
        self.assertIn("中國新疆南部一所創傷加護病房", fall)
        self.assertIn("不是台灣所有墜落者的發生率", fall)
        rtw = next(
            stat for stat in self.reviews["TW-01-034"]["statistics_assessed"]
            if stat["indicator"] == "重大創傷後重返工作"
        )
        self.assertEqual(rtw["numerator"], {"returned_to_work": 4741, "not_returned_to_work": 1224})
        self.assertEqual(rtw["denominator"], 5965)
        germany = next(
            stat for stat in self.reviews["TW-01-034"]["statistics_assessed"]
            if stat["indicator"] == "重度多重創傷患者重返工作"
        )
        self.assertEqual(germany["numerator"], {"reported_proportion_percent": 58})
        self.assertEqual(germany["denominator"], 84)
        self.assertIn("未載明精確長度", germany["period"])

    def test_current_workplace_bullying_route_and_publication_state(self):
        guide = self.items["TW-NAV-011"]["body"]
        self.assertIn("只有被申訴人屬法定「最高負責人」時", guide)
        self.assertIn("該類申訴須以書面提出", guide)
        self.assertIn("2026-06-23發布、2026-07-01施行", guide)
        self.assertIn("行為終了後未逾3年", guide)
        self.assertIn("離職日起1年內提出", guide)
        temporal = self.reviews["TW-NAV-011"]["legal_temporal_checks"]
        provisions = {
            (check["law"], amendment["promulgated_at"], amendment["effective_at"])
            for group in temporal for check in group["checks"]
            for amendment in check["relevant_provision_amendments"]
        }
        self.assertIn(("職業安全衛生法", "2025-12-19", "2026-07-01"), provisions)
        self.assertIn(("地方主管機關受理最高負責人職場霸凌事件申訴處理辦法", "2026-06-23", "2026-07-01"), provisions)

        for key in IDS:
            with self.subTest(id=key):
                body = self.items[key]["body"]
                self.assertNotIn("本批", body)
                self.assertNotIn("AI審查", body)
                self.assertNotIn("fork 維護", body)
                self.assertEqual(self.reviews[key]["professional_review"]["status"], "pending")
        self.assertFalse(self.coverage["publication_ready"])
        self.assertEqual(self.coverage, audit_drafts())
        self.assertEqual(self.evidence["counts_before"]["substantive_rechecks"] + 3,
                         self.evidence["counts_after"]["substantive_rechecks"])
        self.assertEqual(self.evidence["counts_before"]["runtime_sources"] + len(NEW_SOURCE_IDS),
                         self.evidence["counts_after"]["runtime_sources"])
        self.assertLessEqual(self.evidence["counts_after"]["json_files_checked"], self.coverage["json_files_checked"])
        self.assertLessEqual(self.evidence["counts_after"]["source_registry"], self.coverage["registry_sources"])


if __name__ == "__main__":
    unittest.main()
