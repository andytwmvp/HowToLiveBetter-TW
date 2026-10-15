// 把 index.html + README + book/*.md 打成一個自包含的 HTML：雙擊就能看，不用伺服器、不用聯網。
// 用法：node tools/offline/build.mjs [輸出路徑]   預設輸出 dist/HowToLiveBetter.html
// 正文內聯進 window.__CORPUS__，index.html 的 init() 認這個變量就不再發請求；
// 站內相對連結改成線上地址，側欄圖片轉成 data URI，其餘一個字不動。
import { writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { ROOT, REPO, SITE, read, gitCommit, buildStamp } from '../lib/book.mjs';

const OUT = resolve(ROOT, process.argv[2] ?? 'dist/HowToLiveBetter.html');
const STAMP = buildStamp();
const COMMIT = gitCommit();

// ---------- 正文 ----------
const readme = read('README.md');
const files = [...new Set([...readme.matchAll(/\]\((book\/[^)]+\.md)\)/g)].map(m => m[1]))].sort();
if (!files.length) throw new Error('README 目錄裡沒找到 book/ 文件，離線版會是空的');
// 長文（docs/*.md）也要帶上：檢索頁的長文彈窗就地渲染它們，離線副本里沒有就只剩
// 一個點不開的 GitHub 連結。清單從 README 裡扒，和 EPUB、PDF 兩套構建用的是同一處。
const docs = [...new Set([...readme.matchAll(/\]\((docs\/[^)#/]+\.md)\)/g)].map(m => m[1]))].sort();
const corpus = {
  readme,
  parts: Object.fromEntries(files.map(f => [f, read(f)])),
  docs: Object.fromEntries(docs.map(f => [f, read(f)])),
};
// </script 會提前關掉腳本標籤；\/ 在 JS 字符串裡就是 /，內容不變
const corpusJson = JSON.stringify(corpus).replace(/<\/script/gi, '<\\/script');

// ---------- 頁面 ----------
let html = read('index.html');
const must = (needle, label) => {
  if (!html.includes(needle)) throw new Error(`index.html 裡找不到${label}，離線版腳本要跟著改：${needle}`);
};

// 臺灣 fork 的網頁不含原作者追蹤碼，離線產物亦不得含追蹤端點。
if (/googletagmanager|google-analytics/.test(html)) throw new Error('禁止在離線版帶入追蹤端點');

// 相對連結在本地打開時是死的，改成線上地址
must('href="README.md"', ' README.md 連結');
must('href="book/"', ' book/ 連結');
must('href="selfcheck.html"', ' 自查頁連結');
html = html
  .replaceAll('href="README.md"', `href="${REPO}/blob/main/README.md"`)
  .replaceAll('href="selfcheck.html"', `href="${SITE}selfcheck.html"`)
  .replaceAll('href="book/"', `href="${REPO}/tree/main/book"`)
  .replaceAll('<a class="title" href="./"', `<a class="title" href="${SITE}"`);

// 頁腳註明這是哪一版的離線副本
const foot = '<div class="foot">';
must(foot, '頁腳');
const commitNote = COMMIT ? `，正文提交 ${COMMIT.slice(0, 7)}` : '';
html = html.replace(foot, `${foot}離線副本，生成於 ${STAMP}（臺北時間）${commitNote}；正文會繼續更新，以 <a href="${SITE}">線上版</a> 為準。<br>`);

// 正文要在主腳本之前就位
const mainScript = '\n<script>\n/* ---------- 調試面板';
must(mainScript, '主腳本的開頭');
html = html.replace(mainScript, `\n<script>window.__CORPUS__=${corpusJson}</script>${mainScript}`);

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, html);
const kb = n => (n / 1024 | 0) + ' KB';
console.log(`已生成 ${OUT}：${files.length} 個正文文件，長文 ${docs.length} 篇，${kb(Buffer.byteLength(html))}（其中正文 ${kb(Buffer.byteLength(corpusJson))}）`);
