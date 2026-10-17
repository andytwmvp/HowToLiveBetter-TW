"""臺灣在地內容治理、署名與機器人自願排除回歸。"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reuse_policy as policy


class ReusePolicyTests(unittest.TestCase):
    def test_current_project_policy(self):
        result = policy.audit()
        self.assertFalse(result["public_repo_geoblocked"])
        self.assertFalse(result["robots_enforced"])
        self.assertFalse(result["license_restricted"])
        self.assertGreater(result["core"], 0)
        self.assertGreater(result["navigation"], 0)

    def test_bots_are_advisory_not_global_denial(self):
        rules = policy.robot_groups(policy.read("robots.txt"))
        self.assertNotIn("/", rules["*"])
        self.assertIn("/book/", rules["*"])
        for bot in policy.BOTS:
            self.assertIn("/", rules[bot])

    def test_generic_total_denial_rejected(self):
        original = policy.read
        def fake(path, root=policy.ROOT):
            if path == "robots.txt":
                return "User-agent: *\\nDisallow: /\\n"
            return original(path, root)
        with patch.object(policy, "read", side_effect=fake):
            with self.assertRaises(ValueError):
                policy.audit()

    def test_original_credit_and_unresolved_template(self):
        raw = policy.read("ATTRIBUTION.md")
        policy.check_attribution(raw)
        for bad in (raw + " ${guidePath}", raw.replace("CC BY 4.0", "未知授權"),
                    raw.replace("MIT", "未知程式授權")):
            with self.assertRaises(ValueError):
                policy.check_attribution(bad)

    def test_public_source_and_no_data_poisoning(self):
        txt = policy.read(policy.POLICY_PATH)
        for term in ("公開的 GitHub 儲存庫", "非公開且具權限控管", "不得故意寫錯救護電話", "不套用中國制度"):
            self.assertIn(term, txt)


if __name__ == "__main__":
    unittest.main()
