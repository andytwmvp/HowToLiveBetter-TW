"""Read append-only source-bundle IDs at a Git revision for regression tests."""
import json
import subprocess
from pathlib import Path


def source_bundle_ids_added_since(root: Path, revision: str) -> set[str]:
    bundle_dir = "localization/tw-edition/sources"
    changed_paths = subprocess.check_output(
        ["git", "diff", "--name-only", revision, "--", bundle_dir],
        cwd=root,
        text=True,
    ).splitlines()
    untracked_paths = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "--", bundle_dir],
        cwd=root,
        text=True,
    ).splitlines()
    changed_paths = sorted(set(changed_paths) | set(untracked_paths))

    def ids(document):
        return {
            row[0]
            for row in document.get("sources", [])
            if isinstance(row, list) and row and isinstance(row[0], str)
        } if isinstance(document, dict) else set()

    added = set()
    for relative_path in changed_paths:
        current_path = root / relative_path
        if not current_path.is_file():
            continue
        current = json.loads(current_path.read_text(encoding="utf-8"))
        try:
            prior = json.loads(subprocess.check_output(
                ["git", "show", f"{revision}:{relative_path}"],
                cwd=root,
                stderr=subprocess.DEVNULL,
            ))
        except subprocess.CalledProcessError:
            prior = {}
        added.update(ids(current) - ids(prior))
    return added
