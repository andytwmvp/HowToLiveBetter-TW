#!/usr/bin/env python3
"""日常來源審閱與全書驗收；不以工程綠燈或任意路徑冒充內容完成。"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from datetime import date
from content_validation import (
    array, checked_date, load_json, object_value, review_window,
    source_url, taipei_today, text, validate_runtime_data,
)
ROOT = Path(__file__).resolve().parents[2]
STATUSES = {'pending', 'draft', 'needs_review', 'source_checked', 'verified', 'needs_recheck', 'not_applicable'}
CORE_ID = re.compile(r'TW-[0-9]{2}-[0-9]{3}\Z')


def safe_path(root: Path, value: str, prefix: str) -> Path:
    if not isinstance(value, str) or not value.startswith(prefix) or '\\' in value or any(part in {'', '.', '..'} for part in value.split('/')):
        raise ValueError('目標路徑不在允許的內容目錄或含路徑跳脫')
    try:
        root = root.resolve()
        allowed = root / prefix
        # 命名空間本身也不能透過符號連結換成另一個目錄。
        if allowed.resolve() != allowed or not allowed.is_dir():
            raise ValueError('指定內容目錄不存在或被重新導向')
        path = (root / value).resolve()
        if not path.is_relative_to(allowed) or not path.is_file():
            raise ValueError('目標不存在或越過指定內容目錄：' + value)
        return path
    except (OSError, RuntimeError) as error:
        raise ValueError('無法解析安全內容路徑') from error


def valid_date(value: str, today: date) -> date:
    return checked_date(value, today)


def validate_entry(entry: dict, root: Path = ROOT, today: date | None = None) -> bool:
    today = today or taipei_today()
    entry = object_value(entry, '原作條目')
    key = text(entry.get('id'), '條目ID')
    if not CORE_ID.fullmatch(key):
        raise ValueError('原作條目ID格式錯誤')
    status = entry.get('status')
    if not isinstance(status, str) or status not in STATUSES:
        raise ValueError('不認識的條目狀態')
    target = entry.get('target_path')
    if target is not None:
        text(target, '正文路徑')
    path = safe_path(root, target, 'locales/zh-TW/') if target is not None else None
    if path is not None and path.suffix != '.md':
        raise ValueError('條目正文必須為Markdown文件')
    if status not in {'verified', 'not_applicable'}:
        return False
    review_path = safe_path(root, f'localization/reviews/{key}.json', 'localization/reviews/')
    review = load_json(review_path)
    if review.get('id') != key or review.get('jurisdiction') != 'TW':
        raise ValueError('審閱地區或條目ID不符')
    text(review.get('reviewer'), '審閱者')
    checked = review_window(entry.get('verified_at'), review.get('review_due_at'), today, key)
    if review.get('reviewed_at') != checked.isoformat():
        raise ValueError('審閱日期不同步')
    for source in array(review.get('source_checks'), '來源核對紀錄'):
        source = object_value(source, '來源核對紀錄')
        source_url(source.get('url'))
        text(source.get('claim'), '來源主張')
        text(source.get('supporting_passage'), '來源支持段落')
        if checked_date(source.get('accessed_at'), today, '來源查閱日期') > checked:
            raise ValueError('來源查閱晚於條目審閱，須更新審閱紀錄')
    if status == 'not_applicable':
        text(review.get('reason'), '不適用理由')
        return True
    if path is None:
        raise ValueError('已查核條目缺少實際臺灣正文')
    try:
        raw = path.read_bytes()
        body = raw.decode('utf-8')
    except (OSError, UnicodeError) as error:
        raise ValueError('正文無法以UTF-8讀取') from error
    if review.get('target_path') != target or review.get('target_sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('正文變更後尚未更新來源審閱')
    if f'<!-- TW-ID: {key} -->' not in body:
        raise ValueError('正文缺少固定條目ID')
    return True


def validate_runtime(root: Path = ROOT, today: date | None = None) -> dict:
    return validate_runtime_data(load_json(root / 'localization/tw-edition/runtime.json'), today)


def publication_report(root: Path = ROOT, manifest: dict | None = None) -> dict:
    complete, blockers, entries = 0, [], []
    today = taipei_today()
    try:
        manifest = load_json(root / 'localization/manifest.json') if manifest is None else object_value(manifest, '原作清單')
        entries = array(manifest.get('entries'), '原作條目清單')
        keys = [text(object_value(e, '原作條目').get('id'), '條目ID') for e in entries]
        if len(keys) != len(set(keys)):
            raise ValueError('原作清單有重複ID')
        runtime = validate_runtime(root, today)
        published = {entry['id']: entry for entry in runtime['items']}
        sources = {source['id']: source for source in runtime['sources']}
        unknown = set(published) - set(keys)
        if any(not key.startswith('TW-NAV-') for key in unknown):
            raise ValueError('閱讀資料出現未列於原作清單的核心條目')
    except ValueError as error:
        blockers.append('整體資料：' + str(error))
        published, sources = {}, {}
    for entry in entries:
        key = entry.get('id', '?') if isinstance(entry, dict) else '?'
        try:
            if not validate_entry(entry, root, today):
                blockers.append(str(key) + ':尚未完成來源審閱')
                continue
            if entry['status'] == 'verified':
                if key not in published:
                    raise ValueError('尚未整合有效的閱讀輸出')
                target = safe_path(root, entry['target_path'], 'locales/zh-TW/')
                item = published[key]
                if item.get('target_path') != entry['target_path'] or item['body'] != target.read_text(encoding='utf-8') or item['reviewed_at'] != entry['verified_at']:
                    raise ValueError('閱讀內容、路徑或日期與審閱正文不一致')
                review = load_json(safe_path(root, f'localization/reviews/{key}.json', 'localization/reviews/'))
                reviewed_urls = {source['url'] for source in review['source_checks']}
                if not {sources[ref]['url'] for ref in item['source_ids']}.issubset(reviewed_urls):
                    raise ValueError('閱讀輸出引用尚未納入條目審閱的來源')
            elif key in published:
                raise ValueError('不適用條目不能同時當作已核對閱讀建議')
            complete += 1
        except (ValueError, KeyError, TypeError, OSError, UnicodeError) as error:
            blockers.append(str(key) + ':' + str(error))
    return {
        'publication_ready': bool(entries) and not blockers,
        'publication_completed_entries': complete,
        'publication_total_entries': len(entries),
        'publication_blockers': blockers,
        'publication_scope': '驗證資料結構、審閱紀錄與閱讀一致性；不代表獨立事實查核或醫療法律專業簽證。',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    validate_runtime()
    result = publication_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if args.require_complete and not result['publication_ready'] else 0)
