const STYLE_ID = 'block-glossary-style';
const CSS = `
.block-glossary { margin: 1.25rem 0; }
.block-glossary__title {
  margin: 0 0 0.6rem 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.block-glossary__list { display: grid; gap: 0.85rem; }
.block-glossary--two-column .block-glossary__list { grid-template-columns: minmax(8rem, 14rem) 1fr; }
.block-glossary--two-column .block-glossary__item {
  display: contents;
}
.block-glossary--two-column .block-glossary__term-cell {
  font-weight: 600;
  align-self: start;
}
.block-glossary--two-column .block-glossary__definition { margin: 0; }
.block-glossary--stacked .block-glossary__item {
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  padding-top: 0.6rem;
}
.block-glossary--stacked .block-glossary__item:first-child {
  border-top: 0;
  padding-top: 0;
}
.block-glossary__term {
  font-weight: 600;
  margin: 0 0 0.25rem 0;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.block-glossary__alias {
  font-weight: 400;
  font-size: 0.8rem;
  color: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.15);
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
}
.block-glossary__definition { margin: 0; line-height: 1.5; }
.block-glossary__definition p:first-child { margin-top: 0; }
.block-glossary__definition p:last-child { margin-bottom: 0; }
.block-glossary__related {
  font-size: 0.85rem;
  color: rgba(0, 0, 0, 0.6);
  margin-top: 0.3rem;
}
.block-glossary__related a { color: inherit; }
`;

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

function slug(str) {
  return String(str).toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  const layout = ['stacked', 'two-column', 'margin'].includes(data.layout) ? data.layout : 'stacked';
  root.classList.add('block-glossary', `block-glossary--${layout}`);
  root.innerHTML = '';

  if (data.title !== '') {
    const title = doc.createElement('h3');
    title.className = 'block-glossary__title';
    if (root.id) title.id = `${root.id}-title`;
    title.textContent = data.title || 'Glossary';
    root.appendChild(title);
  }

  const list = doc.createElement('div');
  list.className = 'block-glossary__list';

  const terms = Array.isArray(data.terms) ? data.terms : [];
  for (const entry of terms) {
    const item = doc.createElement('div');
    item.className = 'block-glossary__item';
    item.id = `glossary-${slug(entry.term)}`;

    if (layout === 'two-column') {
      const cell = doc.createElement('div');
      cell.className = 'block-glossary__term-cell';
      cell.textContent = entry.term;
      item.appendChild(cell);
      const def = doc.createElement('div');
      def.className = 'block-glossary__definition';
      def.innerHTML = entry.definitionHtml || '';
      item.appendChild(def);
    } else {
      const term = doc.createElement('p');
      term.className = 'block-glossary__term';
      const termText = doc.createElement('span');
      termText.textContent = entry.term;
      term.appendChild(termText);
      if (Array.isArray(entry.aliases)) {
        for (const alias of entry.aliases) {
          const tag = doc.createElement('span');
          tag.className = 'block-glossary__alias';
          tag.textContent = alias;
          term.appendChild(tag);
        }
      }
      item.appendChild(term);

      const def = doc.createElement('div');
      def.className = 'block-glossary__definition';
      def.innerHTML = entry.definitionHtml || '';
      item.appendChild(def);

      if (Array.isArray(entry.related) && entry.related.length > 0) {
        const related = doc.createElement('p');
        related.className = 'block-glossary__related';
        related.append('See also: ');
        entry.related.forEach((r, i) => {
          const a = doc.createElement('a');
          a.href = `#glossary-${slug(r)}`;
          a.textContent = r;
          related.appendChild(a);
          if (i < entry.related.length - 1) related.append(', ');
        });
        item.appendChild(related);
      }
    }
    list.appendChild(item);
  }

  root.appendChild(list);
}
