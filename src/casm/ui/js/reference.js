// Reference Data tab: left rail of reference sets, a table, and an inspector for the selected row.

import { api } from './api.js';
import {
  TABLE_BODY_ROW,
  TABLE_CELL,
  TABLE_CLASS,
  TABLE_HEAD_CELL,
  TABLE_HEAD_ROW,
  countStrip,
  dash,
  debounce,
  esc,
  field,
  inspectorFrame,
  num,
  pageTitle,
  pill,
  productPill,
  section,
  wireCopy,
} from './util.js';

const MONO = 'font-code-md text-code-md';
const statusDot = (s) => `<span class="inline-flex items-center gap-1.5"><span class="w-2 h-2 rounded-full ${s === 'ACTIVE' ? 'bg-[#198038]' : 'bg-[#f1c21b]'}"></span>${esc(s)}</span>`;
const typeTag = (t) => (t ? pill(t, t === 'EXCHANGE' ? 'bg-primary-fixed text-on-primary-fixed' : 'bg-secondary-container text-on-surface') : dash(null));
const right = (v) => `<span class="block text-right">${v}</span>`;
const code = (v, extra = '') => `<span class="${MONO} ${extra}">${esc(v)}</span>`;

const SETS = {
  venues: {
    title: 'Market Identifier Codes (ISO 10383)',
    badges: [],
    search: 'Search by MIC, name or operating MIC',
    key: 'mic',
    columns: [
      ['mic', 'MIC', (r) => code(r.mic, 'font-semibold')],
      ['operating_mic', 'Operating MIC', (r) => code(r.operating_mic, 'text-secondary')],
      ['name', 'Name', (r) => esc(r.name)],
      ['country', 'Country', (r) => dash(r.country)],
      ['type', 'Type', (r) => (r.loaded ? typeTag(r.venue_type) : pill('registry only', 'bg-surface-variant text-secondary'))],
      ['status', 'Status', (r) => statusDot(r.status)],
      ['listings', 'Listings', (r) => right(num(r.listings))],
    ],
    sortKeys: { mic: 'mic', operating_mic: 'operating_mic', name: 'name', country: 'country', type: 'type', status: 'status', listings: 'listings' },
  },
  gics: {
    title: 'GICS Hierarchy (2018 structure)',
    badges: ['Stale: effective until 2023-03-17'],
    search: 'Search by code or name at any level',
    key: 'code',
    columns: [
      ['level', 'Level', (r) => pill(r.level, r.level_no === 1 ? 'bg-primary-fixed text-on-primary-fixed' : 'bg-surface-container text-on-surface')],
      ['code', 'Code', (r) => code(r.code, 'font-semibold')],
      ['name', 'Name', (r) => `<span style="padding-left:${(r.level_no - 1) * 16}px" class="${r.level_no === 1 ? 'font-semibold' : ''}">${esc(r.name)}</span>`],
      ['parent_code', 'Parent Code', (r) => (r.parent_code ? code(r.parent_code, 'text-secondary') : dash(null))],
      ['parent_name', 'Parent', (r) => dash(r.parent_name)],
    ],
    load: async () => (await api('/reference/gics')).items,
  },
  taxonomy: {
    title: 'Instrument Taxonomy',
    badges: [],
    search: 'Search by product code or description',
    key: 'code',
    columns: [
      ['code', 'Product Code', (r) => productPill(r.code)],
      ['asset_class_code', 'Asset Class Code', (r) => code(r.asset_class_code, 'font-semibold')],
      ['asset_class_name', 'Asset Class', (r) => esc(r.asset_class_name)],
      ['base_product_code', 'Base Product Code', (r) => code(r.base_product_code, 'font-semibold')],
      ['base_product_name', 'Base Product', (r) => esc(r.base_product_name)],
      ['description', 'Description', (r) => esc(r.description)],
      ['source', 'Source', (r) => pill(r.source)],
    ],
    load: async () => (await api('/reference/taxonomy')).items,
  },
  countries: {
    title: 'Countries (ISO 3166-1)',
    badges: [],
    search: 'Search by country name or alpha-2 code',
    key: 'alpha2',
    columns: [
      ['alpha2', 'Alpha-2', (r) => code(r.alpha2, 'font-semibold')],
      ['name', 'Name', (r) => esc(r.name)],
      ['issuers', 'Issuers', (r) => right(num(r.issuers))],
      ['venues', 'Loaded Venues', (r) => right(num(r.venues))],
    ],
    load: async () => (await api('/reference/countries')).items,
  },
  isda: {
    title: 'ISDA Taxonomy v2.0: Equity',
    badges: [],
    search: 'Search by base product, sub-product or transaction type',
    key: 'isda_row_no',
    columns: [
      ['isda_row_no', '#', (r) => code(r.isda_row_no)],
      ['base_product', 'Base Product', (r) => esc(r.base_product)],
      ['sub_product', 'Sub-Product', (r) => dash(r.sub_product)],
      ['transaction_type', 'Transaction Type', (r) => dash(r.transaction_type)],
    ],
    load: async () => (await api('/reference/isda-equity')).items,
  },
};

