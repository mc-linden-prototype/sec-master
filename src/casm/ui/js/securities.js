// Securities tab: instruments, issuers and the exception queue, with an inspector for the selected row.
// Every grid shows all of its rows; nothing is paged.

import { api } from './api.js';
import {
  TABLE_BODY_ROW,
  TABLE_CELL,
  TABLE_CLASS,
  TABLE_HEAD_CELL,
  TABLE_HEAD_ROW,
  confidenceBar,
  confidenceDot,
  copyButton,
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
  sortIcon,
  wireCopy,
} from './util.js';

const MONO = 'font-code-md text-code-md';
const SCOPES = [['all', 'All'], ['cusip', 'CUSIP'], ['figi', 'FIGI'], ['ticker', 'Ticker'], ['name', 'Name']];
const VIEWS = [['instruments', 'Instruments'], ['issuers', 'Issuers'], ['exceptions', 'Exception queue']];
const PLACEHOLDER = {
  instruments: 'Search by CUSIP, FIGI, ticker or name',
  issuers: 'Search by issuer name, CIK or CUSIP prefix',
  exceptions: 'The exception queue is filtered by reason below',
};
const COLUMNS = [
  ['name', 'Security Name', 'name', (r, on) => `<td class="${TABLE_CELL} ${on ? 'text-primary font-semibold' : 'font-medium'}">${esc(r.name)}</td>`],
  ['product_code', 'Asset Class', 'product_code', (r) => `<td class="${TABLE_CELL}">${productPill(r.product_code)}</td>`],
  ['issuer', 'Issuer', null, (r) => `<td class="${TABLE_CELL}">${esc(r.issuer)}</td>`],
  ['underlying', 'Und. Security', 'underlying', (r) => `<td class="${TABLE_CELL}">${dash(r.underlying_name)}</td>`],
  ['ticker', 'Ticker', 'ticker', (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.ticker)}</td>`],
  ['bbg_ticker', 'Bloomberg Ticker', 'bbg_ticker', (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.bbg_ticker)}</td>`],
  ['mic', 'Venue (MIC)', 'mic', (r) => `<td class="${TABLE_CELL} ${MONO} text-secondary">${dash(r.mic)}</td>`],
  ['cusip', 'CUSIP', 'cusip', (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.cusip)}</td>`],
  ['figi', 'FIGI', 'figi', (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.figi)}</td>`],
  ['composite_figi', 'Composite FIGI', 'composite_figi', (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.composite_figi)}</td>`],
  ['cik', 'Issuer CIK', 'cik', (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.cik)}</td>`],
  ['country', 'Country', 'country', (r) => `<td class="${TABLE_CELL}">${dash(r.country)}</td>`],
  ['confidence', 'Venue Confidence', 'confidence', (r) => `<td class="${TABLE_CELL}">${confidenceDot(r.confidence)}</td>`],
];
const ISSUER_COLUMNS = [
  ['name', 'Issuer', 'name', (r, on) => `<td class="${TABLE_CELL} ${on ? 'text-primary font-semibold' : 'font-medium'}">${esc(r.legal_name)}</td>`],
  ['type', 'Type', 'type', (r) => `<td class="${TABLE_CELL}">${pill(r.issuer_type)}</td>`],
  ['country', 'Country', 'country', (r) => `<td class="${TABLE_CELL}">${dash(r.country_name)}</td>`],
  ['cik', 'CIK', 'cik', (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.cik)}</td>`],
  ['sic', 'SIC', null, (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.sic)}</td>`],
  ['cusip6', 'CUSIP issuer prefix', null, (r) => `<td class="${TABLE_CELL} ${MONO}">${dash(r.cusip6)}</td>`],
  ['instruments', 'Instruments', 'instruments', (r) => `<td class="${TABLE_CELL} text-right">${num(r.instruments)}</td>`],
];
const TERM_LABELS = {
  coupon_rate: 'Coupon rate',
  maturity_date: 'Maturity date',
  is_144a: '144A restricted',
  conversion_ratio: 'Conversion ratio',
  currency: 'Currency',
  share_class: 'Share class',
  underlying_unresolved: 'Underlying issuer unresolved',
  exercise_price: 'Exercise price',
  exercise_ratio: 'Exercise ratio',
  expiry_date: 'Expiry date',
  fund_structure: 'Fund structure',
  tracked_index_name: 'Tracked index',
  settlement_type: 'Settlement',
};

let state;
let page = { items: [], total: 0 };
let root;

