/* 臺灣閱讀、自查與離線輸出共用資料；禁止退回未查核原作。 */
(function () {
  'use strict';
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
  function validate(data) {
    if (data.schema_version !== 1 || data.locale !== 'zh-TW' || data.jurisdiction !== 'TW' || !Array.isArray(data.items) || !Array.isArray(data.sources)) throw Error('臺灣資料版本或結構不符');
    const sources = new Map(data.sources.map(s => [s.id, s]));
    if (sources.size !== data.sources.length) throw Error('來源 ID 重複');
    const ids = new Set();
    for (const s of sources.values()) {
      if (!s.title || !s.supports || !s.accessed_at || new URL(s.url).protocol !== 'https:') throw Error('來源紀錄不完整');
    }
    for (const entry of data.items) {
      if (ids.has(entry.id) || entry.review_status !== 'source_checked' || !entry.body || !entry.limits || !entry.reviewed_at || !entry.review_due_at || !entry.source_ids.length || !entry.source_ids.every(id => sources.has(id))) throw Error('條目未查核、缺少來源或 ID 重複');
      ids.add(entry.id);
    }
    return data;
  }
  function node(tag, text, cls) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (cls) element.className = cls;
    return element;
  }
  function render() {
    if (!catalog) return;
    const rawAge = byId('age').value;
    const age = rawAge === '' ? null : Number(rawAge);
    if (age !== null && (!Number.isInteger(age) || age < 0 || age > 120)) {
      byId('status').textContent = '請填寫0至120的整數年齡，或留白；不會依無效年齡判定資格。';
      byId('cards').replaceChildren(); return;
    }
    const profile = {age, sex: byId('sex').value, family: byId('family').value};
    const q = byId('q').value.trim().toLocaleLowerCase('zh-TW');
    const today = new Date().toLocaleDateString('sv-SE');
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
  async function load() {
    try {
      const response = window.__TW_RUNTIME__ ? null : await fetch('localization/tw-edition/runtime.json', {cache: 'no-cache'});
      if (response && !response.ok) throw Error(`HTTP ${response.status}`);
      catalog = validate(window.__TW_RUNTIME__ || await response.json());
      byId('scope').textContent = catalog.scope;
      for (const id of ['age', 'sex', 'family', 'q']) byId(id).addEventListener('input', render);
      byId('reset').addEventListener('click', () => {
        for (const id of ['age', 'sex', 'family', 'q']) byId(id).value = '';
        answers.clear(); render();
      });
      render(); window.TWRuntime.ready = true;
      if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
    } catch (error) {
      byId('cards').replaceChildren();
      byId('status').textContent = `臺灣資料載入失敗：${error.message}。不會使用未查核來源稿替代。`;
      byId('status').className = 'error'; window.TWRuntime.failed = true;
    }
  }
  window.TWRuntime = {eligible, validate, ready: false, failed: false};
  load();
})();
