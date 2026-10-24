"""第19章職安與職災五篇歷史再審：保留真實前稿與來源對應。"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retroactive_audit as audit
from body_renderer import body_blocks
from review_contract import ROOT

BASE = "2174e94843e4b034b18ebe851dbe9663b2ca6342"
IDS = ("TW-19-009", "TW-19-010", "TW-19-011", "TW-19-012", "TW-19-016")


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class WorkplaceSafetyRecheckTests(unittest.TestCase):
    def test_each_record_hashes_the_actual_base_and_current_article(self):
        old_runtime = json.loads(subprocess.check_output(
            ["git", "show", BASE + ":localization/tw-edition/runtime.json"],
            cwd=ROOT,
        ))
        current_runtime = read("localization/tw-edition/runtime.json")
        manifest = read("localization/manifest.json")
        register = read("localization/retroactive-review-register-20261019.json")
        old_items = {item["id"]: item for item in old_runtime["items"]}
        current_items = {item["id"]: item for item in current_runtime["items"]}
        records = {row["id"]: row for row in register["substantive_rechecks"]}
        entries = {entry["id"]: entry for entry in manifest["entries"]}
        sources = {source["id"]: source for source in current_runtime["sources"]}

        for item_id in IDS:
            with self.subTest(item_id=item_id):
                old = old_items[item_id]
                current = current_items[item_id]
                record = records[item_id]
                review = read(f"localization/reviews/{item_id}.json")
                before = hashlib.sha256(old["body"].encode("utf-8")).hexdigest()
                after = hashlib.sha256(current["body"].encode("utf-8")).hexdigest()
                markdown = (ROOT / entries[item_id]["target_path"]).read_bytes()
                self.assertNotEqual(before, after)
                self.assertEqual(record["prior_revision"], BASE)
                self.assertEqual(record["before_sha256"], before)
                self.assertEqual(record["after_sha256"], after)
                self.assertEqual(markdown.decode("utf-8"), current["body"])
                self.assertEqual(review["target_path"], entries[item_id]["target_path"])
                self.assertEqual(review["target_sha256"], hashlib.sha256(markdown).hexdigest())
                self.assertIn("AI", review["reviewer"])
                self.assertIn("非獨立", review["reviewer"])
                self.assertEqual(entries[item_id]["sources"], current["source_ids"])
                self.assertEqual(
                    {sources[source_id]["url"] for source_id in current["source_ids"]},
                    {check["url"] for check in review["source_checks"]},
                )
                audit.validate_recheck_history(ROOT, record, current)

    def test_emergency_guidance_precedes_statistics_and_limits_are_explicit(self):
        runtime = {item["id"]: item for item in read("localization/tw-edition/runtime.json")["items"]}
        safety = runtime["TW-19-010"]["body"]
        self.assertLess(safety.index("撥119"), safety.index("重大職災死亡109人"))
        for phrase in ("營造業58人", "墜落占62%", "沒有工作者人數或工作時數分母", "不能當個人事故發生率", "不要下去救人"):
            self.assertIn(phrase, safety)
        for item_id in IDS:
            with self.subTest(item_id=item_id):
                self.assertEqual(sum(block["tag"] == "h3" for block in body_blocks(runtime[item_id])), 5)
        health_exam = runtime["TW-19-009"]["body"]
        self.assertIn("每年或在變更作業時安排特殊健康檢查", health_exam)

    def test_bullying_forms_and_deadlines_follow_employer_size(self):
        runtime = {item["id"]: item for item in read("localization/tw-edition/runtime.json")["items"]}
        body = runtime["TW-19-016"]["body"]
        for phrase in (
            "書面申訴及前述紀錄均須申訴人簽名或蓋章",
            "有法定代理人或委任代理人時，也須列代理人姓名、住居所及聯絡電話",
            "申訴書須列明申訴人姓名、性別、出生年月日、身分證明文件字號",
            "有法定代理人者，也須列其姓名、性別、出生年月日、身分證明文件字號、職業、住所或居所及聯絡電話",
            "有委任代理人者，須列其姓名、身分證明文件字號、住所或居所及聯絡電話，並附委任書",
            "100人以上雇主應自受理申訴之日起15個工作日內組成調查小組",
            "小組成立翌日起2個月完成調查，必要時延長1個月",
            "處理單位應在調查報告完成後1個月內決定",
            "30至99人雇主應自收到申訴翌日起4個月內作成決定",
            "未滿30人則為3個月、必要時延長1個月",
            "資料不全時依通知期限補正",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)


if __name__ == "__main__":
    unittest.main()
