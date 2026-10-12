const STYLE_ID = 'block-concept-map-style';
const KIND_COLORS = {
  info:    { border: '#1f5679', bg: 'rgba(31, 86, 121, 0.06)' },
  success: { border: '#2e6e40', bg: 'rgba(46, 110, 64, 0.06)' },
  warning: { border: '#be8416', bg: 'rgba(190, 132, 22, 0.10)' },
  danger:  { border: '#aa323c', bg: 'rgba(170, 50, 60, 0.06)' },
  key:     { border: '#784e98', bg: 'rgba(120, 78, 152, 0.08)' },
  neutral: { border: '#555',    bg: 'rgba(0, 0, 0, 0.04)' },
};
const EDGE_STYLES = {
  causes:      { dash: '0',     color: 'rgba(0, 0, 0, 0.55)' },
  partOf:      { dash: '0',     color: 'rgba(0, 0, 0, 0.55)', double: true },
  dependsOn:   { dash: '0',     color: 'rgba(0, 0, 0, 0.55)' },
  contradicts: { dash: '6 4',   color: '#aa323c' },
  example:     { dash: '2 4',   color: 'rgba(0, 0, 0, 0.45)' },
  enables:     { dash: '0',     color: '#2e6e40' },
  default:     { dash: '0',     color: 'rgba(0, 0, 0, 0.55)' },
};
const CSS = `
.block-concept-map { margin: 1.25rem 0; min-width: 0; }
.block-concept-map__title { margin: 0 0 0.85rem 0; font-size: 1.05rem; font-weight: 600; }
.block-concept-map__stage {
  position: relative;
  display: grid;
  gap: 1.5rem 2rem;
  padding: 1.25rem;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
  min-width: 0;
}
.block-concept-map__node {
  background: white;
  border: 1.5px solid var(--block-cm-border, #555);
  border-radius: 8px;
  padding: 0.55rem 0.7rem;
  position: relative;
  z-index: 2;
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  text-align: center;
}
.block-concept-map__node-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--block-cm-border, #333);
  line-height: 1.3;
}
.block-concept-map__node-icon { display: inline-flex; flex-shrink: 0; }
.block-concept-map__node-icon > svg { width: 1.05rem; height: 1.05rem; }
.block-concept-map__node-body { font-size: 0.82rem; color: rgba(0, 0, 0, 0.65); margin-top: 0.2rem; line-height: 1.4; }
.block-concept-map__node-body p { margin: 0; }
.block-concept-map__edges { position: absolute; inset: 0; pointer-events: none; z-index: 1; overflow: visible; }
.block-concept-map__edges path { fill: none; stroke-width: 1.5; }
.block-concept-map__edges polygon { stroke-width: 0; }
.block-concept-map__edge-label-bg { fill: rgba(247, 245, 240, 0.96); }
.block-concept-map__edges text {
  font-size: 0.74rem;
  fill: rgba(0, 0, 0, 0.78);
  font-weight: 500;
  font-style: italic;
  dominant-baseline: middle;
}
`;

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