export async function renderSecurities(container, params) {
  root = container;
  state = { q: params.get('q') || '', scope: 'all', product_code: '', mic: '', view: 'instruments', reason: '', selectedId: null, tab: 'details', trail: [], selectToken: 0, loadToken: 0,
    sort: { instruments: 'name', issuers: 'name' }, direction: { instruments: 'asc', issuers: 'asc' } };
  const filters = await api('/securities/filters');
  root.innerHTML = shell(filters);
  wireShell();
  await loadList();
}

function shell(filters) {
  const options = (rows, value, label) => rows.map((r) => `<option value="${esc(r[value])}">${esc(r[value])} · ${esc(label(r))} (${num(r.count)})</option>`).join('');
  const selectClass = 'h-8 w-44 truncate bg-surface-container-lowest border border-outline-variant px-space-sm font-body-md text-body-md outline-none';
  return `<div class="flex flex-col w-full xl:h-[calc(100vh-48px)]">
  <div class="shrink-0 w-full bg-surface-container-lowest px-space-lg py-space-md flex flex-col gap-space-sm border-b border-outline-variant">
    <div class="flex flex-wrap items-center justify-between gap-space-sm">${pageTitle('Securities Master Directory')}
      <div class="inline-flex bg-surface-container p-0.5 font-label-sm text-label-sm">${VIEWS.map(([id, label]) => `<button data-view="${id}" class="px-space-sm py-1">${label}</button>`).join('')}</div></div>
    <div class="flex flex-wrap items-center gap-space-sm">
      <div class="flex items-center w-full max-w-md bg-surface-container-low px-space-sm h-8 border border-outline-variant focus-within:border-primary-container">
        <span class="material-symbols-outlined text-[18px] text-secondary mr-space-xs">search</span>
        <input id="searchInput" value="${esc(state.q)}" class="w-full bg-transparent outline-none font-body-md text-body-md placeholder:text-secondary" type="text">
        <span id="detected" class="px-1.5 bg-primary-fixed text-on-primary-fixed font-code-sm text-code-sm ml-space-xs whitespace-nowrap hidden"></span></div>
      <div data-instrument-only class="inline-flex items-center gap-1 font-label-sm text-label-sm">${SCOPES.map(([id, label]) => `<button data-scope="${id}" class="px-space-sm h-8">${label}</button>`).join('')}</div>
      <select data-instrument-only id="fProduct" class="${selectClass}"><option value="">All asset classes</option>${options(filters.product_codes, 'code', (r) => r.description)}</select>
      <select data-instrument-only id="fMic" class="${selectClass}"><option value="">All venues</option>${options(filters.mics, 'mic', (r) => r.name)}</select>
      <button id="clearAll" class="text-primary hover:underline font-label-md text-label-md" type="button">Clear all</button></div>
    <div id="note" class="hidden font-body-md text-body-md text-on-surface p-space-xs bg-surface-container-low border-l-2 border-primary-container"></div>
  </div>
  <div class="flex-1 min-h-0 w-full flex flex-col xl:flex-row items-stretch bg-surface-container-lowest">
    <div class="flex-1 min-w-0 min-h-0 flex flex-col"><div id="tableArea" class="flex-1 min-h-0 overflow-auto"></div><div id="rowCount"></div></div>
    <aside id="inspector" class="w-full xl:w-[480px] shrink-0 min-h-0 bg-surface-container-lowest flex flex-col border-l border-outline-variant"></aside>
  </div></div>`;
}

function paintToggles() {
  const search = root.querySelector('#searchInput');
  search.placeholder = PLACEHOLDER[state.view];
  search.disabled = state.view === 'exceptions';
  root.querySelectorAll('[data-scope]').forEach((b) => {
    b.className = `px-space-sm h-8 ${b.dataset.scope === state.scope ? 'bg-on-surface text-surface-container-lowest' : 'bg-surface-container-low hover:bg-surface-container text-on-surface'}`;
  });
  root.querySelectorAll('[data-view]').forEach((b) => {
    b.className = `px-space-sm py-1 ${b.dataset.view === state.view ? 'bg-surface-container-lowest text-on-surface shadow-xs' : 'text-secondary hover:text-on-surface'}`;
  });
  root.querySelectorAll('[data-instrument-only]').forEach((el) => el.classList.toggle('hidden', state.view !== 'instruments'));
}

