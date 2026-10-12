import { register } from './_bootstrap.js';

const STYLE_ID = 'block-drag-reorder-style';
const CSS = `
.block-drag-reorder { margin: 1.25rem 0; }
.block-drag-reorder__title { margin: 0 0 0.65rem 0; font-size: 1.05rem; font-weight: 600; }
.block-drag-reorder__board {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
}
.block-drag-reorder__lane {
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  padding: 0.55rem 0.6rem 0.7rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  min-height: 6rem;
}
.block-drag-reorder__lane[data-droptarget] { background: rgba(31, 86, 121, 0.12); border-color: #1f5679; }
.block-drag-reorder__lane-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.4rem;
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.6);
}
.block-drag-reorder__lane-count[data-overflow="true"] { color: #aa323c; font-weight: 700; }
.block-drag-reorder__card {
  background: white;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  padding: 0.4rem 0.55rem;
  cursor: grab;
  font-size: 0.92rem;
  line-height: 1.4;
  position: relative;
}
.block-drag-reorder__card:focus-visible { outline: 2px solid #1f5679; outline-offset: 2px; }
.block-drag-reorder__card[data-dragging] { opacity: 0.5; cursor: grabbing; }
.block-drag-reorder__card-title { font-weight: 500; }
.block-drag-reorder__card-body { font-size: 0.85rem; color: rgba(0, 0, 0, 0.7); margin-top: 0.2rem; }
.block-drag-reorder__card-body p { margin: 0; }
.block-drag-reorder__card-tag {
  position: absolute;
  top: 0.25rem;
  right: 0.4rem;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  background: rgba(0, 0, 0, 0.08);
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
}
.block-drag-reorder__footer { margin-top: 0.6rem; display: flex; justify-content: flex-end; gap: 0.5rem; }
.block-drag-reorder__copy {
  font: inherit;
  font-size: 0.85rem;
  padding: 0.35rem 0.7rem;
  border-radius: 4px;
  border: 1px solid #1f5679;
  background: white;
  color: #1f5679;
  cursor: pointer;
}
.block-drag-reorder__copy:hover { background: #1f5679; color: white; }
.block-drag-reorder__copy[data-copied] { background: #2e6e40; border-color: #2e6e40; color: white; }
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
  root.classList.add('block-drag-reorder');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-drag-reorder__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const lanes = Array.isArray(data.lanes) ? data.lanes : [];
  const items = Array.isArray(data.items) ? data.items : [];
  const exportFormat = ['markdown', 'yaml', 'text'].includes(data.exportFormat) ? data.exportFormat : 'markdown';
  const itemLane = new Map(items.map((it) => [it.id, it.lane]));
  const itemMap = new Map(items.map((it) => [it.id, it]));

  const board = doc.createElement('div');
  board.className = 'block-drag-reorder__board';
  const laneEls = new Map();

  for (const lane of lanes) {
    const laneEl = doc.createElement('div');
    laneEl.className = 'block-drag-reorder__lane';
    laneEl.setAttribute('data-lane-id', lane.id);

    const head = doc.createElement('div');
    head.className = 'block-drag-reorder__lane-head';
    const labelEl = doc.createElement('span');
    labelEl.textContent = lane.label;
    head.appendChild(labelEl);
    const count = doc.createElement('span');
    count.className = 'block-drag-reorder__lane-count';
    head.appendChild(count);
    laneEl.appendChild(head);

    laneEl.addEventListener('dragover', (e) => { e.preventDefault(); laneEl.setAttribute('data-droptarget', ''); });
    laneEl.addEventListener('dragleave', () => laneEl.removeAttribute('data-droptarget'));
    laneEl.addEventListener('drop', (e) => {
      e.preventDefault();
      laneEl.removeAttribute('data-droptarget');
      const id = e.dataTransfer.getData('text/plain');
      if (!id || !itemMap.has(id)) return;
      itemLane.set(id, lane.id);
      render();
    });
    board.appendChild(laneEl);
    laneEls.set(lane.id, { laneEl, headCount: count, lane });
  }
  root.appendChild(board);

  function makeCard(item) {
    const card = doc.createElement('div');
    card.className = 'block-drag-reorder__card';
    card.setAttribute('draggable', 'true');
    card.setAttribute('tabindex', '0');
    card.setAttribute('data-item-id', item.id);
    const title = doc.createElement('div');
    title.className = 'block-drag-reorder__card-title';
    title.textContent = item.label;
    card.appendChild(title);
    if (item.bodyHtml) {
      const body = doc.createElement('div');
      body.className = 'block-drag-reorder__card-body';
      body.innerHTML = item.bodyHtml;
      card.appendChild(body);
    }
    if (item.tag) {
      const tag = doc.createElement('span');
      tag.className = 'block-drag-reorder__card-tag';
      tag.textContent = item.tag;
      card.appendChild(tag);
    }
    card.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', item.id);
      e.dataTransfer.effectAllowed = 'move';
      card.setAttribute('data-dragging', '');
    });
    card.addEventListener('dragend', () => card.removeAttribute('data-dragging'));

    let pickedUp = false;
    card.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        pickedUp = !pickedUp;
        card.setAttribute('aria-grabbed', pickedUp ? 'true' : 'false');
        if (pickedUp) card.setAttribute('data-dragging', '');
        else card.removeAttribute('data-dragging');
        return;
      }
      if (!pickedUp) return;
      const currentLane = itemLane.get(item.id);
      const idx = lanes.findIndex((l) => l.id === currentLane);
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        const next = lanes[Math.min(lanes.length - 1, idx + 1)];
        if (next) { itemLane.set(item.id, next.id); render(); }
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        const next = lanes[Math.max(0, idx - 1)];
        if (next) { itemLane.set(item.id, next.id); render(); }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        pickedUp = false;
        card.setAttribute('aria-grabbed', 'false');
        card.removeAttribute('data-dragging');
      }
    });

    return card;
  }

  function render() {
    for (const lane of lanes) {
      const { laneEl, headCount } = laneEls.get(lane.id);
      const oldCards = laneEl.querySelectorAll(':scope > .block-drag-reorder__card');
      oldCards.forEach((c) => c.remove());
      const inLane = items.filter((it) => itemLane.get(it.id) === lane.id);
      for (const it of inLane) laneEl.appendChild(makeCard(it));
      const cap = lane.cap;
      headCount.textContent = cap ? `${inLane.length} / ${cap}` : `${inLane.length}`;
      headCount.setAttribute('data-overflow', cap && inLane.length > cap ? 'true' : 'false');
    }
  }
  render();

  const footer = doc.createElement('div');
  footer.className = 'block-drag-reorder__footer';
  const copyBtn = doc.createElement('button');
  copyBtn.type = 'button';
  copyBtn.className = 'block-drag-reorder__copy';
  copyBtn.textContent = 'Copy export';
  copyBtn.addEventListener('click', async () => {
    const text = serialise(lanes, items, itemLane, exportFormat);
    const ok = await copyText(text);
    if (ok) {
      copyBtn.setAttribute('data-copied', '');
      copyBtn.textContent = 'Copied';
      setTimeout(() => {
        copyBtn.removeAttribute('data-copied');
        copyBtn.textContent = 'Copy export';
      }, 1200);
    }
  });
  footer.appendChild(copyBtn);
  root.appendChild(footer);
}

function serialise(lanes, items, itemLane, format) {
  const grouped = new Map(lanes.map((l) => [l.id, []]));
  for (const it of items) {
    const lane = itemLane.get(it.id);
    if (!grouped.has(lane)) continue;
    grouped.get(lane).push(it);
  }
  if (format === 'yaml') {
    const out = ['lanes:'];
    for (const lane of lanes) {
      out.push(`  ${lane.id}:`);
      for (const it of grouped.get(lane.id)) out.push(`    - ${it.label}`);
    }
    return out.join('\n');
  }
  if (format === 'text') {
    const out = [];
    for (const lane of lanes) {
      out.push(`${lane.label}:`);
      for (const it of grouped.get(lane.id)) out.push(`  - ${it.label}`);
    }
    return out.join('\n');
  }
  // markdown
  const out = [];
  for (const lane of lanes) {
    out.push(`## ${lane.label}`, '');
    for (const it of grouped.get(lane.id)) out.push(`- ${it.label}`);
    out.push('');
  }
  return out.join('\n').trimEnd();
}

register('drag-reorder', mount);
