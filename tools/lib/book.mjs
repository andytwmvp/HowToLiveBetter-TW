// 原作預覽匯出共用的章節清單與連結設定；臺灣版匯出只讀共用 runtime。
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
export const REPO = 'https://github.com/andytwmvp/HowToLiveBetter-TW';
// 目前以專案說明頁作為閱讀入口；匯出檔不預設一個未確認的網站網址。
export const GUIDE = `${REPO}/blob/main/REPOSITORY_GUIDE.md`;
export const SITE = GUIDE;
// 封面與電子書共用本地文案規格，不再以舊書名綁定 README 的解析。
const imageCopy = JSON.parse(readFileSync(resolve(ROOT, 'localization/image-copy.zh-TW.json'), 'utf8'));
export const TITLE = imageCopy.title;
export const SOURCE_TITLE = 'HowToLiveBetter｜原作繁體中文對照預覽';
export const SOURCE_GUIDE = `${GUIDE}#source-preview`;

// 一律按 LF 交給各套構建：Windows 上 core.autocrlf=true 檢出的是 CRLF，離線版腳本
// 拿 '\n' 寫的 needle 去 index.html 裡找錨點就一個都找不著，本地構建直接報「找不到
// 主腳本的開頭」（CI 是 Linux，從沒碰到過）。正文解析也不必各自處理 \r。
export const read = p => readFileSync(resolve(ROOT, p), 'utf8').replace(/\r\n/g, '\n');
export const unique = arr => [...new Set(arr)];

export function gitCommit() {
  try {
    return execSync('git rev-parse HEAD', { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch {
    return process.env.GITHUB_SHA ?? '';
  }
}

// 正文一天可能改好幾輪，只給日期分不出是哪一版，所以精確到分鐘。
// CI 跑在 UTC 上，統一按臺北時間顯示，免得下載的人按自己那邊的日期對不上。
export function buildStamp() {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Taipei', dateStyle: 'short', timeStyle: 'short' }).format(new Date());
}

export function stripBackLink(md) {
  return md.replace(/^\[← 回總目錄\]\([^)]*\)\s*\n/, '');
}

// 原作預覽只依 manifest 的來源章節清單建目錄；讀者入口 README 不承載原作書籍結構。
export function readBook() {
  const readme = read('README.md');
  const sourceManifest = JSON.parse(read('localization/manifest.json'));
  const chapters = [...sourceManifest.chapters].sort((a, b) => a.chapter - b.chapter);
  const bookFiles = unique(chapters.map(chapter => chapter.display_path));
  if (bookFiles.length !== chapters.length || bookFiles.length === 0) {
    throw new Error('來源 manifest 的章節清單缺少檔案路徑或有重複項');
  }
  const contentsMd = [
    '## 目錄',
    '',
    `本目錄列出原作章節，方便查找、比對原文。要看臺灣版，請參考[閱讀說明](${GUIDE}#reading)。`,
    '',
    '| 章節 | 原作章名 | 來源檔 |',
    '| --- | --- | --- |',
    ...chapters.map(chapter => `| ${chapter.chapter} | ${chapter.source_title_zh_tw} | [原作第${chapter.chapter}章](${chapter.display_path}) |`),
  ].join('\n');
  const description = '原作的繁體中文對照預覽，保留原作內容與用語，方便查找、比對來源。';
  const frontMd = `## 原作來源說明\n\n${description}\n\n要閱讀臺灣版，請參考[閱讀說明](${GUIDE}#reading)。`;
  // 原作章節連結的長文仍可在來源預覽查閱；內部核對紀錄不列為閱讀附錄。
  const docFiles = unique(bookFiles.flatMap(path => {
    const chapter = read(path);
    return [...chapter.matchAll(/\]\((?:\.\.\/)?(docs\/[^)#\s]+\.md)\)/g)]
      .map(match => match[1])
      .filter(doc => !doc.includes('/核實記錄/') && !doc.includes('來源核實'));
  }));
  return { readme, description, frontMd, contentsMd, bookFiles, docFiles };
}

// 性價比三檔：和 index.html 的 COST_W、e.ratio 兩行一致，sync-stats.mjs 每次運行都會比對一次。
// 統計數字和 Anki 牌組的標籤共用這一份。
export const COST_W = {
  money: { '0': 0, '少': 1, '多': 2 },
  time: { '少': 0, '中': 1, '多': 2 },
  will: { '否': 0, '些': 1, '是': 2 },
};

export function ratioOf(cost, level) {
  if (level === '大') return cost === 0 ? '極高' : cost <= 2 ? '高' : '一般';
  return level === '中' && cost === 0 ? '高' : '一般';
}
