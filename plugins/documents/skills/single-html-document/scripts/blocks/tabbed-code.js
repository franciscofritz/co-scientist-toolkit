import { register } from './_bootstrap.js';

const STYLE_ID = 'block-tabbed-code-style';
const CSS = `
.block-tabbed-code { margin: 1.25rem 0; }
.block-tabbed-code__title {
  margin: 0 0 0.65rem 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.block-tabbed-code__tablist {
  display: flex;
  gap: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}
.block-tabbed-code__tab {
  padding: 0.45rem 0.85rem;
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  font: inherit;
  font-weight: 500;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.6);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.block-tabbed-code__tab:hover { color: rgba(0, 0, 0, 0.85); }
.block-tabbed-code__tab[aria-selected="true"] {
  color: #1f5679;
  border-bottom-color: #1f5679;
}
.block-tabbed-code__tab-language {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(0, 0, 0, 0.4);
}
.block-tabbed-code__panel {
  padding: 0.65rem 0.8rem;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 0 0 6px 6px;
}
.block-tabbed-code__panel[hidden] { display: none; }
.block-tabbed-code__source {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  /* Default: reflow long lines so the page never grows wider than the
     viewport. Authors can switch to no-wrap mode via the toggle. */
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.block-tabbed-code[data-wrap="false"] .block-tabbed-code__source {
  white-space: pre;
  word-break: normal;
  overflow-wrap: normal;
  overflow-x: auto;
}
.block-tabbed-code__wrap-toggle {
  font: inherit;
  font-size: 0.74rem;
  letter-spacing: 0.04em;
  padding: 0.18rem 0.5rem;
  margin-left: auto;
  border-radius: 4px;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  background: white;
  color: rgba(0, 0, 0, 0.7);
  cursor: pointer;
}
.block-tabbed-code__wrap-toggle:hover { color: #1f5679; border-color: #1f5679; }
.block-tabbed-code[data-wrap="false"] .block-tabbed-code__wrap-toggle { background: #1f5679; color: white; border-color: #1f5679; }
.block-tabbed-code__caption {
  margin: 0.4rem 0 0;
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.55);
}
`;

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  root.classList.add('block-tabbed-code');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-tabbed-code__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const tabs = Array.isArray(data.tabs) ? data.tabs : [];
  if (tabs.length === 0) return;

  let defaultIdx = 0;
  if (typeof data.default === 'number') defaultIdx = Math.max(0, Math.min(tabs.length - 1, data.default));
  else if (typeof data.default === 'string') {
    const found = tabs.findIndex((tab) => tab.label === data.default);
    if (found >= 0) defaultIdx = found;
  }

  // Wrap mode: default true (lines wrap to fit). Toggle switches to pre + scroll.
  root.setAttribute('data-wrap', 'true');

  const tablist = doc.createElement('div');
  tablist.className = 'block-tabbed-code__tablist';
  tablist.setAttribute('role', 'tablist');

  const buttons = [];
  const panels = [];

  tabs.forEach((tab, i) => {
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.className = 'block-tabbed-code__tab';
    btn.setAttribute('role', 'tab');
    btn.id = `${root.id || 'tabbed-code'}-tab-${i}`;
    const panelId = `${root.id || 'tabbed-code'}-panel-${i}`;
    btn.setAttribute('aria-controls', panelId);
    const labelSpan = doc.createElement('span');
    labelSpan.textContent = tab.label;
    btn.appendChild(labelSpan);
    if (tab.language) {
      const lang = doc.createElement('span');
      lang.className = 'block-tabbed-code__tab-language';
      lang.textContent = tab.language;
      btn.appendChild(lang);
    }
    tablist.appendChild(btn);
    buttons.push(btn);

    const panel = doc.createElement('div');
    panel.className = 'block-tabbed-code__panel';
    panel.id = panelId;
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', btn.id);
    const pre = doc.createElement('pre');
    pre.className = 'block-tabbed-code__source';
    if (tab.language) pre.setAttribute('data-language', tab.language);
    pre.textContent = tab.source || '';
    panel.appendChild(pre);
    if (tab.caption) {
      const cap = doc.createElement('p');
      cap.className = 'block-tabbed-code__caption';
      cap.textContent = tab.caption;
      panel.appendChild(cap);
    }
    panels.push(panel);
  });

  function activate(i) {
    buttons.forEach((b, idx) => {
      const sel = idx === i;
      b.setAttribute('aria-selected', sel ? 'true' : 'false');
      b.setAttribute('tabindex', sel ? '0' : '-1');
      panels[idx].hidden = !sel;
    });
  }

  buttons.forEach((b, i) => {
    b.addEventListener('click', () => activate(i));
    b.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') { e.preventDefault(); const n = (i + 1) % buttons.length; activate(n); buttons[n].focus(); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); const n = (i - 1 + buttons.length) % buttons.length; activate(n); buttons[n].focus(); }
      else if (e.key === 'Home') { e.preventDefault(); activate(0); buttons[0].focus(); }
      else if (e.key === 'End') { e.preventDefault(); const last = buttons.length - 1; activate(last); buttons[last].focus(); }
    });
  });

  activate(defaultIdx);

  // Wrap toggle lives in the tablist, right-aligned.
  const wrapToggle = doc.createElement('button');
  wrapToggle.type = 'button';
  wrapToggle.className = 'block-tabbed-code__wrap-toggle';
  wrapToggle.textContent = 'No wrap';
  wrapToggle.setAttribute('aria-pressed', 'false');
  wrapToggle.addEventListener('click', () => {
    const wrapping = root.getAttribute('data-wrap') !== 'false';
    root.setAttribute('data-wrap', wrapping ? 'false' : 'true');
    wrapToggle.setAttribute('aria-pressed', wrapping ? 'true' : 'false');
    wrapToggle.textContent = wrapping ? 'Wrap' : 'No wrap';
  });
  tablist.appendChild(wrapToggle);

  root.appendChild(tablist);
  for (const panel of panels) root.appendChild(panel);
}

register('tabbed-code', mount);
