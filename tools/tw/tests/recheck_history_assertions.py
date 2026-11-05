"""歷史再審批次的不可變 Git 版本核對輔助函式。"""
import hashlib
import json
import subprocess

from retroactive_audit import documented_revision


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
