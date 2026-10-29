// 明確指定的原作來源預覽，不作為臺灣版預設內容。
import { writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { ROOT, REPO, read, readBook } from '../lib/book.mjs';
const OUT=resolve(ROOT,process.argv[2] ?? 'dist/HowToLiveBetter-source-preview.html');
const {bookFiles:files,docFiles:docs}=readBook();
const corpus={chapters:files,parts:Object.fromEntries(files.map(f=>[f,read(f)])),docs:Object.fromEntries(docs.map(f=>[f,read(f)]))};
const corpusJson=JSON.stringify(corpus).replace(/<\/script/gi,'<\\/script');
let html=read('source.html');
if(/googletagmanager|google-analytics/.test(html))throw Error('來源預覽不得包含追蹤碼');
const must=(needle)=>{if(!html.includes(needle))throw Error('source.html缺少預期標記：'+needle);};
for(const needle of ['href="README.md"','href="locales/zh-TW/README.md"','href="REPOSITORY_GUIDE.md#reading"','href="REPOSITORY_GUIDE.md#source-preview"'])must(needle);
html=html.replaceAll('href="README.md"',`href="${REPO}/blob/main/README.md"`).replaceAll('href="locales/zh-TW/README.md"',`href="${REPO}/blob/main/locales/zh-TW/README.md"`).replaceAll('href="REPOSITORY_GUIDE.md#reading"',`href="${REPO}/blob/main/REPOSITORY_GUIDE.md#reading"`).replaceAll('href="REPOSITORY_GUIDE.md#source-preview"',`href="${REPO}/blob/main/REPOSITORY_GUIDE.md#source-preview"`).replaceAll('href="SUPPORT.md"',`href="${REPO}/blob/main/SUPPORT.md"`).replaceAll('href="ATTRIBUTION.md"',`href="${REPO}/blob/main/ATTRIBUTION.md"`).replaceAll('<a class="title" href="./"',`<a class="title" href="${REPO}/blob/main/locales/zh-TW/README.md"`);
const foot='<div class="foot">';must(foot);
html=html.replace(foot,`${foot}這裡展示原作內容，方便查找原文和比對來源；要找台灣生活指引，請看<a href="${REPO}/blob/main/locales/zh-TW/README.md">台灣文章目錄</a>。<br>`);
const mainScript='\n<script>\n/* ---------- 調試面板';must(mainScript);
html=html.replace(mainScript,`\n<script>window.__CORPUS__=${corpusJson}</script>${mainScript}`);
mkdirSync(dirname(OUT),{recursive:true});writeFileSync(OUT,html);
console.log(`PASS：原作來源預覽${files.length}章、${docs.length}篇原作延伸閱讀；${OUT}`);