// The node and its ancestors, top level first, from the cached GICS rows.
function gicsChain(row) {
  const byCode = new Map((cache || []).map((n) => [n.code, n]));
  const chain = [];
  for (let node = row; node; node = node.parent_code ? byCode.get(node.parent_code) : null) chain.unshift(node);
  return chain;
}
const CHILD_LEVEL = { Sector: 'Industry Groups', 'Industry Group': 'Industries', Industry: 'Sub-Industries' };
const childLevel = (row) => CHILD_LEVEL[row.level] || 'Children';

const link = (cusip, text) => `<a class="text-primary hover:underline" href="#/securities?q=${encodeURIComponent(cusip || text)}">${esc(text)}</a>`;
const list = (rows, line, empty) => (rows.length
  ? `<ul class="col-span-2 flex flex-col font-body-md text-body-md">${rows.map((r) => `<li class="py-1 border-b border-surface-container">${line(r)}</li>`).join('')}</ul>`
  : `<div class="col-span-2 text-secondary font-body-md text-body-md">${empty}</div>`);
const held = (label, value, opts) => (value === null || value === undefined || value === '' ? '' : field(label, value, opts));

// Each inspector returns { subtitle, details, related: [label, html] | null }
const INSPECT = {
  async venues(r) {
    const d = await api(`/reference/venues/${r.mic}`);
    const reg = d.registry;
    const share = d.usage.total_instruments ? (100 * d.usage.listings) / d.usage.total_instruments : 0;
    const usage = d.venue
      ? section('CASM usage', '', `<div class="col-span-2"><div class="flex justify-between font-body-md text-body-md"><span>${num(d.usage.listings)} of ${num(d.usage.total_instruments)} instruments listed here</span><span class="font-semibold">${share.toFixed(1)}%</span></div><div class="w-full bg-surface-container-high h-2 mt-1"><div class="bg-primary-container h-full" style="width:${share}%"></div></div></div>${d.usage.by_product.map((p) => field(p.product_code, num(p.count), { mono: true })).join('')}`)
      : '';
    return {
      subtitle: `${typeTag(d.venue && d.venue.venue_type)}<span class="${MONO}">${esc(reg.mic)} · ${esc(reg.status)}</span>`,
      details:
        section('ISO 10383 identification', '', field('MIC', esc(reg.mic), { mono: true }) + field('Operating MIC', `${esc(reg.operating_mic)} ${reg.operating_mic === reg.mic ? '(self)' : esc(reg.operating_name)}`, { mono: true }) + held('LEI', reg.lei && esc(reg.lei), { mono: true, span2: true }) + field('Segment type', esc(reg.oprt_sgmt)) + held('Market category', reg.market_category_code && esc(reg.market_category_code))) +
        section('Location', '', held('Jurisdiction', d.venue ? d.venue.country_name : reg.country) + (d.venue ? field('OTC or unlisted', d.venue.is_otc ? 'Yes (from venue type)' : 'No') : '')) +
        usage,
      related: d.venue ? [`Mapped assets (${num(d.usage.listings)})`, section('Instruments listed on this venue', '', list(d.assets, (a) => `${link(a.cusip, a.name)} <span class="${MONO} text-secondary">${esc(a.product_code)}${a.ticker ? ' · ' + esc(a.ticker) : ''}</span>`, 'No instruments are listed on this venue.'))] : null,
    };
  },
  async gics(r) {
    const chain = gicsChain(r);
    const children = (cache || []).filter((n) => n.parent_code === r.code);
    return {
      subtitle: `${pill(r.level)}<span class="${MONO}">${esc(r.code)}</span>`,
      details:
        section('Hierarchy', '', chain.map((n) => field(n.level, `${code(n.code, 'font-semibold')} ${esc(n.name)}`, { span2: true })).join('')) +
        (r.description ? section('Definition', '', field('Description', esc(r.description), { span2: true })) : ''),
      related: children.length
        ? [`${childLevel(r)} (${num(children.length)})`, section(childLevel(r), '', list(children, (n) => `${code(n.code, 'font-semibold')} ${esc(n.name)}`, ''))]
        : null,
    };
  },
  async taxonomy(r) {
    const instruments = await api(`/reference/taxonomy/${r.code}/instruments`);
    return {
      subtitle: `<span>${esc(r.asset_class_name)} › ${esc(r.base_product_name)}</span>`,
      details:
        section('Classification', '', field('Asset class', `${esc(r.asset_class_code)} ${esc(r.asset_class_name)}`) + field('Base product', `${esc(r.base_product_code)} ${esc(r.base_product_name)}`) + field('Description', esc(r.description), { span2: true }) + field('Taxonomy source', pill(r.source)) + field('Subtype table', esc(r.subtype_table), { mono: true, span2: true })) +
        section('Regulatory attributes', '', held('CFTC asset class', r.cftc_asset_class && esc(r.cftc_asset_class)) + held('MiFID II category', r.mifid_category && esc(r.mifid_category)) + held('Desk family', r.desk_family && esc(r.desk_family)) + held('ISDA path', r.isda_path && esc(r.isda_path)) + (r.cftc_asset_class || r.mifid_category ? '' : field('Applicability', 'Not defined for spot, fund and bond codes.', { span2: true }))) +
        section('CASM usage', '', field('Instruments with this code', num(r.instruments))),
      related: [`Instruments (${num(r.instruments)})`, section('Instruments (first 50)', '', list(instruments, (a) => `${link(a.cusip, a.name)} <span class="${MONO} text-secondary">${esc(a.ticker || '')}${a.mic ? ' · ' + esc(a.mic) : ''}</span>`, 'No instrument carries this product code.'))],
    };
  },
  async countries(r) {
    const issuers = await api(`/reference/countries/${r.alpha2}/issuers`);
    return {
      subtitle: code(r.alpha2, 'text-secondary'),
      details:
        section('ISO 3166-1', '', field('Alpha-2 code', esc(r.alpha2), { mono: true }) + field('English short name', esc(r.name))) +
        section('CASM usage', '', field('Issuers incorporated here', num(r.issuers)) + field('Loaded venues here', num(r.venues))),
      related: [`Issuers (${num(r.issuers)})`, section('Issuers (first 100)', '', list(issuers, (i) => `${esc(i.legal_name)} <span class="${MONO} text-secondary">CIK ${esc(i.cik)} · ${esc(i.issuer_type)}</span>`, 'No issuer is incorporated in this country.'))],
    };
  },
  async isda(r) {
    return { subtitle: code(`row ${r.isda_row_no}`, 'text-secondary'), details: section('ISDA row', '', field('Base product', esc(r.base_product)) + held('Sub-product', r.sub_product && esc(r.sub_product)) + held('Transaction type', r.transaction_type && esc(r.transaction_type))), related: null };
  },
};

