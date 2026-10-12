const STYLE_ID = 'block-mind-map-style';
const KIND_COLORS = {
  info:    { border: '#1f5679', bg: 'rgba(31, 86, 121, 0.06)' },
  success: { border: '#2e6e40', bg: 'rgba(46, 110, 64, 0.06)' },
  warning: { border: '#be8416', bg: 'rgba(190, 132, 22, 0.10)' },
  danger:  { border: '#aa323c', bg: 'rgba(170, 50, 60, 0.06)' },
  key:     { border: '#784e98', bg: 'rgba(120, 78, 152, 0.06)' },
  neutral: { border: '#555',    bg: 'rgba(0, 0, 0, 0.04)' },
};
const CSS = `
.block-mind-map { margin: 1.25rem 0; min-width: 0; }
.block-mind-map__title { margin: 0 0 0.85rem 0; font-size: 1.05rem; font-weight: 600; }
.block-mind-map__stage {
  position: relative;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
  padding: 1.25rem;
  display: grid;
  gap: 1rem;
  min-width: 0;
}
.block-mind-map--horizontal .block-mind-map__stage,
.block-mind-map--right .block-mind-map__stage { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; }
.block-mind-map--horizontal .block-mind-map__column-left { grid-column: 1; }
.block-mind-map--horizontal .block-mind-map__root { grid-column: 2; }
.block-mind-map--horizontal .block-mind-map__column-right { grid-column: 3; }
.block-mind-map--right .block-mind-map__column-left { display: none; }
.block-mind-map--right .block-mind-map__root { grid-column: 1; }
.block-mind-map--right .block-mind-map__column-right { grid-column: 2 / span 2; }
.block-mind-map--radial .block-mind-map__stage { grid-template-columns: 1fr; }
.block-mind-map--radial .block-mind-map__row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1rem; }
.block-mind-map__column { display: flex; flex-direction: column; gap: 0.85rem; min-width: 0; }
.block-mind-map__column-left { align-items: flex-end; text-align: right; }
.block-mind-map__column-right { align-items: flex-start; }
.block-mind-map__root {
  background: white;
  border: 2.5px solid #1f5679;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  box-shadow: 0 4px 12px rgba(31, 86, 121, 0.08);
  text-align: center;
  z-index: 2;
  position: relative;
  min-width: 8rem;
  max-width: 22rem;
  justify-self: center;
}
.block-mind-map__root-icon { color: #1f5679; }
.block-mind-map__root-icon > svg { width: 1.5rem; height: 1.5rem; margin-bottom: 0.2rem; }
.block-mind-map__root-label { font-weight: 700; font-size: 1.05rem; line-height: 1.3; }
.block-mind-map__root-body { font-size: 0.85rem; color: rgba(0, 0, 0, 0.65); margin-top: 0.25rem; line-height: 1.4; }
.block-mind-map__root-body p { margin: 0; }
.block-mind-map__branch {
  background: white;
  border: 1.5px solid var(--block-mm-border, #555);
  border-left-width: 4px;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  position: relative;
  min-width: 0;
  width: 100%;
  max-width: 22rem;
}
.block-mind-map__column-left .block-mind-map__branch { border-left-width: 1.5px; border-right-width: 4px; }
.block-mind-map__branch-head {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--block-mm-border, #333);
}
.block-mind-map__branch-icon { display: inline-flex; flex-shrink: 0; }
.block-mind-map__branch-icon > svg { width: 1.05rem; height: 1.05rem; }
.block-mind-map__branch-body { font-size: 0.85rem; color: rgba(0, 0, 0, 0.7); margin-top: 0.2rem; line-height: 1.4; }
.block-mind-map__branch-body p { margin: 0; }
.block-mind-map__children {
  list-style: none;
  margin: 0.4rem 0 0 0;
  padding: 0 0 0 0.85rem;
  border-left: 1px dashed rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.block-mind-map__column-left .block-mind-map__children { padding: 0 0.85rem 0 0; border-left: 0; border-right: 1px dashed rgba(0, 0, 0, 0.2); align-items: flex-end; text-align: right; }
.block-mind-map__children li {
  font-size: 0.88rem;
  color: rgba(0, 0, 0, 0.78);
  line-height: 1.4;
}
.block-mind-map__edges { position: absolute; inset: 0; pointer-events: none; z-index: 1; }
.block-mind-map__edges path { fill: none; stroke: rgba(0, 0, 0, 0.35); stroke-width: 1.4; }
`;

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

