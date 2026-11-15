"""Shared reader-body structure checks, separate from topic-specific assertions."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from body_renderer import body_blocks


def body_structure_issues(
    item: dict,
    *,
    known_source_ids: set[str] | None = None,
    required_headings: tuple[str, ...] = (),
) -> list[str]:
    """Return structural defects without pinning an article to an exact heading count.

    Global checks cover Markdown-to-reader heading fidelity, nonempty sections,
    and registered source IDs. ``required_headings`` is reserved for a real,
    article-specific section requirement; additional valid sections are allowed.
    """
    body = item.get("body")
    if not isinstance(body, str) or not body.strip():
        return ["正文為空或不是文字"]

    errors = []
    markdown_headings = [
        match.group(1).strip()
        for match in re.finditer(r"(?m)^## (.*)$", body)
    ]
    blocks = body_blocks(item)
    rendered_headings = [block["text"] for block in blocks if block.get("tag") == "h3"]

    if markdown_headings != rendered_headings:
        errors.append("正文二級標題與閱讀輸出不一致")
    if any(not heading for heading in markdown_headings):
        errors.append("正文含空白二級標題")
    if len(markdown_headings) != len(set(markdown_headings)):
        errors.append("正文二級標題重複")

    for index, block in enumerate(blocks):
        if block.get("tag") != "h3":
            continue
        next_heading = next(
            (position for position in range(index + 1, len(blocks))
             if blocks[position].get("tag") == "h3"),
            len(blocks),
        )
        if not any(
            following.get("tag") == "p"
            and (following.get("text", "").strip() or following.get("url"))
            for following in blocks[index + 1:next_heading]
        ):
            errors.append("標題「" + block["text"] + "」沒有正文內容")

    missing = [heading for heading in required_headings if heading not in markdown_headings]
    if missing:
        errors.append("缺少必要段落標題：「" + "」、「".join(missing) + "」")

    if known_source_ids is not None:
        source_ids = item.get("source_ids", [])
        if not isinstance(source_ids, list):
            errors.append("來源 ID 欄位不是清單")
        else:
            unknown = sorted(set(source_ids) - known_source_ids)
            if unknown:
                errors.append("來源登錄缺少 ID：「" + "」、「".join(unknown) + "」")

    return errors
