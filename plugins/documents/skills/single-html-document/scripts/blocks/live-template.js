import { register } from './_bootstrap.js';

const STYLE_ID = 'block-live-template-style';
const CSS = `
.block-live-template { margin: 1.25rem 0; padding: 0.85rem 1rem; background: rgba(0, 0, 0, 0.03); border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 6px; }
.block-live-template__title { margin: 0 0 0.4rem 0; font-size: 1.05rem; font-weight: 600; }
.block-live-template__description { margin: 0 0 0.85rem 0; line-height: 1.5; color: rgba(0, 0, 0, 0.75); }
.block-live-template__description p:first-child { margin-top: 0; }
.block-live-template__description p:last-child { margin-bottom: 0; }
.block-live-template__layout { display: grid; gap: 0.85rem; }
@media (min-width: 720px) { .block-live-template__layout { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); } }
.block-live-template__inputs { display: grid; gap: 0.55rem; }
.block-live-template__input-row { display: flex; flex-direction: column; gap: 0.2rem; }
.block-live-template__input-label { font-size: 0.85rem; font-weight: 500; color: rgba(0, 0, 0, 0.75); }
.block-live-template__input,
.block-live-template__textarea,
.block-live-template__select {
  font: inherit;
  font-size: 0.92rem;
  padding: 0.4rem 0.55rem;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.18);
  background: white;
  width: 100%;
  box-sizing: border-box;
}
.block-live-template__textarea { resize: vertical; min-height: 4rem; }
.block-live-template__output {
  background: white;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 4px;
  padding: 0.6rem 0.75rem;
  position: relative;
  min-height: 6rem;
}
.block-live-template__output[data-format="code"] { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.88rem; white-space: pre-wrap; }
.block-live-template__output[data-format="text"] { white-space: pre-wrap; line-height: 1.5; }
.block-live-template__output[data-format="markdown"] p:first-child { margin-top: 0; }
.block-live-template__output[data-format="markdown"] p:last-child { margin-bottom: 0; }
.block-live-template__copy {
  position: absolute;
  top: 0.4rem;
  right: 0.45rem;
  font: inherit;
  font-size: 0.78rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #1f5679;
  background: white;
  color: #1f5679;
  cursor: pointer;
}
.block-live-template__copy:hover { background: #1f5679; color: white; }
.block-live-template__copy[data-copied] { background: #2e6e40; border-color: #2e6e40; color: white; }
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

function fillTemplate(template, values) {
  return template
    .replace(/\{\{\s*(\w+)\s*\}\}/g, (_, name) => values[name] ?? `{{${name}}}`)
    .replace(/\{\s*(\w+)\s*\}/g, (_, name) => values[name] ?? `{${name}}`);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  root.classList.add('block-live-template');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-live-template__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }
  if (data.descriptionHtml) {
    const d = doc.createElement('div');
    d.className = 'block-live-template__description';
    d.innerHTML = data.descriptionHtml;
    root.appendChild(d);
  }

  const layout = doc.createElement('div');
  layout.className = 'block-live-template__layout';

  const inputsBox = doc.createElement('div');
  inputsBox.className = 'block-live-template__inputs';
  const variables = Array.isArray(data.variables) ? data.variables : [];
  const state = {};
  for (const v of variables) state[v.name] = v.default ?? '';

  for (const v of variables) {
    const row = doc.createElement('div');
    row.className = 'block-live-template__input-row';
    const label = doc.createElement('label');
    label.className = 'block-live-template__input-label';
    label.textContent = v.label || v.name;
    label.htmlFor = `${root.id || 'live'}-${v.name}`;
    row.appendChild(label);

    let input;
    if (v.kind === 'multiline') {
      input = doc.createElement('textarea');
      input.className = 'block-live-template__textarea';
      input.rows = 3;
    } else if (v.kind === 'select') {
      input = doc.createElement('select');
      input.className = 'block-live-template__select';
      for (const opt of (v.options || [])) {
        const o = doc.createElement('option');
        o.value = opt;
        o.textContent = opt;
        input.appendChild(o);
      }
    } else {
      input = doc.createElement('input');
      input.type = 'text';
      input.className = 'block-live-template__input';
    }
    input.id = label.htmlFor;
    input.value = state[v.name];
    if (v.placeholder) input.placeholder = v.placeholder;
    input.addEventListener('input', () => { state[v.name] = input.value; refresh(); });
    input.addEventListener('change', () => { state[v.name] = input.value; refresh(); });
    row.appendChild(input);
    inputsBox.appendChild(row);
  }
  layout.appendChild(inputsBox);

  const outputFormat = ['text', 'code', 'markdown'].includes(data.outputFormat) ? data.outputFormat : 'text';
  const outputBox = doc.createElement('div');
  outputBox.className = 'block-live-template__output';
  outputBox.setAttribute('data-format', outputFormat);
  layout.appendChild(outputBox);

  const copyBtn = doc.createElement('button');
  copyBtn.type = 'button';
  copyBtn.className = 'block-live-template__copy';
  copyBtn.textContent = 'Copy';
  outputBox.appendChild(copyBtn);

  function refresh() {
    const filled = fillTemplate(data.template || '', state);
    if (outputFormat === 'markdown') {
      outputBox.innerHTML = '';
      outputBox.appendChild(copyBtn);
      const renderArea = doc.createElement('div');
      renderArea.style.whiteSpace = 'pre-wrap';
      renderArea.textContent = filled;
      outputBox.appendChild(renderArea);
    } else {
      outputBox.innerHTML = '';
      outputBox.appendChild(copyBtn);
      const renderArea = doc.createElement('div');
      renderArea.style.whiteSpace = 'pre-wrap';
      renderArea.textContent = filled;
      outputBox.appendChild(renderArea);
    }
    copyBtn.onclick = async () => {
      const ok = await copyText(filled);
      if (ok) {
        copyBtn.setAttribute('data-copied', '');
        copyBtn.textContent = 'Copied';
        setTimeout(() => {
          copyBtn.removeAttribute('data-copied');
          copyBtn.textContent = 'Copy';
        }, 1100);
      }
    };
  }
  refresh();
  root.appendChild(layout);
}

register('live-template', mount);
