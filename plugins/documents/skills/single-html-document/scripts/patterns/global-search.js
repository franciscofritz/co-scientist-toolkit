// Global search pattern: an overlay that searches all visible text content
// in the page and lets the reader jump to a match with the keyboard.
//
// Triggered by `/` (and optionally `\\`). Within the overlay:
//   - Type to filter results incrementally
//   - ArrowUp/ArrowDown to navigate
//   - Enter jumps to the highlighted result and briefly flashes it
//   - Esc closes
//
// The search index is built lazily on first open from the rendered DOM:
//   - Walks every <section[id]> as a search unit
//   - For each, collects the heading and a chunk of body text
//   - Matches are ranked: heading match > body match
//
// No external dependencies. No fuzzy matching beyond case-insensitive
// substring; that's enough for navigation through a single document.

const STYLE_ID = 'page-global-search-pattern-style';
const CSS = `
.page-global-search {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: none;
  align-items: flex-start;
  justify-content: center;
  padding-top: 6vh;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
}
body[data-global-search-open="true"] .page-global-search { display: flex; }
.page-global-search__panel {
  width: min(36rem, 92vw);
  max-height: 80vh;
  background: white;
  border-radius: 10px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.page-global-search__head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 0.85rem;
  border-bottom: 1px solid var(--page-line, rgba(0, 0, 0, 0.1));
}
.page-global-search__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 0, 0, 0.55);
}
.page-global-search__icon > svg { width: 1.15rem; height: 1.15rem; }
.page-global-search__input {
  flex: 1;
  font: inherit;
  font-size: 1rem;
  border: 0;
  outline: none;
  padding: 0.3rem 0;
  color: var(--page-ink, #1c1c1f);
  background: transparent;
}
.page-global-search__close {
  font: inherit;
  font-size: 0.78rem;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.04);
  color: rgba(0, 0, 0, 0.65);
  cursor: pointer;
}
.page-global-search__close kbd {
  font: inherit;
  font-size: 0.7rem;
  background: rgba(0, 0, 0, 0.08);
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
}
.page-global-search__results {
  flex: 1;
  overflow-y: auto;
  padding: 0.4rem 0.5rem 0.65rem;
  margin: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.page-global-search__empty,
.page-global-search__hint {
  padding: 1rem;
  text-align: center;
  color: rgba(0, 0, 0, 0.5);
  font-size: 0.9rem;
}
.page-global-search__result {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  padding: 0.5rem 0.7rem;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font: inherit;
}
.page-global-search__result:hover { background: rgba(31, 86, 121, 0.08); }
.page-global-search__result[data-keynav="true"] {
  background: rgba(31, 86, 121, 0.14);
  outline: 2px solid var(--page-accent, #1f5679);
  outline-offset: -2px;
}
.page-global-search__result-title { font-weight: 600; color: var(--page-ink, #1c1c1f); line-height: 1.3; }
.page-global-search__result-excerpt {
  font-size: 0.85rem;
  color: rgba(0, 0, 0, 0.65);
  margin-top: 0.15rem;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.page-global-search__result mark {
  background: rgba(190, 132, 22, 0.25);
  color: inherit;
  padding: 0 0.1rem;
  border-radius: 2px;
}

/* Section flash on jump */
.page-global-search-flash {
  animation: page-global-search-flash 1.2s ease-out;
}
@keyframes page-global-search-flash {
  0%   { box-shadow: inset 0 0 0 3px rgba(31, 86, 121, 0.6); }
  100% { box-shadow: inset 0 0 0 3px rgba(31, 86, 121, 0); }
}

.page-global-search__launcher {
  position: fixed;
  /* Top-left, stacked below the TOC launcher (which sits at top: 1rem). */
  top: 4rem;
  left: 1rem;
  z-index: 30;
  width: 2.6rem;
  height: 2.6rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  background: white;
  color: var(--page-ink, #1c1c1f);
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.page-global-search__launcher > svg { width: 1.15rem; height: 1.15rem; }
`;

