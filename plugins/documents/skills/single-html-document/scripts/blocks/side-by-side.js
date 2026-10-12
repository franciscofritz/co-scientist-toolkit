const STYLE_ID = 'block-side-by-side-style';
const ACCENTS = {
  info:    '#1f5679',
  success: '#2e6e40',
  warning: '#be8416',
  danger:  '#aa323c',
  neutral: '#555555',
};
const CSS = `
.block-side-by-side { margin: 1.25rem 0; }
.block-side-by-side__title {
  margin: 0 0 0.85rem 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.block-side-by-side__grid {
  display: grid;
  gap: 1rem;
}
.block-side-by-side__grid--2 { grid-template-columns: 1fr 1fr; }
.block-side-by-side__grid--3 { grid-template-columns: 1fr 1fr 1fr; }
@media (max-width: 720px) {
  .block-side-by-side__grid { grid-template-columns: 1fr !important; }
}
.block-side-by-side__panel {
  position: relative;
  border-left: 4px solid var(--block-sxs-accent, #555);
  padding: 0.6rem 0.9rem;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 0 6px 6px 0;
}
.block-side-by-side__label {
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--block-sxs-accent, #555);
  margin-bottom: 0.35rem;
}
.block-side-by-side__heading {
  margin: 0 0 0.35rem 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.35;
}
.block-side-by-side__body { line-height: 1.5; margin: 0; }
.block-side-by-side__body p:first-child { margin-top: 0; }
.block-side-by-side__body p:last-child { margin-bottom: 0; }
.block-side-by-side__tag {
  position: absolute;
  top: 0.55rem;
  right: 0.6rem;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  background: var(--block-sxs-accent, #555);
  color: white;
  letter-spacing: 0.04em;
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
  root.classList.add('block-side-by-side');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-side-by-side__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const panels = Array.isArray(data.panels) ? data.panels.slice(0, 3) : [];
  const grid = doc.createElement('div');
  grid.className = `block-side-by-side__grid block-side-by-side__grid--${panels.length || 2}`;

  for (const p of panels) {
    const panel = doc.createElement('div');
    panel.className = 'block-side-by-side__panel';
    panel.style.setProperty('--block-sxs-accent', ACCENTS[p.accent] || ACCENTS.neutral);

    const label = doc.createElement('span');
    label.className = 'block-side-by-side__label';
    label.textContent = p.label || '';
    panel.appendChild(label);

    if (p.title) {
      const heading = doc.createElement('p');
      heading.className = 'block-side-by-side__heading';
      heading.textContent = p.title;
      panel.appendChild(heading);
    }
    if (p.bodyHtml) {
      const body = doc.createElement('div');
      body.className = 'block-side-by-side__body';
      body.innerHTML = p.bodyHtml;
      panel.appendChild(body);
    }
    if (p.tag) {
      const tag = doc.createElement('span');
      tag.className = 'block-side-by-side__tag';
      tag.textContent = p.tag;
      panel.appendChild(tag);
    }
    grid.appendChild(panel);
  }

  root.appendChild(grid);
}
