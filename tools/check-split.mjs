// 原作來源頁與來源出版工具的拆分規則必須一致，不將來源稿視為臺灣正文。
import { readdirSync } from 'node:fs';
import vm from 'node:vm';
import { read, readBook } from './lib/book.mjs';
import { splitGain, splitSrc } from './lib/split-items.mjs';
const html=read('source.html');
const m=html.match(/\/\/ <split-rules>[\s\S]*?\/\/ <\/split-rules>/);
if(!m){console.error('source.html沒有拆分規則標記');process.exit(1);}
const ctx={};
vm.runInNewContext(`${m[0]}\nthis.splitGain = splitGain; this.splitSrc = splitSrc;`,ctx);
const {docFiles}=readBook();
const files=[...readdirSync(new URL('../book/',import.meta.url)).filter(f=>f.endsWith('.md')).map(f=>`book/${f}`),...docFiles];
const problems=[];let total=0,split=0;
for(const f of files){
  read(f).split('\n').forEach((line,i)=>{
    const mm=line.match(/^\s*- (收益|備註|來源)：(.*)$/);if(!mm)return;
    const [,label,body]=mm;const at=`${f}:${i+1}（${label}）`;
    const lib=label==='來源'?splitSrc(body):splitGain(body);
    const web=label==='來源'?ctx.splitSrc(body):ctx.splitGain(body);
    total++;if(lib.length>1)split++;
    if(JSON.stringify(lib)!==JSON.stringify(web))problems.push(`${at}：來源頁與出版拆分結果不同`);
    if(label!=='來源'&&lib.join('')!==body)problems.push(`${at}：拆完拼不回原文`);
    if(lib.length>1&&lib.some(c=>(c.match(/\*\*/g)||[]).length%2))problems.push(`${at}：加粗標記被拆開`);
  });
}
for(const p of problems)console.log(p);
console.log(`${files.length}個文件、${total}個欄位、${split}個拆分、${problems.length}個問題`);
process.exit(problems.length?1:0);
