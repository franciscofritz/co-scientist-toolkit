const STYLE_ID = 'block-callout-style';
const TONES = {
  info:    { bg: 'rgba(31, 86, 121, 0.08)',  rail: '#1f5679', icon: 'i' },
  success: { bg: 'rgba(46, 110, 64, 0.08)',  rail: '#2e6e40', icon: '✓' },
  warning: { bg: 'rgba(190, 132, 22, 0.10)', rail: '#be8416', icon: '!' },
  danger:  { bg: 'rgba(170, 50, 60, 0.08)',  rail: '#aa323c', icon: '✗' },
  key:     { bg: 'rgba(120, 78, 152, 0.08)', rail: '#784e98', icon: '★' },
  neutral: { bg: 'rgba(60, 60, 60, 0.06)',   rail: '#555555', icon: '•' },
};
const CSS = `
.block-callout {
  display: grid;
  grid-template-columns: 2.4rem 1fr;
  gap: 0.75rem;
  align-items: start;
  padding: 0.85rem 1rem;
  margin: 1.1rem 0;
  border-radius: 6px;
  border-left: 4px solid var(--block-callout-rail, #555);
  background: var(--block-callout-bg, rgba(0, 0, 0, 0.04));
  line-height: 1.5;
}
.block-callout__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  background: var(--block-callout-rail, #555);
  color: white;
  font-weight: 700;
  font-size: 0.95rem;
  flex-shrink: 0;
}
.block-callout__icon > svg { width: 1.15rem; height: 1.15rem; }
.block-callout__title {
  margin: 0 0 0.25rem 0;
  font-weight: 600;
  font-size: 0.98rem;
  color: var(--block-callout-rail, inherit);
}
.block-callout__body { margin: 0; }
.block-callout__body p { margin: 0 0 0.5rem 0; }
.block-callout__body p:last-child { margin-bottom: 0; }
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
  const tone = TONES[data.tone] || TONES.neutral;
  root.classList.add('block-callout');
  root.style.setProperty('--block-callout-rail', tone.rail);
  root.style.setProperty('--block-callout-bg', tone.bg);
  root.innerHTML = '';

  const iconEl = doc.createElement('span');
  iconEl.className = 'block-callout__icon';
  iconEl.setAttribute('aria-hidden', 'true');
  if (data.iconHtml) {
    iconEl.innerHTML = data.iconHtml;
  } else if (data.icon && typeof window !== 'undefined' && typeof window.__blocksIcon === 'function' && window.__blocksHasIcon(data.icon)) {
    iconEl.innerHTML = window.__blocksIcon(data.icon);
  } else {
    iconEl.textContent = data.icon || tone.icon;
  }
  root.appendChild(iconEl);

  const content = doc.createElement('div');
  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-callout__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    content.appendChild(t);
  }
  if (data.bodyHtml) {
    const body = doc.createElement('div');
    body.className = 'block-callout__body';
    body.innerHTML = data.bodyHtml;
    content.appendChild(body);
  }
  root.appendChild(content);
}
