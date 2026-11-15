"""Compare headings rendered by each reader surface with the official runtime."""

from body_renderer import body_blocks


def runtime_heading_map(items: list[dict]) -> dict[str, list[str]]:
    """Return the ordered h3 text for each official runtime item."""
    return {
        item["id"]: [
            block["text"].strip()
            for block in body_blocks(item)
            if block.get("tag") == "h3"
        ]
        for item in items
    }


def heading_map_issues(
    expected: dict[str, list[str]], actual: dict[str, list[str]]
) -> list[str]:
    """Describe missing articles and ordered heading differences."""
    issues = []
    for item_id in sorted(expected.keys() - actual.keys()):
        issues.append(f"{item_id}: runtime文章未顯示")
    for item_id in sorted(actual.keys() - expected.keys()):
        issues.append(f"{item_id}: 閱讀出口出現非runtime文章")
    for item_id in sorted(expected.keys() & actual.keys()):
        if expected[item_id] != actual[item_id]:
            issues.append(
                f"{item_id}: 小標或順序與runtime不一致；"
                f"預期={expected[item_id]!r}，實際={actual[item_id]!r}"
            )
    return issues


def assert_reader_headings_match_runtime(page, items: list[dict], surface: str) -> None:
    """Fail with article-level detail when a reader surface changes headings."""
    expected = runtime_heading_map(items)
    rows = page.locator("[data-id]").evaluate_all(
        """cards => cards.map(card => [
          card.dataset.id,
          [...card.querySelectorAll('h3')].map(heading => heading.textContent.trim())
        ])"""
    )
    actual = dict(rows)
    issues = heading_map_issues(expected, actual)
    if issues:
        raise AssertionError(f"{surface}的文章小標未與正式runtime一致：" + "；".join(issues[:12]))
