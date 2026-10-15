#!/usr/bin/env python3
"""唯讀驗證自有repo導覽、上游例外與本地目的地；不呼叫外部網站。"""
from __future__ import annotations
import argparse
from collections import Counter
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit
ROOT = Path(__file__).resolve().parents[2]
CONFIG = 'localization/link-policy.json'
SUFFIXES = {'.md','.html','.js','.mjs','.py','.yml','.yaml','.json','.xml','.txt','.typ','.svg'}
ABSOLUTE = re.compile(r'''https?://(?:[^\s<>"'`()\[\]{}，。；：、（）「」『』\\]+|\([^()\s<>]*\))+''')
MARKDOWN = re.compile(r'!?\[[^\]\n]*\]\(([^\s)]+)\)')

class HtmlLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'): self.ids.add(a['id'])
        for key in ('href','src'):
            if key in a: self.links.append(a[key])

def read(path,root=ROOT): return (root/path).read_text(encoding='utf-8')

def tracked(root=ROOT):
    output=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root)
    return sorted({p for p in output.decode().split('\0') if p and (root/p).is_file()})

def stable_anchors(path:Path):
    text=path.read_text(encoding='utf-8');parser=HtmlLinks();parser.feed(text);anchors=parser.ids
    counts=Counter()
    if path.suffix=='.md':
        # 本repo導覽標題不含內嵌HTML；明確id也在上方解析。
        for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$',text,re.M):
            slug=''.join(c for c in heading.lower() if c.isalnum() or c in '-_ ').replace(' ','-')
            suffix=counts[slug];counts[slug]+=1;anchors.add(slug+(f'-{suffix}' if suffix else ''))
    return anchors

def local_target(value:str,source:str,root=ROOT):
    value=unescape(value).strip('<>')
    if any(token in value for token in ('${','{{','<','\\')): return None
    parts=urlsplit(value)
    if parts.scheme or parts.netloc:return None
    decoded=unquote(parts.path)
    target=(root/decoded.lstrip('/') if decoded.startswith('/') else root/Path(source).parent/decoded).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('相對路徑越過儲存庫：'+value)
    if not target.exists():raise ValueError('目的地不存在：'+value)
    if parts.fragment and target.suffix=='.md' and unquote(parts.fragment) not in stable_anchors(target):
        raise ValueError('Markdown錨點不存在：'+value)
    return target

def upstream_kind(value:str,policy:dict):
    normalized=unquote(unquote(value)).replace('\\/','/')
    upstream=policy['upstream_repository']
    parsed=urlsplit(normalized)
    host=parsed.hostname or ''
    path=parsed.path.lstrip('/')
    if host==policy['upstream_site_host']:return True
    if host in {'github.com','raw.githubusercontent.com'} and (path==upstream or path.startswith(upstream+'/') or path==upstream+'.git'):return True
    if host=='api.github.com' and path.startswith('repos/'+upstream+'/'):return True
    return False