function resolveIcon(data) {
  if (data.iconHtml) return data.iconHtml;
  if (data.icon && typeof window !== 'undefined' && typeof window.__blocksHasIcon === 'function' && window.__blocksHasIcon(data.icon)) {
    return window.__blocksIcon(data.icon);
  }
  return null;
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  root.classList.add('block-concept-map');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-concept-map__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const stage = doc.createElement('div');
  stage.className = 'block-concept-map__stage';

  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  const edges = Array.isArray(data.edges) ? data.edges : [];

  let maxCol = 0;
  let maxRow = 0;
  for (const n of nodes) {
    maxCol = Math.max(maxCol, n.col || 0);
    maxRow = Math.max(maxRow, n.row || 0);
  }
  stage.style.gridTemplateColumns = `repeat(${maxCol + 1}, minmax(8rem, 1fr))`;
  stage.style.gridTemplateRows = `repeat(${maxRow + 1}, auto)`;

  const nodeEls = new Map();
  for (const node of nodes) {
    const el = doc.createElement('div');
    el.className = 'block-concept-map__node';
    el.setAttribute('data-node-id', node.id);
    const tone = KIND_COLORS[node.kind] || KIND_COLORS.neutral;
    el.style.setProperty('--block-cm-border', tone.border);
    el.style.background = tone.bg;
    el.style.gridColumn = String((node.col || 0) + 1);
    el.style.gridRow = String((node.row || 0) + 1);
    el.style.alignSelf = 'center';

    const head = doc.createElement('div');
    head.className = 'block-concept-map__node-head';
    const iconHtml = resolveIcon(node);
    if (iconHtml) {
      const iconEl = doc.createElement('span');
      iconEl.className = 'block-concept-map__node-icon';
      iconEl.innerHTML = iconHtml;
      head.appendChild(iconEl);
    }
    const labelEl = doc.createElement('span');
    labelEl.textContent = node.label || node.id;
    head.appendChild(labelEl);
    el.appendChild(head);

    if (node.bodyHtml) {
      const body = doc.createElement('div');
      body.className = 'block-concept-map__node-body';
      body.innerHTML = node.bodyHtml;
      el.appendChild(body);
    }

    stage.appendChild(el);
    nodeEls.set(node.id, el);
  }

  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = doc.createElementNS(svgNS, 'svg');
  svg.setAttribute('class', 'block-concept-map__edges');
  stage.appendChild(svg);

  root.appendChild(stage);

  function drawEdges() {
    const stageRect = stage.getBoundingClientRect();
    if (stageRect.width === 0) return;
    svg.setAttribute('viewBox', `0 0 ${stageRect.width} ${stageRect.height}`);
    svg.setAttribute('width', String(stageRect.width));
    svg.setAttribute('height', String(stageRect.height));
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    // Detect parallel edges between the same pair so we can offset their
    // midpoints and avoid stacking labels.
    const pairKey = (e) => {
      const lo = e.from < e.to ? e.from : e.to;
      const hi = e.from < e.to ? e.to : e.from;
      return `${lo}|${hi}`;
    };
    const pairCounts = new Map();
    edges.forEach((e) => {
      const key = pairKey(e);
      pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
    });
    const pairIndex = new Map();

    const labelTasks = [];

    for (const edge of edges) {
      const fromEl = nodeEls.get(edge.from);
      const toEl = nodeEls.get(edge.to);
      if (!fromEl || !toEl) continue;
      const a = fromEl.getBoundingClientRect();
      const b = toEl.getBoundingClientRect();
      // Connect from edge of source closest to target.
      const ax = (a.left + a.right) / 2 - stageRect.left;
      const ay = (a.top + a.bottom) / 2 - stageRect.top;
      const bx = (b.left + b.right) / 2 - stageRect.left;
      const by = (b.top + b.bottom) / 2 - stageRect.top;
      const dx = bx - ax;
      const dy = by - ay;
      const len = Math.hypot(dx, dy) || 1;

      // Move endpoints to the bounding box edges instead of centres so the
      // path doesn't disappear under the node.
      const halfW = (a.width / 2) - 4;
      const halfH = (a.height / 2) - 4;
      const tHalf = (b.width / 2) - 4;
      const tHalfH = (b.height / 2) - 4;
      const angle = Math.atan2(dy, dx);
      const sx = ax + Math.cos(angle) * Math.min(halfW / Math.max(0.0001, Math.abs(Math.cos(angle))), halfH / Math.max(0.0001, Math.abs(Math.sin(angle))));
      const sy = ay + Math.sin(angle) * Math.min(halfW / Math.max(0.0001, Math.abs(Math.cos(angle))), halfH / Math.max(0.0001, Math.abs(Math.sin(angle))));
      const tx = bx - Math.cos(angle) * Math.min(tHalf / Math.max(0.0001, Math.abs(Math.cos(angle))), tHalfH / Math.max(0.0001, Math.abs(Math.sin(angle))));
      const ty = by - Math.sin(angle) * Math.min(tHalf / Math.max(0.0001, Math.abs(Math.cos(angle))), tHalfH / Math.max(0.0001, Math.abs(Math.sin(angle))));

      const key = pairKey(edge);
      const total = pairCounts.get(key) || 1;
      const idx = pairIndex.get(key) || 0;
      pairIndex.set(key, idx + 1);
      // Offset the curve perpendicular to the line by an amount that scales
      // with the count so multiple edges between the same pair fan out.
      const offsetMag = total > 1 ? ((idx - (total - 1) / 2) * 22) : 0;
      const perpX = -Math.sin(angle) * offsetMag;
      const perpY =  Math.cos(angle) * offsetMag;
      const cx = (sx + tx) / 2 + perpX;
      const cy = (sy + ty) / 2 + perpY;

      const style = EDGE_STYLES[edge.kind] || EDGE_STYLES.default;
      const path = doc.createElementNS(svgNS, 'path');
      path.setAttribute('d', `M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`);
      path.setAttribute('stroke-dasharray', style.dash);
      path.setAttribute('stroke', style.color);
      svg.appendChild(path);

      // Arrowhead at target, pointed along the tangent of the curve at the
      // endpoint (approximated by the angle from cx,cy to tx,ty).
      const headAngle = Math.atan2(ty - cy, tx - cx);
      const headSize = 7;
      const arrow = doc.createElementNS(svgNS, 'polygon');
      const ax1 = tx - Math.cos(headAngle) * headSize - Math.sin(headAngle) * 4;
      const ay1 = ty - Math.sin(headAngle) * headSize + Math.cos(headAngle) * 4;
      const ax2 = tx - Math.cos(headAngle) * headSize + Math.sin(headAngle) * 4;
      const ay2 = ty - Math.sin(headAngle) * headSize - Math.cos(headAngle) * 4;
      arrow.setAttribute('points', `${tx},${ty} ${ax1},${ay1} ${ax2},${ay2}`);
      arrow.setAttribute('fill', style.color);
      svg.appendChild(arrow);

      if (!edge.label) {
        console.warn('[concept-map] edge missing label:', edge.from, '->', edge.to);
      } else {
        labelTasks.push({ x: cx, y: cy, text: edge.label });
      }
    }

    for (const task of labelTasks) {
      const text = doc.createElementNS(svgNS, 'text');
      text.setAttribute('x', String(task.x));
      text.setAttribute('y', String(task.y));
      text.setAttribute('text-anchor', 'middle');
      text.textContent = task.text;
      svg.appendChild(text);
      let bb;
      try { bb = text.getBBox(); } catch (_) { bb = null; }
      if (bb && bb.width > 0) {
        const padX = 4;
        const padY = 2;
        const rect = doc.createElementNS(svgNS, 'rect');
        rect.setAttribute('class', 'block-concept-map__edge-label-bg');
        rect.setAttribute('x', String(bb.x - padX));
        rect.setAttribute('y', String(bb.y - padY));
        rect.setAttribute('width', String(bb.width + padX * 2));
        rect.setAttribute('height', String(bb.height + padY * 2));
        rect.setAttribute('rx', '3');
        svg.insertBefore(rect, text);
      }
    }
  }

  if (typeof window !== 'undefined') {
    requestAnimationFrame(drawEdges);
    window.addEventListener('resize', drawEdges, { passive: true });
  } else {
    drawEdges();
  }
}
