// 失效連結檢查：把正文和長文裡的外鏈挨個請求一遍，報出打不開的。
//
//   node tools/check-links.mjs              # 全量檢查，結果打到終端；在 GitHub Actions 裡還寫進 job summary
//   node tools/check-links.mjs --limit 50   # 只查前 50 條，本地試跑用
//
// 只報告，退出碼恆為 0：gov.cn 一類站點從境外訪問時通時不通，拿它擋構建只會天天紅。
// 結果分兩檔。「確定失效」只收 404 和 410，以及 DOI 在 doi.org 登記處查不到的，這一檔要回去修。
// 「沒連上」是超時、403、5xx 這類，多半是對方擋了機房 IP 或臨時故障，連著幾周都在才值得看。
//
// DOI 不去打開出版商頁面：Wiley、SAGE 這些站對機器請求一律 403，查了也白查。
// 改問 doi.org 的登記處接口，它只回答「這個 DOI 存不存在」，正好是這裡要的。
import { readFileSync, readdirSync, appendFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const limitArg = process.argv.indexOf('--limit');
const LIMIT = limitArg > 0 ? Number(process.argv[limitArg + 1]) : Infinity;
const CONCURRENCY = 8;
const TIMEOUT = 20000;
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';

// 連結從哪來：book/ 每節、docs/ 根下的長文（核實記錄是歷史狀態，不查）、README。
const files = [
  ...readdirSync(resolve(ROOT, 'book')).filter(f => /^\d\d-.*\.md$/.test(f)).map(f => `book/${f}`),
  ...readdirSync(resolve(ROOT, 'docs')).filter(f => f.endsWith('.md') && f !== '引用對照.md').map(f => `docs/${f}`),
  'README.md',
];

// url -> 第一次出現的位置
const where = new Map();
for (const f of files) {
  readFileSync(resolve(ROOT, f), 'utf8').split(/\r?\n/).forEach((line, i) => {
    // 來源欄的連結寫成 <url>，尖括號裡的整段就是連結，DOI 裡的括號（10.1016/S0140-6736(15)01225-8）
    // 也原樣保留；裸寫的連結按空白和中文標點截斷，再去掉末尾不成對的右括號。
    const found = [...line.matchAll(/<(https?:\/\/[^>\s]+)>/g)].map(m => m[1]);
    const rest = line.replace(/<https?:\/\/[^>\s]+>/g, '');
    for (const m of rest.matchAll(/https?:\/\/[^\s<>（）「」，。；、"'`\]]+/g)) {
      let url = m[0].replace(/[.,;:]+$/, '');
      while (url.endsWith(')') && (url.match(/\(/g) ?? []).length < (url.match(/\)/g) ?? []).length) url = url.slice(0, -1);
      found.push(url);
    }
    for (const url of found) if (!where.has(url)) where.set(url, `${f}:${i + 1}`);
  });
}
// 徽章與本機測試網址不查；repo 導覽另由 link_policy.py 驗證，不再把上游或下載網址一概略過。
const SKIP = /img\.shields\.io|localhost|127\.0\.0\.1/;
// 不少地方政府站還用著老的加密套件或證書鏈不全，Node 握手直接報錯，瀏覽器卻能正常打開。
// 這類單獨一檔，不和真正連不上的混在一起。
const TLS = /^(ERR_SSL_|UNABLE_TO_VERIFY|CERT_|SELF_SIGNED|DEPTH_ZERO)/;
const urls = [...where.keys()].filter(u => !SKIP.test(u)).slice(0, LIMIT);

const withTimeout = (p, ms) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error('超時')), ms))]);

async function checkDoi(doi) {
  const r = await withTimeout(fetch(`https://doi.org/api/handles/${encodeURIComponent(doi)}`), TIMEOUT);
  if (r.status === 404) return { dead: true, why: 'doi.org 查無此 DOI' };
  if (!r.ok) return { dead: false, why: `doi.org 返回 ${r.status}` };
  return null;
}

async function checkUrl(url) {
  const doi = /^https?:\/\/(?:dx\.)?doi\.org\/(.+)$/i.exec(url);
  if (doi) return checkDoi(decodeURIComponent(doi[1]));
  // 先 GET 不先 HEAD：有的站 HEAD 返回 403 而 GET 正常（海南省藥監局就是這樣），用 HEAD 會誤判成死鏈。
  const r = await withTimeout(fetch(url, { redirect: 'follow', headers: { 'User-Agent': UA, Accept: 'text/html,*/*' } }), TIMEOUT);
  r.body?.cancel().catch(() => {});
  if ([404, 410].includes(r.status)) return { dead: true, why: `${r.status}` };
  if (!r.ok) return { dead: false, why: `${r.status}` };
  return null;
}

const dead = [];
const flaky = [];
const tls = [];
let next = 0;
async function worker() {
  while (next < urls.length) {
    const url = urls[next++];
    try {
      const res = await checkUrl(url);
      if (res) (res.dead ? dead : flaky).push({ url, why: res.why, at: where.get(url) });
    } catch (e) {
      const why = e.cause?.code ?? e.message;
      (TLS.test(why) ? tls : flaky).push({ url, why, at: where.get(url) });
    }
  }
}
await Promise.all(Array.from({ length: CONCURRENCY }, worker));

const sortAt = a => a.sort((x, y) => x.at.localeCompare(y.at, 'zh'));
const lines = [
  `## 失效連結檢查`,
  ``,
  `共查 ${urls.length} 條連結，確定失效 ${dead.length} 條，沒連上 ${flaky.length} 條，加密握手不兼容 ${tls.length} 條。`,
  ``,
  `### 確定失效（404、410、DOI 查無此號）`,
  ``,
  ...(dead.length ? sortAt(dead).map(d => `- ${d.at}　${d.why}　${d.url}`) : ['無']),
  ``,
  `### 沒連上（超時、403、5xx，多半是對方擋了機房 IP，連著幾周都在才值得看）`,
  ``,
  ...(flaky.length ? sortAt(flaky).map(d => `- ${d.at}　${d.why}　${d.url}`) : ['無']),
  ``,
  `### 加密握手不兼容（老政府站的加密方式 Node 不認，瀏覽器一般能開，不用修）`,
  ``,
  ...(tls.length ? sortAt(tls).map(d => `- ${d.at}　${d.why}　${d.url}`) : ['無']),
  ``,
];
console.log(lines.join('\n'));
if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, lines.join('\n') + '\n');
