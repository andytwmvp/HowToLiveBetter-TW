#!/usr/bin/env python3
"""舊版初始化已退休；不得再以簡體模板覆寫繁體中文工作稿。"""
import subprocess
import sys
from pathlib import Path
if '--apply' in sys.argv:
    raise SystemExit('初始化已完成。請使用目前的協作規則與繁體中文工作分支。')
if '--check' not in sys.argv:
    raise SystemExit('請指定 --check；此相容入口僅提供唯讀檢查。')
raise SystemExit(subprocess.call([sys.executable, str(Path(__file__).with_name('traditionalize.py')), '--check']))
