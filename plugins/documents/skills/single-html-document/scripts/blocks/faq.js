const STYLE_ID = 'block-faq-style';
const CSS = `
.block-faq { margin: 1.25rem 0; }
.block-faq__eyebrow {
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--block-faq-accent, #555);
  margin-bottom: 0.25rem;
}
.block-faq__title {
  margin: 0 0 0.75rem 0;
  font-size: 1.1rem;
  font-weight: 600;
}
.block-faq__item {
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  padding: 0.6rem 0;
}
.block-faq__item:last-child { border-bottom: 1px solid rgba(0, 0, 0, 0.1); }
.block-faq__item > summary {
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.2rem 0;
  font-weight: 500;
  line-height: 1.45;
}
.block-faq__item > summary::-webkit-details-marker { display: none; }
.block-faq__item > summary::before {
  content: "+";
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 4px;
  background: var(--block-faq-accent, #1f5679);
  color: white;
  font-weight: 700;
  flex-shrink: 0;
  transition: transform 0.15s ease;
}
.block-faq__item[open] > summary::before { content: "−"; }
.block-faq__answer { padding: 0.5rem 0 0.25rem 2rem; line-height: 1.55; }
.block-faq__answer p:first-child { margin-top: 0; }
.block-faq__answer p:last-child { margin-bottom: 0; }
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
  root.classList.add('block-faq');
  root.innerHTML = '';

  if (data.eyebrow !== '') {
    const eyebrow = doc.createElement('span');
    eyebrow.className = 'block-faq__eyebrow';
    eyebrow.textContent = data.eyebrow || 'FAQ';
    root.appendChild(eyebrow);
  }
  if (data.title) {
    const title = doc.createElement('h3');
    title.className = 'block-faq__title';
    if (root.id) title.id = `${root.id}-title`;
    title.textContent = data.title;
    root.appendChild(title);
  }

  const defaultOpen = data.defaultOpen || 'none';
  const items = Array.isArray(data.items) ? data.items : [];
  items.forEach((item, index) => {
    const details = doc.createElement('details');
    details.className = 'block-faq__item';
    if (defaultOpen === 'all' || (defaultOpen === 'first' && index === 0)) {
      details.setAttribute('open', '');
    }
    const summary = doc.createElement('summary');
    summary.textContent = item.question;
    details.appendChild(summary);

    const answer = doc.createElement('div');
    answer.className = 'block-faq__answer';
    answer.innerHTML = item.answerHtml || '';
    details.appendChild(answer);

    root.appendChild(details);
  });
}
