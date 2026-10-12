// TOC pattern: sidebar table of contents with multi-level depth, in-TOC
// search, keyboard shortcut, arrow-key navigation, and per-section
// expand/collapse with a footer "Show levels" control.
//
// Visibility states (data-toc-state on body):
//   "expanded" — sidebar visible at full width; the page reserves space for it
//   "rail"     — sidebar visible as a thin rail with just the icon + reopen button
//   "hidden"   — sidebar not visible; floating launcher button replaces it
//
// Keyboard:
//   T   toggles between hidden and expanded (focuses search on open)
//   Esc closes (state -> hidden) when sidebar is visible
//   /   inside the search: ArrowUp/Down navigate, Enter jumps, Esc clears
//
// Public API on window.__pageToc: open, close, toggle, setState(state).

const STYLE_ID = 'page-toc-pattern-style';
const STORAGE_STATE = 'page-toc-state';
const STORAGE_EXPANSION = 'page-toc-expansion';   // 'collapsed' | 'expanded' | 'depth-2' | 'depth-3' | 'depth-4'
const CSS = `
.page-toc-pattern {
  position: fixed;
  top: 0;
  left: 0;
  width: 17rem;
  height: 100vh;
  background: rgba(255, 255, 255, 0.97);
  border-right: 1px solid var(--page-line, rgba(0, 0, 0, 0.1));
  display: flex;
  flex-direction: column;
  font-size: 0.9rem;
  z-index: 40;
  transition: transform 0.18s ease, width 0.18s ease;
  backdrop-filter: blur(6px);
}
body[data-toc-state="hidden"] .page-toc-pattern { transform: translateX(-100%); }
body[data-toc-state="rail"]   .page-toc-pattern { width: 3rem; }
@media (min-width: 881px) {
  body { padding-left: 17rem; transition: padding-left 0.18s ease; }
  body[data-toc-state="rail"]   { padding-left: 3rem; }
  body[data-toc-state="hidden"] { padding-left: 0; }
}
@media (max-width: 880px) {
  body { padding-left: 0; }
  .page-toc-pattern { width: min(20rem, 88vw); box-shadow: 8px 0 24px rgba(0, 0, 0, 0.08); }
}

.page-toc-pattern__head {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.85rem 0.75rem 0.6rem;
  border-bottom: 1px solid var(--page-line, rgba(0, 0, 0, 0.08));
}
body[data-toc-state="rail"] .page-toc-pattern__head { flex-direction: column; padding: 0.7rem 0.4rem; border-bottom: 0; }
.page-toc-pattern__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.6rem;
  height: 1.6rem;
  color: var(--page-accent, #1f5679);
}
.page-toc-pattern__icon > svg { width: 1.15rem; height: 1.15rem; }
.page-toc-pattern__heading {
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  color: #555;
  margin: 0;
  flex: 1;
}
.page-toc-pattern__head-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.6rem;
  height: 1.6rem;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  background: white;
  color: #555;
  font: inherit;
  font-size: 1rem;
  line-height: 1;
  padding: 0;
  border-radius: 4px;
  cursor: pointer;
  flex-shrink: 0;
}
.page-toc-pattern__head-btn:hover { color: var(--page-accent, #1f5679); border-color: var(--page-accent, #1f5679); }
.page-toc-pattern__rail-icon { transition: transform 0.18s ease; display: inline-block; }
body[data-toc-state="rail"] .page-toc-pattern__rail-icon { transform: rotate(180deg); }
body[data-toc-state="rail"] .page-toc-pattern__heading,
body[data-toc-state="rail"] .page-toc-pattern__close,
body[data-toc-state="rail"] .page-toc-pattern__search-wrap,
body[data-toc-state="rail"] .page-toc-pattern__list,
body[data-toc-state="rail"] .page-toc-pattern__footer { display: none; }

.page-toc-pattern__search-wrap {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--page-line, rgba(0, 0, 0, 0.08));
}
.page-toc-pattern__search {
  width: 100%;
  font: inherit;
  font-size: 0.88rem;
  padding: 0.4rem 0.55rem;
  border-radius: 4px;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.15));
  background: white;
  box-sizing: border-box;
}
.page-toc-pattern__search:focus { outline: 2px solid var(--page-accent, #1f5679); outline-offset: 1px; border-color: var(--page-accent, #1f5679); }

.page-toc-pattern__list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0.4rem;
  margin: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}
.page-toc-pattern__row {
  display: grid;
  grid-template-columns: 1.4rem 1fr;
  align-items: center;
}
.page-toc-pattern__chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  border: 0;
  background: transparent;
  font: inherit;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.5);
  border-radius: 3px;
  padding: 0;
}
.page-toc-pattern__chevron:hover { color: var(--page-accent, #1f5679); background: rgba(31, 86, 121, 0.08); }
.page-toc-pattern__chevron-icon { display: inline-block; transition: transform 0.15s ease; font-size: 0.85rem; line-height: 1; }
.page-toc-pattern__row[data-expanded="true"] .page-toc-pattern__chevron-icon { transform: rotate(90deg); }
.page-toc-pattern__chevron[data-leaf="true"] { visibility: hidden; cursor: default; }
.page-toc-pattern__item {
  display: block;
  padding: 0.32rem 0.55rem;
  border-radius: 4px;
  text-decoration: none;
  color: #444;
  border-left: 2px solid transparent;
  line-height: 1.35;
  cursor: pointer;
  font: inherit;
  text-align: left;
  width: 100%;
  background: transparent;
  border-top: 0; border-right: 0; border-bottom: 0;
}
.page-toc-pattern__item--depth-3 { font-size: 0.85rem; color: #666; padding-left: 1.2rem; }
.page-toc-pattern__item--depth-4 { font-size: 0.82rem; color: #777; padding-left: 2.2rem; }
.page-toc-pattern__item:hover { background: rgba(31, 86, 121, 0.08); color: var(--page-accent, #1f5679); }
.page-toc-pattern__item[data-current="true"] {
  color: var(--page-accent, #1f5679);
  background: rgba(31, 86, 121, 0.10);
  border-left-color: var(--page-accent, #1f5679);
  font-weight: 600;
}
.page-toc-pattern__item[data-keynav="true"] {
  outline: 2px solid var(--page-accent, #1f5679);
  outline-offset: -2px;
}
.page-toc-pattern__sublist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}
.page-toc-pattern__row[data-hidden="true"],
.page-toc-pattern__sublist[data-hidden="true"] { display: none; }

.page-toc-pattern__footer {
  border-top: 1px solid var(--page-line, rgba(0, 0, 0, 0.08));
  padding: 0.6rem 0.75rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.65);
}
.page-toc-pattern__top {
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: left;
  padding: 0.35rem 0.55rem;
  background: transparent;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  border-radius: 4px;
  cursor: pointer;
  color: #444;
}
.page-toc-pattern__top:hover { color: var(--page-accent, #1f5679); border-color: var(--page-accent, #1f5679); }
.page-toc-pattern__levels {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.page-toc-pattern__levels-label {
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
  color: #777;
  flex: 1;
}
.page-toc-pattern__level-toggle {
  display: inline-flex;
  gap: 0.2rem;
}
.page-toc-pattern__level-toggle button {
  width: 1.6rem;
  height: 1.6rem;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  background: white;
  border-radius: 4px;
  padding: 0;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.65);
}
.page-toc-pattern__level-toggle button:hover { background: rgba(31, 86, 121, 0.08); color: var(--page-accent, #1f5679); border-color: var(--page-accent, #1f5679); }
.page-toc-pattern__level-toggle button[aria-pressed="true"] { background: var(--page-accent, #1f5679); color: white; border-color: var(--page-accent, #1f5679); }
.page-toc-pattern__hint { font-size: 0.72rem; color: rgba(0, 0, 0, 0.5); line-height: 1.45; }
.page-toc-pattern__hint kbd {
  font: inherit;
  font-size: 0.7rem;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
}

.page-toc-pattern__close { display: inline-flex; }
body[data-toc-state="rail"] .page-toc-pattern__close { display: none; }

.page-toc-pattern__launcher {
  position: fixed;
  top: 1rem;
  left: 1rem;
  z-index: 35;
  width: 2.6rem;
  height: 2.6rem;
  display: none;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--page-line, rgba(0, 0, 0, 0.12));
  background: white;
  color: var(--page-ink, #1c1c1f);
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.page-toc-pattern__launcher > svg { width: 1.2rem; height: 1.2rem; }
body[data-toc-state="hidden"] .page-toc-pattern__launcher { display: inline-flex; }
@media (max-width: 880px) {
  body[data-toc-state="rail"] .page-toc-pattern__launcher { display: inline-flex; }
}
`;