let state;
let root;
let sets;
let cache;

export async function renderReference(container, setId) {
  root = container;
  if (!SETS[setId]) throw new Error(`Unknown reference set ${setId}`);
  sets = await api('/reference/sets');
  state = { setId, q: '', sort: null, direction: 'asc', selected: null, tab: 'details', loaded: false, level: '', country: '', venue_type: '', facets: null, rows: [], total: 0 };
  cache = null;
  const meta = sets.find((s) => s.id === setId);
  const cfg = SETS[setId];
  const rail = sets.map((s) => {
    const on = s.id === setId;
    return `<a href="#/reference/${s.id}" class="flex items-center justify-between px-space-md py-space-sm ${on ? 'bg-surface-container-lowest font-semibold text-on-surface' : 'hover:bg-surface-container text-on-surface-variant'}" ${on ? 'style="box-shadow: inset 3px 0 0 0 #0f62fe"' : ''}><span class="flex items-center gap-space-xs"><span class="material-symbols-outlined text-[18px] ${on ? 'text-primary' : 'text-secondary'}">${s.icon}</span><span class="font-body-md text-body-md">${esc(s.label)}</span></span><span class="px-1.5 py-0.5 whitespace-nowrap font-code-sm text-code-sm ${on ? 'bg-primary-fixed text-on-primary-fixed' : 'bg-surface-container text-secondary'}">${esc(s.badge)}</span></a>`;
  }).join('');
  root.innerHTML = `<div class="flex flex-col lg:flex-row w-full lg:h-[calc(100vh-48px)]">
    <aside class="w-full lg:w-60 shrink-0 bg-surface-container-low flex flex-col justify-between overflow-y-auto"><div><div class="px-space-md py-space-sm border-b border-surface-container-high font-label-sm text-label-sm tracking-wider uppercase text-secondary font-semibold">Reference Sets</div><nav class="flex flex-col py-space-xs">${rail}</nav></div>
      <div class="p-space-md m-space-sm bg-surface-container-lowest border border-surface-container-high"><div class="flex items-center gap-space-xs mb-space-xs"><span class="w-2 h-2 rounded-full bg-[#198038]"></span><span class="font-label-sm text-label-sm font-semibold uppercase tracking-wider">Source pinned</span></div><div class="${MONO} text-secondary truncate" title="${esc(meta.file)}">${esc(meta.file)}</div><div class="${MONO} text-secondary truncate" title="${esc(meta.sha256)}">SHA-256 ${esc((meta.sha256 || 'not found').slice(0, 12))}…</div></div></aside>
    <main class="flex-1 flex flex-col xl:flex-row items-stretch min-w-0 min-h-0 bg-surface-container-lowest">
      <section class="flex-1 flex flex-col min-w-0 min-h-0">
        <div class="shrink-0 px-space-lg py-space-md flex flex-col gap-space-sm border-b border-outline-variant">${pageTitle(cfg.title, cfg.badges.map((b) => pill(b, 'bg-secondary-container text-on-surface')).join(''))}<div id="filterBar" class="flex flex-wrap items-center gap-space-sm"></div></div>
        <div id="refTable" class="flex-1 min-h-0 overflow-auto"></div><div id="refRowCount"></div></section>
      <aside id="refInspector" class="w-full xl:w-[480px] shrink-0 min-h-0 bg-surface-container-lowest border-l border-outline-variant flex flex-col"></aside></main></div>`;
  drawFilterBar();
  await load();
}

