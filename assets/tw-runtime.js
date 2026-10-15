/* 臺灣閱讀、自查與離線輸出共用資料；禁止退回未查核原作。 */
(function () {
  'use strict';
  function taipeiToday(now = new Date()) {
    return new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit'}).format(now);
  }
  // 原生JSON.parse會留下重複欄位的最後值；先解析語法，再逐層拒絕重複鍵。
  function parseRuntimeJson(raw) {
    if (typeof raw !== 'string') throw Error('閱讀資料必須為JSON文字');
    const data = JSON.parse(raw, (_key, value) => {
      if (typeof value === 'number' && !Number.isFinite(value)) throw Error('JSON不接受非有限數值');
      return value;
    });
    const stack = [];
    for (let i = 0; i < raw.length;) {
      const char = raw[i];
      if (char === '"') {
        const start = i++;
        while (i < raw.length) {
          if (raw[i] === '\\') { i += 2; continue; }
          if (raw[i++] === '"') break;
        }
        let next = i;
        while (next < raw.length && /[ \t\r\n]/.test(raw[next])) next++;
        if (raw[next] === ':') {
          const key = JSON.parse(raw.slice(start, i));
          const keys = stack[stack.length - 1];
          if (!(keys instanceof Set) || keys.has(key)) throw Error('JSON欄位重複或物件結構錯誤');
          keys.add(key);
        }
      } else {
        if (char === '{') stack.push(new Set());
        else if (char === '[') stack.push(null);
        else if (char === '}' || char === ']') stack.pop();
        i++;
      }
    }
    return data;
  }
  function validate(data, today = taipeiToday()) {
    const fail = message => { throw Error(message); };
    const obj = (v, label) => v !== null && typeof v === 'object' && !Array.isArray(v) ? v : fail(label + '須為物件');
    const text = (v, label) => typeof v === 'string' && v.trim() ? v : fail(label + '須為非空白文字');
    const array = (v, label) => Array.isArray(v) && v.length ? v : fail(label + '須為非空陣列');
    const iso = (v, label) => {
      if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v) || Number(v.slice(0, 4)) < 1) fail(label + '日期格式錯誤');
      const parsed = new Date(v + 'T00:00:00Z');
      if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== v) fail(label + '日期不存在');
      return v;
    };
    const checked = (v, label) => iso(v, label) <= today ? v : fail(label + '不得在未來');
    const window = (first, last, label) => {
      checked(first, label); iso(last, label);
      if (last < first || last < today) fail(label + '複查日期早於查核日或已逾期');
    };
    iso(today, '目前'); obj(data, '臺灣資料');
    if (data.schema_version !== 1 || data.locale !== 'zh-TW' || data.jurisdiction !== 'TW') fail('臺灣資料版本或地區錯誤');
    text(data.title, '標題'); text(data.scope, '適用範圍');
    window(data.updated_at, data.review_due_at, '資料集');
    const sources = new Map();
    for (const s of array(data.sources, '來源')) {
      obj(s, '來源'); text(s.id, '來源ID');
      if (!/^[a-z][a-z0-9_]*$/.test(s.id) || sources.has(s.id)) fail('來源ID格式錯誤或重複');
      text(s.title, '來源標題'); text(s.supports, '來源支持範圍'); text(s.url, '來源網址');
      if (!s.url.startsWith('https://') || /[\s\\\x00-\x1f\x7f]/.test(s.url) || /%(?![a-fA-F0-9]{2})/.test(s.url)) fail('來源網址格式錯誤');
      // 先檢查原始authority，避免URL解析器自動修補缺少主機的字串。
      const authority = s.url.slice(8).split(/[/?#]/, 1)[0];
      if (!/^[a-zA-Z0-9.-]+(?::\d{1,5})?$/.test(authority)) fail('來源須有完整網域且不能含帳號密碼');
      const u = new URL(s.url);
      if (u.protocol !== 'https:' || u.username || u.password || u.hostname.split('.').length < 2 || !u.hostname.split('.').every(label => /^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/.test(label)) || (u.port && (Number(u.port) < 1 || Number(u.port) > 65535))) fail('來源網址結構錯誤');
      checked(s.accessed_at, '來源查閱');
      if (s.accessed_at > data.updated_at || (s.published_at !== null && s.published_at !== undefined && iso(s.published_at, '來源發布') > s.accessed_at)) fail('來源日期順序錯誤');
      sources.set(s.id, s);
    }
    const ids = new Set();
    for (const e of array(data.items, '閱讀條目')) {
      obj(e, '條目'); text(e.id, '條目ID');
      if (!/^TW-(?:NAV-\d{3}|\d{2}-\d{3})$/.test(e.id) || ids.has(e.id) || e.review_status !== 'source_checked') fail('條目ID錯誤、重複或尚未核對');
      ids.add(e.id);
      for (const key of ['title', 'body', 'limits', 'question']) text(e[key], key);
      window(e.reviewed_at, e.review_due_at, e.id);
      if (e.reviewed_at > data.updated_at) fail('條目查核日晚於資料更新日');
      const refs = array(e.source_ids, '條目來源ID');
      if (refs.some(id => typeof id !== 'string' || !sources.has(id)) || new Set(refs).size !== refs.length) fail('條目來源未登錄或重複');
      if (refs.some(id => sources.get(id).accessed_at > e.reviewed_at)) fail('條目查核早於來源查閱');
      const rule = obj(e.eligibility, '適用條件');
      if (Object.keys(rule).some(key => !['sex', 'min_age', 'max_age', 'ages', 'family_history'].includes(key))) fail('不認識的適用條件');
      if (Object.hasOwn(rule, 'sex') && !['f', 'm'].includes(rule.sex)) fail('方案對象分類錯誤');
      if (Object.hasOwn(rule, 'family_history') && typeof rule.family_history !== 'boolean') fail('家族史必須為布林值');
      for (const key of ['min_age', 'max_age']) if (Object.hasOwn(rule, key) && (!Number.isInteger(rule[key]) || rule[key] < 0 || rule[key] > 120)) fail('年齡須為0至120的整數');
      const low = rule.min_age ?? 0, high = rule.max_age ?? 120;
      if (low > high) fail('年齡區間倒置');
      if (Object.hasOwn(rule, 'ages')) {
        const ages = array(rule.ages, '指定年齡');
        if (ages.some(age => !Number.isInteger(age) || age < low || age > high) || new Set(ages).size !== ages.length) fail('指定年齡錯誤或重複');
      }
    }
    return data;
  }
  function decodeTarget(hash) {
    try {
      const id = decodeURIComponent(hash.slice(1));
      return /^TW-(?:NAV-\d{3}|\d{2}-\d{3})$/.test(id) ? id : null;
    } catch (_) { return null; }
  }
  // Node與瀏覽器測試同一個實際驗證函式；不複製測試專用版本。
  if (typeof module === 'object' && module.exports) {
    module.exports = {validate, taipeiToday, decodeTarget, parseRuntimeJson};
    return;
  }
  // 僅相容本repo舊原作書籤；不接受任意外站或查詢參數重定向。
  const legacy = /^#e-([1-9]|[12]\d|3[0-4])-([1-9]\d{0,2})$/.test(location.hash);
  if (legacy && /^https?:$/.test(location.protocol)) {
    location.replace('source.html' + location.hash);
    return;
  }
  const answers = new Map();
  const byId = id => document.getElementById(id);
  let catalog;
  function eligible(rule, profile) {
    if (profile.sex && rule.sex && profile.sex !== rule.sex) return false;
    if (profile.age !== null) {
      if (rule.min_age !== undefined && profile.age < rule.min_age) return false;
      if (rule.max_age !== undefined && profile.age > rule.max_age) return false;
      if (rule.ages && !rule.ages.includes(profile.age)) return false;
    }
    if (rule.family_history && profile.family === 'n') return false;
    return true;
  }
  function node(tag, text, cls) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (cls) element.className = cls;
    return element;
  }
  function render() {
    if (!catalog) return;
    try { validate(catalog); } catch (error) { showFailure(error); return; }
    const rawAge = byId('age').value;
    const age = rawAge === '' ? null : Number(rawAge);
    if (age !== null && (!Number.isInteger(age) || age < 0 || age > 120)) {
      byId('status').textContent = '請填寫0至120的整數年齡，或留白；不會依無效年齡判定資格。';
      byId('cards').replaceChildren(); return;
    }
    const profile = {age, sex: byId('sex').value, family: byId('family').value};
    const q = byId('q').value.trim().toLocaleLowerCase('zh-TW');
    const today = taipeiToday();
    const rows = catalog.items.filter(e => eligible(e.eligibility, profile) && `${e.title} ${e.body} ${e.limits}`.toLocaleLowerCase('zh-TW').includes(q));
    const container = byId('cards'); container.replaceChildren();
    for (const e of rows) {
      const article = node('article', undefined, 'q'); article.id = e.id; article.dataset.id = e.id;
      article.append(node('h2', e.title), node('p', e.body), node('p', e.limits));
      const stale = today > e.review_due_at;
      article.append(node('p', `${e.id}｜來源核對：${e.reviewed_at}｜下次檢查：${e.review_due_at}${stale ? '｜資料已到複查日期，請向官方確認現況' : ''}`, 'meta'));
      const refs = node('p', '依據：');
      for (const id of e.source_ids) {
        const s = catalog.sources.find(x => x.id === id); const a = node('a', s.title);
        a.href = s.url; a.rel = 'noopener noreferrer'; refs.append(a, document.createTextNode(' '));
      }
      article.append(refs);
      if (document.body.dataset.view === 'selfcheck') {
        article.append(node('p', e.question));
        const controls = node('div', undefined, 'seg'); controls.setAttribute('role', 'group'); controls.setAttribute('aria-label', e.title);
        for (const [value, label] of [['yes', '已瞭解'], ['no', '需要再確認']]) {
          const button = node('button', label, value); button.type = 'button'; button.setAttribute('aria-pressed', String(answers.get(e.id) === value));
          button.addEventListener('click', () => {
            answers.set(e.id, value);
            for (const b of controls.children) b.setAttribute('aria-pressed', String(b === button));
          }); controls.append(button);
        }
        article.append(controls);
      }
      container.append(article);
    }
    byId('status').textContent = `顯示 ${rows.length}／${catalog.items.length} 則已核對導航。未填的條件不作資格判定；這不是全書完成數。`;
    if (!rows.length) container.append(node('p', '沒有符合目前篩選的已核對項目；不會改以原作或未審閱草稿填補。'));
  }
  function showFailure(error) {
    catalog = null; answers.clear();
    byId('cards').replaceChildren();
    byId('status').textContent = `臺灣資料未通過檢查：${error.message}。不會使用未查核來源稿替代。`;
    byId('status').className = 'error';
    window.TWRuntime.failed = true; window.TWRuntime.ready = false;
  }
  async function load() {
    try {
      const response = window.__TW_RUNTIME__ ? null : await fetch('localization/tw-edition/runtime.json', {cache: 'no-cache'});
      if (response && !response.ok) throw Error(`HTTP ${response.status}`);
      catalog = validate(window.__TW_RUNTIME__ || parseRuntimeJson(await response.text()));
      byId('scope').textContent = catalog.scope;
      for (const id of ['age', 'sex', 'family', 'q']) byId(id).addEventListener('input', render);
      byId('reset').addEventListener('click', () => {
        for (const id of ['age', 'sex', 'family', 'q']) byId(id).value = '';
        answers.clear(); render();
      });
      render(); window.TWRuntime.ready = !!catalog;
      document.addEventListener('visibilitychange', () => { if (!document.hidden && catalog) render(); });
      const target = decodeTarget(location.hash);
      if (target) document.getElementById(target)?.scrollIntoView();
    } catch (error) {
      showFailure(error);
    }
  }
  window.TWRuntime = {eligible, validate, ready: false, failed: false};
  load();
})();
