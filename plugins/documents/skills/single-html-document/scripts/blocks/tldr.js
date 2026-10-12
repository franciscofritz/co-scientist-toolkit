const STYLE_ID = 'block-tldr-style';
const CSS = `
.block-tldr {
  border-left: 4px solid var(--block-tldr-accent, #0f3d5e);
  background: var(--block-tldr-surface, rgba(15, 61, 94, 0.06));
  padding: 1rem 1.25rem;
  margin: 1.25rem 0;
  border-radius: 0 6px 6px 0;
  font: inherit;
}
.block-tldr__eyebrow {
  display: inline-block;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--block-tldr-accent, #0f3d5e);
  margin-bottom: 0.35rem;
}
.block-tldr__title {
  margin: 0 0 0.4rem 0;
  font-size: 1.05rem;
  font-weight: 600;
  line-height: 1.35;
}
.block-tldr__body { margin: 0; line-height: 1.55; }
.block-tldr__body p { margin: 0 0 0.5rem 0; }
.block-tldr__body p:last-child { margin-bottom: 0; }
.block-tldr__points { margin: 0.6rem 0 0; padding-left: 1.1rem; }
.block-tldr__points li { margin: 0.2rem 0; line-height: 1.45; }
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
  root.classList.add('block-tldr');
  root.innerHTML = '';

  const eyebrow = doc.createElement('span');
  eyebrow.className = 'block-tldr__eyebrow';
  eyebrow.textContent = data.eyebrow || 'TL;DR';
  root.appendChild(eyebrow);

  if (data.title) {
    const title = doc.createElement('h3');
    title.className = 'block-tldr__title';
    if (root.id) title.id = `${root.id}-title`;
    title.textContent = data.title;
    root.appendChild(title);
  }

  if (data.bodyHtml) {
    const body = doc.createElement('div');
    body.className = 'block-tldr__body';
    body.innerHTML = data.bodyHtml;
    root.appendChild(body);
  }

  if (Array.isArray(data.pointsHtml) && data.pointsHtml.length > 0) {
    const list = doc.createElement('ul');
    list.className = 'block-tldr__points';
    for (const pointHtml of data.pointsHtml) {
      const li = doc.createElement('li');
      li.innerHTML = pointHtml;
      list.appendChild(li);
    }
    root.appendChild(list);
  }
}
