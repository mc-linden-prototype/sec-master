// Wiki tab: the wiki pages in reading order, rendered from markdown, mermaid diagrams included.

import { api } from './api.js';
import { esc } from './util.js';

const PAGE_LINK = /(?:^|\/)(\d_\d-[^/]+)\.md(?:#.*)?$/;
const INDEX_LINK = /(?:^|\/)README\.md(?:#.*)?$/;
let current = 0; // identifies the latest render, so a slow diagram never draws into a page the reader has left
let diagramCount = 0;

function linkTarget(href) {
  if (INDEX_LINK.test(href)) return 'index';
  const match = PAGE_LINK.exec(href);
  return match ? match[1] : null;
}

// Mermaid renders each diagram off-screen and returns the SVG; we insert it only if this render is still current.
async function drawMermaid(article, token) {
  const blocks = [...article.querySelectorAll('pre > code.language-mermaid')];
  for (const code of blocks) {
    const holder = document.createElement('div');
    holder.className = 'mermaid my-space-md overflow-x-auto bg-surface-container-lowest p-space-md border border-outline-variant';
    holder.textContent = 'Drawing diagram…';
    code.parentElement.replaceWith(holder);
    if (!window.mermaid) continue;
    const { svg } = await window.mermaid.render(`mermaid-${(diagramCount += 1)}`, code.textContent);
    if (token !== current) return;
    holder.innerHTML = svg;
    holder.dataset.processed = 'true';
  }
}

export async function renderWiki(root, pageId) {
  const token = (current += 1);
  const [pages, page] = await Promise.all([api('/wiki'), api(`/wiki/${encodeURIComponent(pageId)}`)]);
  if (token !== current) return;
  const rail = pages
    .map((p) => {
      const active = p.id === pageId;
      return `<a href="#/wiki/${p.id}" class="block px-space-md py-space-sm font-body-md text-body-md ${active ? 'bg-surface-container-lowest text-on-surface font-semibold' : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'}" ${active ? 'style="box-shadow: inset 3px 0 0 0 #0f62fe"' : ''}>${esc(p.title)}</a>`;
    })
    .join('');
  root.innerHTML = `<div class="flex flex-col lg:flex-row w-full lg:h-[calc(100vh-48px)]">
    <aside class="w-full lg:w-72 shrink-0 bg-surface-container-low lg:overflow-y-auto"><div class="px-space-md py-space-sm font-label-sm text-label-sm tracking-wider uppercase text-secondary font-semibold border-b border-outline-variant">Wiki</div><nav class="flex flex-col py-space-xs">${rail}</nav></aside>
    <section id="wikiScroll" class="flex-1 min-w-0 min-h-0 bg-surface-container-lowest lg:overflow-y-auto"><article id="wikiArticle" class="prose prose-sm font-body-md text-body-md max-w-4xl mx-auto p-space-lg prose-headings:font-semibold prose-code:before:content-none prose-code:after:content-none prose-code:bg-surface-container prose-code:px-1 [&_code]:font-code-md [&_pre_code]:text-code-md [&_th]:text-label-sm [&_pre]:bg-white [&_pre]:text-[#161616] [&_pre]:border [&_pre]:border-outline-variant [&_pre_code]:bg-transparent [&_pre_code]:text-[#161616] [&_pre_code]:p-0"></article></section></div>`;
  const article = document.getElementById('wikiArticle');
  article.innerHTML = window.marked.parse(page.markdown);
  article.querySelectorAll('a[href]').forEach((a) => {
    const href = a.getAttribute('href');
    const target = linkTarget(href);
    if (target) a.setAttribute('href', `#/wiki/${target}`);
    else if (/^https?:/.test(href)) a.setAttribute('target', '_blank');
    else if (!href.startsWith('#')) {
      // A link to a repository file that is not a wiki page: show the path instead of a dead link.
      const path = document.createElement('code');
      path.textContent = href;
      path.title = 'Repository file';
      a.replaceWith(path);
    }
  });
  document.getElementById('wikiScroll').scrollTop = 0;
  window.scrollTo(0, 0);
  await drawMermaid(article, token);
}
