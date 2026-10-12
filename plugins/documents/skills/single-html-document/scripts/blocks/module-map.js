const STYLE_ID = 'block-module-map-style';
const KIND_COLORS = {
  package:    { border: '#1f5679', bg: 'rgba(31, 86, 121, 0.06)' },
  entry:      { border: '#2e6e40', bg: 'rgba(46, 110, 64, 0.06)' },
  'hot-path': { border: '#be8416', bg: 'rgba(190, 132, 22, 0.08)' },
  external:   { border: '#aa323c', bg: 'rgba(170, 50, 60, 0.06)' },
  default:    { border: '#555',    bg: 'rgba(0, 0, 0, 0.04)' },
};
const CONN_STYLES = {
  import: { dash: '0',     opacity: 0.75 },
  data:   { dash: '6 4',   opacity: 0.75 },
  event:  { dash: '2 4',   opacity: 0.75 },
};
const CSS = `
.block-module-map { margin: 1.25rem 0; min-width: 0; }
.block-module-map__title { margin: 0 0 0.85rem 0; font-size: 1.05rem; font-weight: 600; }
.block-module-map__stage {
  position: relative;
  display: flex;
  gap: 3rem;
  padding: 1.25rem 1rem;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
  min-width: 0;
}
.block-module-map__column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  min-width: 0;
}
.block-module-map__column-header {
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.5);
  margin-bottom: 0.15rem;
}
.block-module-map__module {
  background: var(--block-mm-bg, rgba(0, 0, 0, 0.04));
  border: 1.5px solid var(--block-mm-border, #555);
  border-radius: 6px;
  padding: 0.55rem 0.7rem;
  position: relative;
  z-index: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
.block-module-map__module-label { font-weight: 600; font-size: 0.95rem; line-height: 1.3; }
.block-module-map__module-summary {
  font-size: 0.85rem;
  color: rgba(0, 0, 0, 0.7);
  margin: 0.25rem 0 0;
  line-height: 1.4;
}
.block-module-map__module-summary p { margin: 0; }
.block-module-map__edges { position: absolute; inset: 0; pointer-events: none; overflow: visible; }
.block-module-map__edges path { fill: none; stroke: rgba(0, 0, 0, 0.5); stroke-width: 1.4; stroke-linejoin: round; stroke-linecap: round; }
.block-module-map__edges polygon { fill: rgba(0, 0, 0, 0.5); }
.block-module-map__edge-label-bg {
  fill: rgba(247, 245, 240, 0.96);
  stroke: rgba(247, 245, 240, 0.96);
  stroke-width: 0.5;
}
.block-module-map__edges text {
  font-size: 0.74rem;
  fill: rgba(0, 0, 0, 0.7);
  font-weight: 500;
  dominant-baseline: middle;
}
.block-module-map__legend {
  margin-top: 0.65rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  font-size: 0.78rem;
}
.block-module-map__legend-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  border: 1.5px solid currentColor;
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
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
  root.classList.add('block-module-map');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-module-map__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const stage = doc.createElement('div');
  stage.className = 'block-module-map__stage';

  const modules = Array.isArray(data.modules) ? data.modules : [];
  const connections = Array.isArray(data.connections) ? data.connections : [];
  const columns = Array.isArray(data.columns) ? data.columns : [];
  const numColumns = Math.max(
    columns.length,
    ...modules.map((m) => (m.column || 0) + 1),
    1,
  );

  const moduleEls = new Map();
  const moduleColumn = new Map();
  const columnEls = [];
  for (let i = 0; i < numColumns; i++) {
    const col = doc.createElement('div');
    col.className = 'block-module-map__column';
    if (columns[i] && columns[i].label) {
      const head = doc.createElement('div');
      head.className = 'block-module-map__column-header';
      head.textContent = columns[i].label;
      col.appendChild(head);
    }
    stage.appendChild(col);
    columnEls.push(col);
  }

  for (const m of modules) {
    const el = doc.createElement('div');
    el.className = 'block-module-map__module';
    const tone = KIND_COLORS[m.kind] || KIND_COLORS.default;
    el.style.setProperty('--block-mm-border', tone.border);
    el.style.setProperty('--block-mm-bg', tone.bg);
    el.setAttribute('data-module-id', m.id);
    const label = doc.createElement('div');
    label.className = 'block-module-map__module-label';
    label.textContent = m.label || m.id;
    el.appendChild(label);
    if (m.summaryHtml) {
      const summary = doc.createElement('div');
      summary.className = 'block-module-map__module-summary';
      summary.innerHTML = m.summaryHtml;
      el.appendChild(summary);
    }
    columnEls[m.column || 0].appendChild(el);
    moduleEls.set(m.id, el);
    moduleColumn.set(m.id, m.column || 0);
  }

  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = doc.createElementNS(svgNS, 'svg');
  svg.setAttribute('class', 'block-module-map__edges');
  stage.appendChild(svg);

  root.appendChild(stage);

  const showLegend = data.legend !== false && modules.some((m) => m.kind && KIND_COLORS[m.kind]);
  if (showLegend) {
    const legend = doc.createElement('div');
    legend.className = 'block-module-map__legend';
    const seen = new Set();
    for (const m of modules) {
      if (!m.kind || seen.has(m.kind)) continue;
      seen.add(m.kind);
      const tone = KIND_COLORS[m.kind] || KIND_COLORS.default;
      const chip = doc.createElement('span');
      chip.className = 'block-module-map__legend-chip';
      chip.style.color = tone.border;
      chip.textContent = m.kind;
      legend.appendChild(chip);
    }
    root.appendChild(legend);
  }

  function drawEdges() {
    const stageRect = stage.getBoundingClientRect();
    if (stageRect.width === 0) return;
    svg.setAttribute('viewBox', `0 0 ${stageRect.width} ${stageRect.height}`);
    svg.setAttribute('width', String(stageRect.width));
    svg.setAttribute('height', String(stageRect.height));
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    // Resolve column geometry up-front so we route through real gutters,
    // not through arbitrary points between source and target.
    const columnRects = columnEls.map((el) => {
      const r = el.getBoundingClientRect();
      return { left: r.left - stageRect.left, right: r.right - stageRect.left };
    });

    // Group edges by ordered (sourceCol, targetCol) so edges sharing a gutter
    // can stagger their crossings and labels.
    const groupKey = (conn) => `${moduleColumn.get(conn.from)}->${moduleColumn.get(conn.to)}`;
    const groups = new Map();
    for (const conn of connections) {
      const key = groupKey(conn);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(conn);
    }

    // Reserve labels for a second pass so they layer above the paths.
    const labelTasks = [];

    for (const [, group] of groups) {
      group.forEach((conn, i) => {
        const fromEl = moduleEls.get(conn.from);
        const toEl = moduleEls.get(conn.to);
        if (!fromEl || !toEl) return;

        const sourceCol = moduleColumn.get(conn.from);
        const targetCol = moduleColumn.get(conn.to);
        const forward = sourceCol < targetCol;
        const backward = sourceCol > targetCol;
        const sameCol = sourceCol === targetCol;

        const a = fromEl.getBoundingClientRect();
        const b = toEl.getBoundingClientRect();
        const aMidY = a.top + a.height / 2 - stageRect.top;
        const bMidY = b.top + b.height / 2 - stageRect.top;

        const n = group.length;
        // frac in [-0.5, +0.5], evenly spaced across edges in this group
        const frac = ((i + 1) / (n + 1)) - 0.5;

        let sx, sy, tx, ty, gx;
        let arrowDir; // 1 = pointing right, -1 = pointing left

        if (forward) {
          sx = a.right - stageRect.left;
          tx = b.left - stageRect.left;
          sy = aMidY;
          ty = bMidY;
          // Real gutter between the two columns
          const gutterLeft = columnRects[sourceCol].right;
          const gutterRight = columnRects[targetCol].left;
          const gutterWidth = Math.max(8, gutterRight - gutterLeft);
          const gutterCenter = (gutterLeft + gutterRight) / 2;
          // Stagger across 60% of the gutter width; clamp to keep edges off the column edges
          gx = gutterCenter + frac * gutterWidth * 0.6;
          gx = Math.max(gutterLeft + 4, Math.min(gutterRight - 4, gx));
          arrowDir = 1; // pointing right into target.left
        } else if (backward) {
          // Mirror of forward
          sx = a.left - stageRect.left;
          tx = b.right - stageRect.left;
          sy = aMidY;
          ty = bMidY;
          const gutterLeft = columnRects[targetCol].right;
          const gutterRight = columnRects[sourceCol].left;
          const gutterWidth = Math.max(8, gutterRight - gutterLeft);
          const gutterCenter = (gutterLeft + gutterRight) / 2;
          gx = gutterCenter + frac * gutterWidth * 0.6;
          gx = Math.max(gutterLeft + 4, Math.min(gutterRight - 4, gx));
          arrowDir = -1; // pointing left into target.right
        } else {
          // Same column: route around the right edge of the column.
          sx = a.right - stageRect.left;
          tx = b.right - stageRect.left;
          sy = aMidY;
          ty = bMidY;
          const colRight = columnRects[sourceCol].right;
          // 18px base offset; stagger by 6px per edge
          gx = colRight + 18 + i * 6;
          arrowDir = -1; // pointing left into target.right
        }

        // Pure orthogonal path: H, V, H. No curves.
        const d = `M ${sx} ${sy} L ${gx} ${sy} L ${gx} ${ty} L ${tx} ${ty}`;
        const path = doc.createElementNS(svgNS, 'path');
        const style = CONN_STYLES[conn.kind] || CONN_STYLES.import;
        path.setAttribute('d', d);
        path.setAttribute('stroke-dasharray', style.dash);
        path.setAttribute('opacity', String(style.opacity));
        svg.appendChild(path);

        // Arrowhead at (tx, ty) pointing in arrowDir.
        const arrowSize = 7;
        const arrow = doc.createElementNS(svgNS, 'polygon');
        if (arrowDir === 1) {
          arrow.setAttribute('points', `${tx},${ty} ${tx - arrowSize},${ty - 4.5} ${tx - arrowSize},${ty + 4.5}`);
        } else {
          arrow.setAttribute('points', `${tx},${ty} ${tx + arrowSize},${ty - 4.5} ${tx + arrowSize},${ty + 4.5}`);
        }
        svg.appendChild(arrow);

        // Defer the label render until all paths are drawn so labels layer on top.
        if (conn.label) {
          // Place the label on the vertical segment in the gutter; that's the
          // safest position because the gutter is by definition free of module
          // text.
          labelTasks.push({ x: gx, y: (sy + ty) / 2, text: conn.label });
        }
      });
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
        rect.setAttribute('class', 'block-module-map__edge-label-bg');
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
