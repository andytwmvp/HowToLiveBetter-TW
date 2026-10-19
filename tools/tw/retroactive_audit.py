#!/usr/bin/env python3
"""全書臺灣版歷史內容回溯稽核；辨識待人工核對項目，不冒充專業或來源再認證。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ID = re.compile(r"TW-\d{2}-\d{3}\Z")
LOCAL_CONTEXT = re.compile(
    r"臺灣|台灣|臺北|新北|桃園|臺中|臺南|高雄|花蓮|臺東|健保|勞保|"
    r"消防局|衛福部|交通部|勞動部|衛生局|警政署|國健署|區公所|"
    r"臺鐵|高鐵|農業部|疾管署|社會局|法規|公所|新臺幣"
)
FREQUENCY = re.compile(
    r"發生率|盛行率|死亡率|事件頻率|件數|官方統計|統計數據|統計顯示|"
    r"統計資料|每十萬|每[千萬]人口|人年|病例數|死亡人數|年度通報"
)
YEAR = re.compile(r"(?:20[012]\d年|民國\d{2,3}年|(?:20[012]\d)[－至~～-](?:20[012]\d)年)")
NUMERIC_CASE = re.compile(
    r"\d{1,3}(?:,\d{3})+(?:人|件|例|人次)|"
    r"\d+(?:\.\d+)?(?:%|％|萬人|萬件|人次|個案|病例)"
)
HIGH_RISK = {1, 13}
ELEVATED_RISK = {7, 16, 17, 19, 23, 24, 25}


def documented_revision(old: dict, new: dict, record: dict) -> bool:
    # 相同正文或只改日期，不能取得實質再審的修訂資格。
    if not isinstance(record, dict) or old.get("id") != new.get("id") or record.get("id") != old.get("id"):
        return False
    if old.get("body") == new.get("body"):
        return False
    allowed = {"body", "reviewed_at"}
    if {k: v for k, v in old.items() if k not in allowed} != {k: v for k, v in new.items() if k not in allowed}:
        return False
    for field, item in (("before_sha256", old), ("after_sha256", new)):
        if record.get(field) != hashlib.sha256(item.get("body", "").encode("utf-8")).hexdigest():
            return False
    if record.get("status") != "ai_source_rechecked_professional_pending":
        return False
    for field, length in (("prior_revision", 40), ("prior_review_sha256", 64)):
        if not re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", record.get(field, "")):
            return False
    for field in ("taiwan_context", "frequency_assessment", "changes"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            return False
    if not isinstance(record.get("limits"), list) or not record["limits"] or not all(isinstance(v, str) and v.strip() for v in record["limits"]):
        return False
    from datetime import date
    try:
        checked = date.fromisoformat(record["reviewed_at"])
        due = date.fromisoformat(record["review_due_at"])
        from content_validation import taipei_today
        if checked > taipei_today() or due < checked or new.get("reviewed_at") != checked.isoformat():
            return False
    except (KeyError, TypeError, ValueError):
        return False
    checks = record.get("source_checks")
    if not isinstance(checks, list) or not checks:
        return False
    from content_validation import source_url
    for check in checks:
        if not isinstance(check, dict) or any(not isinstance(check.get(k), str) or not check[k].strip() for k in ("url", "claim", "supporting_passage", "accessed_at")):
            return False
        try:
            source_url(check["url"])
            if date.fromisoformat(check["accessed_at"]) > checked:
                return False
        except (ValueError, TypeError):
            return False
    return True


def validate_recheck_history(root: Path, record: dict, new: dict) -> None:
    key = new["id"]
    revision = record.get("prior_revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("實質再審原版本不符")
    try:
        before = json.loads(subprocess.check_output(
            ["git", "show", revision + ":localization/tw-edition/runtime.json"], cwd=root))
        old = next(i for i in before["items"] if i["id"] == key)
        prior_review = subprocess.check_output(
            ["git", "show", revision + ":localization/reviews/" + key + ".json"], cwd=root)
    except (subprocess.CalledProcessError, StopIteration, KeyError, ValueError) as error:
        raise ValueError("無法核對再審的歷史正文與審閱：" + key) from error
    if record.get("prior_review_sha256") != hashlib.sha256(prior_review).hexdigest():
        raise ValueError("再審原始審閱 SHA 不符：" + key)
    if not documented_revision(old, new, record):
        raise ValueError("實質再審證據或前後正文 SHA 不符：" + key)
    current_review = load(root, "localization/reviews/" + key + ".json")
    if record["source_checks"] != current_review["source_checks"] or record["limits"] != current_review["limits"]:
        raise ValueError("實質再審與現行審閱不同步：" + key)


def assert_preserved_or_rechecked(case, old: dict, new: dict) -> None:
    """歷史保全測試僅允許具完整證據且已核對前後版本的正文修訂。"""
    if old == new:
        return
    register = load(ROOT, "localization/retroactive-review-register-20261019.json")
    records = [r for r in register.get("substantive_rechecks", []) if r.get("id") == old.get("id")]
    case.assertEqual(len(records), 1, "正文變更必須有唯一再審紀錄")
    case.assertTrue(documented_revision(old, new, records[0]), "未登錄、證據缺漏或雜湊不同的正文修訂")
    validate_recheck_history(ROOT, records[0], new)


def load(root: Path, relative: str) -> dict:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def checked_markdown(root: Path, path: str) -> bytes:
    # 僅允許儲存庫已存在之繁體中文正文明確路徑，不跟隨路徑跳脫。
    if not isinstance(path, str) or not path.startswith("locales/zh-TW/"):
        raise ValueError("臺灣正文位置不符")
    if any(part in {"", ".", ".."} for part in path.split("/")) or "\\" in path:
        raise ValueError("無效正文路徑")
    target = root / path
    allowed = root / "locales/zh-TW"
    if not target.is_file() or not target.resolve().is_relative_to(allowed.resolve()):
        raise ValueError("臺灣正文不存在或超出允許目錄：" + path)
    if target.suffix != ".md":
        raise ValueError("臺灣正文格式不是 Markdown：" + path)
    return target.read_bytes()


def cues(body: str) -> dict:
    """文字特徵只是候選提示；不可當作統計來源可靠性或台灣適用性證明。"""
    return {
        "tw_context_marker": bool(LOCAL_CONTEXT.search(body)),
        "frequency_term_marker": bool(FREQUENCY.search(body)),
        "statistic_year_marker": bool(YEAR.search(body)),
        "numeric_claim_marker": bool(NUMERIC_CASE.search(body)),
    }


def risk(chapter: int | None, key: str) -> str:
    if key in {"TW-NAV-001", "TW-NAV-002", "TW-NAV-010"}:
        return "P0"
    if chapter in HIGH_RISK:
        return "P0"
    if chapter in ELEVATED_RISK or key.startswith("TW-NAV-"):
        return "P1"
    return "P2"


def audit(root: Path = ROOT) -> dict:
    manifest = load(root, "localization/manifest.json")
    runtime = load(root, "localization/tw-edition/runtime.json")
    coverage = load(root, "localization/tw-edition/coverage.json")
    assets = load(root, "localization/assets-inventory.json")
    entries = manifest["entries"]
    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)) or any(not ID.fullmatch(k) for k in ids):
        raise ValueError("原作核心 ID 重複或不符格式")
    published = runtime["items"]
    published_map = {i["id"]: i for i in published}
    if len(published_map) != len(published):
        raise ValueError("閱讀輸出有重複條目")
    reviewed = {e["id"] for e in entries if e["status"] == "verified"}
    live_core = {k for k in published_map if not k.startswith("TW-NAV-")}
    if reviewed != live_core:
        raise ValueError("歷史正式核心未完整納入共同 runtime")
    sources = {s["id"] for s in runtime["sources"]}
    if len(sources) != len(runtime["sources"]):
        raise ValueError("共用來源 ID 重複")
    for item in published:
        if set(item.get("source_ids", [])) - sources:
            raise ValueError("閱讀條目引用未登錄的共用來源：" + item["id"])
    result = []
    per_chapter = defaultdict(lambda: {"core": 0, "published": 0, "frequency_term_marker": 0,
                                      "tw_context_marker": 0, "requires_substantive_recheck": 0})
    for entry in entries:
        key = entry["id"]
        ch = int(entry["upstream_chapter"])
        per_chapter[ch]["core"] += 1
        row = {
            "id": key,
            "chapter": ch,
            "prior_status": entry["status"],
            "priority": risk(ch, key),
            "source_title": entry.get("source_title_zh_tw", ""),
        }
        if key not in reviewed:
            # 草稿不是正式臺灣正文；不讀未審閱中國原作作為備援。
            row["new_standard_review"] = "not_published_research_pending"
            result.append(row)
            continue
        per_chapter[ch]["published"] += 1
        target = entry["target_path"]
        raw = checked_markdown(root, target)
        body = raw.decode("utf-8")
        page = published_map[key]
        if page["body"] != body:
            raise ValueError("舊正文與共用閱讀內容不同步：" + key)
        review = load(root, "localization/reviews/" + key + ".json")
        if (review.get("id") != key or review.get("target_path") != target or
                review.get("target_sha256") != hashlib.sha256(raw).hexdigest()):
            raise ValueError("原審閱與正式正文雜湊不一致：" + key)
        checks = review.get("source_checks", [])
        if not checks or any(not c.get("url") or not c.get("supporting_passage") for c in checks):
            raise ValueError("歷史來源核對紀錄欠缺可追查來源：" + key)
        markers = cues(body)
        for name in ("frequency_term_marker", "tw_context_marker"):
            per_chapter[ch][name] += int(markers[name])
        per_chapter[ch]["requires_substantive_recheck"] += 1
        row.update({
            "target_path": target,
            "old_reviewed_at": review.get("reviewed_at"),
            "old_review_due_at": review.get("review_due_at"),
            "old_source_checks": len(checks),
            "runtime_source_ids": len(page.get("source_ids", [])),
            "content_sha256": review["target_sha256"],
            "evidence_markers_only": markers,
            "new_standard_review": "pending_substantive_taiwan_context_and_frequency_recheck",
            "verification_boundary": "正規表示式不證明統計定義、分母、年份、原始來源或專業正確性",
        })
        result.append(row)
    nav = []
    for key, page in sorted(published_map.items()):
        if not key.startswith("TW-NAV-"):
            continue
        markers = cues(page["body"])
        nav.append({
            "id": key,
            "title": page["title"],
            "old_reviewed_at": page.get("reviewed_at"),
            "runtime_source_ids": len(page.get("source_ids", [])),
            "priority": risk(None, key),
            "evidence_markers_only": markers,
            "new_standard_review": "pending_substantive_taiwan_context_and_frequency_recheck",
        })
    if len(result) != len(entries) or len(nav) != len(published) - len(reviewed):
        raise ValueError("回溯稽核清單未涵蓋全書")
    if coverage["publication_completed_entries"] != len(reviewed):
        raise ValueError("動態 coverage 核心完成數與來源不符")
    if coverage["original_entries"] != len(entries):
        raise ValueError("動態 coverage 核心原始總數與來源不符")
    register = load(root, "localization/retroactive-review-register-20261019.json")
    rechecks = register.get("substantive_rechecks", [])
    if not isinstance(rechecks, list):
        raise ValueError("實質再審紀錄必須為清單")
    seen = set()
    for record in rechecks:
        key = record.get("id")
        if key not in published_map or key in seen:
            raise ValueError("實質再審 ID 不存在或重複")
        seen.add(key)
        revision = record.get("prior_revision", "")
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("實質再審原版本不符")
        validate_recheck_history(root, record, published_map[key])
    return {
        "schema_version": 1,
        "standard": "PR #27：臺灣情境、發生頻率、原始來源與風險分流",
        "scope": "完整來源核心清單、所有已發布核心正文及10則補充導航；未審稿與圖片另追蹤",
        "limitations": [
            "本次為機械化回溯盤點；不宣稱每一條舊正文都已完成新標準實質來源審閱",
            "僅有文字特徵不能證明臺灣事故真實發生率，不能將未出現統計詞視為錯誤或必要缺漏",
            "醫療／法律／災防的 AI 輔助審閱不等同有執照專業審閱",
            "圖片雜湊與字形沿用既有 image_copy.py 及瀏覽器 CI，制度內容仍須人工核對",
        ],
        "summary": {
            "all_core_inventory": len(entries),
            "published_core_retroactively_screened": len(reviewed),
            "published_navigation_retroactively_screened": len(nav),
            "unpublished_core_tracked": len(entries) - len(reviewed),
            "draft_topics": coverage["unique_draft_entries"],
            "topics_without_any_draft": coverage["entries_without_any_draft"],
            "previously_reviewed_items_still_needing_new_standard_substantive_recheck": len(reviewed) + len(nav),
            "ai_source_rechecked_professional_pending": len(rechecks),
            "publication_ready": False,
        },
        "ai_source_rechecks": rechecks,
        "per_chapter": [{"chapter": n, **v} for n, v in sorted(per_chapter.items())],
        "core": result,
        "navigation": nav,
        "assets": {
            "existing_inventory": "localization/assets-inventory.json",
            "raster_and_vector_assets": len(assets.get("raster_and_vector_files", [])),
            "badges": len(assets.get("dynamic_badges", [])),
            "svg_icons": len(assets.get("inline_svg", [])),
            "substantive_language_and_visual_review": "not_completed_by_automated_scan",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="核對回溯盤點全面性與來源一致性")
    parser.add_argument("--report", help="輸出動態逐條清單（供 CI artifact 保存）")
    args = parser.parse_args()
    if not args.check:
        parser.error("請指定 --check，避免被誤用為自動重新認證工具")
    report = audit()
    if args.report:
        file = Path(args.report)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