function wireShell() {
  const search = root.querySelector('#searchInput');
  search.addEventListener('input', debounce(() => { state.q = search.value; loadList(); }));
  root.querySelectorAll('[data-scope]').forEach((b) => b.addEventListener('click', () => { state.scope = b.dataset.scope; loadList(); }));
  root.querySelectorAll('[data-view]').forEach((b) => b.addEventListener('click', () => { state.view = b.dataset.view; state.selectedId = null; state.tab = 'details'; loadList(); }));
  root.querySelector('#fProduct').addEventListener('change', (e) => { state.product_code = e.target.value; loadList(); });
  root.querySelector('#fMic').addEventListener('change', (e) => { state.mic = e.target.value; loadList(); });
  root.querySelector('#clearAll').addEventListener('click', () => {
    Object.assign(state, { q: '', scope: 'all', product_code: '', mic: '', reason: '' });
    search.value = '';
    root.querySelector('#fProduct').value = '';
    root.querySelector('#fMic').value = '';
    loadList();
  });
}

const inspectorEl = () => root.querySelector('#inspector');
const empty = (text) => { inspectorEl().innerHTML = `<div class="p-space-lg font-body-md text-body-md text-secondary">${text}</div>`; };

function fetchList(view) {
  if (view === 'exceptions') return api('/exceptions', { reason: state.reason });
  if (view === 'issuers') return api('/issuers', { q: state.q, sort: state.sort.issuers, direction: state.direction.issuers });
  return api('/securities', { q: state.q, scope: state.scope, product_code: state.product_code, mic: state.mic, sort: state.sort.instruments, direction: state.direction.instruments });
}

async function loadList() {
  paintToggles();
  const view = state.view;
  inspectorEl().classList.toggle('hidden', view === 'exceptions');
  const detected = root.querySelector('#detected');
  const note = root.querySelector('#note');
  detected.classList.add('hidden');
  note.classList.add('hidden');
  const token = (state.loadToken += 1);
  const result = await fetchList(view);
  if (token !== state.loadToken) return; // a newer request has already replaced this one
  page = result;
  if (view === 'exceptions') {
    drawExceptions();
    return;
  }
  if (view === 'instruments') {
    detected.textContent = page.detected ? `Detected: ${page.detected}` : '';
    detected.classList.toggle('hidden', !page.detected);
    const notHeld = page.total === 0 && ['ISIN', 'SEDOL'].includes(page.detected);
    note.textContent = page.note || (notHeld ? `No ${page.detected} is held in this prototype (no free authoritative source).` : '');
    note.classList.toggle('hidden', !note.textContent);
  }
  drawGrid();
  const key = view === 'issuers' ? 'issuer_id' : 'instrument_id';
  const listed = page.items.some((r) => r[key] === state.selectedId);
  if (!listed && page.items.length) select(page.items[0][key]);
  else if (!page.items.length) empty(`No ${view === 'issuers' ? 'issuer' : 'instrument'} matches. Clear the filters or change the search.`);
}

function drawGrid() {
  const issuers = state.view === 'issuers';
  const columns = issuers ? ISSUER_COLUMNS : COLUMNS;
  const key = issuers ? 'issuer_id' : 'instrument_id';
  const sort = { by: state.sort[state.view], direction: state.direction[state.view] };
  const head = columns.map(([, label, sortKey]) => `<th class="${TABLE_HEAD_CELL} ${sortKey ? 'cursor-pointer hover:bg-surface-container-highest' : ''}" ${sortKey ? `data-sort="${sortKey}"` : ''}><div class="flex items-center gap-1">${label}${sortKey ? sortIcon({ sort: sort.by, direction: sort.direction }, sortKey) : ''}</div></th>`).join('');
  const rows = page.items.map((r) => {
    const on = r[key] === state.selectedId;
    return `<tr data-id="${r[key]}" class="${TABLE_BODY_ROW} ${on ? 'row-selected' : ''}">${columns.map(([, , , render]) => render(r, on)).join('')}</tr>`;
  }).join('');
  root.querySelector('#tableArea').innerHTML = `<table class="${TABLE_CLASS}"><thead><tr class="${TABLE_HEAD_ROW}">${head}</tr></thead><tbody class="font-body-md text-body-md text-on-surface">${rows || `<tr><td colspan="${columns.length}" class="p-space-lg text-secondary">No results.</td></tr>`}</tbody></table>`;
  root.querySelector('#rowCount').innerHTML = (issuers ? countStrip(page.total, 'issuer', 'issuers') : countStrip(page.total, 'security', 'securities'));
  root.querySelectorAll('[data-sort]').forEach((th) => th.addEventListener('click', () => {
    const view = state.view;
    state.direction[view] = state.sort[view] === th.dataset.sort && state.direction[view] === 'asc' ? 'desc' : 'asc';
    state.sort[view] = th.dataset.sort;
    loadList();
  }));
  root.querySelectorAll('tbody tr[data-id]').forEach((tr) => tr.addEventListener('click', () => select(Number(tr.dataset.id))));
}

