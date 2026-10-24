"""臺灣健保跨縣市、遛狗跌倒及醫療防詐之歷史再審契約。"""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_contract import ROOT, publication_report, validate_runtime
from retroactive_audit import assert_preserved_or_rechecked, validate_recheck_history

BASE = '794d51344b914da70ea430cb68e172683f5ed412'
IDS = {'TW-16-002', 'TW-17-010', 'TW-24-003', 'TW-24-004', 'TW-24-011'}
BATCH = 'localization/medical-access-falls-20261025.json'


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


class MedicalAccessFallsRecheckTests(unittest.TestCase):
    def test_body_hash_review_history_and_manifest_sources_match(self):
        runtime = validate_runtime()
        items = {item['id']: item for item in runtime['items']}
        sources = {source['id']: source for source in runtime['sources']}
        rows = {
            row['id']: row
            for row in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']
        }
        manifest = {row['id']: row for row in load('localization/manifest.json')['entries']}
        for key in IDS:
            item = items[key]
            review = load(f'localization/reviews/{key}.json')
            register_row = rows[key]
            validate_recheck_history(ROOT, register_row, item)
            self.assertEqual((ROOT / item['target_path']).read_text(encoding='utf-8'), item['body'])
            self.assertEqual(review['target_sha256'], hashlib.sha256(item['body'].encode()).hexdigest())
            self.assertEqual(review['source_checks'], register_row['source_checks'])
            self.assertEqual(
                {check['url'] for check in review['source_checks']},
                {sources[source_id]['url'] for source_id in item['source_ids']},
            )
            self.assertEqual(manifest[key]['sources'], item['source_ids'])
            self.assertEqual(item['reviewed_at'], '2026-10-25')
            self.assertEqual(item['review_due_at'], '2027-01-31')
            self.assertEqual(register_row['status'], 'ai_source_rechecked_professional_pending')
            for check in review['source_checks']:
                self.assertGreaterEqual(len(check['supporting_passage']), 50)
                self.assertNotEqual(check['claim'], check['supporting_passage'])
                self.assertIn('非逐字', check['supporting_passage'])

    def test_previous_runtime_items_and_source_objects_are_preserved(self):
        previous = json.loads(
            subprocess.check_output(
                ['git', 'show', BASE + ':localization/tw-edition/runtime.json'], cwd=ROOT
            )
        )
        runtime = validate_runtime()
        items = {item['id']: item for item in runtime['items']}
        sources = {source['id']: source for source in runtime['sources']}
        self.assertEqual([item['id'] for item in previous['items']], [item['id'] for item in runtime['items']])
        for item in previous['items']:
            assert_preserved_or_rechecked(self, item, items[item['id']])
        for source in previous['sources']:
            self.assertEqual(source, sources[source['id']])

    def test_taiwan_frequency_evidence_keeps_population_and_denominator_limits(self):
        batch = load(BATCH)
        self.assertEqual(batch['new_core_ids'], [])
        self.assertEqual(set(batch['frequency_assessments']), IDS)
        stats = batch['statistics']
        hpa = [row for row in stats if row['source_id'] == 'ch17_hpa_falls_20261025']
        self.assertEqual({row['value'] for row in hpa}, {16.7, 8.3})
        for row in hpa:
            self.assertIsNone(row['numerator'])
            self.assertIsNone(row['denominator'])
            self.assertIn('摘要', row['limitations'])
            self.assertTrue('未列' in row['limitations'] or '未提供' in row['limitations'])
        mortality = next(row for row in stats if row['value'] == 24.4)
        self.assertEqual((mortality['numerator'], mortality['denominator']), (1632, 6678))
        self.assertIn('事故傷害死因死亡者', mortality['population'])
        taipei = [row for row in stats if row['source_id'] == 'ch17_taipei_pet_incidents_20261025']
        self.assertEqual({row['value'] for row in taipei}, {102, 41})
        for row in taipei:
            self.assertIsNone(row['denominator'])
            self.assertIn('分母', row['limitations'])
            self.assertTrue('不能' in row['limitations'] or '不可' in row['limitations'])
        body = next(item['body'] for item in validate_runtime()['items'] if item['id'] == 'TW-17-010')
        self.assertEqual(body.count('\n## '), 5)
        self.assertLess(body.index('119'), body.index('臺灣資料、成本與可期待的效益'))
        self.assertIn('跌倒骨折', body)
        self.assertIn('55日', body)
        self.assertIn('www.tcapo.gov.taipei', body)
        self.assertNotIn('原頁本輪載入逾時', body)
        review_method = load('localization/reviews/TW-17-010.json')['review_method']
        self.assertIn('直接讀取臺北市動保處2023-08-29官方頁面', review_method)
        self.assertNotIn('原頁本輪載入逾時', review_method)
        taipei_method = next(row['method'] for row in load(BATCH)['statistics'] if row['value'] == 41)
        self.assertIn('直接核讀臺北市動保處官方新聞稿', taipei_method)
        self.assertNotIn('索引可讀', taipei_method)

    def test_medical_guidance_retains_taiwan_specific_legal_boundaries(self):
        items = {item['id']: item['body'] for item in validate_runtime()['items']}
        for key in IDS:
            self.assertEqual(items[key].count('\n## '), 5)
        self.assertIn('第15條', items['TW-16-002'])
        self.assertIn('條文列出的特定情形', items['TW-16-002'])
        self.assertIn('第3條', items['TW-24-004'])
        self.assertIn('一般特約門診', items['TW-24-004'])
        self.assertIn('不能判定每一第三方服務都觸法', items['TW-24-003'])
        self.assertIn('簡訊驗證碼', items['TW-24-003'])
        self.assertIn('公立醫院依法任用、受俸的編制醫事人員', items['TW-24-011'])
        self.assertIn('約聘僱醫師不適用該規範本身', items['TW-24-011'])
        self.assertIn('不將所有事後感謝卡或小禮物都概括認定為違法', items['TW-24-011'])

    def test_added_sources_and_retired_references_keep_provenance(self):
        batch = load(BATCH)
        runtime = validate_runtime()
        source_map = {source['id']: source for source in runtime['sources']}
        added_ids = set(batch['new_source_ids'])
        self.assertEqual(len(added_ids), 11)
        self.assertTrue(added_ids.issubset(source_map))
        self.assertEqual(batch['sources_added'], 11)
        rows = {
            row['id']: row
            for row in load('localization/retroactive-review-register-20261019.json')['substantive_rechecks']
        }
        previous = json.loads(
            subprocess.check_output(
                ['git', 'show', BASE + ':localization/tw-edition/runtime.json'], cwd=ROOT
            )
        )
        old_sources = {source['id']: source for source in previous['sources']}
        for key, retired_ids in {
            'TW-16-002': {'ch16_nhi_rx', 'ch16_nhi_fam'},
            'TW-17-010': {'ch17_ltc'},
        }.items():
            item = next(item for item in runtime['items'] if item['id'] == key)
            self.assertTrue(retired_ids.isdisjoint(item['source_ids']))
            retired = {record['id']: record for record in rows[key]['retired_sources']}
            self.assertTrue(retired_ids.issubset(retired))
            for source_id in retired_ids:
                prior = old_sources[source_id]
                self.assertEqual(
                    retired[source_id]['prior_source_sha256'],
                    hashlib.sha256(json.dumps(prior, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                )

    def test_professional_review_and_publication_gate_remain_pending(self):
        batch = load(BATCH)
        self.assertEqual(batch['professional_review'], 'pending')
        self.assertFalse(publication_report()['publication_ready'])
        for key in IDS:
            review = load(f'localization/reviews/{key}.json')
            self.assertIn('ChatGPT', review['reviewer'])
            self.assertIn('非', review['reviewer'])

    def test_legal_article_versions_have_verified_effective_dates(self):
        rows = {row['law']: row for row in load(BATCH)['legal_evidence']}
        self.assertEqual(
            (rows['全民健康保險醫療辦法第3、15條（現行條文版本）']['announced_at'],
             rows['全民健康保險醫療辦法第3、15條（現行條文版本）']['effective_at']),
            ('2018-04-27', '2018-04-29'),
        )
        self.assertEqual(
            (rows['動物保護法第5條（現行條文版本）']['announced_at'],
             rows['動物保護法第5條（現行條文版本）']['effective_at']),
            ('2021-02-03', '2021-02-05'),
        )
        self.assertEqual(
            (rows['動物保護法第20條（現行條文版本）']['announced_at'],
             rows['動物保護法第20條（現行條文版本）']['effective_at']),
            ('2008-01-16', '2008-01-18'),
        )
        taipei = rows['臺北市動物保護自治條例第10條（現行條文版本）']
        self.assertEqual((taipei['announced_at'], taipei['effective_at']), ('2015-05-19', '2015-05-21'))
        medical = rows['醫療法第21、22、61條（現行條文版本）']
        self.assertEqual((medical['announced_at'], medical['effective_at']), ('2004-04-28', '2004-04-30'))
        self.assertEqual(
            (medical['latest_act_amendment_announced_at'], medical['latest_act_amendment_effective_at']),
            ('2026-09-23', '2026-09-25'),
        )
        self.assertIn('未修第21、22、61條', medical['scope'])
        self.assertTrue(all(row['date_basis'] and row['urls'] for row in rows.values()))


if __name__ == '__main__':
    unittest.main()
