import { register } from './_bootstrap.js';

const STYLE_ID = 'block-slider-style';
const CSS = `
.block-slider {
  margin: 1.25rem 0;
  padding: 0.85rem 1rem;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}
.block-slider__title { margin: 0 0 0.4rem 0; font-size: 1.05rem; font-weight: 600; }
.block-slider__description { margin: 0 0 0.85rem 0; line-height: 1.5; color: rgba(0, 0, 0, 0.75); }
.block-slider__description p:first-child { margin-top: 0; }
.block-slider__description p:last-child { margin-bottom: 0; }
.block-slider__params { display: grid; gap: 0.65rem; margin-bottom: 0.85rem; }
.block-slider__row { display: grid; grid-template-columns: minmax(8rem, 1fr) 2fr minmax(4rem, max-content); gap: 0.6rem; align-items: center; }
.block-slider__label { font-weight: 500; font-size: 0.92rem; }
.block-slider__input { width: 100%; }
.block-slider__readout {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.88rem;
  text-align: right;
  color: #1f5679;
  font-weight: 600;
}
.block-slider__outputs {
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  padding-top: 0.65rem;
  display: grid;
  gap: 0.4rem;
}
.block-slider__output {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.6rem;
}
.block-slider__output-label { font-size: 0.92rem; font-weight: 500; }
.block-slider__output-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 1rem;
  color: #2e6e40;
  font-weight: 700;
}
`;

const FORMATTERS = {
  number:   (v, decimals) => Number(v).toFixed(decimals ?? 2),
  integer:  (v) => String(Math.round(Number(v))),
  percent:  (v, decimals) => `${(Number(v) * 100).toFixed(decimals ?? 1)}%`,
  currency: (v, decimals) => Number(v).toLocaleString(undefined, { minimumFractionDigits: decimals ?? 2, maximumFractionDigits: decimals ?? 2 }),
  text:     (v) => String(v),
};

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
  root.classList.add('block-slider');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-slider__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }
  if (data.descriptionHtml) {
    const d = doc.createElement('div');
    d.className = 'block-slider__description';
    d.innerHTML = data.descriptionHtml;
    root.appendChild(d);
  }

  const parameters = Array.isArray(data.parameters) ? data.parameters : [];
  const outputs = Array.isArray(data.outputs) ? data.outputs : [];

  const params = doc.createElement('div');
  params.className = 'block-slider__params';
  const state = {};
  const readouts = new Map();

  for (const p of parameters) {
    state[p.name] = Number(p.default);
    const row = doc.createElement('div');
    row.className = 'block-slider__row';

    const label = doc.createElement('label');
    label.className = 'block-slider__label';
    label.htmlFor = `${root.id || 'slider'}-${p.name}`;
    label.textContent = p.label;
    row.appendChild(label);

    const input = doc.createElement('input');
    input.type = 'range';
    input.className = 'block-slider__input';
    input.id = label.htmlFor;
    input.min = String(p.min);
    input.max = String(p.max);
    input.step = String(p.step ?? (p.max - p.min) / 100);
    input.value = String(p.default);
    row.appendChild(input);

    const readout = doc.createElement('span');
    readout.className = 'block-slider__readout';
    readout.textContent = `${p.default}${p.unit ? ' ' + p.unit : ''}`;
    row.appendChild(readout);
    readouts.set(p.name, { readout, unit: p.unit });

    input.addEventListener('input', () => {
      state[p.name] = Number(input.value);
      readout.textContent = `${input.value}${p.unit ? ' ' + p.unit : ''}`;
      recompute();
    });
    params.appendChild(row);
  }
  root.appendChild(params);

  const outputsBox = doc.createElement('div');
  outputsBox.className = 'block-slider__outputs';
  const outputEls = [];
  const computeFns = [];
  for (const o of outputs) {
    const row = doc.createElement('div');
    row.className = 'block-slider__output';
    const lbl = doc.createElement('span');
    lbl.className = 'block-slider__output-label';
    lbl.textContent = o.label;
    row.appendChild(lbl);
    const val = doc.createElement('span');
    val.className = 'block-slider__output-value';
    row.appendChild(val);
    outputsBox.appendChild(row);
    outputEls.push({ row, val, output: o });

    let fn;
    try {
      const argNames = parameters.map((p) => p.name);
      fn = new Function(...argNames, `return (${o.compute});`);
    } catch (err) {
      console.error('[slider] compile error', o.label, err);
      fn = () => 'error';
    }
    computeFns.push(fn);
  }
  root.appendChild(outputsBox);

  function recompute() {
    const args = parameters.map((p) => state[p.name]);
    outputEls.forEach((entry, i) => {
      let result;
      try { result = computeFns[i](...args); } catch (e) { result = 'error'; }
      const fmt = FORMATTERS[entry.output.format] || FORMATTERS.number;
      const formatted = fmt(result, entry.output.decimals);
      entry.val.textContent = `${formatted}${entry.output.unit ? ' ' + entry.output.unit : ''}`;
    });
  }
  recompute();
}

register('slider', mount);