function drawExceptions() {
  const chips = page.reasons.map((r) => `<button data-reason="${r.reason_code}" class="px-space-sm h-8 ${state.reason === r.reason_code ? 'bg-on-surface text-surface-container-lowest' : 'bg-surface-container-low hover:bg-surface-container text-on-surface'}">${esc(r.reason_code)} (${r.count})</button>`).join('');
  const heads = ['Filing row', 'Name of issuer', 'Class', 'CUSIP', 'Reason', 'Detail'].map((h) => `<th class="${TABLE_HEAD_CELL}">${h}</th>`).join('');
  const rows = page.items.map((r) => `<tr class="h-9"><td class="${TABLE_CELL} ${MONO}">${r.row_number}</td><td class="${TABLE_CELL}">${esc(r.name_of_issuer)}</td><td class="${TABLE_CELL}">${esc(r.title_of_class)}</td><td class="${TABLE_CELL} ${MONO}">${esc(r.cusip)}</td><td class="${TABLE_CELL}">${pill(r.reason_code)}</td><td class="${TABLE_CELL} text-secondary">${esc(r.detail)}</td></tr>`).join('');
  root.querySelector('#tableArea').innerHTML = `<div class="px-space-lg py-space-sm flex flex-wrap items-center gap-space-sm border-b border-outline-variant font-label-sm text-label-sm"><span class="font-body-md text-body-md text-secondary">Filing rows that could not become an instrument, with the reason.</span>${chips}</div><table class="${TABLE_CLASS}"><thead><tr class="${TABLE_HEAD_ROW}">${heads}</tr></thead><tbody class="font-body-md text-body-md">${rows}</tbody></table>`;
  root.querySelector('#rowCount').innerHTML = countStrip(page.total, 'queued row', 'queued rows');
  root.querySelectorAll('[data-reason]').forEach((b) => b.addEventListener('click', () => { state.reason = state.reason === b.dataset.reason ? '' : b.dataset.reason; loadList(); }));
}

// `link` is true when the user followed an underlying or breadcrumb link rather than picking a grid row.
async function select(id, { link = false } = {}) {
  state.selectedId = id;
  root.querySelectorAll('tbody tr[data-id]').forEach((tr) => tr.classList.toggle('row-selected', Number(tr.dataset.id) === id));
  const token = (state.selectToken += 1);
  if (state.view === 'issuers') {
    const issuer = await api(`/issuers/${id}`);
    if (token === state.selectToken) drawIssuerInspector(issuer);
    return;
  }
  const detail = await api(`/securities/${id}`);
  if (token !== state.selectToken) return; // a newer selection has already replaced this one
  updateTrail(detail, link);
  drawInspector(detail);
}

// The trail starts at the grid row and grows with each link followed; following a link already in the trail
// (or a breadcrumb) cuts the trail back to it.
function updateTrail(detail, link) {
  const entry = { id: detail.instrument.instrument_id, code: detail.instrument.product_code, name: detail.instrument.name };
  if (!link) state.trail = [entry];
  else {
    const at = state.trail.findIndex((e) => e.id === entry.id);
    state.trail = at >= 0 ? state.trail.slice(0, at + 1) : [...state.trail, entry];
  }
}

// Earlier items are shortened to 10 characters and "..."; the security being viewed is shown in full.
const CRUMB_CHARS = 10;
const shorten = (name) => (name.length > CRUMB_CHARS ? `${name.slice(0, CRUMB_CHARS)}...` : name);

function breadcrumb() {
  if (state.trail.length < 2) return '';
  const last = state.trail.length - 1;
  const items = state.trail.map((e, i) => (i === last
    ? `<span class="font-semibold text-on-surface" title="${esc(e.name)} (${esc(e.code)})" aria-current="page">${esc(e.name)}</span>`
    : `<a href="#" data-crumb="${e.id}" class="text-primary hover:underline" title="${esc(e.name)} (${esc(e.code)})">${esc(shorten(e.name))}</a>`));
  return `<nav id="trail" aria-label="Navigation trail" class="shrink-0 px-space-md py-space-xs bg-surface-container-lowest border-b border-outline-variant flex flex-wrap items-center gap-space-xs font-body-md text-body-md">${items.join('<span class="text-outline">›</span>')}</nav>`;
}