function drawFilterBar() {
  const cfg = SETS[state.setId];
  const f = state.facets;
  const box = 'h-8 bg-surface-container-lowest border border-outline-variant px-space-sm font-body-md text-body-md outline-none';
  const select = (id, label, values, current) => `<select id="${id}" class="${box}"><option value="">${label}</option>${(values || []).map((v) => `<option ${v === current ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>`;
  const venueFilters = state.setId === 'venues'
    ? `<select id="fLoaded" class="${box}"><option value="false" ${state.loaded ? '' : 'selected'}>Full ISO 10383 registry</option><option value="true" ${state.loaded ? 'selected' : ''}>Loaded in CASM</option></select>${select('fCountry', 'All countries', f && f.countries, state.country)}${select('fType', 'All types', f && f.types, state.venue_type)}`
    : '';
  const gicsFilters = state.setId === 'gics'
    ? `<select id="fLevel" class="${box}"><option value="">All levels</option>${['Sector', 'Industry Group', 'Industry', 'Sub-Industry'].map((l) => `<option ${l === state.level ? 'selected' : ''}>${l}</option>`).join('')}</select>`
    : '';
  const bar = root.querySelector('#filterBar');
  bar.innerHTML = `<div class="flex items-center w-full max-w-xl bg-surface-container-low px-space-sm h-8 border border-outline-variant focus-within:border-primary-container"><span class="material-symbols-outlined text-[18px] text-secondary mr-space-xs">search</span><input id="refSearch" value="${esc(state.q)}" class="w-full bg-transparent outline-none font-body-md text-body-md placeholder:text-secondary" placeholder="${esc(cfg.search)}" type="text"></div>${venueFilters}${gicsFilters}`;
  const reload = () => load(false);
  const search = bar.querySelector('#refSearch');
  search.addEventListener('input', debounce(() => { state.q = search.value; reload(); }));
  const bind = (id, key, parse = (v) => v) => bar.querySelector(id)?.addEventListener('change', (e) => { state[key] = parse(e.target.value); reload(); });
  bind('#fLoaded', 'loaded', (v) => v === 'true');
  bind('#fCountry', 'country');
  bind('#fType', 'venue_type');
  bind('#fLevel', 'level');
}

async function fetchRows() {
  const cfg = SETS[state.setId];
  if (state.setId === 'venues') {
    const r = await api('/reference/venues', { q: state.q, country: state.country, venue_type: state.venue_type, loaded: state.loaded, sort: state.sort || 'mic', direction: state.direction });
    state.facets = r.facets;
    return { rows: r.items, total: r.total };
  }
  cache = cache || (await cfg.load());
  const needle = state.q.trim().toLowerCase();
  const inLevel = state.setId === 'gics' && state.level ? cache.filter((r) => r.level === state.level) : cache;
  const rows = needle ? inLevel.filter((r) => Object.values(r).some((v) => String(v ?? '').toLowerCase().includes(needle))) : inLevel.slice();
  if (state.sort) rows.sort((a, b) => (String(a[state.sort] ?? '') > String(b[state.sort] ?? '') ? 1 : -1) * (state.direction === 'asc' ? 1 : -1));
  return { rows, total: rows.length };
}

async function load(rebuildBar = true) {
  const token = (state.loadToken = (state.loadToken || 0) + 1);
  const { rows, total } = await fetchRows();
  if (token !== state.loadToken) return; // a newer request has already replaced this one
  state.rows = rows;
  state.total = total;
  if (rebuildBar && state.setId === 'venues') {
    const q = root.querySelector('#refSearch').value;
    drawFilterBar();
    root.querySelector('#refSearch').value = q;
  }
  drawTable();
  const key = SETS[state.setId].key;
  if (rows.length && !rows.some((r) => String(r[key]) === state.selected)) select(rows[0]);
  else if (!rows.length) root.querySelector('#refInspector').innerHTML = '<div class="p-space-lg text-secondary font-body-md text-body-md">No rows match.</div>';
}

function drawTable() {
  const cfg = SETS[state.setId];
  const head = cfg.columns.map(([key, label]) => {
    const sortKey = cfg.sortKeys ? cfg.sortKeys[key] : key;
    const icon = state.sort === sortKey ? `<span class="material-symbols-outlined text-[14px] text-primary">${state.direction === 'asc' ? 'arrow_upward' : 'arrow_downward'}</span>` : '<span class="material-symbols-outlined text-[14px]">unfold_more</span>';
    return `<th class="${TABLE_HEAD_CELL} cursor-pointer hover:bg-surface-container-highest" data-sort="${sortKey}"><div class="flex items-center gap-1">${label}${icon}</div></th>`;
  }).join('');
  const body = state.rows.map((r) => {
    const id = String(r[cfg.key]);
    return `<tr data-key="${esc(id)}" class="${TABLE_BODY_ROW} ${id === state.selected ? 'row-selected' : ''}">${cfg.columns.map(([, , render]) => `<td class="${TABLE_CELL}">${render(r)}</td>`).join('')}</tr>`;
  }).join('');
  root.querySelector('#refTable').innerHTML = `<table class="${TABLE_CLASS}"><thead><tr class="${TABLE_HEAD_ROW}">${head}</tr></thead><tbody class="font-body-md text-body-md text-on-surface">${body}</tbody></table>`;
  root.querySelector('#refRowCount').innerHTML = (state.setId === 'venues' && !state.loaded ? countStrip(state.total, 'venue in the ISO 10383 registry', 'venues in the ISO 10383 registry') : (state.setId === 'venues' ? countStrip(state.total, 'venue loaded in CASM', 'venues loaded in CASM') : countStrip(state.total, 'row', 'rows')));
  root.querySelectorAll('#refTable th[data-sort]').forEach((th) => th.addEventListener('click', () => {
    state.direction = state.sort === th.dataset.sort && state.direction === 'asc' ? 'desc' : 'asc';
    state.sort = th.dataset.sort;
    load(false);
  }));
  root.querySelectorAll('#refTable tbody tr').forEach((tr) => tr.addEventListener('click', () => select(state.rows.find((r) => String(r[cfg.key]) === tr.dataset.key))));
}

async function select(row) {
  const cfg = SETS[state.setId];
  state.selected = String(row[cfg.key]);
  state.tab = 'details';
  root.querySelectorAll('#refTable tbody tr').forEach((tr) => tr.classList.toggle('row-selected', tr.dataset.key === state.selected));
  const token = (state.selectToken = (state.selectToken || 0) + 1);
  const detail = await INSPECT[state.setId](row);
  if (token !== state.selectToken) return; // a newer selection has already replaced this one
  drawInspector(row, detail);
}

function drawInspector(row, detail) {
  const cfg = SETS[state.setId];
  const meta = sets.find((s) => s.id === state.setId);
  const note = state.setId === 'taxonomy' ? 'Defined in the 02_products_taxonomy.sql migration.' : 'Loaded by a seed migration; the file is pinned and read-only.';
  const lineage = section('Source and lineage', '', field('Source file', esc(meta.file), { mono: true, span2: true }) + field('SHA-256', esc(meta.sha256 || 'file not found'), { mono: true, span2: true }) + field('Note', note, { span2: true }));
  const tabs = [['details', 'Details', detail.details], ...(detail.related ? [['related', detail.related[0], detail.related[1]]] : []), ['lineage', 'Lineage', lineage]];
  const title = esc(row.name || row.sub_industry_name || row.code || row.base_product || row[cfg.key]);
  const el = root.querySelector('#refInspector');
  el.innerHTML = inspectorFrame({ title, subtitle: detail.subtitle, tabs, active: state.tab });
  el.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', () => { state.tab = b.dataset.tab; drawInspector(row, detail); }));
  wireCopy(el);
}
