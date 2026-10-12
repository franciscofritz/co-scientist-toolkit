import { register } from './_bootstrap.js';

const STYLE_ID = 'block-swatches-style';
const CSS = `
.block-swatches { margin: 1.25rem 0; }
.block-swatches__title {
  margin: 0 0 0.85rem 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.block-swatches__grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
}
.block-swatches__cell {
  position: relative;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 0;
  background: white;
  text-align: left;
  font: inherit;
  cursor: pointer;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.block-swatches__cell:focus-visible { outline: 2px solid #1f5679; outline-offset: 2px; }
.block-swatches__cell[disabled] { cursor: default; }
.block-swatches__chip {
  height: 3rem;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
}
.block-swatches__chip--color { background: var(--block-swatches-value, #ccc); }
.block-swatches__chip--space {
  background: rgba(0, 0, 0, 0.03);
}
.block-swatches__chip--space::before {
  content: "";
  display: block;
  background: #1f5679;
  height: var(--block-swatches-value, 4px);
  width: 60%;
  border-radius: 2px;
}
.block-swatches__chip--radius {
  background: #1f5679;
  height: 3rem;
  border-radius: var(--block-swatches-value, 4px);
  margin: 0.4rem;
}
.block-swatches__chip--typescale {
  font-family: inherit;
  font-size: var(--block-swatches-value, 1rem);
  text-align: center;
  padding: 0.4rem;
  height: auto;
}
.block-swatches__meta {
  padding: 0.5rem 0.65rem 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.block-swatches__name {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.82rem;
  font-weight: 600;
}
.block-swatches__value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.6);
}
.block-swatches__role {
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.7);
  margin-top: 0.15rem;
}
.block-swatches__description { font-size: 0.78rem; color: rgba(0, 0, 0, 0.6); margin-top: 0.25rem; line-height: 1.4; }
.block-swatches__description p { margin: 0; }
.block-swatches__feedback {
  position: absolute;
  top: 0.4rem;
  right: 0.5rem;
  font-size: 0.7rem;
  font-weight: 600;
  background: #2e6e40;
  color: white;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.block-swatches__cell[data-copied] .block-swatches__feedback { opacity: 1; }
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
    try { await navigator.clipboard.writeText(text); return true; } catch (_) { /* fall through */ }
  }
  if (typeof document === 'undefined') return false;
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (_) { ok = false; }
  document.body.removeChild(ta);
  return ok;
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  root.classList.add('block-swatches');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-swatches__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const kind = ['color', 'space', 'radius', 'typescale', 'custom'].includes(data.kind) ? data.kind : 'color';
  const copyValue = ['value', 'name', 'var'].includes(data.copyValue) ? data.copyValue : 'value';
  const interactive = root.getAttribute('data-block-type') === 'swatches' || root.dataset.swatchesInteractive !== 'false';

  const grid = doc.createElement('div');
  grid.className = 'block-swatches__grid';
  const swatches = Array.isArray(data.swatches) ? data.swatches : [];

  for (const s of swatches) {
    const cell = doc.createElement('button');
    cell.type = 'button';
    cell.className = 'block-swatches__cell';
    if (!interactive) cell.disabled = true;

    const chip = doc.createElement('span');
    chip.className = `block-swatches__chip block-swatches__chip--${kind}`;
    if (kind === 'color') chip.style.setProperty('--block-swatches-value', s.value);
    else if (kind === 'space' || kind === 'radius' || kind === 'typescale') {
      chip.style.setProperty('--block-swatches-value', s.value);
    }
    if (kind === 'color') chip.textContent = ''; else if (kind === 'typescale') chip.textContent = 'Aa';
    cell.appendChild(chip);

    const meta = doc.createElement('span');
    meta.className = 'block-swatches__meta';
    const name = doc.createElement('span');
    name.className = 'block-swatches__name';
    name.textContent = s.label || s.name;
    meta.appendChild(name);
    const valueEl = doc.createElement('span');
    valueEl.className = 'block-swatches__value';
    valueEl.textContent = s.value;
    meta.appendChild(valueEl);
    if (s.role) {
      const role = doc.createElement('span');
      role.className = 'block-swatches__role';
      role.textContent = s.role;
      meta.appendChild(role);
    }
    if (s.descriptionHtml) {
      const desc = doc.createElement('span');
      desc.className = 'block-swatches__description';
      desc.innerHTML = s.descriptionHtml;
      meta.appendChild(desc);
    }
    cell.appendChild(meta);

    const feedback = doc.createElement('span');
    feedback.className = 'block-swatches__feedback';
    feedback.textContent = 'Copied';
    cell.appendChild(feedback);

    if (interactive) {
      cell.addEventListener('click', async () => {
        const text = copyValue === 'name' ? s.name
          : copyValue === 'var' ? `var(${s.name})`
          : s.value;
        const ok = await copyText(text);
        if (ok) {
          cell.setAttribute('data-copied', '');
          setTimeout(() => cell.removeAttribute('data-copied'), 1100);
        }
      });
    }

    grid.appendChild(cell);
  }
  root.appendChild(grid);
}

register('swatches', mount);
