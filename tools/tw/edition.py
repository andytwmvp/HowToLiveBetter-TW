#!/usr/bin/env python3
"""由單一臺灣已核對目錄匯出HTML、EPUB及Anki；不默默取用草稿或原作。"""
from __future__ import annotations
import argparse
from contextlib import closing
from body_renderer import body_html
import hashlib
import html
import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from review_contract import ROOT, validate_runtime, publication_report
from content_validation import validate_runtime_data


def data_json(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def build_html(output: Path, data: dict) -> None:
    validate_runtime_data(data)
    page = (ROOT/'index.html').read_text(encoding='utf-8')
    script = (ROOT/'assets/tw-runtime.js').read_text(encoding='utf-8')
    payload = data_json(data).replace('<', '\\u003c')
    page = page.replace('<script src="assets/tw-runtime.js"></script>', f'<script>window.__TW_RUNTIME__={payload};</script>\n<script>{script}</script>')
    page = page.replace('data-view="reader"', 'data-view="selfcheck"')
    repo = 'https://github.com/andytwmvp/HowToLiveBetter-TW/blob/main/'
    for path in ('source.html','ATTRIBUTION.md','PROJECT_STATE.md'):
        page = page.replace(f'href="{path}"', f'href="{repo}{path}"')
    for path in ('index.html','selfcheck.html'):
        page = page.replace(f'href="{path}"', 'href="#cards"')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding='utf-8')


def refs(entry: dict, data: dict) -> list[dict]:
    mapping = {s['id']: s for s in data['sources']}
    reader_titles = data.get('reader_source_titles', {})
    result = []
    for key in entry['source_ids']:
        source = mapping[key]
        if key in reader_titles:
            source = {**source, 'title': reader_titles[key]}
        result.append(source)
    return result


def freshness_copy(entry: dict, today: str | None = None) -> str:
    """Return reader-facing confirmation dates and a current-date reminder."""
    if today is None:
        today = datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
    copy = f"內容最後確認日期：{entry['reviewed_at']}；建議再次確認日期：{entry['review_due_at']}。"
    if today >= entry['review_due_at']:
        copy += '已到再次確認日期，採取行動前請向主管機關或服務單位確認最新資訊。'
    else:
        copy += '到建議再次確認日期後，採取行動前請向主管機關或服務單位確認最新資訊。'
    return copy


