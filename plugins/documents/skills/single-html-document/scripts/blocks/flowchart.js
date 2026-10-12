import { register } from './_bootstrap.js';

const STYLE_ID = 'block-flowchart-style';
const STATUS_COLORS = {
  info:    '#1f5679',
  success: '#2e6e40',
  warning: '#be8416',
  danger:  '#aa323c',
};
const CSS = `
.block-flowchart { margin: 1.25rem 0; }
.block-flowchart__title {
  margin: 0 0 0.85rem 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.block-flowchart__stage {
  position: relative;
  display: grid;
  gap: 1.4rem 1rem;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
}
.block-flowchart__edges {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
}
.block-flowchart__edges path { fill: none; stroke: rgba(0, 0, 0, 0.4); stroke-width: 1.4; }
.block-flowchart__edges text {
  font-size: 0.72rem;
  fill: rgba(0, 0, 0, 0.6);
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.85);
  stroke-width: 3px;
}
.block-flowchart__node {
  position: relative;
  background: white;
  border: 1.5px solid var(--block-flowchart-status, rgba(0, 0, 0, 0.5));
  border-radius: 6px;
  padding: 0.55rem 0.75rem;
  min-width: 8rem;
  text-align: center;
  font-size: 0.92rem;
  line-height: 1.3;
  cursor: pointer;
  z-index: 1;
}
.block-flowchart__node:focus { outline: 2px solid var(--block-flowchart-status, #1f5679); outline-offset: 2px; }
.block-flowchart__node--decision { border-radius: 6px; transform: skewX(-8deg); }
.block-flowchart__node--decision .block-flowchart__node-label { transform: skewX(8deg); display: inline-block; }
.block-flowchart__node--terminal { border-radius: 999px; }
.block-flowchart__node-timing {
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  color: rgba(0, 0, 0, 0.55);
  margin-top: 0.2rem;
}
.block-flowchart__details {
  margin-top: 0.85rem;
  padding: 0.65rem 0.85rem;
  background: white;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 6px;
  min-height: 1rem;
}
.block-flowchart__details:empty { display: none; }
.block-flowchart__details-eyebrow {
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.5);
  margin-bottom: 0.25rem;
}
.block-flowchart__details-body p:first-child { margin-top: 0; }
.block-flowchart__details-body p:last-child { margin-bottom: 0; }
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
  root.classList.add('block-flowchart');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-flowchart__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const stage = doc.createElement('div');
  stage.className = 'block-flowchart__stage';
  const direction = data.direction === 'left-right' ? 'left-right' : 'top-down';
  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  const edges = Array.isArray(data.edges) ? data.edges : [];

  let maxLane = 0;
  let maxOrder = 0;
  const positions = new Map();
  for (const n of nodes) {
    maxLane = Math.max(maxLane, n.lane || 0);
    maxOrder = Math.max(maxOrder, n.order || 0);
  }
  if (direction === 'top-down') {
    stage.style.gridTemplateColumns = `repeat(${maxLane + 1}, minmax(8rem, 1fr))`;
    stage.style.gridTemplateRows = `repeat(${maxOrder + 1}, auto)`;
  } else {
    stage.style.gridTemplateRows = `repeat(${maxLane + 1}, auto)`;
    stage.style.gridTemplateColumns = `repeat(${maxOrder + 1}, minmax(8rem, 1fr))`;
  }

  const nodeEls = new Map();
  for (const node of nodes) {
    const el = doc.createElement('button');
    el.type = 'button';
    el.className = `block-flowchart__node block-flowchart__node--${node.kind || 'step'}`;
    el.setAttribute('data-node-id', node.id);
    if (node.status) {
      el.style.setProperty('--block-flowchart-status', STATUS_COLORS[node.status] || STATUS_COLORS.info);
    }
    if (direction === 'top-down') {
      el.style.gridColumn = String((node.lane || 0) + 1);
      el.style.gridRow = String((node.order || 0) + 1);
    } else {
      el.style.gridRow = String((node.lane || 0) + 1);
      el.style.gridColumn = String((node.order || 0) + 1);
    }
    const labelSpan = doc.createElement('span');
    labelSpan.className = 'block-flowchart__node-label';
    labelSpan.textContent = node.label || node.id;
    el.appendChild(labelSpan);
    if (node.timing) {
      const timing = doc.createElement('span');
      timing.className = 'block-flowchart__node-timing';
      timing.textContent = node.timing;
      el.appendChild(timing);
    }
    stage.appendChild(el);
    nodeEls.set(node.id, { el, node });
  }

  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = doc.createElementNS(svgNS, 'svg');
  svg.setAttribute('class', 'block-flowchart__edges');
  svg.setAttribute('preserveAspectRatio', 'none');
  stage.appendChild(svg);

  root.appendChild(stage);

  const details = doc.createElement('div');
  details.className = 'block-flowchart__details';
  root.appendChild(details);

  function drawEdges() {
    const stageRect = stage.getBoundingClientRect();
    if (stageRect.width === 0) return;
    svg.setAttribute('viewBox', `0 0 ${stageRect.width} ${stageRect.height}`);
    svg.setAttribute('width', String(stageRect.width));
    svg.setAttribute('height', String(stageRect.height));
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    for (const edge of edges) {
      const fromEntry = nodeEls.get(edge.from);
      const toEntry = nodeEls.get(edge.to);
      if (!fromEntry || !toEntry) continue;
      const a = fromEntry.el.getBoundingClientRect();
      const b = toEntry.el.getBoundingClientRect();
      let x1, y1, x2, y2;
      if (direction === 'top-down') {
        x1 = a.left + a.width / 2 - stageRect.left;
        y1 = a.bottom - stageRect.top;
        x2 = b.left + b.width / 2 - stageRect.left;
        y2 = b.top - stageRect.top;
      } else {
        x1 = a.right - stageRect.left;
        y1 = a.top + a.height / 2 - stageRect.top;
        x2 = b.left - stageRect.left;
        y2 = b.top + b.height / 2 - stageRect.top;
      }
      const d = direction === 'top-down'
        ? `M ${x1} ${y1} C ${x1} ${(y1 + y2) / 2}, ${x2} ${(y1 + y2) / 2}, ${x2} ${y2}`
        : `M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`;
      const path = doc.createElementNS(svgNS, 'path');
      path.setAttribute('d', d);
      svg.appendChild(path);
      if (edge.label) {
        const text = doc.createElementNS(svgNS, 'text');
        text.setAttribute('x', String((x1 + x2) / 2));
        text.setAttribute('y', String((y1 + y2) / 2));
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('dominant-baseline', 'middle');
        text.textContent = edge.label;
        svg.appendChild(text);
      }
    }
  }

  function showDetails(nodeId) {
    const entry = nodeEls.get(nodeId);
    if (!entry) return;
    const node = entry.node;
    details.innerHTML = '';
    const eyebrow = doc.createElement('div');
    eyebrow.className = 'block-flowchart__details-eyebrow';
    eyebrow.textContent = `${node.kind || 'step'} · ${node.label || node.id}`;
    details.appendChild(eyebrow);
    if (node.bodyHtml) {
      const body = doc.createElement('div');
      body.className = 'block-flowchart__details-body';
      body.innerHTML = node.bodyHtml;
      details.appendChild(body);
    }
  }

  for (const [id, entry] of nodeEls) {
    entry.el.addEventListener('click', () => showDetails(id));
  }

  if (typeof window !== 'undefined') {
    requestAnimationFrame(drawEdges);
    window.addEventListener('resize', drawEdges, { passive: true });
  } else {
    drawEdges();
  }
}

register('flowchart', mount);
