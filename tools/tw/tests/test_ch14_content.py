"""第14章實質正文、來源與預設閱讀／匯出一致性。"""
import hashlib
import html
import json
from collections import Counter
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retroactive_audit import assert_preserved_or_rechecked
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

    def test_historical_sources_and_rechecks_registered(self):
        data=validate_runtime();sources={s['id']:s for s in data['sources']}
        batch=json.loads((ROOT/'localization/tw-edition/ch14-reviewed.json').read_text())
        self.assertEqual(len(batch['sources']),14);self.assertEqual({e['id'] for e in batch['entries']},IDS)
        registry=json.loads((ROOT/'localization/tw-edition/sources/ch14.json').read_text())
        historical_ids={s['id'] for s in batch['sources']}
        recheck=json.loads((ROOT/'localization/ch14-account-recovery-fraud-recheck-20261026.json').read_text())
        recheck_ids={s['id'] for s in recheck['sources_added']}
        registry_ids={r[0] for r in registry['sources']}
        self.assertTrue(historical_ids.issubset(registry_ids))
        self.assertEqual(registry_ids,historical_ids|recheck_ids)
        for item in data['items']:
            if item['id'] in IDS:
                for key in item['source_ids']:self.assertIn(key,sources)

    def test_supplemental_medical_items_not_rewritten(self):
        old=json.loads(subprocess.check_output(['git','show',BASE+':localization/tw-edition/runtime.json'],cwd=ROOT,text=True))
        new=validate_runtime()
        previous_nav={e['id']:e for e in old['items']}
        current_nav={e['id']:e for e in new['items'] if e['id'].startswith('TW-NAV-')}
        self.assertTrue(set(previous_nav).issubset(current_nav))
        for key, previous in previous_nav.items(): assert_preserved_or_rechecked(self,previous,current_nav[key])
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

    def test_bulleted_source_links_render_as_readable_links(self):
        url='https://www.nhi.gov.tw/ch/np-2926-1.html'
        entry={
            'id':'TW-14-001',
            'title':'測試',
            'target_path':'locales/zh-TW/example.md',
            'body':f'# 測試\n\n<!-- TW-ID: TW-14-001 -->\n\n## 參考資料\n\n- [健保署：特約院所查詢]({url})',
        }
        expected=[{'tag':'h3','text':'參考資料'},{'tag':'p','text':'健保署：特約院所查詢','url':url}]
        self.assertEqual(body_blocks(entry),expected)
        self.assertIn(f'<a href="{url}">健保署：特約院所查詢</a>',body_html(entry))
        script="const fs=require('fs');const {bodyBlocks}=require('./assets/tw-runtime.js');console.log(JSON.stringify(bodyBlocks(JSON.parse(fs.readFileSync(0,'utf8')))));"
        actual=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(entry),text=True,cwd=ROOT))
        self.assertEqual(actual,expected)

    def test_consecutive_source_links_and_link_explanations_render_as_readable_blocks(self):
        first='https://www.nhi.gov.tw/ch/np-2926-1.html'
        second='https://1966.gov.tw/LTC/cp-6440-82812-207.html'
        entry={
            'id':'TW-17-013',
            'title':'測試',
            'target_path':'locales/zh-TW/example.md',
            'body':f'# 測試\n\n<!-- TW-ID: TW-17-013 -->\n\n## 參考資料\n\n- [健保署：院所查詢]({first})\n- [衛福部1966：長照資格]({second})：新增全年齡失智且失能者，自2026年1月1日起施行。',
        }
        expected=[
            {'tag':'h3','text':'參考資料'},
            {'tag':'p','text':'健保署：院所查詢','url':first},
            {'tag':'p','text':'衛福部1966：長照資格','url':second,'suffix':'：新增全年齡失智且失能者，自2026年1月1日起施行。'},
        ]
        blocks=body_blocks(entry)
        self.assertEqual(blocks,expected)
        rendered=body_html(entry)
        self.assertIn(f'<a href="{first}">健保署：院所查詢</a>',rendered)
        self.assertIn(f'<a href="{second}">衛福部1966：長照資格</a>：新增全年齡失智且失能者，自2026年1月1日起施行。',rendered)
        script="const fs=require('fs');const {bodyBlocks}=require('./assets/tw-runtime.js');console.log(JSON.stringify(bodyBlocks(JSON.parse(fs.readFileSync(0,'utf8')))));"
        actual=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(entry),text=True,cwd=ROOT))
        self.assertEqual(actual,expected)

    def test_adjacent_source_links_on_one_line_remain_separate(self):
        first='https://mojlaw.moj.gov.tw/LawContent.aspx?LSID=FL001351&TypeSort=2&lawNumber=1186'
        second='https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=B0000001'
        entry={
            'id':'TW-17-002',
            'title':'測試',
            'target_path':'locales/zh-TW/example.md',
            'body':f'# 測試\n\n<!-- TW-ID: TW-17-002 -->\n\n## 參考資料\n\n- [法務部：遺囑條文]({first})及[民法全條文]({second})：相關條文適用仍須看個案。',
        }
        expected=[{
            'tag':'h3','text':'參考資料'
        },{
            'tag':'p',
            'text':'法務部：遺囑條文及民法全條文：相關條文適用仍須看個案。',
            'segments':[
                {'text':'法務部：遺囑條文','url':first},
                {'text':'及'},
                {'text':'民法全條文','url':second},
                {'text':'：相關條文適用仍須看個案。'},
            ],
        }]
        blocks=body_blocks(entry)
        self.assertEqual(blocks,expected)
        rendered=body_html(entry)
        self.assertIn(f'<a href="{html.escape(first, quote=True)}">法務部：遺囑條文</a>及',rendered)
        self.assertIn(f'<a href="{html.escape(second, quote=True)}">民法全條文</a>：相關條文適用仍須看個案。',rendered)
        script="const fs=require('fs');const {bodyBlocks}=require('./assets/tw-runtime.js');console.log(JSON.stringify(bodyBlocks(JSON.parse(fs.readFileSync(0,'utf8')))));"
        actual=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(entry),text=True,cwd=ROOT))
        self.assertEqual(actual,expected)

    def test_existing_adjacent_sources_keep_registered_urls(self):
        runtime=validate_runtime()
        items={item['id']:item for item in runtime['items']}
        sources={source['id']:source for source in runtime['sources']}
        for item_id in ('TW-17-002','TW-01-040','TW-01-047'):
            with self.subTest(item_id=item_id):
                urls=[]
                for block in body_blocks(items[item_id]):
                    if block.get('segments'):
                        urls.extend(segment['url'] for segment in block['segments'] if segment.get('url'))
                    elif block.get('url'):
                        urls.append(block['url'])
                expected=[sources[source_id]['url'] for source_id in items[item_id]['source_ids']]
                normalize=lambda url: url.replace('://www.', '://', 1)
                self.assertEqual(Counter(map(normalize,urls)),Counter(map(normalize,expected)))

    def test_reader_markdown_links_are_readable_and_resolve_in_this_edition(self):
        items={item['id']:item for item in validate_runtime()['items']}
        known_ids=set(items)
        for item in items.values():
            for block in body_blocks(item):
                text_parts=[block.get('text','')]
                text_parts.extend(segment.get('text','') for segment in block.get('segments',[]))
                self.assertFalse(any('](' in text for text in text_parts),item['id'])
                hrefs=[block['href']] if block.get('href') else []
                hrefs.extend(segment['href'] for segment in block.get('segments',[]) if segment.get('href'))
                self.assertTrue(all(href.startswith('#TW-') and href[1:] in known_ids for href in hrefs),item['id'])
        self.assertIn('<a href="#TW-16-002">第16章慢箋與長療程指引（TW-16-002）</a>',body_html(items['TW-24-004']))

    def test_absolute_paths_are_not_rewritten_as_article_references(self):
        entry={
            'id':'TW-13-038','title':'測試','target_path':'locales/zh-TW/book/ch13/TW-13-038.md',
            'body':'# 測試\n\n<!-- TW-ID: TW-13-038 -->\n\n絕對路徑 [一](/outside/TW-13-038.md)、網域路徑 [二](//example.test/TW-13-038.md)、相對路徑 [三](TW-13-042.md)。',
        }
        blocks=body_blocks(entry)
        self.assertEqual(blocks[0]['text'],'絕對路徑 一、網域路徑 二、相對路徑 三。')
        self.assertEqual([segment.get('href') for segment in blocks[0]['segments'] if 'href' in segment],['#TW-13-042'])
        rendered=body_html(entry)
        self.assertNotIn('href="/outside/',rendered);self.assertNotIn('href="//example.test/',rendered)
        self.assertIn('href="#TW-13-042"',rendered)
        script="const fs=require('fs');const {bodyBlocks}=require('./assets/tw-runtime.js');console.log(JSON.stringify(bodyBlocks(JSON.parse(fs.readFileSync(0,'utf8')))));"
        actual=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(entry),text=True,cwd=ROOT))
        self.assertEqual(actual,blocks)

    def test_renderer_does_not_execute_raw_html(self):
        entry={'id':'TW-14-001','title':'測試','target_path':'locales/zh-TW/example.md','body':'# 測試\n\n<!-- TW-ID: TW-14-001 -->\n\n## 小標題\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1))'}
        html=body_html(entry)
        self.assertNotIn('<script>',html);self.assertNotIn('href="javascript:',html)
        self.assertIn('&lt;script&gt;',html);self.assertIn('<h3>小標題</h3>',html)

    def test_sensitive_localization_qualifications_are_present(self):
        items={e['id']:e for e in validate_runtime()['items']}
        self.assertIn('不試猜',items['TW-14-003']['body']);self.assertNotIn('1234',items['TW-14-003']['body'])
        self.assertIn('30',items['TW-14-005']['body']);self.assertIn('60',items['TW-14-005']['body'])
        self.assertIn('尚未生效',items['TW-14-007']['body']);self.assertIn('未生效',items['TW-14-008']['body'])
        self.assertIn('2026-01-14',items['TW-14-010']['body'])
        self.assertIn('第19條規範政府使用',items['TW-14-010']['body'])
        self.assertIn('不等於私人使用者一律被禁止',items['TW-14-010']['body'])
        self.assertIn('B6',items['TW-14-010']['body'])
        self.assertIn('7天',items['TW-14-012']['body'])

if __name__=='__main__':unittest.main()
