/**
 * FitOut Post — Cross-section search overlay
 * Searches across news, pipeline, tenders and companies (embedded in each page's JSON).
 * Also fetches other sections' JSON files if accessible (http:// context).
 *
 * Usage: include this script after cookie-consent.js on any page.
 * The search icon (#masthead-search-btn) triggers the overlay.
 */
(function() {
  'use strict';

  /* ── Inject styles ──────────────────────────────────────────────────── */
  const STYLES = `
#fop-search-overlay {
  display: none; position: fixed; inset: 0; z-index: 9000;
  background: rgba(0,0,0,.72); backdrop-filter: blur(3px);
}
#fop-search-overlay.open { display: flex; flex-direction: column; align-items: center; padding-top: 10vh; }
#fop-search-box {
  background: #fff; border-radius: 3px; width: min(680px, 94vw);
  box-shadow: 0 20px 60px rgba(0,0,0,.4); overflow: hidden;
}
#fop-search-input-row {
  display: flex; align-items: center; gap: 0;
  border-bottom: 2px solid #D8C9A8;
}
#fop-search-icon { padding: 0 14px; color: #990033; font-size: 18px; flex-shrink: 0; }
#fop-search-input {
  flex: 1; border: none; outline: none; padding: 16px 8px;
  font-family: 'EB Garamond', Georgia, serif; font-size: 20px;
  color: #1a1a1a; background: transparent;
}
#fop-search-input::placeholder { color: #bbb; }
#fop-search-close {
  background: none; border: none; padding: 0 16px; cursor: pointer;
  font-size: 22px; color: #8a7f72; line-height: 1;
}
#fop-search-close:hover { color: #990033; }
#fop-search-meta {
  padding: 8px 16px; font-family: Inter, sans-serif; font-size: 11px;
  color: #8a7f72; border-bottom: 1px solid #eee; background: #fdfaf5;
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
}
#fop-search-results {
  max-height: 56vh; overflow-y: auto; padding: 8px 0;
}
.fop-sr-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 10px 16px; cursor: pointer; text-decoration: none;
  color: inherit; transition: background .1s;
}
.fop-sr-item:hover { background: #FFF1E5; }
.fop-sr-badge {
  flex-shrink: 0; font-family: Inter, sans-serif; font-size: 9px;
  font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
  padding: 2px 7px; border-radius: 10px; margin-top: 3px;
}
.fop-sr-badge.news     { background: #e8f0f8; color: #2a5f8f; }
.fop-sr-badge.pipeline { background: #fdf0e0; color: #8a4a00; }
.fop-sr-badge.tender   { background: #f3e8f3; color: #7a3f6e; }
.fop-sr-badge.company  { background: #e8f5ee; color: #2a6f3f; }
.fop-sr-badge.award    { background: #f5f0e8; color: #5a6e1f; }
.fop-sr-text { flex: 1; min-width: 0; }
.fop-sr-headline {
  font-family: 'EB Garamond', Georgia, serif; font-size: 16px;
  line-height: 1.3; color: #1a1a1a; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.fop-sr-sub {
  font-family: Inter, sans-serif; font-size: 11px; color: #8a7f72;
  margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fop-sr-empty {
  padding: 32px 16px; text-align: center;
  font-family: Inter, sans-serif; font-size: 13px; color: #8a7f72;
}
#fop-search-footer {
  padding: 10px 16px; border-top: 1px solid #eee;
  font-family: Inter, sans-serif; font-size: 11px; color: #8a7f72;
  text-align: center; background: #fdfaf5;
}
#fop-search-footer a { color: #990033; text-decoration: none; }
`;

  const styleEl = document.createElement('style');
  styleEl.textContent = STYLES;
  document.head.appendChild(styleEl);

  /* ── Inject overlay HTML ─────────────────────────────────────────────── */
  const OVERLAY_HTML = `
<div id="fop-search-overlay" role="dialog" aria-modal="true" aria-label="Search FitOut Post">
  <div id="fop-search-box">
    <div id="fop-search-input-row">
      <span id="fop-search-icon">🔍</span>
      <input id="fop-search-input" type="search" placeholder="Search news, tenders, pipeline, companies…" autocomplete="off" spellcheck="false" />
      <button id="fop-search-close" aria-label="Close search">×</button>
    </div>
    <div id="fop-search-meta">
      <span id="fop-search-scope">Searching this page's data…</span>
      <span id="fop-search-status"></span>
    </div>
    <div id="fop-search-results"></div>
    <div id="fop-search-footer">
      Search covers all sections ·
      <a href="index.html">News</a> ·
      <a href="pipeline.html">Pipeline</a> ·
      <a href="tenders.html">Tenders</a> ·
      <a href="companies_site.html">Directory</a>
    </div>
  </div>
</div>`;

  document.body.insertAdjacentHTML('beforeend', OVERLAY_HTML);

  /* ── Data registry ───────────────────────────────────────────────────── */
  const SOURCES = { news: [], pipeline: [], tender: [], company: [], award: [] };
  let dataLoaded = 0;
  let totalSources = 0;

  function registerArticles(type, articles, urlKey, titleKey, metaFn) {
    for (const a of articles) {
      SOURCES[type].push({
        type,
        url:   a[urlKey] || '#',
        title: a[titleKey] || a.headline || a.title || '',
        meta:  metaFn(a),
        _obj:  a,
      });
    }
  }

  /* ── Extract data from embedded slots ────────────────────────────────── */
  function loadEmbedded() {
    // News / index
    const newsSlot = document.getElementById('fitout-data');
    if (newsSlot) {
      try {
        const d = JSON.parse(newsSlot.textContent);
        registerArticles('news', d.articles||[], 'url', 'headline',
          a => [a.country, a.source, a.date_display].filter(Boolean).join(' · '));
      } catch(e) {}
    }
    // Pipeline
    const plSlot = document.getElementById('pipeline-data');
    if (plSlot) {
      try {
        const d = JSON.parse(plSlot.textContent);
        registerArticles('pipeline', d.items||d.articles||[], 'url', 'headline',
          a => [a.country, a.continent, a.sector].filter(Boolean).join(' · '));
      } catch(e) {}
    }
    // Tenders
    const tdSlot = document.getElementById('tenders-data');
    if (tdSlot) {
      try {
        const d = JSON.parse(tdSlot.textContent);
        registerArticles('tender', d.tenders||d.articles||[], 'url', 'title',
          a => [a.country, a.deadline, a.value].filter(Boolean).join(' · '));
      } catch(e) {}
    }
    // Awards
    const awSlot = document.getElementById('awards-data');
    if (awSlot) {
      try {
        const d = JSON.parse(awSlot.textContent);
        registerArticles('award', d.awards||[], 'url', 'headline',
          a => [a.country, a.source, a.date_display].filter(Boolean).join(' · '));
      } catch(e) {}
    }
    // Companies
    const coSlot = document.getElementById('__FITOUT_CO__');
    if (!coSlot) {
      try {
        const co = window.__FITOUT_CO__;
        if (co && co.companies) {
          registerArticles('company', co.companies, 'website', 'name',
            a => [a.hq_city, a.hq_country, a.type].filter(Boolean).join(' · '));
        }
      } catch(e) {}
    }
  }

  /* ── Fetch other sections' JSON (works on http://) ──────────────────── */
  async function fetchRemote(src, type, itemsKey, urlKey, titleKey, metaFn) {
    try {
      const r = await fetch(src, { cache: 'default' });
      if (!r.ok) return;
      const d = await r.json();
      registerArticles(type, d[itemsKey]||[], urlKey, titleKey, metaFn);
      dataLoaded++;
      updateScope();
    } catch(e) { dataLoaded++; updateScope(); }
  }

  function updateScope() {
    const total = Object.values(SOURCES).reduce((s,arr) => s+arr.length, 0);
    const status = document.getElementById('fop-search-scope');
    if (status) {
      status.textContent = `Searching ${total.toLocaleString()} records across all sections`;
    }
  }

  function loadAll() {
    loadEmbedded();
    // Only attempt remote fetches if on http:// (not file://)
    if (location.protocol.startsWith('http')) {
      const fetches = [
        ['news.json',      'news',     'articles', 'url', 'headline', a => [a.country,a.source].filter(Boolean).join(' · ')],
        ['pipeline.json',  'pipeline', 'items',    'url', 'headline', a => [a.country,a.sector].filter(Boolean).join(' · ')],
        ['tenders.json',   'tender',   'tenders',  'url', 'title',    a => [a.country,a.deadline].filter(Boolean).join(' · ')],
        ['awards.json',    'award',    'awards',   'url', 'headline', a => [a.country,a.source].filter(Boolean).join(' · ')],
      ];
      totalSources = fetches.length;
      fetches.forEach(([src, ...args]) => fetchRemote(src, ...args));
    }
    updateScope();
  }

  /* ── Search ──────────────────────────────────────────────────────────── */
  let debounceTimer = null;

  function search(q) {
    const results = document.getElementById('fop-search-results');
    const status  = document.getElementById('fop-search-status');
    if (!q || q.length < 2) { results.innerHTML = ''; status.textContent = ''; return; }

    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    const hits = [];

    for (const [type, items] of Object.entries(SOURCES)) {
      for (const item of items) {
        const haystack = (item.title + ' ' + item.meta).toLowerCase();
        if (terms.every(t => haystack.includes(t))) {
          hits.push(item);
        }
        if (hits.length >= 60) break;
      }
      if (hits.length >= 60) break;
    }

    // Sort: exact match in title first
    hits.sort((a, b) => {
      const aq = q.toLowerCase(), at = a.title.toLowerCase(), bt = b.title.toLowerCase();
      return (bt.includes(aq) ? 1 : 0) - (at.includes(aq) ? 1 : 0);
    });

    const shown = hits.slice(0, 20);
    status.textContent = `${hits.length} result${hits.length!==1?'s':''}`;

    if (!shown.length) {
      results.innerHTML = `<div class="fop-sr-empty">No results for "<strong>${esc(q)}</strong>"</div>`;
      return;
    }

    results.innerHTML = shown.map(item => `
      <a class="fop-sr-item" href="${esc(item.url)}" target="${item.url.startsWith('http')?'_blank':'_self'}" rel="noopener">
        <span class="fop-sr-badge ${item.type}">${item.type.charAt(0).toUpperCase()+item.type.slice(1)}</span>
        <div class="fop-sr-text">
          <div class="fop-sr-headline">${esc(item.title)}</div>
          ${item.meta ? `<div class="fop-sr-sub">${esc(item.meta)}</div>` : ''}
        </div>
      </a>`).join('');
  }

  function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ── Open / close ────────────────────────────────────────────────────── */
  const overlay = document.getElementById('fop-search-overlay');
  const input   = document.getElementById('fop-search-input');

  function open() {
    overlay.classList.add('open');
    setTimeout(() => input.focus(), 50);
  }
  function close() {
    overlay.classList.remove('open');
    input.value = '';
    document.getElementById('fop-search-results').innerHTML = '';
    document.getElementById('fop-search-status').textContent = '';
  }

  document.getElementById('fop-search-close').addEventListener('click', close);
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') close();
    if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || e.key === '/') {
      if (!overlay.classList.contains('open')) { e.preventDefault(); open(); }
    }
  });

  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => search(input.value.trim()), 200);
  });

  /* ── Wire up trigger button ──────────────────────────────────────────── */
  function wireBtn(id) {
    const btn = document.getElementById(id);
    if (btn) btn.addEventListener('click', open);
  }
  wireBtn('masthead-search-btn');
  wireBtn('fop-global-search-btn');

  /* ── Init ────────────────────────────────────────────────────────────── */
  loadAll();

  // Expose global open function so pages can call FopSearch.open()
  window.FopSearch = { open, close };
})();
