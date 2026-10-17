"""第14章實質正文、來源與預設閱讀／匯出一致性。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, publication_report, validate_entry, validate_runtime
from body_renderer import body_blocks, body_html

BASE='37d33f484ee85736170694754528f4392e8ee94d'
IDS={f'TW-14-{n:03}' for n in range(1,13)}

class ChapterContentTests(unittest.TestCase):
    def test_complete_core_chapter_with_evidence(self):
        data=validate_runtime();items={e['id']:e for e in data['items']}
        manifest=json.loads((ROOT/'localization/manifest.json').read_text())
        core=[e for e in manifest['entries'] if e['id'] in IDS]
        self.assertEqual(len(core),12)
        for entry in core:
            self.assertEqual(entry['status'],'verified');self.assertTrue(validate_entry(entry))
            raw=(ROOT/entry['target_path']).read_bytes();review=json.loads((ROOT/f"localization/reviews/{entry['id']}.json").read_text())
            self.assertEqual(raw.decode(),items[entry['id']]['body'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),review['target_sha256'])
            self.assertIn('AI',review['reviewer']);self.assertTrue(review['source_checks'])
            self.assertGreater(len(raw.decode()),500)
        report=publication_report();self.assertGreaterEqual(report['publication_completed_entries'],len(IDS))
        self.assertFalse(report['publication_ready']);self.assertEqual(report['publication_total_entries'],765)

    def test_all_fourteen_sources_registered(self):
        data=validate_runtime();sources={s['id']:s for s in data['sources']}
        batch=json.loads((ROOT/'localization/tw-edition/ch14-reviewed.json').read_text())
        self.assertEqual(len(batch['sources']),14);self.assertEqual({e['id'] for e in batch['entries']},IDS)
        registry=json.loads((ROOT/'localization/tw-edition/sources/ch14.json').read_text())
        self.assertEqual({r[0] for r in registry['sources']},{s['id'] for s in batch['sources']})
        for item in data['items']:
            if item['id'] in IDS:
                for key in item['source_ids']:self.assertIn(key,sources)

    def test_supplemental_medical_items_not_rewritten(self):
        old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
        new=validate_runtime()
        previous_nav={e['id']:e for e in old['items']}
        current_nav={e['id']:e for e in new['items'] if e['id'].startswith('TW-NAV-')}
        self.assertTrue(set(previous_nav).issubset(current_nav))
        for key, previous in previous_nav.items(): self.assertEqual(previous, current_nav[key])
        self.assertEqual(old['sources'],[s for s in new['sources'] if s['id'] in {source['id'] for source in old['sources']}])

    def test_core_metadata_preserves_upstream_provenance(self):
        old=json.loads(subprocess.check_output(['git','show',BASE+':localization/manifest.json'],cwd=ROOT,text=True))
        new=json.loads((ROOT/'localization/manifest.json').read_text())
        for before,after in zip(old['entries'],new['entries'],strict=True):
            for key in ('upstream_text_sha256','upstream_commit','upstream_path_uri','id','upstream_chapter','upstream_item','display_path','source_title_zh_tw'):
                self.assertEqual(before[key],after[key])

    def test_python_and_javascript_render_identical_blocks(self):
        data=validate_runtime()['items']
        script="const fs=require('fs');const {bodyBlocks}=require('./assets/tw-runtime.js');console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(bodyBlocks)));"
        result=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(data),text=True,cwd=ROOT))
        self.assertEqual(result,[body_blocks(e) for e in data])
        for item,blocks in zip(data,result,strict=True):
            if item['id'] in IDS:
                self.assertEqual(sum(b['tag']=='h3' for b in blocks),5)
                self.assertNotIn('TW-ID:',json.dumps(blocks))
                self.assertNotIn('## ',json.dumps(blocks))

    def test_renderer_does_not_execute_raw_html(self):
        entry={'id':'TW-14-001','title':'測試','target_path':'locales/zh-TW/example.md','body':'# 測試\n\n<!-- TW-ID: TW-14-001 -->\n\n## 小標題\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1))'}
        html=body_html(entry)
        self.assertNotIn('<script>',html);self.assertNotIn('href="javascript:',html)
        self.assertIn('&lt;script&gt;',html);self.assertIn('<h3>小標題</h3>',html)

    def test_sensitive_localization_qualifications_are_present(self):
        items={e['id']:e for e in validate_runtime()['items']}
        self.assertIn('不試猜',items['TW-14-003']['body']);self.assertNotIn('1234',items['TW-14-003']['body'])
        self.assertIn('30',items['TW-14-005']['body']);self.assertIn('60',items['TW-14-005']['body'])
        self.assertIn('尚未',items['TW-14-007']['body']);self.assertIn('未生效',items['TW-14-008']['body'])
        self.assertIn('特定公部門適用範圍',items['TW-14-010']['body'])
        self.assertIn('7天',items['TW-14-012']['body'])

if __name__=='__main__':unittest.main()