function termValue(key, value) {
  if (key === 'coupon_rate') return `${Number(value).toFixed(3)}%`;
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return esc(value);
}

const held = (label, value, opts) => (value === null || value === undefined || value === '' ? '' : field(label, value, opts));

const securityLink = (r) => `<a href="#" data-open="${r.instrument_id}" class="text-primary hover:underline">${esc(r.name)}</a> ${productPill(r.product_code)}${r.ticker ? ` <span class="${MONO} text-secondary">${esc(r.ticker)}</span>` : ''}`;

function detailsTab(d) {
  const cusip = d.identifiers.find((i) => i.scheme === 'CUSIP');
  const figi = d.identifiers.find((i) => i.scheme === 'FIGI');
  const primary = d.listings.find((l) => l.is_primary) || d.listings[0];
  const t = d.taxonomy;
  const iss = d.issuer;
  const relations = d.underlying ? field('Underlying security', securityLink(d.underlying), { span2: true }) : '';
  const summary = section('Security', '',
    field('Product code', productPill(d.instrument.product_code)) +
    field('Taxonomy', `${esc(t.asset_class_name)} / ${esc(t.base_product_name)}`) +
    field('Issuer', `<a href="#" data-open-issuer="${iss.issuer_id}" class="text-primary hover:underline">${esc(iss.legal_name)}</a>`, { span2: true }) +
    (primary ? field('Primary listing', `${esc(primary.mic)} ${esc(primary.venue_name)}${primary.symbol ? ` · <span class="${MONO}">${esc(primary.symbol)}</span>` : ''}`, { span2: true }) : '') +
    relations);
  const identification = section('Identification', '',
    held('CUSIP', cusip && `<span class="font-semibold text-primary">${esc(cusip.value)}</span> ${copyButton(cusip.value)}`, { mono: true }) +
    held('FIGI (share class)', figi && `${esc(figi.value)} ${copyButton(figi.value)}`, { mono: true }) +
    field('Internal ID', `CASM-${String(d.instrument.instrument_id).padStart(6, '0')}`, { mono: true }));
  const issuer = section('Issuer', '',
    field('Issuer type', pill(iss.issuer_type)) + held('Country', iss.country_name && esc(iss.country_name)) +
    held('CIK', iss.cik && esc(iss.cik), { mono: true }) + held('SIC (EDGAR)', iss.sic && esc(iss.sic), { mono: true }) +
    field('Taxonomy source', esc(t.taxonomy_source)));
  const listings = d.listings.map((l) => section(`Listing · ${l.mic}`, '',
    field('Venue', `${esc(l.venue_name)} ${l.is_otc ? pill('OTC / unlisted', 'bg-secondary-container text-on-surface') : ''} ${l.is_primary ? pill('PRIMARY', 'bg-primary-fixed text-on-primary-fixed') : ''}`, { span2: true }) +
    held('Symbol', l.symbol && esc(l.symbol), { mono: true }) + held('Lot size', l.lot_size && num(l.lot_size), { mono: true }) +
    held('Composite FIGI', l.composite_figi && esc(l.composite_figi), { mono: true, span2: true }) +
    field('Venue confidence', confidenceBar(l.confidence)) + field('Source · as of', `${esc(l.source)} · ${esc(l.as_of)}`, { mono: true }))).join('');
  const termRows = Object.entries(d.terms || {}).filter(([k, v]) => TERM_LABELS[k] && v !== null && v !== undefined && !(k === 'underlying_unresolved' && v === false)).map(([k, v]) => field(TERM_LABELS[k], termValue(k, v), { mono: true })).join('');
  const terms = termRows ? section('Terms & Conditions', '', termRows) : '';
  return summary + identification + issuer + listings + terms;
}

function governanceTab(d) {
  const gaps = d.governance.gaps.map((g) => `<li class="flex items-center gap-space-xs"><span class="material-symbols-outlined text-[18px] text-secondary">remove_circle_outline</span><span>${esc(g)}</span></li>`).join('');
  return section('Attributes not held', '', `<ul class="col-span-2 flex flex-col gap-space-xs font-body-md text-body-md">${gaps}</ul>`);
}