const ICON_BOOK_OPEN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>';

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

function slugifyHeading(text, fallback) {
  return (text || fallback || '').toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || fallback;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}

function cssEscape(s) {
  // Use the browser's CSS.escape if available; fall back to a minimal
  // version that escapes characters problematic in attribute selectors.
  if (typeof window !== 'undefined' && window.CSS && typeof window.CSS.escape === 'function') {
    return window.CSS.escape(s);
  }
  return String(s).replace(/[^\w-]/g, (c) => '\\' + c);
}

export function init(options) {
  if (typeof document === 'undefined') return;
  const opts = Object.assign({
    enabled: true,
    depth: 4,                    // include all levels by default; UI controls visibility
    search: true,
    shortcut: 't',
    icon: ICON_BOOK_OPEN,
    // Initial expansion mode: 'collapsed' (only h2), 'expanded' (all),
    // 'depth-3' (h2 + h3), 'depth-4' (h2 + h3 + h4).
    initialExpansion: 'collapsed',
  }, options || {});
  if (!opts.enabled) return;

  const ready = (fn) => {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  };

  ready(() => {
    ensureStyle(document);

    // Build a tree of h2 -> [h3 -> [h4]] from the rendered DOM. h3/h4 nodes
    // get auto-generated ids if they are missing one.
    const sections = Array.from(document.querySelectorAll('section[id]'));
    const tree = [];
    const maxDepth = Math.min(4, Math.max(2, opts.depth));
    for (const section of sections) {
      const h2 = section.querySelector('h2');
      if (!h2) continue;
      const h2Node = { id: section.id, label: h2.textContent.trim(), depth: 2, target: section, children: [] };
      if (maxDepth >= 3) {
        const subTags = maxDepth === 3 ? 'h3' : 'h3,h4';
        const subs = Array.from(section.querySelectorAll(subTags));
        let lastH3 = null;
        for (const h of subs) {
          if (!h.id) h.id = `${section.id}-${slugifyHeading(h.textContent, 'sub')}`;
          const depth = parseInt(h.tagName.substring(1), 10);
          const node = { id: h.id, label: h.textContent.trim(), depth, target: h, children: [] };
          if (depth === 3) { h2Node.children.push(node); lastH3 = node; }
          else if (depth === 4) {
            if (lastH3) lastH3.children.push(node);
            else h2Node.children.push(node);
          }
        }
      }
      tree.push(h2Node);
    }
    if (tree.length === 0) return;

    // Build sidebar UI.
    const sidebar = document.createElement('aside');
    sidebar.className = 'page-toc-pattern';
    sidebar.setAttribute('aria-label', 'Section navigation');

    // Header
    const head = document.createElement('div');
    head.className = 'page-toc-pattern__head';
    const iconWrap = document.createElement('span');
    iconWrap.className = 'page-toc-pattern__icon';
    iconWrap.innerHTML = opts.icon || ICON_BOOK_OPEN;
    head.appendChild(iconWrap);
    const heading = document.createElement('p');
    heading.className = 'page-toc-pattern__heading';
    heading.textContent = 'Contents';
    head.appendChild(heading);
    const railBtn = document.createElement('button');
    railBtn.type = 'button';
    railBtn.className = 'page-toc-pattern__head-btn page-toc-pattern__rail';
    railBtn.setAttribute('aria-label', 'Collapse to rail');
    railBtn.innerHTML = '<span class="page-toc-pattern__rail-icon" aria-hidden="true">‹</span>';
    head.appendChild(railBtn);
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'page-toc-pattern__head-btn page-toc-pattern__close';
    closeBtn.setAttribute('aria-label', 'Hide contents');
    closeBtn.innerHTML = '×';
    head.appendChild(closeBtn);
    sidebar.appendChild(head);

    // Search
    let searchInput = null;
    if (opts.search !== false) {
      const sw = document.createElement('div');
      sw.className = 'page-toc-pattern__search-wrap';
      searchInput = document.createElement('input');
      searchInput.type = 'search';
      searchInput.className = 'page-toc-pattern__search';
      searchInput.placeholder = 'Filter sections…';
      searchInput.setAttribute('aria-label', 'Filter sections');
      sw.appendChild(searchInput);
      sidebar.appendChild(sw);
    }

    // List
    const list = document.createElement('ul');
    list.className = 'page-toc-pattern__list';

    // Track all renderable nodes for keyboard nav + filter.
    const allItems = [];      // { row, btn, sublist?, node, parents: [] }
    const expansionState = new Map(); // node.id -> boolean (for h2 only)

    function renderNode(node, parentList, parents) {
      const li = document.createElement('li');

      const row = document.createElement('div');
      row.className = 'page-toc-pattern__row';
      row.setAttribute('data-id', node.id);
      const hasChildren = Array.isArray(node.children) && node.children.length > 0;

      const chevron = document.createElement('button');
      chevron.type = 'button';
      chevron.className = 'page-toc-pattern__chevron';
      chevron.setAttribute('aria-label', hasChildren ? 'Toggle subsections' : '');
      chevron.innerHTML = '<span class="page-toc-pattern__chevron-icon" aria-hidden="true">›</span>';
      if (!hasChildren) chevron.setAttribute('data-leaf', 'true');
      row.appendChild(chevron);

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `page-toc-pattern__item page-toc-pattern__item--depth-${node.depth}`;
      btn.textContent = node.label;
      btn.setAttribute('data-target', node.id);
      btn.setAttribute('data-label', node.label.toLowerCase());
      row.appendChild(btn);

      li.appendChild(row);

      // Push the parent into allItems BEFORE recursing into its children so
      // the array stays in pre-order DFS — i.e. the visual top-to-bottom
      // order. Otherwise ArrowDown traversal sees children before the parent
      // and the parent looks skipped from the previous sibling's perspective.
      const entry = { row, btn, sublist: null, node, parents, chevron };
      allItems.push(entry);

      let sublist = null;
      if (hasChildren) {
        sublist = document.createElement('ul');
        sublist.className = 'page-toc-pattern__sublist';
        for (const child of node.children) {
          renderNode(child, sublist, parents.concat([node]));
        }
        li.appendChild(sublist);
        entry.sublist = sublist;
      }
      parentList.appendChild(li);

      chevron.addEventListener('click', (e) => {
        e.stopPropagation();
        if (!hasChildren) return;
        const isExpanded = row.getAttribute('data-expanded') === 'true';
        setExpanded(node.id, !isExpanded);
      });
    }

    for (const node of tree) renderNode(node, list, []);
    sidebar.appendChild(list);

    // Footer with Top button + Show levels toggle
    const footer = document.createElement('div');
    footer.className = 'page-toc-pattern__footer';
    const topBtn = document.createElement('button');
    topBtn.type = 'button';
    topBtn.className = 'page-toc-pattern__top';
    topBtn.textContent = '↑ Back to top';
    footer.appendChild(topBtn);

    // "Show levels" toggle: numbered buttons (1, 2, 3, …) corresponding to
    // how many heading levels deep to expand. Only buttons for levels that
    // actually exist in the tree are shown. If only one level exists, the
    // toggle is omitted entirely — there's nothing to expand or collapse.
    let detectedMaxHLevel = 2;
    function walkDepth(node) {
      if (node.depth > detectedMaxHLevel) detectedMaxHLevel = node.depth;
      if (node.children) for (const c of node.children) walkDepth(c);
    }
    for (const n of tree) walkDepth(n);
    // Convert h-level (2..4) to user-facing "levels deep" (1..3).
    // h2 = level 1, h3 = level 2, h4 = level 3.
    const maxLevels = detectedMaxHLevel - 1;
    const levelButtons = {};
    let levelsWrap = null;
    if (maxLevels >= 2) {
      levelsWrap = document.createElement('div');
      levelsWrap.className = 'page-toc-pattern__levels';
      const levelsLabel = document.createElement('span');
      levelsLabel.className = 'page-toc-pattern__levels-label';
      levelsLabel.textContent = 'Show levels';
      levelsWrap.appendChild(levelsLabel);
      const levelsToggle = document.createElement('div');
      levelsToggle.className = 'page-toc-pattern__level-toggle';
      for (let n = 1; n <= maxLevels; n++) {
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = String(n);
        b.title = `Show ${n} level${n === 1 ? '' : 's'} deep`;
        b.setAttribute('aria-pressed', 'false');
        b.dataset.level = String(n);
        b.addEventListener('click', () => setExpansionLevel(n));
        levelButtons[n] = b;
        levelsToggle.appendChild(b);
      }
      levelsWrap.appendChild(levelsToggle);
      footer.appendChild(levelsWrap);
    }

    if (opts.shortcut) {
      const hint = document.createElement('div');
      hint.className = 'page-toc-pattern__hint';
      hint.innerHTML = `<kbd>${escapeHtml(opts.shortcut.toUpperCase())}</kbd> open · <kbd>↑↓</kbd> nav · <kbd>← →</kbd> collapse / expand · <kbd>Enter</kbd> jump · <kbd>Esc</kbd> close`;
      footer.appendChild(hint);
    }
    sidebar.appendChild(footer);

    document.body.appendChild(sidebar);

    // Floating launcher
    const launcher = document.createElement('button');
    launcher.type = 'button';
    launcher.className = 'page-toc-pattern__launcher';
    launcher.setAttribute('aria-label', 'Open contents');
    launcher.innerHTML = opts.icon || ICON_BOOK_OPEN;
    document.body.appendChild(launcher);

    // State management ----------------------------------------------------
    function setState(state) {
      if (!['expanded', 'rail', 'hidden'].includes(state)) state = 'expanded';
      document.body.setAttribute('data-toc-state', state);
      try { localStorage.setItem(STORAGE_STATE, state); } catch (_) {}
      if (state === 'expanded' && searchInput) {
        setTimeout(() => { searchInput.focus(); searchInput.select(); }, 30);
      }
      if (state === 'hidden') {
        // Move focus out of the sidebar so subsequent shortcuts work.
        const active = document.activeElement;
        if (active && sidebar.contains(active) && typeof active.blur === 'function') active.blur();
      }
    }
    function currentState() {
      return document.body.getAttribute('data-toc-state') || 'expanded';
    }

    // Initial state from storage; default to "expanded"
    let savedState = 'expanded';
    try { savedState = localStorage.getItem(STORAGE_STATE) || 'expanded'; } catch (_) {}
    setState(savedState);

    // Per-node expansion ---------------------------------------------------
    function setExpanded(nodeId, expanded) {
      expansionState.set(nodeId, expanded);
      const row = sidebar.querySelector(`.page-toc-pattern__row[data-id="${cssEscape(nodeId)}"]`);
      if (row) {
        row.setAttribute('data-expanded', expanded ? 'true' : 'false');
        const li = row.parentElement;
        const sublist = li ? li.querySelector(':scope > .page-toc-pattern__sublist') : null;
        if (sublist) sublist.setAttribute('data-hidden', expanded ? 'false' : 'true');
      }
    }
    // setExpansionLevel(n): expand all chevrons up to the given level.
    //   n = 1 -> only h2 visible (all chevrons closed)
    //   n = 2 -> h2 + h3 visible
    //   n = 3 -> h2 + h3 + h4 visible
    function setExpansionLevel(n) {
      const num = Math.max(1, Math.min(maxLevels || 1, parseInt(n, 10) || 1));
      try { localStorage.setItem(STORAGE_EXPANSION, String(num)); } catch (_) {}
      Object.keys(levelButtons).forEach((k) => {
        levelButtons[k].setAttribute('aria-pressed', String(num) === k ? 'true' : 'false');
      });
      // Convert level (1..3) to h-level threshold (2..4): items whose parent
      // is at h-level <= (num + 1) get expanded.
      for (const item of allItems) {
        const node = item.node;
        // h2 children are h3+ : expand h2 if num >= 2
        // h3 children are h4  : expand h3 if num >= 3
        const childThresholdHLevel = node.depth + 1;
        const userLevelOfChildren = childThresholdHLevel - 1; // h3->2, h4->3
        const expand = num >= userLevelOfChildren;
        setExpanded(node.id, expand);
      }
    }

    // Initialise expansion level from storage or option.
    let savedLevel = (typeof opts.initialExpansion === 'number') ? opts.initialExpansion : 1;
    try {
      const stored = localStorage.getItem(STORAGE_EXPANSION);
      if (stored) {
        const parsed = parseInt(stored, 10);
        if (!Number.isNaN(parsed)) savedLevel = parsed;
      }
    } catch (_) {}
    if (maxLevels >= 2) setExpansionLevel(savedLevel);

    // Filter & keyboard nav -----------------------------------------------
    let keyNavIndex = -1;
    function filter(q) {
      const needle = q.toLowerCase().trim();
      for (const item of allItems) {
        const label = item.btn.getAttribute('data-label') || '';
        const match = !needle || label.indexOf(needle) >= 0;
        item.row.setAttribute('data-hidden', match ? 'false' : 'true');
        // When filtering, force-expand parents of any visible match.
        if (match && needle && item.parents.length > 0) {
          for (const p of item.parents) setExpanded(p.id, true);
        }
      }
      keyNavIndex = -1;
      const visible = visibleItems();
      if (visible.length > 0) setKeyNav(0);
    }
    function visibleItems() {
      return allItems.filter((it) => {
        if (it.row.getAttribute('data-hidden') === 'true') return false;
        for (const p of it.parents) {
          const parentRow = sidebar.querySelector(`.page-toc-pattern__row[data-id="${cssEscape(p.id)}"]`);
          if (parentRow && parentRow.getAttribute('data-expanded') !== 'true') return false;
        }
        return true;
      });
    }
    function setKeyNav(idx) {
      allItems.forEach((it) => it.btn.removeAttribute('data-keynav'));
      const visible = visibleItems();
      keyNavIndex = idx;
      if (idx >= 0 && idx < visible.length) {
        visible[idx].btn.setAttribute('data-keynav', 'true');
        visible[idx].btn.scrollIntoView({ block: 'nearest' });
      }
    }

    // Navigation actions --------------------------------------------------
    function jumpTo(id) {
      const target = document.getElementById(id);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        history.replaceState(null, '', `#${id}`);
      }
      // On narrow viewports, hide after navigation; on wide, leave visible.
      if (window.matchMedia && window.matchMedia('(max-width: 880px)').matches) setState('hidden');
    }
    function jumpToTop() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }

    // Wire interactions ---------------------------------------------------
    list.addEventListener('click', (e) => {
      const item = e.target && e.target.closest && e.target.closest('[data-target]');
      if (item) jumpTo(item.getAttribute('data-target'));
    });
    railBtn.addEventListener('click', () => {
      setState(currentState() === 'rail' ? 'expanded' : 'rail');
    });
    closeBtn.addEventListener('click', () => setState('hidden'));
    launcher.addEventListener('click', () => setState('expanded'));
    topBtn.addEventListener('click', () => jumpToTop());

    if (searchInput) {
      searchInput.addEventListener('input', () => filter(searchInput.value));
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          const visible = visibleItems();
          setKeyNav(Math.min(visible.length - 1, keyNavIndex + 1));
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          const visible = visibleItems();
          setKeyNav(Math.max(0, keyNavIndex - 1));
        } else if (e.key === 'ArrowRight') {
          // Expand the focused node's children. If already expanded and the
          // node has children, jump down into the first child instead — the
          // conventional tree-navigation behaviour.
          const visible = visibleItems();
          const target = keyNavIndex >= 0 ? visible[keyNavIndex] : null;
          if (!target) return;
          const node = target.node;
          const hasChildren = Array.isArray(node.children) && node.children.length > 0;
          if (!hasChildren) return;
          e.preventDefault();
          const isExpanded = target.row.getAttribute('data-expanded') === 'true';
          if (!isExpanded) {
            setExpanded(node.id, true);
          } else {
            const after = visibleItems();
            const myIdx = after.indexOf(target);
            if (myIdx >= 0 && myIdx < after.length - 1) setKeyNav(myIdx + 1);
          }
        } else if (e.key === 'ArrowLeft') {
          // Collapse the focused node if it's an expanded parent; otherwise
          // jump up to its parent.
          const visible = visibleItems();
          const target = keyNavIndex >= 0 ? visible[keyNavIndex] : null;
          if (!target) return;
          e.preventDefault();
          const node = target.node;
          const hasChildren = Array.isArray(node.children) && node.children.length > 0;
          const isExpanded = hasChildren && target.row.getAttribute('data-expanded') === 'true';
          if (isExpanded) {
            setExpanded(node.id, false);
          } else if (target.parents.length > 0) {
            const parentNode = target.parents[target.parents.length - 1];
            const after = visibleItems();
            const parentIdx = after.findIndex((it) => it.node.id === parentNode.id);
            if (parentIdx >= 0) setKeyNav(parentIdx);
          }
        } else if (e.key === 'Enter') {
          e.preventDefault();
          const visible = visibleItems();
          const target = keyNavIndex >= 0 ? visible[keyNavIndex] : visible[0];
          if (target) jumpTo(target.btn.getAttribute('data-target'));
        } else if (e.key === 'Home') {
          e.preventDefault();
          setKeyNav(0);
        } else if (e.key === 'End') {
          e.preventDefault();
          const visible = visibleItems();
          setKeyNav(visible.length - 1);
        } else if (e.key === 'Escape') {
          e.preventDefault();
          if (searchInput.value) {
            searchInput.value = '';
            filter('');
          } else {
            // Critical: blur the search input before hiding so subsequent
            // T presses are not swallowed by the isEditableTarget check
            // (the input is still focused even when its container has been
            // translated off-screen).
            searchInput.blur();
            setState('hidden');
          }
        }
      });
    }

    // Global keyboard shortcuts ------------------------------------------
    if (opts.shortcut) {
      const sc = String(opts.shortcut).toLowerCase();
      document.addEventListener('keydown', (e) => {
        if (isEditableTarget(e.target)) return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        if (e.key && e.key.toLowerCase() === sc) {
          e.preventDefault();
          // Toggle: hidden -> expanded, anything else -> hidden
          if (currentState() === 'hidden') setState('expanded');
          else setState('hidden');
        }
      });
    }
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && currentState() !== 'hidden' && !isEditableTarget(e.target)) {
        setState('hidden');
      }
    });

    // Section highlight on scroll
    const targets = allItems.map((it) => document.getElementById(it.node.id)).filter(Boolean);
    if ('IntersectionObserver' in window && targets.length > 0) {
      const visible = new Set();
      const obs = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.add(entry.target.id);
          else visible.delete(entry.target.id);
        }
        let activeId = null;
        for (const t of targets) {
          if (visible.has(t.id)) { activeId = t.id; break; }
        }
        allItems.forEach((it) => {
          if (it.btn.getAttribute('data-target') === activeId) it.btn.setAttribute('data-current', 'true');
          else it.btn.removeAttribute('data-current');
        });
      }, { rootMargin: '-15% 0px -65% 0px', threshold: 0 });
      targets.forEach((t) => obs.observe(t));
    }

    if (typeof window !== 'undefined') {
      window.__pageToc = {
        open: () => setState('expanded'),
        close: () => setState('hidden'),
        toggle: () => setState(currentState() === 'hidden' ? 'expanded' : 'hidden'),
        setState,
        setExpansionLevel,
      };
    }
  });
}
