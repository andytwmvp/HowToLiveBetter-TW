#!/usr/bin/env python3
"""一次性修正本fork匯出識別；逐檔核對前後雜湊，僅限本次隔離分支。"""
from pathlib import Path
import hashlib
import subprocess

ROOT=Path(__file__).resolve().parents[2]
EXPECTED={
 'tools/anki/source-preview.mjs':('b9eca4aa0d6a54ab8e5c607683604ef9cb8a8f4cdbf4de612499fc711e80a82a','56ec4dd9ed4fcdbe63dadc0ce77b2b0694b3574c9c1b7d7017b19fcd2f495b55'),
 'tools/epub/source-preview.mjs':('35df777847978dd668b487778c04b48e3fd41d1b96d84d773b158cfcb5bc13c5','34da794f773116305c7b02bc040cc9c8b1086307b90cb8cb2ef829f820e2a949')
}
def digest(value):return hashlib.sha256(value).hexdigest()
def replace(text,old,new):
    if old not in text:raise RuntimeError('已審查文字不存在：'+old)
    return text.replace(old,new)

def main():
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    origin=subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT,text=True).strip().removesuffix('.git')
    if branch!='fix/export-integrity-20261015' or origin!='https://github.com/andytwmvp/HowToLiveBetter-TW':
        raise RuntimeError('只能套用於授權fork的本次隔離分支')
    prepared=[]
    for name,(before_sha,after_sha) in EXPECTED.items():
        path=ROOT/name;raw=path.read_bytes()
        if digest(raw)==after_sha:continue
        if digest(raw)!=before_sha:raise RuntimeError('來源有其他變更，停止：'+name)
        text=raw.decode('utf-8')
        kind=name.split('/')[1];ext='apkg' if kind=='anki' else 'epub'
        text=replace(text,f'// 用法：node tools/{kind}/build.mjs [輸出路徑]   預設輸出 dist/HowToLiveBetter.{ext}',f'// 用法：node tools/{kind}/build.mjs --source-preview [輸出路徑]；此模組只建立原作繁體來源預覽。')
        text=replace(text,f"process.argv[2] ?? 'dist/HowToLiveBetter.{ext}'",f"process.argv[2] ?? 'dist/HowToLiveBetter-source-preview.{ext}'")
        if kind=='anki':
            start=text.index('// 重新導入時');end=text.index('import { writeFileSync')
            text=text[:start]+'// 本fork來源預覽採獨立且穩定的牌組／筆記識別碼，不與原作或臺灣導航共用。\n// 首次改用新版會形成獨立牌組，不會自動遷移或刪除先前版本的學習紀錄。\n'+text[end:]
            replacements=[
              ('1759900000001','1792060000001'),('1759900000100','1792060000100'),('1759900100000','1792060100000'),('1759900200000','1792060200000'),
              ('`hltb-${s.sec}-${e.n}`','`hltb-tw-source-v1-${s.sec}-${e.n}`'),
              ('（北京時間）','（臺北時間）'),('各版本 Anki 都能導入','用戶端匯入相容性另行驗證'),('再給一個線上版連結。','再附本repo來源章節連結。'),
              ('const deckName = s => `${TITLE}::','const deckName = s => `${TITLE}｜原作繁體來源預覽::'),
              ('name: `${TITLE}（問答卡）`','name: `${TITLE}（本repo原作來源卡）`'),
              ('[ROOT_DECK_ID]: deck(ROOT_DECK_ID, TITLE, rootDesc)','[ROOT_DECK_ID]: deck(ROOT_DECK_ID, `${TITLE}｜原作繁體來源預覽`, rootDesc)'),
              ('const rootDesc = `《${TITLE}》全書條目','const rootDesc = `《${TITLE}》原作繁體來源預覽（非臺灣制度定稿），全書條目'),
              ("+ '重新下載導入會更新卡片內容，複習記錄保留。';","+ '本fork來源卡採獨立識別碼；第一次匯入新版不自動遷移舊版或原作的學習紀錄。請先備份，再依Anki匯入選項處理。';")
            ]
            for old,new in replacements:text=replace(text,old,new)
            for field in ('QFMT','AFMT'):
                text=replace(text,f'const {field} = `<div class="sec">',f'const {field} = `<div class="hint">原作繁體來源預覽；非臺灣制度定稿。</div>\n<div class="sec">')
        else:
            text=replace(text,'urn:uuid:5c0c1c0e-6a5c-4d2b-9b1e-7d1f0a4e8c31','urn:uuid:cee8db2b-5e19-59ea-ad9f-b3f59b53f469')
            text=replace(text,'<dc:title>${TITLE}</dc:title>','<dc:title>${TITLE}（本repo原作繁體來源預覽）</dc:title>')
            text=replace(text,'<dc:creator>eternity4719</dc:creator>','<dc:creator>eternity4719</dc:creator>\n<dc:contributor>andytwmvp/HowToLiveBetter-TW（繁體來源預覽編修）</dc:contributor>')
        updated=text.encode('utf-8')
        if digest(updated)!=after_sha:raise RuntimeError('修正结果與已測試版本不同：'+name)
        prepared.append((path,updated))
    for path,updated in prepared:path.write_bytes(updated)
    print('PASS：兩個來源匯出模組與已測試前後雜湊一致；沒有改動使用者牌組或上游。')
if __name__=='__main__':main()
