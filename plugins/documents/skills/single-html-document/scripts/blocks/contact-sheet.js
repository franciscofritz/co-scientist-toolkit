const STYLE_ID = 'block-contact-sheet-style';
const CSS = `
.block-contact-sheet { margin: 1.25rem 0; }
.block-contact-sheet__title {
  margin: 0 0 0.85rem 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.block-contact-sheet__group-header {
  font-size: 0.78rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.55);
  margin: 0.85rem 0 0.4rem;
}
.block-contact-sheet__group-header:first-child { margin-top: 0; }
.block-contact-sheet__grid {
  display: grid;
  gap: 0.75rem;
}
.block-contact-sheet__cell {
  position: relative;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 0.55rem 0.7rem 0.65rem;
  background: white;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-height: 5rem;
}
.block-contact-sheet__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.4rem;
}
.block-contact-sheet__label {
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.block-contact-sheet__sublabel {
  font-size: 0.72rem;
  color: rgba(0, 0, 0, 0.5);
  font-style: italic;
}
.block-contact-sheet__tag {
  position: absolute;
  top: 0.4rem;
  right: 0.5rem;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  background: rgba(0, 0, 0, 0.08);
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
}
.block-contact-sheet__body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.block-contact-sheet__body > svg { max-width: 100%; height: auto; }
.block-contact-sheet__caption {
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.6);
  margin: 0;
  line-height: 1.4;
}
.block-contact-sheet__caption p { margin: 0; }
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
  root.classList.add('block-contact-sheet');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-contact-sheet__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const cells = Array.isArray(data.cells) ? data.cells : [];
  const cellMinWidth = data.cellMinWidth || '12rem';
  const groups = new Map();
  const groupOrder = [];
  for (const cell of cells) {
    const g = cell.group || '__nogroup__';
    if (!groups.has(g)) {
      groups.set(g, []);
      groupOrder.push(g);
    }
    groups.get(g).push(cell);
  }

  for (const g of groupOrder) {
    if (g !== '__nogroup__') {
      const header = doc.createElement('p');
      header.className = 'block-contact-sheet__group-header';
      header.textContent = g;
      root.appendChild(header);
    }
    const grid = doc.createElement('div');
    grid.className = 'block-contact-sheet__grid';
    grid.style.gridTemplateColumns = `repeat(auto-fit, minmax(${cellMinWidth}, 1fr))`;
    for (const cell of groups.get(g)) {
      const el = doc.createElement('div');
      el.className = 'block-contact-sheet__cell';

      const head = doc.createElement('div');
      head.className = 'block-contact-sheet__head';
      const label = doc.createElement('span');
      label.className = 'block-contact-sheet__label';
      label.textContent = cell.label || '';
      head.appendChild(label);
      if (cell.sublabel) {
        const sub = doc.createElement('span');
        sub.className = 'block-contact-sheet__sublabel';
        sub.textContent = cell.sublabel;
        head.appendChild(sub);
      }
      el.appendChild(head);

      if (cell.tag) {
        const tag = doc.createElement('span');
        tag.className = 'block-contact-sheet__tag';
        tag.textContent = cell.tag;
        el.appendChild(tag);
      }

      const body = doc.createElement('div');
      body.className = 'block-contact-sheet__body';
      if (cell.svg) body.innerHTML = cell.svg;
      else if (cell.html) body.innerHTML = cell.html;
      el.appendChild(body);

      if (cell.captionHtml) {
        const caption = doc.createElement('div');
        caption.className = 'block-contact-sheet__caption';
        caption.innerHTML = cell.captionHtml;
        el.appendChild(caption);
      }
      grid.appendChild(el);
    }
    root.appendChild(grid);
  }
}