def own_target(value:str,policy:dict,root=ROOT):
    u=urlsplit(unescape(value));name=policy['repository']
    if u.hostname==policy['unpublished_site_host']:raise ValueError('尚未部署網站，不可使用猜測的Pages網址：'+value)
    if u.hostname not in {'github.com','raw.githubusercontent.com'}:return None
    path=unquote(u.path).strip('/')
    if not (path==name or path==name+'.git' or path.startswith(name+'/')):return None
    rest=path[len(name):].lstrip('/')
    if not rest or rest=='.git':return None
    if rest.startswith('releases/download/'):
        raise ValueError('repo沒有已發布下載資產：'+value)
    if rest.startswith('issues') and not policy['issues_enabled']:
        raise ValueError('Issues未啟用，應指向SUPPORT.md：'+value)
    if u.hostname=='raw.githubusercontent.com':
        ref,sep,destination=rest.partition('/')
        kind='blob'
    elif rest.startswith(('blob/','tree/')):
        kind,rest=rest.split('/',1);ref,sep,destination=rest.partition('/')
    else:
        return None
    if not sep or not destination:raise ValueError('repo檔案連結格式不完整：'+value)
    if any(t in destination for t in ('${','{','}')):return None
    if ref=='main':
        target=local_target(destination,'README.md',root)
        if target is None:raise ValueError('不合法的repo目標')
        if kind=='blob' and not target.is_file():raise ValueError('blob目標不是檔案：'+value)
        if kind=='tree' and not target.is_dir():raise ValueError('tree目標不是目錄：'+value)
        if u.fragment and target.suffix=='.md' and unquote(u.fragment) not in stable_anchors(target):
            raise ValueError('repo Markdown錨點不存在：'+value)
        return target
    if re.fullmatch('[0-9a-f]{40}',ref):
        check=subprocess.run(['git','cat-file','-e',f'{ref}:{destination}'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if check.returncode:raise ValueError('固定歷史版本的目標不存在：'+value)
        return None
    raise ValueError('運作入口不可綁在舊工作分支：'+value)

def audit(root=ROOT):
    policy=json.loads(read(CONFIG,root));counts=Counter();problems=[];kept=[]
    exceptions={(e['path'],e['url']):e for e in policy['upstream_exceptions']}
    # 例外必須有理由且指向具體檔案，不允許目錄級白名單。
    for (path,url),rule in exceptions.items():
        if not rule.get('reason') or not (root/path).is_file() or not upstream_kind(url,policy):
            raise ValueError('上游例外格式錯誤')
    files=[p for p in tracked(root) if Path(p).suffix in SUFFIXES]
    for path in files:
        text=read(path,root)
        # 政策自己保存待比對的來源網址，單元測試用負向案例，不是實際連結入口。
        if path==CONFIG or path.startswith('tools/tw/tests/'):continue
        text_for_scan=text.replace('\\/','/')
        urls=ABSOLUTE.findall(text_for_scan)
        for value in urls:
            counts['absolute_occurrences']+=1
            if upstream_kind(value,policy):
                rule=exceptions.get((path,value))
                if not rule:problems.append(f'{path}:未核准上游連結 {value}')
                else:
                    counts[(path,value)]+=1
                    kept.append({'path':path,'url':value,'reason':rule['reason']})
                continue
            # 僅明確的程式常數前綴例外；真正href/src仍在下方完整驗證。
            if (path,value) in {(row['path'],row['url']) for row in policy.get('code_url_prefixes',[])}:
                counts['code_url_prefixes']+=1
                continue
            try:
                if own_target(value,policy,root) is not None:counts['repo_file_targets']+=1
            except ValueError as e:problems.append(f'{path}:{e}')
        # 防止用非HTTP git transport繞過上游檢查；純署名/來源ID不算操作連結。
        if ('git@github.com:'+policy['upstream_repository']) in text or ('git://github.com/'+policy['upstream_repository']) in text:
            problems.append(path+':不得使用上游Git操作端點')
    for key,rule in exceptions.items():
        if counts[key]!=rule.get('occurrences',1):problems.append(f'{key[0]}:必要原作來源連結遺失或數量異常')
    for path in policy['local_navigation_files']:
        text=read(path,root);parser=HtmlLinks();parser.feed(text)
        links=parser.links+(MARKDOWN.findall(text) if path.endswith('.md') else [])
        for value in links:
            try:
                own_target(value,policy,root)
                if local_target(value,path,root) is not None:counts['local_navigation_targets']+=1
            except ValueError as e:problems.append(f'{path}:{e}')
    if problems:raise ValueError('\n'.join(sorted(set(problems))))
    return {'scope':'上游連結例外、自有repo目標與本地導覽；不表示所有外部研究網址可連線或內容已查核',
            'scanned_text_files':len(files),'absolute_url_occurrences':counts['absolute_occurrences'],
            'validated_repo_file_links':counts['repo_file_targets'],'validated_local_navigation_links':counts['local_navigation_targets'],
            'retained_upstream_links':kept,'issues_enabled':policy['issues_enabled'],'public_site':None,
            'metadata_homepage_update':'pending_repository_settings_access','errors':[]}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path);args=parser.parse_args()
    result=audit();print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
