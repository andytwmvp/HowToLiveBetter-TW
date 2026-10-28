// 把 README + book/*.md + docs/*.md 排成一本 PDF：pandoc 把 Markdown 轉成 typst，typst 排版。
// 用法：node tools/pdf/build.mjs [輸出路徑]   預設輸出 dist/HowToLiveBetter.pdf
// 需要 pandoc（≥3.1，要有 typst 輸出）和 typst（≥0.13）在 PATH 上，或用環境變量 PANDOC、TYPST 指路徑。
// 版面在 tools/pdf/template.typ 裡；正文一個字都不改，只做三件事：
// 去掉「← 回總目錄」、給每節的標題掛上錨點、把倉庫內的連結改成書內跳轉或 GitHub 網址。
import { writeFileSync, mkdirSync, statSync } from 'node:fs';
import { resolve, dirname, posix, basename } from 'node:path';
import { execFileSync } from 'node:child_process';
import { ROOT, REPO, SITE, TITLE, read, readBook, stripBackLink } from '../lib/book.mjs';
import { splitLongItems } from '../lib/split-items.mjs';

const OUT = resolve(ROOT, process.argv[2] ?? 'dist/HowToLiveBetter.pdf');
const WORK = resolve(ROOT, 'dist/pdf-build.md');
const PANDOC = process.env.PANDOC ?? 'pandoc';
const TYPST = process.env.TYPST ?? 'typst';
const { contentsMd, bookFiles, docFiles } = readBook();
const sourceDescription = '原作繁體來源預覽，保留原作內容與用語，方便查找及比對來源。臺灣版生活指引請從本專案閱讀入口閱讀。';

// ---------- 頁（每頁一個一級標題，一級標題在 typst 裡另起一頁） ----------
const anchorOf = new Map();
bookFiles.forEach(f => anchorOf.set(f, 'sec-' + (basename(f).match(/^\d+/)?.[0] ?? anchorOf.size + 1)));
docFiles.forEach((f, i) => anchorOf.set(f, `doc-${i + 1}`));

const pages = [
  { src: 'README.md', md: `# 前言\n\n${sourceDescription}`, anchor: 'front' },
  { src: 'README.md', md: contentsMd.replace(/^## 目錄/, '# 各節簡介'), anchor: 'contents' },
  ...[...bookFiles, ...docFiles].map(src => ({ src, md: splitLongItems(stripBackLink(read(src))), anchor: anchorOf.get(src) })),
  { src: 'README.md', md: aboutMd(), anchor: 'about' },
];

function aboutMd() {
  return `# 原作來源預覽說明

這份 PDF 保留原作內容與用語，方便查找及比對來源。臺灣版生活指引請從[專案閱讀入口](${SITE})閱讀。

- 專案閱讀與建置說明：${REPO}/blob/main/REPOSITORY_GUIDE.md#reading
- 原作來源閱讀方式：${SITE}#source-preview

正文中指向其他章節的連結已改為書內跳轉；來源紀錄與授權檔等未收錄在書中的文件則連回專案儲存庫。

原作、授權與修改說明：${REPO}/blob/main/ATTRIBUTION.md

正文依 CC BY 4.0 授權（https://creativecommons.org/licenses/by/4.0/）。轉載或改編時，請標明「高性價比人生指南」及原始作品連結，並說明修改情形。`;
}

// ---------- 連結：書內的改成錨點，書外的改成絕對網址 ----------
function rewriteLinks(md, src) {
  return md.replace(/\]\(([^)\s]+)(\s+"[^"]*")?\)/g, (all, href, title) => {
    if (/^(https?:|mailto:)/.test(href)) return all;
    // README 裡指向自身小節的錨點（#目錄 這種）在書裡不一定有，指回 GitHub 上的 README
    if (href.startsWith('#')) return `](${REPO}/blob/main/README.md${href}${title ?? ''})`;
    const [path] = href.split('#');
    const target = posix.normalize(posix.join(posix.dirname(src), path));
    const anchor = anchorOf.get(target);
    if (anchor) return `](#${anchor}${title ?? ''})`;
    const kind = target.endsWith('/') ? 'tree' : 'blob';
    return `](${REPO}/${kind}/main/${target}${title ?? ''})`;
  });
}

const body = pages.map(p => {
  const md = rewriteLinks(p.md, p.src)
    .replace(/<!--[\s\S]*?-->/g, '')                       // 成本標籤這類 HTML 註釋不進 PDF
    .replace(/^(# .+?)\s*$/m, `$1 {#${p.anchor}}`);        // 給這一頁的一級標題掛錨點
  if (!md.includes(`{#${p.anchor}}`)) throw new Error(`${p.src} 裡沒找到一級標題，掛不上錨點`);
  return md.trim();
}).join('\n\n');

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(WORK, body);

// ---------- pandoc → typst → pdf ----------
const run = (cmd, args) => {
  try {
    return execFileSync(cmd, args, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (err) {
    if (err.code === 'ENOENT') throw new Error(`找不到 ${cmd}，裝上它或用環境變量 ${cmd === PANDOC ? 'PANDOC' : 'TYPST'} 指到可執行文件`);
    throw new Error(`${cmd} 失敗：\n${err.stderr || err.stdout || err.message}`);
  }
};

const typFile = resolve(ROOT, 'dist/pdf-build.typ');
run(PANDOC, [
  '--from=gfm+attributes', '--to=typst', '--wrap=none',
  `--template=${resolve(ROOT, 'tools/pdf/template.typ')}`,
  '-V', `booktitle=${TITLE}`, '-V', `subtitle=${sourceDescription}`,
  '-V', `site=${SITE}`, '-V', `repo=${REPO}`,
  '-o', typFile, WORK,
]);
const log = run(TYPST, ['compile', typFile, OUT, '--root', ROOT]);
if (log.trim()) console.log(log.trim());

const entries = pages.filter(p => bookFiles.includes(p.src))
  .reduce((n, p) => n + p.md.split('\n').filter(l => l.startsWith('### ')).length, 0);
console.log(`已生成 ${OUT}：${bookFiles.length} 節 ${entries} 條，附錄 ${docFiles.length} 篇，${(statSync(OUT).size / 1048576).toFixed(1)} MB`);
