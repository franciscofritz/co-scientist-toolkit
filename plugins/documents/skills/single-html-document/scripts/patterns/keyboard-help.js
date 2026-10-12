// Keyboard help pattern: a `?` overlay listing the page's active shortcuts.
//
// The pattern collects entries from a registry that other patterns
// contribute to. To add an entry from a manifest, pass `entries` in options.
// To add programmatically (e.g. from another pattern), call
// window.__pageKeyboardHelp.register({ keys: 'T', label: 'Open contents' }).
//
// The overlay is keyboard-first: ? to open, Esc to close.

const STYLE_ID = 'page-keyboard-help-pattern-style';
const CSS = `
.page-keyboard-help {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
}
body[data-keyboard-help-open="true"] .page-keyboard-help { display: flex; }
.page-keyboard-help__panel {
  width: min(28rem, 92vw);
  background: white;
  border-radius: 10px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  padding: 1rem 1.1rem 1.2rem;
}
.page-keyboard-help__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 0.7rem;
}
.page-keyboard-help__title { margin: 0; font-size: 0.78rem; letter-spacing: 0.14em; text-transform: uppercase; color: #555; font-weight: 700; }
.page-keyboard-help__close {
  font: inherit;
  font-size: 0.78rem;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  padding: 0.18rem 0.5rem;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.04);
  color: rgba(0, 0, 0, 0.65);
  cursor: pointer;
}
.page-keyboard-help__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.4rem 0.85rem;
  align-items: baseline;
}
.page-keyboard-help__keys { display: inline-flex; gap: 0.15rem; }
.page-keyboard-help__keys kbd {
  font: inherit;
  font-size: 0.78rem;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.15));
  padding: 0.05rem 0.4rem;
  border-radius: 3px;
  font-weight: 600;
  color: var(--page-ink, #1c1c1f);
}
.page-keyboard-help__label { color: rgba(0, 0, 0, 0.78); font-size: 0.92rem; }
.page-keyboard-help__hint {
  margin: 0.85rem 0 0;
  font-size: 0.8rem;
  color: rgba(0, 0, 0, 0.5);
}
`;

const REGISTRY = [];
let overlay = null;
let listEl = null;
let opts = null;

function isEditableTarget(el) {
  if (!el) return false;
  const tag = (el.tagName || '').toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.isContentEditable) return true;
  return false;
}

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

function rerender() {
  if (!listEl) return;
  listEl.innerHTML = '';
  for (const entry of REGISTRY) {
    const li = document.createElement('li');
    li.style.display = 'contents';
    const keys = document.createElement('span');
    keys.className = 'page-keyboard-help__keys';
    const parts = String(entry.keys).split(/\s+\+\s+|\s+/).filter(Boolean);
    if (parts.length === 0) parts.push(entry.keys);
    parts.forEach((p, i) => {
      const kb = document.createElement('kbd');
      kb.textContent = p;
      keys.appendChild(kb);
      if (i < parts.length - 1) keys.append(' + ');
    });
    const label = document.createElement('span');
    label.className = 'page-keyboard-help__label';
    label.textContent = entry.label;
    listEl.appendChild(keys);
    listEl.appendChild(label);
  }
}

function setOpen(open) {
  document.body.setAttribute('data-keyboard-help-open', open ? 'true' : 'false');
  if (open) rerender();
}

export function register(entry) {
  if (!entry || !entry.keys || !entry.label) return;
  // Avoid duplicates by key+label.
  for (const e of REGISTRY) {
    if (e.keys === entry.keys && e.label === entry.label) return;
  }
  REGISTRY.push(entry);
}

export function init(options) {
  if (typeof document === 'undefined') return;
  opts = Object.assign({
    enabled: true,
    shortcut: '?',
    entries: [],
  }, options || {});
  if (!opts.enabled) return;

  // Always-on entries.
  register({ keys: opts.shortcut, label: 'Show this help' });

  // Pull entries from manifest config.
  for (const e of opts.entries || []) register(e);

  const ready = (fn) => {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  };

  ready(() => {
    ensureStyle(document);

    overlay = document.createElement('div');
    overlay.className = 'page-keyboard-help';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Keyboard shortcuts');

    const panel = document.createElement('div');
    panel.className = 'page-keyboard-help__panel';

    const head = document.createElement('div');
    head.className = 'page-keyboard-help__head';
    const title = document.createElement('p');
    title.className = 'page-keyboard-help__title';
    title.textContent = 'Keyboard shortcuts';
    head.appendChild(title);
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'page-keyboard-help__close';
    closeBtn.textContent = 'Close';
    head.appendChild(closeBtn);
    panel.appendChild(head);

    listEl = document.createElement('ul');
    listEl.className = 'page-keyboard-help__list';
    panel.appendChild(listEl);

    const hint = document.createElement('p');
    hint.className = 'page-keyboard-help__hint';
    hint.textContent = 'Shortcuts work anywhere on the page. They are ignored while you are typing in a search box or text field.';
    panel.appendChild(hint);

    overlay.appendChild(panel);
    document.body.appendChild(overlay);

    closeBtn.addEventListener('click', () => setOpen(false));
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) setOpen(false);
    });

    document.addEventListener('keydown', (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isEditableTarget(e.target)) return;
      if (e.key === opts.shortcut) {
        e.preventDefault();
        setOpen(document.body.getAttribute('data-keyboard-help-open') !== 'true');
      } else if (e.key === 'Escape' && document.body.getAttribute('data-keyboard-help-open') === 'true') {
        e.preventDefault();
        setOpen(false);
      }
    });

    if (typeof window !== 'undefined') {
      window.__pageKeyboardHelp = {
        open: () => setOpen(true),
        close: () => setOpen(false),
        toggle: () => setOpen(document.body.getAttribute('data-keyboard-help-open') !== 'true'),
        register,
      };
    }
  });
}
