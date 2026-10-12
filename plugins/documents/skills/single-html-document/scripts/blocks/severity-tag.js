const STYLE_ID = 'block-severity-tag-style';
const TONES = {
  info:    { bg: 'rgba(31, 86, 121, 0.12)',  fg: '#1f5679' },
  success: { bg: 'rgba(46, 110, 64, 0.12)',  fg: '#2e6e40' },
  warning: { bg: 'rgba(190, 132, 22, 0.16)', fg: '#8a5d10' },
  danger:  { bg: 'rgba(170, 50, 60, 0.12)',  fg: '#aa323c' },
  key:     { bg: 'rgba(120, 78, 152, 0.12)', fg: '#5e3a78' },
  neutral: { bg: 'rgba(60, 60, 60, 0.10)',   fg: '#444' },
};
const CSS = `
.block-severity-tag { margin: 1.25rem 0; }
.block-severity-tag__title {
  margin: 0 0 0.85rem 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.block-severity-tag__grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
}
.block-severity-tag__list {
  display: grid;
  gap: 0.6rem;
  grid-template-columns: minmax(5rem, max-content) 1fr;
}
.block-severity-tag__cell {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  padding: 0.55rem 0.7rem 0.65rem;
  background: white;
}
.block-severity-tag__pill {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  background: var(--block-tag-bg, rgba(0, 0, 0, 0.05));
  color: var(--block-tag-fg, #333);
  margin-bottom: 0.35rem;
}
.block-severity-tag__list .block-severity-tag__pill {
  align-self: start;
  margin-bottom: 0;
}
.block-severity-tag__description {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.45;
}
.block-severity-tag__description p:first-child { margin-top: 0; }
.block-severity-tag__description p:last-child  { margin-bottom: 0; }
.block-severity-tag__when, .block-severity-tag__sla {
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.6);
  margin-top: 0.3rem;
  display: block;
}
.block-severity-tag__when strong, .block-severity-tag__sla strong {
  color: rgba(0, 0, 0, 0.75);
  font-weight: 600;
  margin-right: 0.25rem;
}
`;

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

function emitTagRules(doc, tags) {
  const id = 'block-severity-tag-rules';
  let style = doc.getElementById(id);
  if (!style) {
    style = doc.createElement('style');
    style.id = id;
    doc.head.appendChild(style);
  }
  const rules = [];
  for (const tag of tags) {
    const tone = TONES[tag.tone] || TONES.neutral;
    const safeName = String(tag.name).replace(/[^A-Za-z0-9_-]/g, '_');
    rules.push(`.tag-${safeName} { background: ${tone.bg}; color: ${tone.fg}; padding: 0.05rem 0.4rem; border-radius: 999px; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em; }`);
  }
  style.textContent = rules.join('\n');
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  root.classList.add('block-severity-tag');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-severity-tag__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const layout = data.layout === 'list' ? 'list' : 'grid';
  const container = doc.createElement('div');
  container.className = layout === 'grid' ? 'block-severity-tag__grid' : 'block-severity-tag__list';

  const tags = Array.isArray(data.tags) ? data.tags : [];
  emitTagRules(doc, tags);

  for (const tag of tags) {
    const tone = TONES[tag.tone] || TONES.neutral;
    if (layout === 'grid') {
      const cell = doc.createElement('div');
      cell.className = 'block-severity-tag__cell';
      const pill = doc.createElement('span');
      pill.className = 'block-severity-tag__pill';
      pill.style.setProperty('--block-tag-bg', tone.bg);
      pill.style.setProperty('--block-tag-fg', tone.fg);
      pill.textContent = tag.label || tag.name;
      cell.appendChild(pill);

      const desc = doc.createElement('div');
      desc.className = 'block-severity-tag__description';
      desc.innerHTML = tag.descriptionHtml || '';
      cell.appendChild(desc);

      if (tag.when) {
        const w = doc.createElement('span');
        w.className = 'block-severity-tag__when';
        w.innerHTML = `<strong>When:</strong>`;
        w.append(' ' + tag.when);
        cell.appendChild(w);
      }
      if (tag.sla) {
        const s = doc.createElement('span');
        s.className = 'block-severity-tag__sla';
        s.innerHTML = `<strong>SLA:</strong>`;
        s.append(' ' + tag.sla);
        cell.appendChild(s);
      }
      container.appendChild(cell);
    } else {
      const pill = doc.createElement('span');
      pill.className = 'block-severity-tag__pill';
      pill.style.setProperty('--block-tag-bg', tone.bg);
      pill.style.setProperty('--block-tag-fg', tone.fg);
      pill.textContent = tag.label || tag.name;
      container.appendChild(pill);

      const cell = doc.createElement('div');
      const desc = doc.createElement('div');
      desc.className = 'block-severity-tag__description';
      desc.innerHTML = tag.descriptionHtml || '';
      cell.appendChild(desc);
      if (tag.when) {
        const w = doc.createElement('span');
        w.className = 'block-severity-tag__when';
        w.innerHTML = `<strong>When:</strong>`;
        w.append(' ' + tag.when);
        cell.appendChild(w);
      }
      if (tag.sla) {
        const s = doc.createElement('span');
        s.className = 'block-severity-tag__sla';
        s.innerHTML = `<strong>SLA:</strong>`;
        s.append(' ' + tag.sla);
        cell.appendChild(s);
      }
      container.appendChild(cell);
    }
  }

  root.appendChild(container);
}
