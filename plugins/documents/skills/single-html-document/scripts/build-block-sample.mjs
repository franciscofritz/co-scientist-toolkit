#!/usr/bin/env node
// Build a single-file HTML sample that demonstrates the block layer.
//
// Usage:
//   node scripts/build-block-sample.mjs <manifest> [output-folder]
//
// With no output folder the sample is written into this skill's assets/design-samples/,
// which a plugin update replaces; pass a folder of your own when building a document.
//
// The script reads scripts/blocks/_bootstrap.js and every renderer module
// in scripts/blocks/, transforms them into a self-contained <script> block,
// and emits a single-file HTML deliverable that mounts each block instance
// from inline JSON payloads.
//
// Manifests live alongside this script. They describe the deliverable's
// title, intro, sections, and the block instances to render in each section.
// Fields named bodyHtml/answerHtml/etc. are pre-rendered HTML — the
// real compiler is responsible for converting authored Markdown to HTML;
// for the samples we hand-render to keep the build dependency-free.

import { readFile, writeFile, readdir, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { ICONS, hasIcon } from './icons.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BLOCKS_DIR = resolve(__dirname, 'blocks');
const PATTERNS_DIR = resolve(__dirname, 'patterns');
const REPO_ROOT = resolve(__dirname, '..');

async function loadBootstrap() {
  const text = await readFile(join(BLOCKS_DIR, '_bootstrap.js'), 'utf8');
  // Drop ES module exports; keep behaviour. Expose register on window so
  // inlined renderer modules can find it without ES module semantics.
  let transformed = text
    .replace(/^export\s+function\s+/gm, 'function ')
    .replace(/^export\s+/gm, '');
  transformed += '\nif (typeof window !== "undefined") { window.__blocksRegister = register; window.__blocksBootstrap = bootstrap; }\n';
  return transformed;
}

async function loadRenderer(name) {
  const filePath = join(BLOCKS_DIR, `${name}.js`);
  let text = await readFile(filePath, 'utf8');
  // Strip the import line; register comes from window.__blocksRegister via the wrapper.
  text = text.replace(/^\s*import\s+\{[^}]*\}\s+from\s+['"]\.\/_bootstrap\.js['"];?\s*$/m, '');
  // Drop register('name', mount) calls if present — we'll add our own at the end.
  text = text.replace(/^\s*register\(['"][^'"]+['"]\s*,\s*mount\);\s*$/gm, '');
  // Drop export keywords; the IIFE wrapper handles scope.
  text = text.replace(/^export\s+function\s+/gm, 'function ');
  text = text.replace(/^export\s+const\s+/gm, 'const ');
  text = text.replace(/^export\s+/gm, '');
  return `// === block: ${name} ===
(function () {
  const register = window.__blocksRegister;
${text}
  register(${JSON.stringify(name)}, mount);
})();`;
}

async function listRendererNames() {
  const entries = await readdir(BLOCKS_DIR);
  return entries
    .filter((name) => name.endsWith('.js') && !name.startsWith('_'))
    .map((name) => name.slice(0, -3))
    .sort();
}

async function loadPattern(name) {
  const filePath = join(PATTERNS_DIR, `${name}.js`);
  let text = await readFile(filePath, 'utf8');
  // Strip ES module exports; the wrapper keeps everything in IIFE scope.
  text = text.replace(/^\s*export\s+function\s+/gm, 'function ');
  text = text.replace(/^\s*export\s+const\s+/gm, 'const ');
  text = text.replace(/^\s*export\s+/gm, '');
  return text;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}

// Resolve icon references in block data. Walks every value in `data` looking
// for strings on `icon`, `iconName`, or any *-icon-style key, and writes the
// matching SVG markup back as <key>Html. Returns the set of icon names found
// so the build can also expose them at runtime.
function resolveIconsInData(data, used) {
  if (!data || typeof data !== 'object') return data;
  if (Array.isArray(data)) {
    for (let i = 0; i < data.length; i++) data[i] = resolveIconsInData(data[i], used);
    return data;
  }
  const out = data;
  for (const key of Object.keys(out)) {
    const value = out[key];
    if ((key === 'icon' || key.endsWith('Icon')) && typeof value === 'string') {
      const name = value.trim();
      if (hasIcon(name)) {
        out[`${key}Html`] = ICONS[name];
        used.add(name);
      } else if (name) {
        console.warn(`[build] icon not found: "${name}". Add it to scripts/icons.mjs.`);
      }
    } else if (value && typeof value === 'object') {
      resolveIconsInData(value, used);
    }
  }
  return out;
}

function resolveIconsInManifest(manifest) {
  const used = new Set();
  for (const section of manifest.sections || []) {
    for (const block of section.blocks || []) {
      block.data = resolveIconsInData(block.data, used);
    }
  }
  return used;
}

// Emit a small inline runtime so renderers (and authored html fields) can
// look icons up by name at runtime via window.__blocksIcon('shield-alert').
function buildIconRuntime(usedIconNames) {
  if (usedIconNames.size === 0) return '';
  const dict = {};
  for (const name of usedIconNames) dict[name] = ICONS[name];
  const json = JSON.stringify(dict);
  return `(function () {
  if (typeof window === 'undefined') return;
  const ICONS = ${json};
  window.__blocksIcon = function (name) { return ICONS[name] || ''; };
  window.__blocksHasIcon = function (name) { return Object.prototype.hasOwnProperty.call(ICONS, name); };
})();`;
}

function renderBlockInstance(instance, index) {
  const id = instance.id || `block-${index}`;
  const payload = JSON.stringify(instance.data ?? {});
  return `<div class="sample-block" data-block-type="${escapeHtml(instance.type)}" id="${escapeHtml(id)}">
  <script type="application/json" data-block-payload>${payload.replace(/<\//g, '<\\/')}</script>
</div>`;
}

function renderSection(section, sectionIndex) {
  const lines = [];
  if (section.id) lines.push(`<section id="${escapeHtml(section.id)}" class="sample-section">`);
  else lines.push(`<section class="sample-section">`);
  if (section.heading) lines.push(`<h2>${escapeHtml(section.heading)}</h2>`);
  if (section.kicker) lines.push(`<p class="sample-section__kicker">${escapeHtml(section.kicker)}</p>`);
  if (section.lead) lines.push(`<p class="sample-section__lead">${section.lead}</p>`);
  const sectionId = section.id || `s-${sectionIndex}`;
  for (let i = 0; i < (section.blocks || []).length; i++) {
    const block = section.blocks[i];
    // Make sure each block instance has a stable id; renderers use it to
    // anchor their own headings (data.title -> h3 with id `<blockId>-title`)
    // so the TOC pattern picks the title up as a subheading.
    if (!block.id) block.id = `${sectionId}-${block.type || 'block'}-${i}`;
    if (block.label) {
      // Block label stays a styled caption, not a heading. The block's own
      // data.title is what the renderer emits as the h3 used for navigation.
      lines.push(`<p class="sample-block__label">${escapeHtml(block.label)}</p>`);
    }
    lines.push(renderBlockInstance(block, `${sectionIndex}-${i}`));
  }
  if (section.afterHtml) lines.push(section.afterHtml);
  lines.push(`</section>`);
  return lines.join('\n');
}

// TOC and search now live as page patterns under scripts/patterns/.
// Manifests opt in via the `patterns` field. See references/patterns/.

const PAGE_CSS = `:root {
  color-scheme: light;
  --page-bg: #f7f5f0;
  --page-ink: #1c1c1f;
  --page-muted: #4a4a4a;
  --page-line: rgba(0, 0, 0, 0.1);
  --page-accent: #1f5679;
}
* { box-sizing: border-box; min-width: 0; }
html, body {
  background: var(--page-bg);
  color: var(--page-ink);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  line-height: 1.6;
  margin: 0;
  /* Page-contract rule: never scroll horizontally at the page level. */
  overflow-x: clip;
  overflow-wrap: anywhere;
}
html { scroll-behavior: smooth; }
body { width: 100%; max-width: 100%; }
.page-back-to-top {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  z-index: 30;
  width: 2.4rem;
  height: 2.4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--page-line);
  background: white;
  color: var(--page-ink);
  font-size: 1.1rem;
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  opacity: 0;
  transform: translateY(0.5rem);
  transition: opacity 0.18s ease, transform 0.18s ease;
  pointer-events: none;
}
.page-back-to-top[data-visible="true"] {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}
.sample-shell { max-width: 56rem; margin: 0 auto; padding: 3rem 1.5rem 5rem; min-width: 0; width: 100%; box-sizing: border-box; }
.sample-masthead { margin-bottom: 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--page-line); min-width: 0; }
.sample-masthead .eyebrow { font-size: 0.78rem; letter-spacing: 0.14em; text-transform: uppercase; color: #555; font-weight: 600; }
.sample-masthead h1 { font-size: 2rem; line-height: 1.15; margin: 0.5rem 0 0.4rem; font-weight: 700; overflow-wrap: anywhere; }
.sample-masthead p { margin: 0.4rem 0 0; max-width: 50rem; color: var(--page-muted); }
.sample-section { margin: 0 0 3rem; min-width: 0; scroll-margin-top: 1.5rem; }
.sample-section h2 { font-size: 1.4rem; margin: 0 0 0.4rem; font-weight: 700; overflow-wrap: anywhere; }
.sample-section__kicker { margin: 0 0 0.4rem; font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600; color: var(--page-accent); }
.sample-section__lead { margin: 0 0 1.25rem; color: var(--page-muted); max-width: 48rem; line-height: 1.6; }
.sample-block__label { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.78rem; font-weight: 500; letter-spacing: 0.04em; color: #555; margin: 1.5rem 0 0.4rem; overflow-wrap: anywhere; scroll-margin-top: 1.5rem; }
.sample-block__label::before { content: "block: "; color: #888; }
.sample-block { margin: 0; min-width: 0; }
footer.sample-footer { margin-top: 4rem; padding-top: 1.5rem; border-top: 1px solid var(--page-line); font-size: 0.85rem; color: #555; }

@media print {
  .sample-shell { max-width: none; padding: 0; }
  .sample-block__label { display: none; }
  .page-toc-pattern, .page-global-search__launcher, .page-back-to-top { display: none !important; }
  body { padding-left: 0 !important; }
}
`;

// Floating back-to-top button; the patterns layer handles TOC and search.
const PAGE_BACK_TO_TOP_SCRIPT = `
(function () {
  if (typeof document === 'undefined') return;
  const ready = (fn) => {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  };
  ready(() => {
    const backToTop = document.createElement('button');
    backToTop.type = 'button';
    backToTop.className = 'page-back-to-top';
    backToTop.setAttribute('aria-label', 'Back to top');
    backToTop.innerHTML = '↑';
    backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    document.body.appendChild(backToTop);
    const showThreshold = 320;
    const updateBackToTop = () => {
      const visible = window.scrollY > showThreshold;
      backToTop.setAttribute('data-visible', visible ? 'true' : 'false');
    };
    window.addEventListener('scroll', updateBackToTop, { passive: true });
    updateBackToTop();
  });
})();
`;

async function buildPatternsScript(manifest) {
  const patternsConfig = manifest.patterns || {};
  const enabledNames = Object.keys(patternsConfig).filter((name) => {
    const cfg = patternsConfig[name];
    return cfg && cfg.enabled !== false;
  });
  if (enabledNames.length === 0) return '';
  const blocks = [];
  for (const name of enabledNames) {
    const text = await loadPattern(name);
    const cfg = JSON.stringify(patternsConfig[name]);
    blocks.push(`// === pattern: ${name} ===
(function () {
${text}
  if (typeof init === 'function') init(${cfg});
})();`);
  }
  return blocks.join('\n\n');
}

async function build(manifest, outPath) {
  const bootstrap = await loadBootstrap();
  const names = await listRendererNames();
  const renderers = await Promise.all(names.map(loadRenderer));
  const usedIcons = resolveIconsInManifest(manifest);
  const iconRuntime = buildIconRuntime(usedIcons);
  const patternsScript = await buildPatternsScript(manifest);
  const inlineScript = `${bootstrap}\n\n${renderers.join('\n\n')}\n\n${iconRuntime}\n\n${patternsScript}`;

  const sectionsHtml = (manifest.sections || []).map(renderSection).join('\n');
  const showLabels = manifest.showBlockLabels !== false;
  // Escape any literal `</` inside the inlined JS so a string or comment
  // containing `</script>` doesn't close the outer <script> tag early.
  const safeInlineScript = (inlineScript + '\n\n' + PAGE_BACK_TO_TOP_SCRIPT).replace(/<\//g, '<\\/');

  const html = `<!doctype html>
<html lang="${escapeHtml(manifest.lang || 'en')}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(manifest.title || 'Block Sample')}</title>
  <style>${PAGE_CSS}${showLabels ? '' : '\n.sample-block__label { display: none; }'}</style>
</head>
<body>
  <main class="sample-shell">
    <header class="sample-masthead">
      <p class="eyebrow">${escapeHtml(manifest.eyebrow || 'Composed blocks sample')}</p>
      <h1>${escapeHtml(manifest.title || 'Block Sample')}</h1>
      ${manifest.subtitle ? `<p>${manifest.subtitle}</p>` : ''}
    </header>
${sectionsHtml}
    <footer class="sample-footer">${manifest.footer || 'Generated by single-html-document &middot; build-block-sample.mjs'}</footer>
  </main>
  <script>
${safeInlineScript}
  </script>
</body>
</html>
`;
  await writeFile(outPath, html, 'utf8');
  return { outPath, sizeBytes: Buffer.byteLength(html, 'utf8') };
}

async function main() {
  const arg = process.argv[2];
  if (!arg) {
    console.error('Usage: node scripts/build-block-sample.mjs <manifest.mjs> [output-folder]');
    process.exit(1);
  }
  const manifestPath = resolve(process.cwd(), arg);
  const mod = await import(manifestPath);
  const manifest = mod.default;
  if (!manifest) {
    console.error(`No default export from ${manifestPath}`);
    process.exit(1);
  }
  const outDir = process.argv[3] ? resolve(process.cwd(), process.argv[3]) : resolve(REPO_ROOT, 'assets', 'design-samples');
  await mkdir(outDir, { recursive: true });
  const outPath = join(outDir, manifest.outputName || 'block-sample.single.html');
  const result = await build(manifest, outPath);
  console.log(`✓ wrote ${result.outPath} (${(result.sizeBytes / 1024).toFixed(1)} KB)`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch((err) => { console.error(err); process.exit(1); });
}

export { build, loadBootstrap, loadRenderer, listRendererNames };
