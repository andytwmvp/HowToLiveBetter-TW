// 原作統計只同步原作來源閱讀器，不放在臺灣版 README。
// --check 唯讀；--no-screenshot 同步文字但不重新產生圖片。
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdtempSync, rmSync, statSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { COST_W as W, ratioOf } from './lib/book.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const CHECK=process.argv.includes('--check');
const read=f=>readFileSync(join(ROOT,f),'utf8');
const indexText=read('source.html');
const COST_W_LINE="const COST_W = { money:{'0':0,'少':1,'多':2}, time:{'少':0,'中':1,'多':2}, will:{'否':0,'些':1,'是':2} };";
const RATIO_LINE="e.ratio = e.level === '大' ? (e.cs === 0 ? '極高' : (e.cs <= 2 ? '高' : '一般'))";
if(!indexText.includes(COST_W_LINE))throw Error('source.html成本權重與共用工具不同步');
if(!indexText.includes(RATIO_LINE))throw Error('source.html分級規則與共用工具不同步');
const bookFiles=readdirSync(join(ROOT,'book')).filter(f=>f.endsWith('.md')).sort();
const sections=bookFiles.length;
let entries=0,dispute=0,todo=0,links=0;
const grade={A:0,B:0,C:0};
const ratio={'極高':0,'高':0,'一般':0};
const WHO=new Set(['懷孕','嬰幼兒','孩子','老人','35歲','60歲','女性']);
const badWho=[];
for(const f of bookFiles){
  for(const line of read(join('book',f)).split(/\r?\n/)){
    if(line.startsWith('### '))entries++;
    const g=line.match(/^- 證據等級：([ABC])/);if(g)grade[g[1]]++;
    if(line.startsWith('- 備註：爭議'))dispute++;
    if(/待核實|TODO/.test(line))todo++;
    if(/^- (來源|備註)：/.test(line))links+=(line.match(/https?:\/\//g)??[]).length;
    const t=line.match(/<!--\s*成本標籤:\s*錢=(\S+)\s+時間=(\S+)\s+毅力=(\S+)\s+收益=(\S+)\s+口徑=/);
    if(t)ratio[ratioOf(W.money[t[1]]+W.time[t[2]]+W.will[t[3]],t[4])]++;
    const w=line.match(/<!--\s*成本標籤:.*\s人群=(\S+)/);
    if(w)for(const v of w[1].split(/[,+]/))if(!WHO.has(v))badWho.push(`${f}：${v}`);
  }
}
if(badWho.length){console.error('不認識的適用對象標籤：'+badWho.join('、'));process.exitCode=1;}
const tagged=ratio['極高']+ratio['高']+ratio['一般'];
if(tagged!==entries)console.warn('成本標籤數與條目數不同');
if(grade.A+grade.B+grade.C!==entries)console.warn('證據等級數與條目數不同');
const ORDER=['極高','高','一般'];const pct={},rem={};
for(const k of ORDER){const exact=ratio[k]*100/entries;pct[k]=Math.floor(exact);rem[k]=exact-pct[k];}
const short=100-ORDER.reduce((s,k)=>s+pct[k],0);
for(const k of [...ORDER].sort((a,b)=>rem[b]-rem[a]).slice(0,Math.max(short,0)))pct[k]++;
console.log(`原作${entries}條／${sections}章；A ${grade.A}、B ${grade.B}、C ${grade.C}；爭議${dispute}、待核${todo}、來源連結${links}`);
const EDITS=[
  ['source.html','來源描述',/(\d+) 條建議/g,`${entries} 條建議`],
  ['source.html','頁頭條目數',/原作 (\d+) 章、(\d+) 條建議/g,`原作 ${sections} 章、${entries} 條建議`],
  ['source.html','頁腳文件數',/資料夾下的 (\d+) 個檔案/g,`資料夾下的 ${sections} 個檔案`],
];
const texts=new Map(),stale=[];
for(const [file,label,pattern,repl] of EDITS){
  const text=texts.get(file)??read(file);const found=[...text.matchAll(pattern)];
  if(!found.length)throw Error(`${file}缺少${label}標記`);
  const updated=text.replace(pattern,()=>repl);texts.set(file,updated);
  if(updated!==text)stale.push(`${file} ${label}`);
}
if(CHECK){
  if(!stale.length&&!badWho.length){console.log('PASS：原作來源閱讀器統計一致。');process.exit(0);}
  console.error('統計過時或標籤錯誤：'+stale.join('、'));process.exit(1);
}
for(const [file,text] of texts)if(text!==read(file))writeFileSync(join(ROOT,file),text);
const runTool=name=>spawnSync(process.execPath,[join(ROOT,'tools',name)],{stdio:'inherit'}).status;
if(runTool('check-refs.mjs')!==0)throw Error('交叉引用檢查失敗');
if(runTool('check-plain.mjs')!==0)console.warn('文字易讀性檢查有待修正項目');
if(process.argv.includes('--no-screenshot'))process.exit(0);
const paths=[process.env.CHROME,'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe','C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium','/usr/bin/chromium-browser'];
const chrome=paths.find(p=>p&&existsSync(p));if(!chrome)throw Error('找不到Chrome，請設定CHROME或使用--no-screenshot');
const profile=mkdtempSync(join(tmpdir(),'og-shot-'));const target=join(ROOT,'og.png'),startedAt=Date.now();
try {
  const result=spawnSync(chrome,['--headless','--disable-gpu','--hide-scrollbars','--force-device-scale-factor=1','--window-size=1200,630',`--user-data-dir=${profile}`,`--screenshot=${target}`,pathToFileURL(join(ROOT,'tools','og.html')).href],{stdio:'ignore'});
  if(result.error||result.status!==0)throw Error('封面重新產生失敗');
} finally {rmSync(profile,{recursive:true,force:true});}
const png=statSync(target);
if(png.mtimeMs<startedAt-1000||png.size<120*1024||png.size>400*1024)throw Error('封面時間或大小異常，請實際檢視');
console.log('封面已重新產生；仍須檢視排版並更新圖片、模板與文案規格雜湊紀錄。');
