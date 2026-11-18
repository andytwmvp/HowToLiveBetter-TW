"""歷史再審批次的不可變 Git 版本核對輔助函式。"""
import hashlib
import json
import subprocess
from pathlib import Path

from retroactive_audit import assert_preserved_or_rechecked, documented_revision

ROOT = Path(__file__).resolve().parents[3]


def assert_append_only_rechecks(testcase, baseline_rows, current_rows, *, expected_rows=()):
    """Keep a historical prefix immutable while allowing later rechecks to append."""
    testcase.assertGreaterEqual(len(current_rows), len(baseline_rows))
    testcase.assertEqual(current_rows[:len(baseline_rows)], baseline_rows)
    appended = current_rows[len(baseline_rows):]
    for row in expected_rows:
        testcase.assertEqual(appended.count(row), 1, row.get("id"))
    return appended


def assert_chapter_entries_preserved_or_rechecked(
    testcase,
    *,
    chapter_number,
    baseline_entries,
    current_entries,
    baseline_items,
    current_items,
    baseline_rechecks,
    current_rechecks,
):
    """Allow a structured row to change only with a hash-linked later recheck.

    This keeps old batch tests independent of future item IDs while still
    checking row inventory, append-only history, and the exact body hash chain
    behind every changed row.
    """
    baseline_rows = {row[0]: row for row in baseline_entries}
    current_rows = {row[0]: row for row in current_entries}
    testcase.assertEqual(set(current_rows), set(baseline_rows))
    appended = assert_append_only_rechecks(
        testcase, baseline_rechecks, current_rechecks
    )
    by_id = {}
    for record in appended:
        by_id.setdefault(record["id"], []).append(record)

    changed_ids = set()
    for number, old_row in baseline_rows.items():
        new_row = current_rows[number]
        if new_row == old_row:
            continue
        item_id = f"TW-{chapter_number:02d}-{int(number):03d}"
        old_item = baseline_items.get(item_id)
        new_item = current_items.get(item_id)
        testcase.assertIsNotNone(new_item, f"{item_id} 缺少目前 runtime 條目")
        if old_item is None:
            _assert_draft_was_published_with_its_structured_hash(
                testcase, item_id, old_row, new_item
            )
            changed_ids.add(item_id)
            continue
        records = by_id.get(item_id, [])
        testcase.assertTrue(records, f"{item_id} 章節資料列變更沒有追加再審紀錄")
        assert_preserved_or_rechecked(testcase, old_item, new_item)

        old_sha = hashlib.sha256(old_item["body"].encode("utf-8")).hexdigest()
        new_sha = hashlib.sha256(new_item["body"].encode("utf-8")).hexdigest()
        testcase.assertEqual(records[0]["before_sha256"], old_sha, item_id)
        for previous, following in zip(records, records[1:]):
            testcase.assertEqual(following["before_sha256"], previous["after_sha256"], item_id)
        testcase.assertEqual(records[-1]["after_sha256"], new_sha, item_id)
        changed_ids.add(item_id)

    return changed_ids


def _assert_draft_was_published_with_its_structured_hash(testcase, item_id, old_row, item):
    """Verify a draft row changed as its first reviewed runtime publication."""
    manifest = json.loads((ROOT / "localization/manifest.json").read_text(encoding="utf-8"))
    entry = next(row for row in manifest["entries"] if row["id"] == item_id)
    review = json.loads(
        (ROOT / f"localization/reviews/{item_id}.json").read_text(encoding="utf-8")
    )
    body = item["body"].encode("utf-8")
    body_sha = hashlib.sha256(body).hexdigest()
    row_sha = hashlib.sha256(
        json.dumps(old_row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    testcase.assertEqual(entry["status"], "verified", item_id)
    testcase.assertEqual(entry["target_path"], item["target_path"], item_id)
    testcase.assertEqual(entry["sources"], item["source_ids"], item_id)
    testcase.assertEqual(review["target_path"], item["target_path"], item_id)
    testcase.assertEqual(review["source_ids"], item["source_ids"], item_id)
    testcase.assertEqual(review["target_sha256"], body_sha, item_id)
    testcase.assertRegex(review["source_reviewed_sha256"], r"^[0-9a-f]{64}$", item_id)
    testcase.assertEqual(
        {row["source_id"] for row in review["source_checks"]},
        set(item["source_ids"]),
        item_id,
    )
    testcase.assertEqual((ROOT / item["target_path"]).read_bytes(), body, item_id)
    prior_draft_hashes = {
        review.get("prior_structured_draft_sha256"),
        review.get("prior_chapter_draft_sha256"),
    }
    testcase.assertIn(row_sha, prior_draft_hashes, f"{item_id} 首次發布審閱未綁定舊結構草稿")


def _json_at(root, revision, path):
    raw = subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=root)
    return json.loads(raw)


def _blob_at(root, revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=root)


def assert_historical_recheck_edge(testcase, root, record, *, merged_revision):
    """驗證歷史批次的前後正文、原審閱、來源及批次審閱快照。"""
    key = record["id"]
    old_runtime = _json_at(root, record["prior_revision"], "localization/tw-edition/runtime.json")
    new_runtime = _json_at(root, merged_revision, "localization/tw-edition/runtime.json")
    old_item = next(item for item in old_runtime["items"] if item["id"] == key)
    new_item = next(item for item in new_runtime["items"] if item["id"] == key)
    old_review = _blob_at(root, record["prior_revision"], f"localization/reviews/{key}.json")
    new_review = _json_at(root, merged_revision, f"localization/reviews/{key}.json")

    testcase.assertEqual(
        hashlib.sha256(old_review).hexdigest(), record["prior_review_sha256"]
    )
    testcase.assertEqual(
        hashlib.sha256(old_item["body"].encode("utf-8")).hexdigest(),
        record["before_sha256"],
    )
    testcase.assertEqual(
        hashlib.sha256(new_item["body"].encode("utf-8")).hexdigest(),
        record["after_sha256"],
    )
    testcase.assertTrue(documented_revision(old_item, new_item, record))
    testcase.assertEqual(new_review["target_sha256"], record["after_sha256"])
    testcase.assertEqual(new_review["source_checks"], record["source_checks"])
    testcase.assertEqual(new_review["limits"], record["limits"])
