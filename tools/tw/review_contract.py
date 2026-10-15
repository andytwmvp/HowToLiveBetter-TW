#!/usr/bin/env python3
"""日常內容契約與全書驗收門檻；不以原作遷移狀態凍結後續編修。"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[2]
STATUSES = {'pending', 'draft', 'needs_review', 'source_checked', 'verified', 'needs_recheck', 'not_applicable'}


def safe_path(root: Path, value: str, prefix: str) -> Path:
    if not isinstance(value, str) or not value.startswith(prefix) or '\\' in value:
        raise ValueError('目標路徑不在允許的臺灣內容目錄')
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('目標不存在或越過專案範圍：' + value)
    return path


def valid_date(value: str, today: date) -> date:
    parsed = date.fromisoformat(value)
    if parsed > today: raise ValueError('查核日期不得在未來')
    return parsed


def validate_entry(entry: dict, root: Path = ROOT, today: date | None = None) -> bool:
    today = today or date.today()
    status = entry.get('status')
    if status not in STATUSES: raise ValueError('不認識的條目狀態：' + str(status))
    target = entry.get('target_path')
    path = safe_path(root, target, 'locales/zh-TW/') if target else None
    if status not in {'verified', 'not_applicable'}:
        return False
    review_path = safe_path(root, f"localization/reviews/{entry['id']}.json", 'localization/reviews/')
    review = json.loads(review_path.read_text(encoding='utf-8'))
    if review.get('id') != entry['id'] or not review.get('reviewer') or review.get('jurisdiction') != 'TW':
        raise ValueError('審閱者、地區或條目 ID 不完整')
    checked = valid_date(entry.get('verified_at'), today)
    if review.get('reviewed_at') != checked.isoformat(): raise ValueError('審閱日期不同步')
    if date.fromisoformat(review['review_due_at']) < today: raise ValueError('審閱已到期')
    if not review.get('source_checks'): raise ValueError('缺少逐項來源核對紀錄')
    for source in review['source_checks']:
        url = urlsplit(source.get('url', ''))
        if url.scheme != 'https' or not url.netloc or not source.get('claim') or not source.get('supporting_passage'):
            raise ValueError('來源必須包含具體主張與支持段落，不能只有首頁')
        valid_date(source.get('accessed_at'), today)
    if status == 'not_applicable':
        if not review.get('reason'): raise ValueError('不適用須有具體理由與審閱依據')
        return True
    if not path: raise ValueError('已查核條目缺少實際臺灣正文')
    raw = path.read_bytes()
    if review.get('target_path') != target or review.get('target_sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('正文改變後尚未更新來源審閱')
    if f"<!-- TW-ID: {entry['id']} -->" not in raw.decode('utf-8'):
        raise ValueError('正文沒有對應條目的固定 ID')
    return True


def publication_report(root: Path = ROOT, manifest: dict | None = None) -> dict:
    manifest = manifest or json.loads((root / 'localization/manifest.json').read_text(encoding='utf-8'))
    runtime_path = root / 'localization/tw-edition/runtime.json'
    runtime = json.loads(runtime_path.read_text(encoding='utf-8')) if runtime_path.exists() else {'items': []}
    published = {e['id']: e for e in runtime['items']}
    complete, blockers = 0, []
    for entry in manifest['entries']:
        try:
            reviewed = validate_entry(entry, root)
            if not reviewed: blockers.append(entry['id'] + ':尚未完成來源審閱'); continue
            if entry['status'] == 'verified' and entry['id'] not in published:
                blockers.append(entry['id'] + ':尚未整合閱讀輸出'); continue
            if entry['status'] == 'verified':
                target = safe_path(root, entry['target_path'], 'locales/zh-TW/')
                item = published[entry['id']]
                if item.get('target_path') != entry['target_path'] or item.get('body') != target.read_text(encoding='utf-8'):
                    blockers.append(entry['id'] + ':閱讀內容與已審閱正文不一致'); continue
            complete += 1
        except (ValueError, KeyError, TypeError) as error:
            blockers.append(entry['id'] + ':' + str(error))
    return {'publication_ready': len(manifest['entries']) > 0 and not blockers,
            'publication_completed_entries': complete, 'publication_total_entries': len(manifest['entries']),
            'publication_blockers': blockers,
            'publication_scope': '依正文、逐條來源審閱紀錄與閱讀整合計算；不代表醫療或法律專業簽證。'}


def validate_runtime(root: Path = ROOT, today: date | None = None) -> dict:
    today = today or date.today()
    data = json.loads((root / 'localization/tw-edition/runtime.json').read_text(encoding='utf-8'))
    if (data.get('schema_version'), data.get('locale'), data.get('jurisdiction')) != (1, 'zh-TW', 'TW'):
        raise ValueError('臺灣閱讀資料結構不符')
    if date.fromisoformat(data['review_due_at']) < today: raise ValueError('導航來源須重新查核')
    sources = {s['id']:s for s in data['sources']}
    if len(sources) != len(data['sources']): raise ValueError('來源 ID 重複')
    ids = set()
    for source in sources.values():
        if not source.get('supports') or not source.get('title') or urlsplit(source['url']).scheme != 'https':
            raise ValueError('來源缺少主張範圍或安全網址')
        valid_date(source['accessed_at'], today)
    for entry in data['items']:
        if entry['id'] in ids or entry.get('review_status') != 'source_checked': raise ValueError('重複 ID 或未核對條目不得公開')
        ids.add(entry['id'])
        for field in ('title', 'body', 'limits', 'question'):
            if not isinstance(entry.get(field), str) or not entry[field].strip(): raise ValueError('條目欄位缺漏：' + field)
        valid_date(entry['reviewed_at'], today)
        if date.fromisoformat(entry['review_due_at']) < today: raise ValueError('條目須重新查核')
        if not entry['source_ids'] or any(s not in sources for s in entry['source_ids']): raise ValueError('條目引用未登錄來源')
        rule = entry['eligibility']
        if set(rule) - {'sex','min_age','max_age','ages','family_history'}: raise ValueError('不認識的適用條件')
        if rule.get('sex') not in {None,'f','m'}: raise ValueError('方案對象分類錯誤')
        for k in ('min_age','max_age'):
            if k in rule and (type(rule[k]) is not int or not 0 <= rule[k] <= 120): raise ValueError('年齡格式錯誤')
        if rule.get('min_age',0) > rule.get('max_age',120): raise ValueError('年齡區間倒置')
        if 'ages' in rule and (not rule['ages'] or any(type(a) is not int or not 0 <= a <= 120 for a in rule['ages'])): raise ValueError('指定年齡格式錯誤')
    if not ids: raise ValueError('沒有可供閱讀的已核對導航')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    validate_runtime()
    result = publication_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if args.require_complete and not result['publication_ready'] else 0)
