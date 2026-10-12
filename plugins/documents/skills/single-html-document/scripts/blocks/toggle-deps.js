import { register } from './_bootstrap.js';

const STYLE_ID = 'block-toggle-deps-style';
const CSS = `
.block-toggle-deps { margin: 1.25rem 0; padding: 0.85rem 1rem; background: rgba(0, 0, 0, 0.03); border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 6px; }
.block-toggle-deps__title { margin: 0 0 0.65rem 0; font-size: 1.05rem; font-weight: 600; }
.block-toggle-deps__group-header {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.55);
  margin: 0.7rem 0 0.3rem;
}
.block-toggle-deps__group-header:first-child { margin-top: 0; }
.block-toggle-deps__row {
  display: grid;
  grid-template-columns: 2.6rem 1fr;
  gap: 0.65rem;
  align-items: start;
  padding: 0.5rem 0;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}
.block-toggle-deps__row:first-child { border-top: 0; }
.block-toggle-deps__switch {
  position: relative;
  width: 2.4rem;
  height: 1.3rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease;
  flex-shrink: 0;
  border: 0;
  padding: 0;
}
.block-toggle-deps__switch::before {
  content: "";
  position: absolute;
  width: 1rem;
  height: 1rem;
  border-radius: 999px;
  background: white;
  top: 0.15rem;
  left: 0.15rem;
  transition: transform 0.15s ease;
}
.block-toggle-deps__switch[aria-checked="true"] { background: #2e6e40; }
.block-toggle-deps__switch[aria-checked="true"]::before { transform: translateX(1.1rem); }
.block-toggle-deps__row[disabled] .block-toggle-deps__switch { cursor: default; opacity: 0.6; }
.block-toggle-deps__label { font-weight: 500; line-height: 1.4; }
.block-toggle-deps__description { font-size: 0.85rem; color: rgba(0, 0, 0, 0.7); line-height: 1.45; margin-top: 0.15rem; }
.block-toggle-deps__description p { margin: 0; }
.block-toggle-deps__warning {
  margin-top: 0.3rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: #aa323c;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}
.block-toggle-deps__warning::before { content: "!"; display: inline-flex; align-items: center; justify-content: center; width: 1.1rem; height: 1.1rem; border-radius: 999px; background: #aa323c; color: white; font-weight: 700; font-size: 0.75rem; }
.block-toggle-deps__footer { margin-top: 0.85rem; display: flex; justify-content: flex-end; gap: 0.5rem; }
.block-toggle-deps__copy {
  font: inherit;
  font-size: 0.85rem;
  padding: 0.35rem 0.7rem;
  border-radius: 4px;
  border: 1px solid #1f5679;
  background: white;
  color: #1f5679;
  cursor: pointer;
}
.block-toggle-deps__copy:hover { background: #1f5679; color: white; }
.block-toggle-deps__copy[data-copied] { background: #2e6e40; border-color: #2e6e40; color: white; }
`;

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

async function copyText(text) {
  if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
    try { await navigator.clipboard.writeText(text); return true; } catch (_) {}
  }
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (_) {}
  document.body.removeChild(ta);
  return ok;
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  root.classList.add('block-toggle-deps');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-toggle-deps__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const toggles = Array.isArray(data.toggles) ? data.toggles : [];
  const groups = Array.isArray(data.groups) ? data.groups : [];
  const state = {};
  const switchEls = new Map();
  const warningEls = new Map();

  const groupOrder = groups.length > 0 ? groups : [{ id: '__default__', label: '' }];
  for (const t of toggles) {
    state[t.id] = !!t.default;
  }

  for (const g of groupOrder) {
    const groupToggles = toggles.filter((t) => (t.group || '__default__') === g.id);
    if (groupToggles.length === 0) continue;
    if (g.label) {
      const header = doc.createElement('p');
      header.className = 'block-toggle-deps__group-header';
      header.textContent = g.label;
      root.appendChild(header);
    }
    for (const tg of groupToggles) {
      const row = doc.createElement('div');
      row.className = 'block-toggle-deps__row';
      row.id = `${root.id || 'toggle'}-${tg.id}`;

      const sw = doc.createElement('button');
      sw.type = 'button';
      sw.className = 'block-toggle-deps__switch';
      sw.setAttribute('role', 'switch');
      sw.setAttribute('aria-checked', state[tg.id] ? 'true' : 'false');
      row.appendChild(sw);
      switchEls.set(tg.id, sw);

      const meta = doc.createElement('div');
      const label = doc.createElement('div');
      label.className = 'block-toggle-deps__label';
      label.textContent = tg.label;
      meta.appendChild(label);
      if (tg.descriptionHtml) {
        const desc = doc.createElement('div');
        desc.className = 'block-toggle-deps__description';
        desc.innerHTML = tg.descriptionHtml;
        meta.appendChild(desc);
      }
      const warn = doc.createElement('div');
      warn.className = 'block-toggle-deps__warning';
      warn.style.display = 'none';
      meta.appendChild(warn);
      warningEls.set(tg.id, warn);

      row.appendChild(meta);
      root.appendChild(row);

      sw.addEventListener('click', () => {
        state[tg.id] = !state[tg.id];
        sw.setAttribute('aria-checked', state[tg.id] ? 'true' : 'false');
        update();
      });
    }
  }

  function update() {
    for (const tg of toggles) {
      const warn = warningEls.get(tg.id);
      const issues = [];
      if (state[tg.id]) {
        for (const dep of tg.dependencies || []) {
          if (!state[dep]) issues.push(`requires ${dep}`);
        }
        for (const conflict of tg.conflicts || []) {
          if (state[conflict]) issues.push(`conflicts with ${conflict}`);
        }
      }
      if (issues.length === 0) {
        warn.style.display = 'none';
        warn.textContent = '';
      } else {
        warn.style.display = 'inline-flex';
        warn.textContent = issues.join('; ');
      }
    }
  }
  update();

  const footer = doc.createElement('div');
  footer.className = 'block-toggle-deps__footer';
  const copyBtn = doc.createElement('button');
  copyBtn.type = 'button';
  copyBtn.className = 'block-toggle-deps__copy';
  copyBtn.textContent = 'Copy as YAML';
  copyBtn.addEventListener('click', async () => {
    const lines = ['toggles:'];
    for (const tg of toggles) {
      lines.push(`  ${tg.id}: ${state[tg.id] ? 'true' : 'false'}`);
    }
    const ok = await copyText(lines.join('\n'));
    if (ok) {
      copyBtn.setAttribute('data-copied', '');
      copyBtn.textContent = 'Copied';
      setTimeout(() => {
        copyBtn.removeAttribute('data-copied');
        copyBtn.textContent = 'Copy as YAML';
      }, 1200);
    }
  });
  footer.appendChild(copyBtn);
  root.appendChild(footer);
}

register('toggle-deps', mount);
