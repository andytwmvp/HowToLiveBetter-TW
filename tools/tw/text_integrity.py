#!/usr/bin/env python3
"""檢查實際文案與 Markdown 圖片邊界；不把整段網址後面的文字列為例外。"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote
import traditionalize as base

# 允許 DOI 路徑中的成對圓括號；排除 Markdown 收尾及中文標點。
URL = re.compile(r'''https?://(?:[^\s<>"'`()\[\]{}，。；：、（）「」『』\\]+|\([^()\s<>]*\))+''')
BADGE = re.compile(r'^\[!\[([^\]]+)\]\((https://img\.shields\.io/badge/[^\s)]+)\)\]\(([^\s)]+)\)$', re.M)


def normalized(text: str, paths: list[str]) -> str:
    protected: list[str] = []
    def keep(value: str) -> str:
        protected.append(value)
        return f'@@TWTEXTGUARD{len(protected)-1}@@'
    text = text.replace(base.NOTICE, keep(base.NOTICE))
    text = URL.sub(lambda m: keep(m.group()), text)
    # 檔案路徑是識別碼；已有重命名對照，不以第二次詞組判斷重寫。
    for path in paths:
        if path in text: text = text.replace(path, keep(path))
    for _ in range(4):
        next_text = base.cc().convert(text)
        if next_text == text: break
        text = next_text
    else: raise RuntimeError('字形正規化未收斂，停止，不提交')
    for i in range(len(protected)-1, -1, -1):
        text = text.replace(f'@@TWTEXTGUARD{i}@@', protected[i])
    return text


def targets():
    return [p for p in base.current_files() if Path(p).suffix in base.SUFFIXES and not p.startswith(('tools/tw/', '.github/workflows/')) and not p.endswith('package-lock.json')]


def protected_paths():
    return sorted({p for p in base.current_files() if any(ord(c)>127 for c in p)}, key=len, reverse=True)


def check():
    # 日常驗證委派給目前政策；不再使用已退休遷移的全檔差異比較。
    from ci_language_policy import check as current_check
    current_check()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true'); parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not (args.apply or args.check): parser.error('請指定 --apply 或 --check')
    if args.apply: parser.error('--apply 已退休；不可覆寫後續連結與內容')
    if args.check: check()
