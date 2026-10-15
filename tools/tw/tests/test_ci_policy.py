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
        for value in ('台灣與臺灣','雇主及勞雇關係','公布與發布法令','依法占有','核准與獲准','只有必要資料','不是只拿底薪','平台設定'):
            with self.subTest(value=value):
                self.assertEqual(policy.canonical(value),policy.canonical(text.normalized(value,[])))
    def test_simplified_is_rejected(self):
        for value in ('立即\u5371\u9669','\u5199清條件','工作\u65f6間','\u5f53作保證','修改\u5185容'):
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
