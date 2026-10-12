const STYLE_ID = 'block-timeline-style';
const STATUS_COLORS = {
  info:    '#1f5679',
  success: '#2e6e40',
  warning: '#be8416',
  danger:  '#aa323c',
};
const CSS = `
.block-timeline { margin: 1.25rem 0; }
.block-timeline__title {
  margin: 0 0 0.85rem 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.block-timeline__list {
  position: relative;
  list-style: none;
  margin: 0;
  padding: 0 0 0 1.5rem;
}
.block-timeline__list::before {
  content: "";
  position: absolute;
  top: 0.4rem;
  bottom: 0.4rem;
  left: 0.45rem;
  width: 2px;
  background: rgba(0, 0, 0, 0.12);
}
.block-timeline__event {
  position: relative;
  padding: 0 0 1rem 0;
}
.block-timeline__event::before {
  content: "";
  position: absolute;
  left: -1.2rem;
  top: 0.35rem;
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 999px;
  background: var(--block-timeline-status, #1f5679);
  box-shadow: 0 0 0 3px white, 0 0 0 4px rgba(0, 0, 0, 0.08);
}
.block-timeline__head {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.block-timeline__date {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  color: rgba(0, 0, 0, 0.55);
  text-transform: uppercase;
}
.block-timeline__tag {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  color: var(--block-timeline-status, #1f5679);
  border: 1px solid currentColor;
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
}
.block-timeline__title-line {
  margin: 0.2rem 0 0.3rem 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.4;
}
.block-timeline__body { margin: 0; line-height: 1.5; }
.block-timeline__body p:first-child { margin-top: 0; }
.block-timeline__body p:last-child { margin-bottom: 0; }
.block-timeline__follow-ups {
  margin: 0.45rem 0 0;
  padding-left: 1.1rem;
  list-style: none;
}
.block-timeline__follow-ups li {
  position: relative;
  padding-left: 1.3rem;
  line-height: 1.5;
  margin: 0.15rem 0;
}
.block-timeline__follow-ups li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.35rem;
  width: 0.8rem;
  height: 0.8rem;
  border: 1.5px solid rgba(0, 0, 0, 0.4);
  border-radius: 3px;
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
  root.classList.add('block-timeline');
  root.innerHTML = '';

  if (data.title) {
    const t = doc.createElement('h3');
    t.className = 'block-timeline__title';
    if (root.id) t.id = `${root.id}-title`;
    t.textContent = data.title;
    root.appendChild(t);
  }

  const list = doc.createElement('ol');
  list.className = 'block-timeline__list';
  const events = Array.isArray(data.events) ? data.events : [];

  for (const event of events) {
    const li = doc.createElement('li');
    li.className = 'block-timeline__event';
    const status = STATUS_COLORS[event.status] || STATUS_COLORS.info;
    li.style.setProperty('--block-timeline-status', status);

    const head = doc.createElement('div');
    head.className = 'block-timeline__head';
    if (event.date) {
      const dateEl = doc.createElement('span');
      dateEl.className = 'block-timeline__date';
      dateEl.textContent = event.date;
      head.appendChild(dateEl);
    }
    if (event.tag) {
      const tagEl = doc.createElement('span');
      tagEl.className = 'block-timeline__tag';
      tagEl.textContent = event.tag;
      head.appendChild(tagEl);
    }
    li.appendChild(head);

    if (event.title) {
      const titleEl = doc.createElement('p');
      titleEl.className = 'block-timeline__title-line';
      titleEl.textContent = event.title;
      li.appendChild(titleEl);
    }

    if (event.bodyHtml) {
      const body = doc.createElement('div');
      body.className = 'block-timeline__body';
      body.innerHTML = event.bodyHtml;
      li.appendChild(body);
    }

    if (Array.isArray(event.followUps) && event.followUps.length > 0) {
      const ul = doc.createElement('ul');
      ul.className = 'block-timeline__follow-ups';
      for (const f of event.followUps) {
        const item = doc.createElement('li');
        item.textContent = f;
        ul.appendChild(item);
      }
      li.appendChild(ul);
    }

    list.appendChild(li);
  }

  root.appendChild(list);
}
