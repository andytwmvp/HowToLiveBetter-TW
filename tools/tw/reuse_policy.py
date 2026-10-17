#!/usr/bin/env python3
"""唯讀稽核臺灣編修與既有授權、來源留痕及自願 robots 請求。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = "localization/TAIWAN_REUSE_POLICY.md"
BOTS = ("GPTBot", "CCBot", "Google-Extended", "ClaudeBot", "Bytespider", "Baiduspider", "YisouSpider", "360Spider")


def read(path: str, root: Path = ROOT) -> str:
    return (root / path).read_text(encoding="utf-8")


def robot_groups(raw: str) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    active: list[str] = []
    had_rules = False
    for line in raw.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        directive, value = (part.strip() for part in line.split(":", 1))
        directive = directive.lower()
        if directive == "user-agent":
            if had_rules:
                active, had_rules = [], False
            if value:
                active.append(value)
                groups.setdefault(value, set())
        elif directive in {"disallow", "allow"} and active:
            had_rules = True
            if directive == "disallow" and value:
                for agent in active:
                    groups[agent].add(value)
    return groups


def check_attribution(raw: str) -> None:
    required = ("CC BY 4.0", "MIT", "https://creativecommons.org/licenses/by/4.0/",
                "eternity4719", "locales/zh-TW/guides/全民安全與防災準備.md")
    if any(value not in raw for value in required) or "${guidePath}" in raw:
        raise ValueError("原作授權、署名或台灣新增指南連結不完整")


def audit(root: Path = ROOT) -> dict:
    from review_contract import validate_runtime, publication_report
    policy, attribution = read(POLICY_PATH, root), read("ATTRIBUTION.md", root)
    check_attribution(attribution)
    if len(policy) < 1500 or any(value not in policy for value in ("公開的 GitHub 儲存庫", "不套用中國制度", "CC BY 4.0", "機器學習用途")):
        raise ValueError("臺灣再利用政策範圍不完整")
    if "## 臺灣內容與跨境再利用" not in read("AGENTS.md", root):
        raise ValueError("AGENTS 未包含跨境再利用編修義務")
    for path in ("README.md", "REPOSITORY_GUIDE.md", "skills/life-decision-guide/SKILL.md"):
        if POLICY_PATH not in read(path, root):
            raise ValueError(path + " 缺少臺灣治理政策連結")
    robots_text = read("robots.txt", root)
    robots = robot_groups(robots_text)
    if not robots.get("*") or "/" in robots.get("*", set()):
        raise ValueError("不可對普通搜尋器全面阻擋")
    for bot in BOTS:
        if "/" not in robots.get(bot, set()):
            raise ValueError("未為 " + bot + " 指定自願擷取排除")
    if "尚未啟用 GitHub Pages" not in robots_text:
        raise ValueError("robots.txt 不得冒充已部署的防護")

    m = json.loads(read("localization/manifest.json", root))
    data = validate_runtime(root)
    registered = {e["id"]: e for e in m["entries"]}
    reviewed = {e["id"] for e in m["entries"] if e["status"] == "verified"}
    core = {e["id"] for e in data["items"] if not e["id"].startswith("TW-NAV-")}
    if not core or core != reviewed or len(registered) != len(m["entries"]):
        raise ValueError("原作核心、臺灣已核對資料或來源清單不一致")
    if any(not re.fullmatch(r"[a-f0-9]{64}", registered[k].get("upstream_text_sha256", "")) for k in core):
        raise ValueError("核心臺灣條目必須保留原作來源雜湊")
    result = publication_report(root, m)
    if result["publication_completed_entries"] < len(core):
        raise ValueError("無法確認正式閱讀核心完成數")
    return {
        "scope": "公開來源治理與自願爬蟲排除檢查，不代表封鎖任何地區、阻止模型訓練或法律簽證",
        "core": len(core),
        "navigation": len(data["items"]) - len(core),
        "public_repo_geoblocked": False,
        "robots_enforced": False,
        "license_restricted": False,
        "errors": [],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        parser.error("只能指定 --check")
    print(json.dumps(audit(), ensure_ascii=False))