const ICON_SEARCH = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>';

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

function isEditableTarget(el) {
  if (!el) return false;
  const tag = (el.tagName || '').toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.isContentEditable) return true;
  return false;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}

function highlight(text, needle) {
  if (!needle) return escapeHtml(text);
  const t = String(text);
  const lower = t.toLowerCase();
  const n = needle.toLowerCase();
  let out = '';
  let i = 0;
  while (i < t.length) {
    const at = lower.indexOf(n, i);
    if (at < 0) { out += escapeHtml(t.slice(i)); break; }
    out += escapeHtml(t.slice(i, at)) + '<mark>' + escapeHtml(t.slice(at, at + n.length)) + '</mark>';
    i = at + n.length;
  }
  return out;
}

function buildIndex() {
  const sections = Array.from(document.querySelectorAll('section[id]'));
  const docs = [];
  for (const section of sections) {
    const heading = section.querySelector('h2');
    if (!heading) continue;
    const title = heading.textContent.trim();
    // Body text: everything inside the section, minus its h2.
    const clone = section.cloneNode(true);
    const h2Clone = clone.querySelector('h2');
    if (h2Clone) h2Clone.remove();
    const body = clone.textContent.replace(/\s+/g, ' ').trim();
    docs.push({ id: section.id, title, body, target: section });
  }
  return docs;
}

function search(docs, q) {
  const needle = q.toLowerCase().trim();
  if (!needle) return [];
  const out = [];
  for (const doc of docs) {
    const titleLower = doc.title.toLowerCase();
    const titleHit = titleLower.indexOf(needle);
    const bodyLower = doc.body.toLowerCase();
    const bodyHit = bodyLower.indexOf(needle);
    if (titleHit < 0 && bodyHit < 0) continue;
    let score = 0;
    if (titleHit >= 0) score += 100 - Math.min(50, titleHit);
    if (bodyHit >= 0) score += 50 - Math.min(40, bodyHit / 10);
    let excerpt = '';
    if (bodyHit >= 0) {
      const start = Math.max(0, bodyHit - 40);
      const end = Math.min(doc.body.length, bodyHit + needle.length + 80);
      excerpt = (start > 0 ? '… ' : '') + doc.body.slice(start, end) + (end < doc.body.length ? ' …' : '');
    }
    out.push({ id: doc.id, title: doc.title, excerpt, score });
  }
  out.sort((a, b) => b.score - a.score);
  return out.slice(0, 30);
}

