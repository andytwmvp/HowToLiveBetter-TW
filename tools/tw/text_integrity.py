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


def apply():
    assert base.git('branch', '--show-current').decode().strip() == base.BRANCH
    assert base.git('remote', 'get-url', 'origin').decode().strip().removesuffix('.git') == 'https://github.com/' + base.REPO
    # 修復先前把 Markdown 的 )]( 編進 Shields URL 的六個徽章。
    text = base.read('README.md')
    lines = text.splitlines()
    repaired = 0
    for i, line in enumerate(lines):
        if line.startswith('[![') and '%29%5D%28' in line:
            left, right = line.split('%29%5D%28', 1)
            assert right.endswith('%29'), '徽章結尾不符，停止'
            lines[i] = left + ')](' + unquote(right[:-3]) + ')'
            repaired += 1
    text = '\n'.join(lines) + '\n'
    # 閱讀入口留在繁體分支，不把讀者送回原作的簡體與廣告頁面。
    text = text.replace('](https://eternity4719.github.io/HowToLiveBetter/selfcheck.html)', '](selfcheck.html)')
    text = text.replace('](https://eternity4719.github.io/HowToLiveBetter/)', '](index.html)')
    # 尚未出版的檔案指向建置說明，不宣稱已存在下載版。
    text = re.sub(r'\[離線單文件 HTML\]\(https://github\.com/eternity4719/HowToLiveBetter/releases/download/epub-latest/HowToLiveBetter\.html\)', '[繁體工作稿離線建置說明](locales/zh-TW/README.md)', text)
    base.write('README.md', text)
    changed = []
    paths = protected_paths()
    for path in targets():
        before = base.read(path)
        after = normalized(before, paths)
        assert Counter(URL.findall(before)) == Counter(URL.findall(after)), f'來源網址變動：{path}'
        assert re.findall(r'\d+', before) == re.findall(r'\d+', after), f'數字變動：{path}'
        if after != before:
            base.write(path, after); changed.append(path)
    # 原始來源驗證也使用正確邊界，不能把 URL 後的中文敘述算成 URL。
    code = base.read('tools/tw/traditionalize.py')
    before_line = next(line for line in code.splitlines() if line.startswith('URL = re.compile('))
    code = code.replace(before_line, 'URL = re.compile(' + repr(URL.pattern) + ')')
    base.write('tools/tw/traditionalize.py', code)
    base.dump('localization/text-integrity-report.json', {'badge_markup_repaired': repaired, 'additional_normalized_files': len(changed), 'files': changed, 'source_urls_and_numbers_preserved': True, 'note': '修正網址後方漏轉文字、Markdown 圖片語法及繁體異體字正規化；仍未完成逐句人工精校。'})
    print(f'修復 {repaired} 個徽章語法；正規化 {len(changed)} 份文件。')


def check():
    paths = protected_paths(); errors = []
    for path in targets():
        text = base.read(path)
        if normalized(text, paths) != text: errors.append(path)
    if errors: raise RuntimeError('仍有待正規化文案：' + ', '.join(errors))
    md = base.read('README.md')
    badges = BADGE.findall(md)
    assert len(badges) == 6, f'可解析徽章數不是 6：{len(badges)}'
    assert '%29%5D%28' not in md, 'Markdown 邊界仍被誤編碼'
    for label, url, dest in badges:
        assert not re.search(r'[\[\]()]', unquote(url)), '圖片 URL 混入 Markdown 邊界'
        assert base.cc().convert(label) == label
        if not dest.startswith(('https:', 'http:', '#')):
            assert (base.ROOT / unquote(dest)).exists(), dest
    # 真實網址必須能保留 DOI 圓括號，且不得吞入連結後方的中文文案。
    fixture = '[閱讀](https://example.org/a)：\u8fd9\u4e2a\u9875\u9762'
    assert URL.findall(fixture) == ['https://example.org/a']
    assert URL.findall('<https://doi.org/10.1016/S0140-6736(20)30367-6>') == ['https://doi.org/10.1016/S0140-6736(20)30367-6']
    assert normalized(fixture, []) != fixture
    print(f'PASS：{len(targets())} 份文案、6 個 Markdown 圖片徽章、網址邊界與 DOI 括號回歸測試。')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true'); parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not (args.apply or args.check): parser.error('請指定 --apply 或 --check')
    if args.apply: apply()
    if args.check: check()