function resolveIcon(doc, data) {
  if (data.iconHtml) return data.iconHtml;
  if (data.icon && typeof window !== 'undefined' && typeof window.__blocksHasIcon === 'function' && window.__blocksHasIcon(data.icon)) {
    return window.__blocksIcon(data.icon);
  }
  return null;
}

function renderBranch(doc, branch, side) {
  const el = doc.createElement('div');
  el.className = 'block-mind-map__branch';
  el.setAttribute('data-side', side);
  const tone = KIND_COLORS[branch.kind] || KIND_COLORS.neutral;
  el.style.setProperty('--block-mm-border', tone.border);

  const head = doc.createElement('div');
  head.className = 'block-mind-map__branch-head';
  const iconHtml = resolveIcon(doc, branch);
  if (iconHtml) {
    const iconEl = doc.createElement('span');
    iconEl.className = 'block-mind-map__branch-icon';
    iconEl.innerHTML = iconHtml;
    head.appendChild(iconEl);
  }
  const labelEl = doc.createElement('span');
  labelEl.textContent = branch.label || '';
  head.appendChild(labelEl);
  el.appendChild(head);

  if (branch.bodyHtml) {
    const body = doc.createElement('div');
    body.className = 'block-mind-map__branch-body';
    body.innerHTML = branch.bodyHtml;
    el.appendChild(body);
  }

  if (Array.isArray(branch.children) && branch.children.length > 0) {
    const list = doc.createElement('ul');
    list.className = 'block-mind-map__children';
    for (const child of branch.children) {
      const li = doc.createElement('li');
      const head = doc.createElement('div');
      head.style.fontWeight = '500';
      head.textContent = child.label || '';
      li.appendChild(head);
      if (child.bodyHtml) {
        const sub = doc.createElement('div');
        sub.style.fontSize = '0.82rem';
        sub.style.color = 'rgba(0, 0, 0, 0.6)';
        sub.innerHTML = child.bodyHtml;
        li.appendChild(sub);
      }
      list.appendChild(li);
    }
    el.appendChild(list);
  }

  return el;
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  const direction = ['radial', 'right', 'horizontal'].includes(data.direction) ? data.direction : 'horizontal';
  root.classList.add('block-mind-map', `block-mind-map--${direction}`);
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-mind-map__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const stage = doc.createElement('div');
  stage.className = 'block-mind-map__stage';

  // Build the root node
  const rootEl = doc.createElement('div');
  rootEl.className = 'block-mind-map__root';
  const rootIcon = resolveIcon(doc, data.root || {});
  if (rootIcon) {
    const icon = doc.createElement('div');
    icon.className = 'block-mind-map__root-icon';
    icon.innerHTML = rootIcon;
    rootEl.appendChild(icon);
  }
  if (data.root && data.root.label) {
    const labelEl = doc.createElement('div');
    labelEl.className = 'block-mind-map__root-label';
    labelEl.textContent = data.root.label;
    rootEl.appendChild(labelEl);
  }
  if (data.root && data.root.bodyHtml) {
    const body = doc.createElement('div');
    body.className = 'block-mind-map__root-body';
    body.innerHTML = data.root.bodyHtml;
    rootEl.appendChild(body);
  }

  const branches = Array.isArray(data.branches) ? data.branches : [];
  const branchEls = [];

  if (direction === 'right') {
    const colRight = doc.createElement('div');
    colRight.className = 'block-mind-map__column block-mind-map__column-right';
    branches.forEach((b) => {
      const el = renderBranch(doc, b, 'right');
      colRight.appendChild(el);
      branchEls.push({ el, side: 'right' });
    });
    stage.appendChild(rootEl);
    stage.appendChild(colRight);
  } else if (direction === 'horizontal') {
    const colLeft = doc.createElement('div');
    colLeft.className = 'block-mind-map__column block-mind-map__column-left';
    const colRight = doc.createElement('div');
    colRight.className = 'block-mind-map__column block-mind-map__column-right';
    branches.forEach((b, i) => {
      const side = i % 2 === 0 ? 'right' : 'left';
      const el = renderBranch(doc, b, side);
      (side === 'right' ? colRight : colLeft).appendChild(el);
      branchEls.push({ el, side });
    });
    stage.appendChild(colLeft);
    stage.appendChild(rootEl);
    stage.appendChild(colRight);
  } else {
    // radial: branches in two columns above and below the root
    // Simple implementation: row before root, then root, then row after
    const half = Math.ceil(branches.length / 2);
    const before = branches.slice(0, half);
    const after = branches.slice(half);
    const beforeRow = doc.createElement('div');
    beforeRow.className = 'block-mind-map__row';
    const afterRow = doc.createElement('div');
    afterRow.className = 'block-mind-map__row';
    before.forEach((b, i) => {
      const side = i % 2 === 0 ? 'left' : 'right';
      const el = renderBranch(doc, b, side);
      beforeRow.appendChild(el);
      branchEls.push({ el, side: 'top' });
    });
    after.forEach((b, i) => {
      const side = i % 2 === 0 ? 'left' : 'right';
      const el = renderBranch(doc, b, side);
      afterRow.appendChild(el);
      branchEls.push({ el, side: 'bottom' });
    });
    stage.appendChild(beforeRow);
    stage.appendChild(rootEl);
    stage.appendChild(afterRow);
  }

  // SVG overlay for edges
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = doc.createElementNS(svgNS, 'svg');
  svg.setAttribute('class', 'block-mind-map__edges');
  stage.appendChild(svg);

  root.appendChild(stage);

  function drawEdges() {
    const stageRect = stage.getBoundingClientRect();
    if (stageRect.width === 0) return;
    svg.setAttribute('viewBox', `0 0 ${stageRect.width} ${stageRect.height}`);
    svg.setAttribute('width', String(stageRect.width));
    svg.setAttribute('height', String(stageRect.height));
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    const rootRect = rootEl.getBoundingClientRect();
    const rcx = (rootRect.left + rootRect.right) / 2 - stageRect.left;
    const rcy = (rootRect.top + rootRect.bottom) / 2 - stageRect.top;

    for (const { el, side } of branchEls) {
      const r = el.getBoundingClientRect();
      let bx, by;
      if (side === 'right') {
        bx = r.left - stageRect.left;
        by = (r.top + r.bottom) / 2 - stageRect.top;
      } else if (side === 'left') {
        bx = r.right - stageRect.left;
        by = (r.top + r.bottom) / 2 - stageRect.top;
      } else if (side === 'top') {
        bx = (r.left + r.right) / 2 - stageRect.left;
        by = r.bottom - stageRect.top;
      } else {
        bx = (r.left + r.right) / 2 - stageRect.left;
        by = r.top - stageRect.top;
      }
      // Smooth curve from root to branch
      const dx = bx - rcx;
      const dy = by - rcy;
      const c1x = rcx + dx * 0.5;
      const c1y = rcy;
      const c2x = bx - dx * 0.5;
      const c2y = by;
      const path = doc.createElementNS(svgNS, 'path');
      path.setAttribute('d', `M ${rcx} ${rcy} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${bx} ${by}`);
      svg.appendChild(path);
    }
  }

  if (typeof window !== 'undefined') {
    requestAnimationFrame(drawEdges);
    window.addEventListener('resize', drawEdges, { passive: true });
  } else {
    drawEdges();
  }
}