export function init(options) {
  if (typeof document === 'undefined') return;
  const opts = Object.assign({
    enabled: true,
    shortcut: '/',
    altShortcut: '\\',
    showLauncher: true,
  }, options || {});
  if (!opts.enabled) return;

  const ready = (fn) => {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  };

  ready(() => {
    ensureStyle(document);

    let docs = null;
    let lastResults = [];
    let keyNav = -1;

    const overlay = document.createElement('div');
    overlay.className = 'page-global-search';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Search the page');

    const panel = document.createElement('div');
    panel.className = 'page-global-search__panel';

    const head = document.createElement('div');
    head.className = 'page-global-search__head';
    const iconWrap = document.createElement('span');
    iconWrap.className = 'page-global-search__icon';
    iconWrap.innerHTML = ICON_SEARCH;
    head.appendChild(iconWrap);
    const input = document.createElement('input');
    input.type = 'search';
    input.className = 'page-global-search__input';
    input.placeholder = 'Search the page…';
    input.setAttribute('aria-label', 'Search the page');
    head.appendChild(input);
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'page-global-search__close';
    closeBtn.innerHTML = 'Close <kbd>Esc</kbd>';
    head.appendChild(closeBtn);
    panel.appendChild(head);

    const list = document.createElement('ul');
    list.className = 'page-global-search__results';
    panel.appendChild(list);

    const hint = document.createElement('div');
    hint.className = 'page-global-search__hint';
    hint.innerHTML = `Type to search · <kbd>↑↓</kbd> navigate · <kbd>Enter</kbd> jump · <kbd>Esc</kbd> close`;
    panel.appendChild(hint);

    overlay.appendChild(panel);
    document.body.appendChild(overlay);

    const setOpen = (open) => {
      document.body.setAttribute('data-global-search-open', open ? 'true' : 'false');
      if (open) {
        if (docs == null) docs = buildIndex();
        // Reset hint visibility
        hint.style.display = '';
        list.style.display = '';
        setTimeout(() => { input.focus(); input.select(); }, 30);
      } else {
        input.value = '';
        list.innerHTML = '';
        hint.style.display = '';
        keyNav = -1;
      }
    };

    const renderResults = () => {
      list.innerHTML = '';
      hint.style.display = lastResults.length > 0 || input.value === '' ? '' : 'none';
      if (lastResults.length === 0 && input.value !== '') {
        const empty = document.createElement('div');
        empty.className = 'page-global-search__empty';
        empty.textContent = 'No matches.';
        list.appendChild(empty);
        return;
      }
      lastResults.forEach((res, idx) => {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'page-global-search__result';
        btn.setAttribute('data-target', res.id);
        if (idx === keyNav) btn.setAttribute('data-keynav', 'true');
        const titleEl = document.createElement('div');
        titleEl.className = 'page-global-search__result-title';
        titleEl.innerHTML = highlight(res.title, input.value);
        btn.appendChild(titleEl);
        if (res.excerpt) {
          const excerpt = document.createElement('div');
          excerpt.className = 'page-global-search__result-excerpt';
          excerpt.innerHTML = highlight(res.excerpt, input.value);
          btn.appendChild(excerpt);
        }
        btn.addEventListener('click', () => jumpTo(res.id));
        li.appendChild(btn);
        list.appendChild(li);
      });
    };

    const jumpTo = (id) => {
      setOpen(false);
      const target = document.getElementById(id);
      if (!target) return;
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState(null, '', `#${id}`);
      target.classList.remove('page-global-search-flash');
      // Force reflow so the animation restarts.
      void target.offsetWidth;
      target.classList.add('page-global-search-flash');
      setTimeout(() => target.classList.remove('page-global-search-flash'), 1300);
    };

    input.addEventListener('input', () => {
      if (docs == null) docs = buildIndex();
      lastResults = search(docs, input.value);
      keyNav = lastResults.length > 0 ? 0 : -1;
      renderResults();
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (lastResults.length > 0) {
          keyNav = Math.min(lastResults.length - 1, keyNav + 1);
          renderResults();
          const items = list.querySelectorAll('.page-global-search__result');
          if (items[keyNav]) items[keyNav].scrollIntoView({ block: 'nearest' });
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (lastResults.length > 0) {
          keyNav = Math.max(0, keyNav - 1);
          renderResults();
        }
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (keyNav >= 0 && lastResults[keyNav]) jumpTo(lastResults[keyNav].id);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
      }
    });
    closeBtn.addEventListener('click', () => setOpen(false));
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) setOpen(false);
    });

    if (opts.showLauncher) {
      const launcher = document.createElement('button');
      launcher.type = 'button';
      launcher.className = 'page-global-search__launcher';
      launcher.setAttribute('aria-label', 'Open search');
      launcher.innerHTML = ICON_SEARCH;
      launcher.addEventListener('click', () => setOpen(true));
      document.body.appendChild(launcher);
    }

    const shortcuts = [opts.shortcut, opts.altShortcut].filter(Boolean);
    document.addEventListener('keydown', (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isEditableTarget(e.target)) return;
      if (shortcuts.indexOf(e.key) >= 0) {
        e.preventDefault();
        setOpen(true);
      }
    });

    if (typeof window !== 'undefined') {
      window.__pageSearch = {
        open: () => setOpen(true),
        close: () => setOpen(false),
        toggle: () => setOpen(document.body.getAttribute('data-global-search-open') !== 'true'),
      };
    }
  });
}
