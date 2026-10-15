"""臺灣公開資料的型別、日期與來源契約；不取代逐條事實核對。"""
from __future__ import annotations
import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ITEM_ID = re.compile(r'TW-(?:NAV-[0-9]{3}|[0-9]{2}-[0-9]{3})\Z')
SOURCE_ID = re.compile(r'[a-z][a-z0-9_]*\Z')
ISO_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\Z')
HOST_LABEL = re.compile(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\Z')


def taipei_today(now: datetime | None = None) -> date:
    if now is not None and now.tzinfo is None:
        raise ValueError('測試時鐘必須含時區')
    return (now or datetime.now(ZoneInfo('Asia/Taipei'))).astimezone(ZoneInfo('Asia/Taipei')).date()


def text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + '須為非空白文字')
    return value


def object_value(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(label + '須為物件')
    return value


def array(value, label: str, nonempty: bool = True) -> list:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(label + '須為' + ('非空' if nonempty else '') + '陣列')
    return value


def iso_date(value, label: str) -> date:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        raise ValueError(label + '須為YYYY-MM-DD格式')
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(label + '不是有效日期') from error


def checked_date(value, today: date, label: str = '查核日期') -> date:
    parsed = iso_date(value, label)
    if parsed > today:
        raise ValueError(label + '不得在未來')
    return parsed


def review_window(checked, due, today: date, label: str) -> date:
    first = checked_date(checked, today, label + '查核日期')
    last = iso_date(due, label + '複查日期')
    if last < first or last < today:
        raise ValueError(label + '複查日期早於查核日或已逾期')
    return first


def source_url(value) -> str:
    value = text(value, '來源網址')
    if not value.startswith('https://') or re.search(r'[\s\\\x00-\x1f\x7f]', value) or re.search(r'%(?![0-9A-Fa-f]{2})', value):
        raise ValueError('來源必須為無空白或反斜線的完整HTTPS網址')
    authority = re.split(r'[/?#]', value[8:], maxsplit=1)[0]
    if not re.fullmatch(r'[a-zA-Z0-9.-]+(?::[0-9]{1,5})?', authority):
        raise ValueError('來源網址的網域或連接埠格式錯誤')
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        labels = host.split('.')
        if parsed.username is not None or parsed.password is not None or len(labels) < 2 or not all(HOST_LABEL.fullmatch(label) for label in labels):
            raise ValueError('來源須有完整網域，不能含帳號密碼')
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError('來源連接埠不合法')
    except (ValueError, UnicodeError) as error:
        raise ValueError('來源網址結構不合法') from error
    return value


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('JSON重複欄位：' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('JSON不接受非有限數值：' + value)


def finite_float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError('JSON數值超出有限範圍')
    return parsed


def load_json(path: Path) -> dict:
    try:
        return object_value(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_pairs, parse_constant=reject_constant, parse_float=finite_float), str(path))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError('無法讀取有效JSON：' + str(path)) from error


def integer(value) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value) and value.is_integer())


def eligibility(rule) -> None:
    rule = object_value(rule, '適用條件')
    if set(rule) - {'sex', 'min_age', 'max_age', 'ages', 'family_history'}:
        raise ValueError('不認識的適用條件')
    if 'sex' in rule and rule['sex'] not in ('f', 'm'):
        raise ValueError('方案對象分類錯誤')
    if 'family_history' in rule and type(rule['family_history']) is not bool:
        raise ValueError('家族史條件必須為布林值')
    for key in ('min_age', 'max_age'):
        if key in rule and (not integer(rule[key]) or not 0 <= rule[key] <= 120):
            raise ValueError('年齡須為0至120的整數')
    low, high = rule.get('min_age', 0), rule.get('max_age', 120)
    if low > high:
        raise ValueError('年齡區間倒置')
    if 'ages' in rule:
        ages = array(rule['ages'], '指定年齡')
        if any(not integer(age) or not low <= age <= high for age in ages) or len(ages) != len(set(ages)):
            raise ValueError('指定年齡須為範圍內不重複的整數')


def validate_runtime_data(data, today: date | None = None) -> dict:
    today = today or taipei_today()
    data = object_value(data, '臺灣閱讀資料')
    if not integer(data.get('schema_version')) or (data['schema_version'], data.get('locale'), data.get('jurisdiction')) != (1, 'zh-TW', 'TW'):
        raise ValueError('臺灣閱讀資料結構不符')
    for field in ('title', 'scope'):
        text(data.get(field), field)
    updated = review_window(data.get('updated_at'), data.get('review_due_at'), today, '資料集')
    sources = {}
    for source in array(data.get('sources'), '來源'):
        source = object_value(source, '來源項目')
        key = text(source.get('id'), '來源ID')
        if not SOURCE_ID.fullmatch(key) or key in sources:
            raise ValueError('來源ID格式錯誤或重複')
        for field in ('title', 'supports'):
            text(source.get(field), '來源' + field)
        source_url(source.get('url'))
        accessed = checked_date(source.get('accessed_at'), today, '來源查閱日期')
        if accessed > updated:
            raise ValueError('來源查閱日期晚於資料集更新日')
        if source.get('published_at') is not None and iso_date(source['published_at'], '發布日期') > accessed:
            raise ValueError('來源發布日期晚於查閱日')
        sources[key] = source
    ids = set()
    for entry in array(data.get('items'), '閱讀條目'):
        entry = object_value(entry, '閱讀條目')
        key = text(entry.get('id'), '條目ID')
        if not ITEM_ID.fullmatch(key) or key in ids or entry.get('review_status') != 'source_checked':
            raise ValueError('條目ID錯誤、重複或尚未核對')
        ids.add(key)
        for field in ('title', 'body', 'limits', 'question'):
            text(entry.get(field), field)
        reviewed = review_window(entry.get('reviewed_at'), entry.get('review_due_at'), today, key)
        if reviewed > updated:
            raise ValueError('條目查核日晚於資料集更新日')
        refs = array(entry.get('source_ids'), '條目來源ID')
        if any(not isinstance(ref, str) or ref not in sources for ref in refs) or len(refs) != len(set(refs)):
            raise ValueError('條目引用未登錄或重複的來源')
        if any(iso_date(sources[ref]['accessed_at'], '來源查閱日期') > reviewed for ref in refs):
            raise ValueError('條目查核日早於引用來源查閱日')
        eligibility(entry.get('eligibility'))
    return data
