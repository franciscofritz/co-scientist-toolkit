import { register } from './_bootstrap.js';

const STYLE_ID = 'block-annotated-diff-style';
const KIND_GLYPHS = { add: '+', remove: '−', change: '~', context: ' ' };
const CSS = `
.block-annotated-diff { margin: 1.25rem 0; border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 6px; overflow: hidden; }
.block-annotated-diff__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0.5rem 0.85rem;
  background: rgba(0, 0, 0, 0.04);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  gap: 0.6rem;
  flex-wrap: wrap;
}
.block-annotated-diff__title { margin: 0; font-size: 0.95rem; font-weight: 600; }
.block-annotated-diff__path {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.65);
}
.block-annotated-diff__jumps { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.block-annotated-diff__jump {
  font: inherit;
  font-size: 0.78rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #1f5679;
  background: white;
  color: #1f5679;
  cursor: pointer;
}
.block-annotated-diff__jump:hover { background: #1f5679; color: white; }
.block-annotated-diff__layout { display: grid; grid-template-columns: 1fr; gap: 0; }
@media (min-width: 900px) { .block-annotated-diff__layout { grid-template-columns: 1fr minmax(14rem, 22rem); } }
.block-annotated-diff__diff { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; line-height: 1.55; min-width: 0; }
.block-annotated-diff[data-wrap="false"] .block-annotated-diff__diff { overflow-x: auto; }
.block-annotated-diff__line { display: grid; grid-template-columns: 3rem 3rem 1.5rem 1fr; gap: 0; align-items: stretch; }
.block-annotated-diff__line[data-kind="add"]    { background: rgba(46, 110, 64, 0.08); }
.block-annotated-diff__line[data-kind="remove"] { background: rgba(170, 50, 60, 0.08); }
.block-annotated-diff__line[data-kind="change"] { background: rgba(190, 132, 22, 0.10); }
.block-annotated-diff__line[data-flash] { box-shadow: inset 0 0 0 2px #1f5679; }
.block-annotated-diff__num,
.block-annotated-diff__gutter {
  text-align: right;
  padding: 0 0.4rem;
  color: rgba(0, 0, 0, 0.45);
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  user-select: none;
}
.block-annotated-diff__gutter { text-align: center; font-weight: 700; }
.block-annotated-diff__line[data-kind="add"]    .block-annotated-diff__gutter { color: #2e6e40; }
.block-annotated-diff__line[data-kind="remove"] .block-annotated-diff__gutter { color: #aa323c; }
.block-annotated-diff__content {
  padding: 0 0.5rem;
  /* Default: wrap long lines so the page stays within its width. */
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.block-annotated-diff[data-wrap="false"] .block-annotated-diff__content {
  white-space: pre;
  word-break: normal;
  overflow-wrap: normal;
}
.block-annotated-diff__wrap-toggle {
  font: inherit;
  font-size: 0.74rem;
  letter-spacing: 0.04em;
  padding: 0.18rem 0.5rem;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.15);
  background: white;
  color: rgba(0, 0, 0, 0.7);
  cursor: pointer;
}
.block-annotated-diff__wrap-toggle:hover { color: #1f5679; border-color: #1f5679; }
.block-annotated-diff[data-wrap="false"] .block-annotated-diff__wrap-toggle { background: #1f5679; color: white; border-color: #1f5679; }
.block-annotated-diff__notes {
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(0, 0, 0, 0.02);
  padding: 0.5rem 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
@media (min-width: 900px) { .block-annotated-diff__notes { border-top: 0; border-left: 1px solid rgba(0, 0, 0, 0.08); } }
.block-annotated-diff__note {
  border-left: 3px solid var(--block-ad-severity, #1f5679);
  padding: 0.3rem 0.55rem;
  background: white;
  border-radius: 0 4px 4px 0;
  font-size: 0.88rem;
  line-height: 1.45;
}
.block-annotated-diff__note-head {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 600;
  margin-bottom: 0.15rem;
  flex-wrap: wrap;
}
.block-annotated-diff__note-range { color: rgba(0, 0, 0, 0.5); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.block-annotated-diff__note-body p:first-child { margin-top: 0; }
.block-annotated-diff__note-body p:last-child  { margin-bottom: 0; }
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
  root.classList.add('block-annotated-diff');
  root.setAttribute('data-wrap', 'true');
  root.innerHTML = '';

  const head = doc.createElement('div');
  head.className = 'block-annotated-diff__head';
  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-annotated-diff__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    head.appendChild(t);
  }
  if (data.path) {
    const p = doc.createElement('span');
    p.className = 'block-annotated-diff__path';
    p.textContent = data.path;
    head.appendChild(p);
  }
  const jumpsEl = doc.createElement('div');
  jumpsEl.className = 'block-annotated-diff__jumps';
  head.appendChild(jumpsEl);

  const wrapToggle = doc.createElement('button');
  wrapToggle.type = 'button';
  wrapToggle.className = 'block-annotated-diff__wrap-toggle';
  wrapToggle.textContent = 'No wrap';
  wrapToggle.setAttribute('aria-pressed', 'false');
  wrapToggle.addEventListener('click', () => {
    const wrapping = root.getAttribute('data-wrap') !== 'false';
    root.setAttribute('data-wrap', wrapping ? 'false' : 'true');
    wrapToggle.setAttribute('aria-pressed', wrapping ? 'true' : 'false');
    wrapToggle.textContent = wrapping ? 'Wrap' : 'No wrap';
  });
  head.appendChild(wrapToggle);
  root.appendChild(head);

  const layout = doc.createElement('div');
  layout.className = 'block-annotated-diff__layout';

  const diff = doc.createElement('div');
  diff.className = 'block-annotated-diff__diff';
  const lines = Array.isArray(data.lines) ? data.lines : [];
  const lineEls = [];
  lines.forEach((line, idx) => {
    const row = doc.createElement('div');
    row.className = 'block-annotated-diff__line';
    row.setAttribute('data-kind', line.kind || 'context');
    row.id = `${root.id || 'diff'}-line-${idx + 1}`;

    const oldN = doc.createElement('span');
    oldN.className = 'block-annotated-diff__num';
    oldN.textContent = line.oldNumber != null ? String(line.oldNumber) : '';
    row.appendChild(oldN);

    const newN = doc.createElement('span');
    newN.className = 'block-annotated-diff__num';
    newN.textContent = line.newNumber != null ? String(line.newNumber) : '';
    row.appendChild(newN);

    const gutter = doc.createElement('span');
    gutter.className = 'block-annotated-diff__gutter';
    gutter.textContent = KIND_GLYPHS[line.kind] || ' ';
    row.appendChild(gutter);

    const content = doc.createElement('span');
    content.className = 'block-annotated-diff__content';
    content.textContent = line.content || '';
    row.appendChild(content);

    diff.appendChild(row);
    lineEls.push(row);
  });

  const notesPane = doc.createElement('div');
  notesPane.className = 'block-annotated-diff__notes';
  const notes = Array.isArray(data.notes) ? data.notes : [];
  for (const note of notes) {
    const noteEl = doc.createElement('div');
    noteEl.className = 'block-annotated-diff__note';
    const safeName = String(note.severity || '').replace(/[^A-Za-z0-9_-]/g, '_');
    if (safeName) noteEl.classList.add(`tag-${safeName}-rail`);

    const noteHead = doc.createElement('div');
    noteHead.className = 'block-annotated-diff__note-head';
    if (note.severity) {
      const tag = doc.createElement('span');
      const safe = String(note.severity).replace(/[^A-Za-z0-9_-]/g, '_');
      tag.className = `tag-${safe}`;
      tag.textContent = note.severity;
      noteHead.appendChild(tag);
    }
    const range = doc.createElement('span');
    range.className = 'block-annotated-diff__note-range';
    const [a, b] = Array.isArray(note.onLines) ? note.onLines : [null, null];
    range.textContent = a != null && b != null
      ? (a === b ? `line ${a}` : `lines ${a}–${b}`)
      : '';
    noteHead.appendChild(range);
    noteEl.appendChild(noteHead);

    const body = doc.createElement('div');
    body.className = 'block-annotated-diff__note-body';
    body.innerHTML = note.bodyHtml || '';
    noteEl.appendChild(body);

    notesPane.appendChild(noteEl);
  }

  layout.appendChild(diff);
  layout.appendChild(notesPane);
  root.appendChild(layout);

  const jumpLinks = Array.isArray(data.jumpLinks) ? data.jumpLinks : [];
  for (const j of jumpLinks) {
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.className = 'block-annotated-diff__jump';
    btn.textContent = j.label;
    btn.addEventListener('click', () => {
      const el = lineEls[(j.atLine || 1) - 1];
      if (!el) return;
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      el.setAttribute('data-flash', '');
      setTimeout(() => el.removeAttribute('data-flash'), 1200);
    });
    jumpsEl.appendChild(btn);
  }
}

register('annotated-diff', mount);