function lineageTab(d) {
  const rows = d.lineage.map((l) => `<tr class="h-9"><td class="${TABLE_CELL}">${esc(l.datapoint)}</td><td class="${TABLE_CELL} ${MONO}">${esc(l.source)}</td><td class="${TABLE_CELL} ${MONO}">${esc(l.as_of)}</td></tr>`).join('');
  const heads = ['Datapoint', 'Source', 'As of'].map((h) => `<th class="${TABLE_HEAD_CELL}">${h}</th>`).join('');
  return `<div class="col-span-2 overflow-x-auto"><table class="${TABLE_CLASS} font-body-md text-body-md"><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

function wireInspector(el, rerender) {
  el.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', () => { state.tab = b.dataset.tab; rerender(); }));
  el.querySelectorAll('[data-open]').forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    // Inside an instrument the link extends the trail; from an issuer it opens the instrument fresh.
    if (state.view === 'instruments') select(Number(a.dataset.open), { link: true });
    else openInstrument(Number(a.dataset.open));
  }));
  el.querySelectorAll('[data-crumb]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); select(Number(a.dataset.crumb), { link: true }); }));
  el.querySelectorAll('[data-open-issuer]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); openIssuer(Number(a.dataset.openIssuer)); }));
  wireCopy(el);
}

function drawInspector(d) {
  const cusip = d.identifiers.find((i) => i.scheme === 'CUSIP');
  const tabs = [['details', 'Details', detailsTab(d)], ['governance', 'Governance', governanceTab(d)], ['lineage', 'Lineage', lineageTab(d)]];
  inspectorEl().innerHTML = breadcrumb() + inspectorFrame({
    title: esc(d.instrument.name),
    subtitle: `${productPill(d.instrument.product_code)}${cusip ? `<span>·</span><span class="${MONO}">${esc(cusip.value)}</span>` : ''}`,
    tabs,
    active: state.tab,
  });
  wireInspector(inspectorEl(), () => drawInspector(d));
}

function drawIssuerInspector(d) {
  const i = d.issuer;
  const instruments = d.instruments.map((r) => `<tr class="h-9"><td class="${TABLE_CELL}"><a href="#" data-open="${r.instrument_id}" class="text-primary hover:underline">${esc(r.name)}</a></td><td class="${TABLE_CELL}">${productPill(r.product_code)}</td><td class="${TABLE_CELL} ${MONO}">${dash(r.ticker)}</td><td class="${TABLE_CELL} ${MONO}">${dash(r.cusip)}</td></tr>`).join('');
  const heads = ['Instrument', 'Asset Class', 'Ticker', 'CUSIP'].map((h) => `<th class="${TABLE_HEAD_CELL}">${h}</th>`).join('');
  const details =
    section('Issuer', '', field('Legal name', esc(i.legal_name), { span2: true }) + field('Issuer type', pill(i.issuer_type)) + held('Country', i.country_name && esc(i.country_name)) + held('CIK', i.cik && esc(i.cik), { mono: true }) + held('SIC (EDGAR)', i.sic && esc(i.sic), { mono: true }) + held('CUSIP issuer prefix', i.cusip6 && esc(i.cusip6), { mono: true })) +
    `<div class="overflow-x-auto"><table class="${TABLE_CLASS} font-body-md text-body-md"><thead><tr>${heads}</tr></thead><tbody>${instruments}</tbody></table></div>`;
  const lineage = section('Source and lineage', '', field('Source', esc(i.source), { mono: true }) + field('As of', esc(i.as_of), { mono: true }));
  inspectorEl().innerHTML = inspectorFrame({
    title: esc(i.legal_name),
    subtitle: `${pill(i.issuer_type)}<span>·</span><span>${num(d.instruments.length)} instruments</span>`,
    tabs: [['details', 'Details', details], ['lineage', 'Lineage', lineage]],
    active: state.tab === 'lineage' ? 'lineage' : 'details',
  });
  wireInspector(inspectorEl(), () => drawIssuerInspector(d));
}

async function openInstrument(id) {
  state.view = 'instruments';
  state.q = '';
  state.scope = 'all';
  state.selectedId = id;
  root.querySelector('#searchInput').value = '';
  await loadList();
  await select(id);
  root.querySelector(`tr[data-id="${id}"]`)?.scrollIntoView({ block: 'center' });
}

async function openIssuer(id) {
  state.view = 'issuers';
  state.q = '';
  state.selectedId = id;
  root.querySelector('#searchInput').value = '';
  await loadList();
  await select(id);
  root.querySelector(`tr[data-id="${id}"]`)?.scrollIntoView({ block: 'center' });
}
