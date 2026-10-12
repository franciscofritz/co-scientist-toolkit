const STYLE_ID = 'block-before-after-style';
const CSS = `
.block-before-after {
  display: grid;
  gap: 1rem;
  margin: 1.25rem 0;
}
.block-before-after--horizontal { grid-template-columns: 1fr 1fr; }
.block-before-after--vertical { grid-template-columns: 1fr; }
@media (max-width: 720px) {
  .block-before-after--horizontal { grid-template-columns: 1fr; }
}
.block-before-after__panel {
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 0.9rem 1rem;
  background: rgba(0, 0, 0, 0.02);
}
.block-before-after__panel--before {
  border-left: 3px solid #aa323c;
}
.block-before-after__panel--after {
  border-left: 3px solid #2e6e40;
}
.block-before-after__label {
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 0.5rem;
}
.block-before-after__panel--before .block-before-after__label { color: #aa323c; }
.block-before-after__panel--after  .block-before-after__label { color: #2e6e40; }
.block-before-after__body { line-height: 1.5; margin: 0; }
.block-before-after__body p:first-child { margin-top: 0; }
.block-before-after__body p:last-child { margin-bottom: 0; }
.block-before-after__code {
  margin: 0.6rem 0 0;
  padding: 0.6rem 0.75rem;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
  line-height: 1.45;
  /* Wrap by default so the page never grows wider than its container. */
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}
`;

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

function renderPanel(doc, side, panel) {
  const wrap = doc.createElement('div');
  wrap.className = `block-before-after__panel block-before-after__panel--${side}`;
  const label = doc.createElement('span');
  label.className = 'block-before-after__label';
  label.textContent = panel.label || (side === 'before' ? 'Before' : 'After');
  wrap.appendChild(label);
  if (panel.bodyHtml) {
    const body = doc.createElement('div');
    body.className = 'block-before-after__body';
    body.innerHTML = panel.bodyHtml;
    wrap.appendChild(body);
  }
  if (panel.code && panel.code.source) {
    const pre = doc.createElement('pre');
    pre.className = 'block-before-after__code';
    if (panel.code.language) pre.setAttribute('data-language', panel.code.language);
    pre.textContent = panel.code.source;
    wrap.appendChild(pre);
  }
  return wrap;
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  const axis = data.axis === 'vertical' ? 'vertical' : 'horizontal';
  root.classList.add('block-before-after', `block-before-after--${axis}`);
  root.innerHTML = '';
  root.appendChild(renderPanel(doc, 'before', data.before || {}));
  root.appendChild(renderPanel(doc, 'after', data.after || {}));
}
