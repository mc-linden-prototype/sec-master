// Shared helpers: escaping, formatting and the small components used on both screens.

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ESCAPES[c]);

export const dash = (value) =>
  value === null || value === undefined || value === ''
    ? '<span class="text-outline">—</span>'
    : esc(value);

export const num = (value) => Number(value ?? 0).toLocaleString('en-US');

const DERIVATIVE_STYLE = 'bg-tertiary-fixed text-on-tertiary-fixed';

export function productPill(code) {
  let style = DERIVATIVE_STYLE;
  if (/RIGHTS|WARRANT|UNIT/.test(code)) style = DERIVATIVE_STYLE;
  else if (code.startsWith('FI-')) style = 'bg-secondary-fixed text-on-secondary-fixed-variant';
  else if (code.startsWith('EQ-SPT') || code.startsWith('EQ-FND')) style = 'bg-primary-fixed text-on-primary-fixed';
  return `<span class="px-2 py-0.5 ${style} font-code-sm text-code-sm whitespace-nowrap">${esc(code)}</span>`;
}

const CONFIDENCE = {
  HIGH: { dot: 'bg-[#198038]', label: 'High', pct: 90 },
  MEDIUM: { dot: 'bg-[#f1c21b]', label: 'Medium', pct: 60 },
  LOW: { dot: 'bg-[#8d8d8d]', label: 'Default venue', pct: 25 },
};

export function confidenceDot(level) {
  const c = CONFIDENCE[level];
  if (!c) return dash(null);
  return `<span class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full ${c.dot}"></span>${c.label}</span>`;
}

export function confidenceBar(level) {
  const c = CONFIDENCE[level] || { pct: 0 };
  return `<div class="flex items-center gap-1.5"><div class="h-1.5 w-16 bg-surface-container overflow-hidden"><div class="h-full bg-primary" style="width:${c.pct}%"></div></div><span class="font-label-sm text-label-sm text-on-surface">${esc(level || '—')}</span></div>`;
}

export const pill = (text, extra = 'bg-surface-container text-on-surface') =>
  `<span class="px-1.5 py-0.5 ${extra} font-code-sm text-code-sm">${esc(text)}</span>`;

export function field(label, valueHtml, { span2 = false, mono = false } = {}) {
  const size = mono ? 'font-code-md text-code-md' : 'font-body-md text-body-md';
  return `<div class="flex flex-col ${span2 ? 'col-span-2' : ''}"><span class="font-label-sm text-label-sm text-secondary">${esc(label)}</span><span class="${size} text-on-surface break-words">${valueHtml}</span></div>`;
}

// A titled block of label/value fields. Only blocks with something to say should be rendered.
export function section(title, _icon, bodyHtml) {
  return `<div class="flex flex-col gap-space-xs p-space-sm bg-surface-container-lowest border border-surface-container-high"><div class="font-label-sm text-label-sm text-secondary uppercase tracking-wider font-semibold">${esc(title)}</div><div class="grid grid-cols-2 gap-x-space-md gap-y-space-sm">${bodyHtml}</div></div>`;
}

// Shared page chrome so every screen has the same title row, table and inspector.
export const TABLE_CLASS = 'w-full text-left border-separate border-spacing-0';
export const TABLE_HEAD_ROW = 'select-none';
export const TABLE_BODY_ROW = 'h-9 cursor-pointer hover:bg-surface-container-low';
// Grid lines both ways: a right and a bottom border on every cell. The header stays pinned while rows scroll.
export const TABLE_HEAD_CELL = 'sticky top-0 z-10 h-10 bg-surface-container-high px-space-sm font-label-sm text-label-sm font-semibold whitespace-nowrap border-r border-b border-outline-variant';
export const TABLE_CELL = 'px-space-sm whitespace-nowrap border-r border-b border-outline-variant/60';

export const pageTitle = (title, extraHtml = '') =>
  `<div class="flex items-center flex-wrap gap-space-sm"><h1 class="font-headline-sm text-headline-sm font-semibold">${esc(title)}</h1>${pill('READ-ONLY', 'bg-surface-container text-secondary')}${extraHtml}</div>`;

// Inspector: title, subtitle, tab strip and a scrolling body. `tabs` is [[id, label, html], ...].
export function inspectorFrame({ title, subtitle, tabs, active }) {
  const buttons = tabs.map(([id, label]) => `<button data-tab="${id}" class="h-full px-space-md font-label-md text-label-md ${active === id ? 'font-semibold text-on-surface tab-active' : 'text-secondary hover:text-on-surface'}">${esc(label)}</button>`).join('');
  const body = (tabs.find(([id]) => id === active) || tabs[0])[2];
  return `<div class="px-space-md py-space-sm bg-surface-container-low border-b border-surface-container-high flex flex-col gap-1"><h2 class="font-headline-sm text-headline-sm font-semibold leading-tight">${title}</h2><div class="flex items-center gap-space-xs font-body-md text-body-md text-secondary">${subtitle}</div></div>
    <div class="h-10 shrink-0 bg-surface-container-lowest flex items-center border-b border-surface-container-high overflow-x-auto">${buttons}</div>
    <div class="flex-1 min-h-0 p-space-md flex flex-col gap-space-sm overflow-y-auto">${body}</div>`;
}

// Every grid shows all of its rows; this strip only says how many there are.
export function countStrip(total, singular = 'item', plural = `${singular}s`) {
  return `<div class="shrink-0 w-full bg-surface-container-lowest px-space-md h-9 border-t border-outline-variant flex items-center font-body-md text-body-md text-secondary">${num(total)} ${esc(total === 1 ? singular : plural)}</div>`;
}

export const copyButton = (text) =>
  `<button data-copy="${esc(text)}" class="text-secondary hover:text-on-surface" title="Copy" type="button"><span class="material-symbols-outlined text-[12px]">content_copy</span></button>`;

export function wireCopy(root) {
  root.querySelectorAll('[data-copy]').forEach((b) =>
    b.addEventListener('click', () => navigator.clipboard?.writeText(b.dataset.copy)),
  );
}

export function debounce(fn, ms = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

export const sortIcon = (state, key) =>
  state.sort === key
    ? `<span class="material-symbols-outlined text-[14px] text-primary">${state.direction === 'asc' ? 'arrow_upward' : 'arrow_downward'}</span>`
    : '<span class="material-symbols-outlined text-[14px]">unfold_more</span>';
