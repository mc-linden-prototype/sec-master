// Router for the three tabs: #/securities, #/reference/<set>, #/wiki/<page>.

import { health } from './api.js';
import { renderReference } from './reference.js';
import { renderSecurities } from './securities.js';
import { esc } from './util.js';
import { renderWiki } from './wiki.js';

const app = document.getElementById('app');
const ACTIVE = 'border-b-2 border-primary-container text-on-surface font-semibold bg-surface-container-low';
const INACTIVE = 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container';

function parseHash() {
  const [path, query = ''] = (location.hash || '#/securities').slice(2).split('?');
  const [section, arg] = path.split('/');
  return { section: section || 'securities', arg, params: new URLSearchParams(query) };
}

async function route() {
  const { section, arg, params } = parseHash();
  document.querySelectorAll('#mainNav a').forEach((a) => {
    a.className = `h-full px-space-md flex items-center font-label-md text-label-md transition-colors ${a.dataset.route === section ? ACTIVE : INACTIVE}`;
  });
  try {
    if (section === 'reference') await renderReference(app, arg || 'venues');
    else if (section === 'wiki') await renderWiki(app, arg || 'index');
    else await renderSecurities(app, params);
  } catch (error) {
    app.innerHTML = `<div class="m-space-lg p-space-md bg-error-container text-on-error-container font-body-md">Could not load this screen: ${esc(error.message)}. Is the API running at ${esc(window.CASM_API)}?</div>`;
  }
}

window.addEventListener('hashchange', route);
route();
health()
  .then((h) => {
    document.getElementById('footerBuild').textContent = `C.A.S.M [Prototype] • database rebuilt ${h.built_at} • ${h.migrations.length} migrations`;
  })
  .catch(() => {});
