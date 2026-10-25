"""CI 回歸：合法台灣寫法、簡體字、JSON、網址及圖片唯讀性。"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ci_language_policy as policy
import text_integrity as text
import assets_and_browser as assets

class PolicyTests(unittest.TestCase):
    def test_valid_taiwan_wording(self):
        for value in ('台灣與臺灣','雇主及勞雇關係','公布與發布法令','依法占有','核准與獲准','只有必要資料','不是只拿底薪','平台設定','不明扣款先通知銀行'):
            with self.subTest(value=value):
                self.assertEqual(policy.canonical(value),policy.canonical(text.normalized(value,[])))
    def test_official_taiwan_water_rescue_slogan_is_preserved(self):
        # 消防署「叫、叫、伸、拋、划」固定用語不應被機械式字形轉換誤判。
        examples = ('叫叫伸拋划', '叫、叫、伸、拋、划', '『划』', '，划是利用大型浮具')
        for value in examples:
            with self.subTest(value=value):
                self.assertEqual(policy.canonical(value), policy.canonical(text.normalized(value, [])))

    def test_official_term_exception_is_not_a_global_waiver(self):
        self.assertNotEqual(policy.canonical('任意划分任務'), policy.canonical('任意劃分任務'))
        self.assertNotEqual(policy.canonical('划出錯誤的路線'), policy.canonical('劃出錯誤的路線'))

    def test_generated_reference_excerpt_preserves_xianggan_context(self):
        # 生成對照表會截斷「不相干」的前文，保留的「干的人下手」仍是正確繁體用字。
        excerpt = '…干的人下手（第 13 條）'
        self.assertEqual(policy.canonical(excerpt), policy.canonical(text.normalized(excerpt, [])))
        self.assertNotEqual(policy.canonical('干活的人'), policy.canonical(text.normalized('干活的人', [])))

    def test_simplified_is_rejected(self):
        for value in ('立即\u5371\u9669','\u5199清條件','工作\u65f6間','\u5f53作保證','修改\u5185容','\u94f6\u884c扣款'):
            with self.subTest(value=value):
                self.assertNotEqual(policy.canonical(value),policy.canonical(text.normalized(value,[])))
    def test_urls_are_preserved(self):
        value='[來源](https://doi.org/10.1016/S0065-2601(06)38002-1)：\u8fd9\u4e2a\u9875\u9762'
        after=text.normalized(value,[])
        self.assertEqual(text.URL.findall(value),text.URL.findall(after))
        self.assertNotEqual(value,after)
    def test_bad_json_is_rejected(self):
        with patch.object(policy.base,'read',return_value='{"intro":"bad\ntext"}'):
            with self.assertRaises(ValueError):policy.load_json('broken.json')
    def test_duplicate_keys_are_rejected(self):
        with patch.object(policy.base,'read',return_value='{"id":1,"id":2}'):
            with self.assertRaises(ValueError):policy.load_json('duplicate.json')
    def test_inventory_is_not_rewritten(self):
        path=policy.base.ROOT/'localization/assets-inventory.json'
        before=path.read_bytes();assets.audit_assets(False)
        self.assertEqual(before,path.read_bytes())
    def test_stale_digest_is_rejected(self):
        original=assets.read
        def stale(path):
            data=original(path)
            if path=='localization/assets-inventory.json':
                obj=json.loads(data);obj['raster_and_vector_files'][0]['sha256']='0'*64
                return json.dumps(obj)
            return data
        with patch.object(assets,'read',side_effect=stale):
            with self.assertRaises(RuntimeError):assets.audit_assets(False)
    def test_drafts_are_not_publication(self):
        data=policy.audit_drafts()
        self.assertFalse(data['publication_ready'])
        self.assertEqual(data['unique_draft_entries']+data['entries_without_any_draft'],765)
if __name__=='__main__':unittest.main()
