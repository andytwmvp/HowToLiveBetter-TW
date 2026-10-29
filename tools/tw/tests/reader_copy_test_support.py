"""Helpers for keeping substantive reviews distinct from later copy edits."""
import hashlib
from functools import lru_cache

from content_validation import load_json
import retroactive_audit as audit
from retroactive_audit import ROOT, normalize_reader_item, validate_reader_copy_cleanup_history


def assert_professional_review_pending(testcase, reviewer: str) -> None:
    """Accept equivalent provenance wording while preserving the review boundary."""
    testcase.assertIn("AI", reviewer)
    testcase.assertTrue("專業" in reviewer)
    testcase.assertTrue("非獨立" in reviewer or "未取得獨立" in reviewer)


@lru_cache(maxsize=1)
def _current_reader_state():
    runtime = load_json(ROOT / "localization/tw-edition/runtime.json")
    register = load_json(ROOT / "localization/retroactive-review-register-20261019.json")
    return (
        {item["id"]: item for item in runtime["items"]},
        register.get("reader_copy_cleanups", []),
    )


@lru_cache(maxsize=512)
def _validated_cleanup_prior_item(item_id: str, current_sha256: str) -> dict:
    items, cleanups = _current_reader_state()
    item = items[item_id]
    matches = [
        row for row in cleanups
        if row.get("id") == item_id and row.get("after_sha256") == current_sha256
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"{item_id} 的讀者正文整理紀錄應恰有一筆，實際為 {len(matches)} 筆"
        )
    previous = validate_reader_copy_cleanup_history(ROOT, matches[0], item)
    return previous


def _validated_cleanup_prior(item_id: str, current_sha256: str) -> str:
    return _validated_cleanup_prior_item(item_id, current_sha256)["body"]


def assert_body_version_matches_review_or_cleanup(
    testcase,
    item_id: str,
    substantive_sha256: str,
    observed_sha256: str,
) -> None:
    """Check the current body against the substantive review or its exact copy-edit edge."""
    items, _cleanups = _current_reader_state()
    item = items[item_id]
    actual_sha256 = hashlib.sha256(item["body"].encode("utf-8")).hexdigest()
    testcase.assertEqual(actual_sha256, observed_sha256, f"{item_id} runtime body hash")
    if actual_sha256 == substantive_sha256:
        return
    rows = [
        row for row in _current_reader_state()[1]
        if row.get("id") == item_id and row.get("after_sha256") == actual_sha256
    ]
    if len(rows) != 1:
        raise AssertionError(f"{item_id} 的讀者正文整理版本不唯一")
    reviewed = audit._pre_cleanup_reviewed_item(
        ROOT, item, rows[0], target_sha256=substantive_sha256
    )
    prior_sha256 = hashlib.sha256(reviewed["body"].encode("utf-8")).hexdigest()
    testcase.assertEqual(
        prior_sha256,
        substantive_sha256,
        f"{item_id} copy cleanup chain must reach the substantively reviewed body",
    )


def assert_reader_limits_match_review_or_cleanup(testcase, item_id: str, reviewed_limit: str) -> None:
    """Allow reader-facing limits to be normalized while requiring an exact history edge."""
    items, _cleanups = _current_reader_state()
    item = items[item_id]
    if item["limits"] == reviewed_limit:
        return
    current_sha256 = hashlib.sha256(item["body"].encode("utf-8")).hexdigest()
    previous = _validated_cleanup_prior_item(item_id, current_sha256)
    normalized, _removed = normalize_reader_item(previous)
    testcase.assertEqual(item["limits"], normalized["limits"], f"{item_id} reader limits")