def build_epub(output: Path, data: dict) -> None:
    validate_runtime_data(data)
    esc = html.escape
    parts = [f'<h1>{esc(data["title"])}</h1><p>{esc(data["scope"])}</p>']
    for e in data['items']:
        links = '；'.join(f'<a href="{esc(s["url"],quote=True)}">{esc(s["title"])}</a>' for s in refs(e,data))
        parts.append(f'<section id="{e["id"]}"><h2>{esc(e["title"])}</h2>{body_html(e)}<p>{esc(e["limits"])}</p><p class="meta">{esc(freshness_copy(e))}</p><p>{links}</p></section>')
    parts.append('<p>本指南改寫自《HowToLiveBetter》，原作者為 eternity4719 與貢獻者，依 CC BY 4.0 授權分享。原作署名與修改說明見 <a href="https://github.com/andytwmvp/HowToLiveBetter-TW/blob/main/ATTRIBUTION.md">原作署名與授權</a>；原作者不代表本臺灣版背書。</p>')
    document = '<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" lang="zh-TW" xml:lang="zh-TW"><head><title>'+esc(data['title'])+'</title><meta charset="utf-8"/></head><body>'+''.join(parts)+'</body></html>'
    nav = '<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-TW"><head><title>目錄</title></head><body><nav epub:type="toc" id="toc"><h1>目錄</h1><ol>'+''.join(f'<li><a href="content.xhtml#{e["id"]}">{esc(e["title"])}</a></li>' for e in data['items'])+'</ol></nav></body></html>'
    uid = 'urn:sha256:' + hashlib.sha256(data_json(data).encode()).hexdigest()
    modified = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    opf = f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">{uid}</dc:identifier><dc:title>{esc(data['title'])}</dc:title><dc:language>zh-TW</dc:language><dc:description>{esc(data['scope'])}</dc:description><dc:rights>CC BY 4.0；臺灣版改寫，原作署名與修改說明見 ATTRIBUTION.md</dc:rights><meta property="dcterms:modified">{modified}</meta></metadata><manifest><item id="content" href="content.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="content"/></spine></package>'''
    container = '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
        for path,value in [('META-INF/container.xml',container),('OEBPS/content.opf',opf),('OEBPS/content.xhtml',document),('OEBPS/nav.xhtml',nav)]: z.writestr(path,value)


SCHEMA = '''
CREATE TABLE col (id integer primary key, crt integer not null, mod integer not null, scm integer not null, ver integer not null, dty integer not null, usn integer not null, ls integer not null, conf text not null, models text not null, decks text not null, dconf text not null, tags text not null);
CREATE TABLE notes (id integer primary key, guid text not null, mid integer not null, mod integer not null, usn integer not null, tags text not null, flds text not null, sfld integer not null, csum integer not null, flags integer not null, data text not null);
CREATE TABLE cards (id integer primary key, nid integer not null, did integer not null, ord integer not null, mod integer not null, usn integer not null, type integer not null, queue integer not null, due integer not null, ivl integer not null, factor integer not null, reps integer not null, lapses integer not null, left integer not null, odue integer not null, odid integer not null, flags integer not null, data text not null);
CREATE TABLE revlog (id integer primary key, cid integer not null, usn integer not null, ease integer not null, ivl integer not null, lastIvl integer not null, factor integer not null, time integer not null, type integer not null);
CREATE TABLE graves (usn integer not null, oid integer not null, type integer not null);
CREATE INDEX ix_notes_usn on notes (usn); CREATE INDEX ix_cards_usn on cards (usn); CREATE INDEX ix_revlog_usn on revlog (usn); CREATE INDEX ix_cards_nid on cards (nid); CREATE INDEX ix_cards_sched on cards (did,queue,due); CREATE INDEX ix_revlog_cid on revlog (cid); CREATE INDEX ix_notes_csum on notes (csum);
'''


def build_anki(output: Path, data: dict) -> None:
    validate_runtime_data(data)
    now = int(datetime.now(timezone.utc).timestamp()); mid, did = 1792000000001,1792000000100
    model = {'id':mid,'name':'臺灣生活指南（生活資訊卡）','type':0,'mod':now,'usn':-1,'sortf':0,'did':did,'tmpls':[{'name':'生活資訊','ord':0,'qfmt':'{{題目}}','afmt':'{{FrontSide}}<hr id="answer">{{內容}}<br>{{來源}}','did':None,'bqfmt':'','bafmt':''}],'flds':[{'name':name,'ord':i,'sticky':False,'rtl':False,'font':'Arial','size':20,'media':[]} for i,name in enumerate(['題目','內容','來源'])],'css':'.card{font-family:system-ui,sans-serif;font-size:18px;line-height:1.8;text-align:left}','latexPre':'','latexPost':'','latexsvg':False,'req':[[0,'any',[0]]],'tags':[],'vers':[]}
    def deck(key, name):
        return {'id':key,'name':name,'desc':data['scope'],'mod':now,'usn':-1,'dyn':0,'conf':1,'collapsed':False,'browserCollapsed':False,'newToday':[0,0],'revToday':[0,0],'lrnToday':[0,0],'timeToday':[0,0],'extendNew':0,'extendRev':0}
    dconf = {1:{'id':1,'name':'Default','mod':0,'usn':0,'maxTaken':60,'autoplay':True,'timer':0,'replayq':True,'dyn':False,'new':{'delays':[1,10],'ints':[1,4,7],'initialFactor':2500,'order':1,'perDay':20,'bury':True,'separate':True},'rev':{'perDay':200,'ease4':1.3,'fuzz':.05,'ivlFct':1,'maxIvl':36500,'minSpace':1,'bury':True},'lapse':{'delays':[10],'mult':0,'minInt':1,'leechFails':8,'leechAction':0}}}
    conf = {'activeDecks':[did],'curDeck':did,'curModel':str(mid),'newSpread':0,'collapseTime':1200,'timeLim':0,'estTimes':True,'dueCounts':True,'nextPos':len(data['items'])+1,'sortType':'noteFld','sortBackwards':False,'addToCur':True}
    with tempfile.TemporaryDirectory(prefix='tw-nav-anki-') as folder:
        db_path = Path(folder)/'collection.anki2'
        with closing(sqlite3.connect(db_path)) as db, db:
            db.executescript(SCHEMA)
            db.execute('INSERT INTO col VALUES (1,?,?,?,?,0,0,0,?,?,?,?,?)',(now,now*1000,now*1000,11,data_json(conf),data_json({mid:model}),data_json({1:deck(1,'Default'),did:deck(did,data['title'])}),data_json(dconf),'{}'))
            for order,e in enumerate(data['items']):
                identity = int.from_bytes(hashlib.sha256(e['id'].encode()).digest()[:6],'big')
                nid = 1792100000000 + identity
                body = body_html(e)+'<br>'+html.escape(e['limits'])+'<br><small>'+html.escape(freshness_copy(e))+'</small>'
                links = '<br>'.join(f'<a href="{html.escape(s["url"],quote=True)}">{html.escape(s["title"])}</a>' for s in refs(e,data))
                flds = '\x1f'.join([html.escape(e['title']),body,links])
                checksum = int(hashlib.sha1(e['title'].encode()).hexdigest()[:8],16)
                db.execute('INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,0,?)',(nid,'hltb-tw-'+e['id'],mid,now,-1,' 臺灣 生活指引 ',flds,e['title'],checksum,e['id']))
                db.execute('INSERT INTO cards VALUES (?,?,?,0,?,-1,0,0,?,0,0,0,0,0,0,0,0,?)',(nid+1,nid,did,now,order,''))
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise RuntimeError('Anki資料庫完整性失敗')
        output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(db_path,'collection.anki2');z.writestr('media','{}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format',choices=['html','epub','anki']);parser.add_argument('--output',type=Path)
    parser.add_argument('--list',action='store_true');parser.add_argument('--id');parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args();data=validate_runtime()
    if args.require_complete and not publication_report()['publication_ready']: raise SystemExit('全書正文、來源審閱與閱讀整合尚未完成，拒絕正式全書輸出。')
    if args.list: print(json.dumps(data,ensure_ascii=False,indent=2));return
    if args.id:
        item=next((e for e in data['items'] if e['id']==args.id),None)
        if item is None: raise SystemExit('沒有此已核對條目；不使用草稿或原作替代。')
        print(json.dumps({'item':item,'sources':refs(item,data)},ensure_ascii=False,indent=2));return
    if not args.format or not args.output: parser.error('請指定格式與輸出路徑，或使用--list／--id')
    output=args.output if args.output.is_absolute() else ROOT/args.output
    {'html':build_html,'epub':build_epub,'anki':build_anki}[args.format](output,data)
    print(f'PASS：{output}；{len(data["items"])}項臺灣來源核對內容，非765條全書定稿。')

if __name__=='__main__':main()
