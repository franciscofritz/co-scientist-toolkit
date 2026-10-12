#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const TEXT_EXTENSIONS = new Set([
  '.md',
  '.markdown',
  '.mdx',
  '.txt',
  '.json',
  '.jsonl',
  '.yaml',
  '.yml',
  '.toml',
  '.xml',
]);

const RUNTIME_EXTENSIONS = new Set(['.js', '.mjs', '.cjs', '.css', '.map']);

const ASSET_EXTENSIONS = new Set([
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
  '.avif',
  '.svg',
  '.ico',
  '.woff',
  '.woff2',
  '.ttf',
  '.otf',
  '.mp3',
  '.mp4',
  '.webm',
  '.wav',
  '.ogg',
  '.glb',
  '.gltf',
]);

const ARTIFACT_EXTENSIONS = new Set([
  '.pdf',
  '.csv',
  '.tsv',
  '.xlsx',
  '.xls',
  '.ods',
  '.pptx',
  '.ppt',
  '.key',
  '.docx',
  '.doc',
  '.zip',
  '.ics',
]);

const LARGE_DATA_URL_BYTES = 1024 * 1024;

function usage(exitCode = 1) {
  console.error(`Usage:
  node audit-single-html.mjs <file.html> [--strict] [--allow-local-artifacts] [--allow-remote-resources] [--max-mb N]

Options:
  --strict                  Exit non-zero when structural blockers are found.
  --allow-local-artifacts   Do not fail strict mode for local PDF/CSV/XLSX/PPTX/ZIP-style artifact links.
  --allow-remote-resources  Do not fail strict mode for remote resource loads such as iframes or images.
  --max-mb N                Override the 100 MB strict size ceiling.
`);
  process.exit(exitCode);
}

function formatMb(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function uniqueObjects(values) {
  const seen = new Set();
  const result = [];
  for (const value of values) {
    const key = `${value.tag}|${value.attr}|${value.value}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(value);
  }
  return result.sort((a, b) => a.value.localeCompare(b.value) || a.tag.localeCompare(b.tag));
}

function cleanReference(value) {
  return value.trim().replace(/^['"]|['"]$/g, '');
}

function isSafeInline(value) {
  return (
    value === '' ||
    value.startsWith('#') ||
    value.startsWith('mailto:') ||
    value.startsWith('tel:') ||
    value.startsWith('javascript:') ||
    value.startsWith('about:')
  );
}

function isRemote(value) {
  return value.startsWith('http://') || value.startsWith('https://') || value.startsWith('//');
}

function extensionFor(value) {
  try {
    const withoutQuery = value.split(/[?#]/, 1)[0];
    return path.extname(withoutQuery).toLowerCase();
  } catch {
    return '';
  }
}

function classifyReference(value) {
  const trimmed = cleanReference(value);
  if (isSafeInline(trimmed)) return 'safe-inline';
  if (trimmed.startsWith('data:')) return 'data';
  if (trimmed.startsWith('blob:')) return 'blob';
  if (isRemote(trimmed)) return 'remote';
  if (trimmed.startsWith('/')) return 'root-absolute';

  const ext = extensionFor(trimmed);
  if (TEXT_EXTENSIONS.has(ext)) return 'local-text';
  if (RUNTIME_EXTENSIONS.has(ext)) return 'local-runtime';
  if (ASSET_EXTENSIONS.has(ext)) return 'local-asset';
  if (ARTIFACT_EXTENSIONS.has(ext)) return 'local-artifact';
  return 'local-other';
}

function collectMatches(source, regex, mapper = (match) => match[1]) {
  const matches = [];
  for (const match of source.matchAll(regex)) {
    matches.push(mapper(match));
  }
  return matches;
}

function looksLikeJavaScriptMemberExpression(value) {
  return /^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+$/.test(value);
}

function collectElementReferences(html) {
  const refs = [];
  const elementRegex = /<([a-z][\w:-]*)\b([^>]*)>/gi;
  const attrRegex = /\b(src|href|poster|data|xlink:href)=["']([^"']+)["']/gi;
  const srcsetRegex = /\bsrcset=["']([^"']+)["']/gi;

  for (const element of html.matchAll(elementRegex)) {
    const tag = element[1].toLowerCase();
    const attrs = element[2];

    for (const attr of attrs.matchAll(attrRegex)) {
      refs.push({
        tag,
        attr: attr[1].toLowerCase(),
        value: cleanReference(attr[2]),
      });
    }

    for (const attr of attrs.matchAll(srcsetRegex)) {
      for (const candidate of attr[1].split(',')) {
        const value = cleanReference(candidate.trim().split(/\s+/)[0] || '');
        if (value) refs.push({ tag, attr: 'srcset', value });
      }
    }
  }

  const cssUrls = collectMatches(html, /(?:^|[\s:;{])url\(([^)]+)\)/gi, (match) => {
    const value = cleanReference(match[1]);
    if (looksLikeJavaScriptMemberExpression(value)) return null;
    return {
      tag: 'style',
      attr: 'url()',
      value,
    };
  }).filter(Boolean);

  return uniqueObjects([...refs, ...cssUrls]);
}

function attrValue(attrs, name) {
  const match = attrs.match(new RegExp(`\\b${name}=["']([^"']+)["']`, 'i'));
  return match ? cleanReference(match[1]) : '';
}

function collectTaggedReferences(html, tagName, predicate, attrName = 'href') {
  const refs = [];
  const elementRegex = new RegExp(`<${tagName}\\b([^>]*)>`, 'gi');

  for (const element of html.matchAll(elementRegex)) {
    const attrs = element[1];
    if (!predicate(attrs)) continue;

    const value = attrValue(attrs, attrName);
    if (value) {
      refs.push({
        tag: tagName.toLowerCase(),
        attr: attrName.toLowerCase(),
        value,
      });
    }
  }

  return uniqueObjects(refs);
}

function bucketReferences(refs) {
  const buckets = {
    remote: [],
    rootAbsolute: [],
    localText: [],
    localRuntime: [],
    localAsset: [],
    localArtifact: [],
    localOther: [],
    data: [],
    blob: [],
  };

  for (const ref of refs) {
    const kind = classifyReference(ref.value);
    if (kind === 'remote') buckets.remote.push(ref);
    if (kind === 'root-absolute') buckets.rootAbsolute.push(ref);
    if (kind === 'local-text') buckets.localText.push(ref);
    if (kind === 'local-runtime') buckets.localRuntime.push(ref);
    if (kind === 'local-asset') buckets.localAsset.push(ref);
    if (kind === 'local-artifact') buckets.localArtifact.push(ref);
    if (kind === 'local-other') buckets.localOther.push(ref);
    if (kind === 'data') buckets.data.push(ref);
    if (kind === 'blob') buckets.blob.push(ref);
  }

  return buckets;
}

function isResourceReference(ref) {
  if (ref.tag === 'a' || ref.tag === 'area') return false;
  return true;
}

function printList(title, values) {
  if (values.length === 0) return;
  console.log(`${title}:`);
  for (const ref of values.slice(0, 10)) {
    console.log(`  - <${ref.tag} ${ref.attr}> ${ref.value}`);
  }
  if (values.length > 10) {
    console.log(`  ... ${values.length - 10} more`);
  }
}

function parseArgs(args) {
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    usage(args.includes('--help') || args.includes('-h') ? 0 : 1);
  }

  const options = {
    strict: args.includes('--strict'),
    allowLocalArtifacts: args.includes('--allow-local-artifacts'),
    allowRemoteResources: args.includes('--allow-remote-resources'),
    maxMb: 100,
  };

  const maxMbIndex = args.indexOf('--max-mb');
  if (maxMbIndex !== -1) {
    const raw = args[maxMbIndex + 1];
    if (!raw || Number.isNaN(Number(raw)) || Number(raw) <= 0) {
      console.error('--max-mb requires a positive number.');
      process.exit(1);
    }
    options.maxMb = Number(raw);
  }

  const target = args.find((arg, index) => {
    if (arg.startsWith('--')) return false;
    if (args[index - 1] === '--max-mb') return false;
    return true;
  });

  if (!target) usage(1);
  return { target, options };
}

function main() {
  const { target, options } = parseArgs(process.argv.slice(2));
  const resolved = path.resolve(target);
  const html = fs.readFileSync(resolved, 'utf8');
  const sizeBytes = Buffer.byteLength(html, 'utf8');
  const maxBytes = options.maxMb * 1024 * 1024;

  const refs = collectElementReferences(html);
  const buckets = bucketReferences(refs);

  const externalScripts = buckets.remote
    .filter((ref) => ref.tag === 'script' && ref.attr === 'src')
    .concat(buckets.localRuntime.filter((ref) => ref.tag === 'script' && ref.attr === 'src'));
  const externalStylesheets = collectTaggedReferences(
    html,
    'link',
    (attrs) => /\brel=["'][^"']*\bstylesheet\b/i.test(attrs),
    'href',
  );
  const moduleScriptSrcs = collectTaggedReferences(
    html,
    'script',
    (attrs) => /\btype=["']module["']/i.test(attrs),
    'src',
  );
  const modulePreloads = collectTaggedReferences(
    html,
    'link',
    (attrs) => /\brel=["']modulepreload["']/i.test(attrs),
    'href',
  );

  const dynamicImportCount = collectMatches(html, /\bimport\s*\(/g, () => 'import()').length;
  const localDynamicImports = collectMatches(
    html,
    /\bimport\s*\(\s*["'](\.?\.?\/[^"']+)["']\s*\)/g,
  );
  const fetchCount = collectMatches(html, /\bfetch\s*\(/g, () => 'fetch()').length;
  const localFetches = collectMatches(html, /\bfetch\s*\(\s*["'](\.?\.?\/[^"']+)["']\s*\)/g);
  const xhrCount = collectMatches(html, /\bXMLHttpRequest\b/g, () => 'XMLHttpRequest').length;
  const serviceWorkerCount = collectMatches(
    html,
    /\bnavigator\.serviceWorker\b/g,
    () => 'navigator.serviceWorker',
  ).length;
  const historyApiCount = collectMatches(
    html,
    /\bhistory\.(?:pushState|replaceState)\b/g,
    (match) => match[0],
  ).length;
  const largeDataDownloadAnchors = refs.filter(
    (ref) =>
      ref.tag === 'a' &&
      ref.attr === 'href' &&
      ref.value.startsWith('data:') &&
      ref.value.length > LARGE_DATA_URL_BYTES,
  );
  const remoteResources = buckets.remote.filter(isResourceReference);
  const blockers = [];
  const warnings = [];

  if (sizeBytes > maxBytes) {
    blockers.push(`File exceeds strict size ceiling (${formatMb(sizeBytes)} > ${options.maxMb} MB).`);
  }
  if (buckets.rootAbsolute.length > 0) {
    blockers.push('Root-absolute references remain and will usually break under file://.');
  }
  if (buckets.localText.length > 0) {
    blockers.push('Local text/source references remain; render these into the HTML.');
  }
  if (buckets.localRuntime.length > 0) {
    blockers.push('Local runtime references remain; inline or bundle JS/CSS into the HTML.');
  }
  if (buckets.localAsset.length > 0) {
    blockers.push('Local asset references remain; inline images/fonts/media or embed them as payloads.');
  }
  if (buckets.localOther.length > 0) {
    blockers.push('Unclassified local references remain.');
  }
  if (buckets.localArtifact.length > 0 && !options.allowLocalArtifacts) {
    blockers.push('Local artifact links remain; embed artifacts or pass --allow-local-artifacts explicitly.');
  }
  if (remoteResources.length > 0 && !options.allowRemoteResources) {
    blockers.push('Remote resource loads remain; remove them or pass --allow-remote-resources explicitly.');
  }
  if (externalScripts.length > 0) {
    blockers.push('External script references remain.');
  }
  if (externalStylesheets.length > 0) {
    blockers.push('External stylesheet references remain.');
  }
  if (moduleScriptSrcs.length > 0) {
    blockers.push('External module scripts remain.');
  }
  if (modulePreloads.length > 0) {
    blockers.push('modulepreload links remain.');
  }
  if (localDynamicImports.length > 0) {
    blockers.push('Local dynamic imports remain.');
  }
  if (localFetches.length > 0) {
    blockers.push('Local runtime fetches remain.');
  }
  if (serviceWorkerCount > 0) {
    blockers.push('Service worker usage remains.');
  }
  if (historyApiCount > 0) {
    warnings.push('History API routing detected; hash routing is usually safer for file:// deliverables.');
  }
  if (dynamicImportCount > localDynamicImports.length) {
    warnings.push('Dynamic imports detected; verify they do not create split chunks or network dependencies.');
  }
  if (fetchCount > localFetches.length) {
    warnings.push('Runtime fetch calls detected; verify they do not require network or companion files.');
  }
  // Backstop for network use that the specific checks above do not name: a bare @import,
  // an unquoted src, a module import from a URL, a form action, and similar.
  const withoutAnchors = html.replace(/<a\b[^>]*>/gi, '<a>');
  const absoluteUrls = [...new Set(collectMatches(withoutAnchors, /\b(?:https?|wss?):\/\/[^\s"'<>)\\]+/gi, (m) => m[0]))]
    .filter((u) => !/^https?:\/\/www\.w3\.org\//i.test(u));
  if (absoluteUrls.length > 0) {
    warnings.push(`Absolute web addresses outside <a href> remain (${absoluteUrls.length}); verify none is loaded when the page opens: ${absoluteUrls.slice(0, 5).join(', ')}`);
  }
  if (/\bsendBeacon\s*\(|\bnew\s+WebSocket\b|\bEventSource\s*\(|http-equiv=["']?refresh/i.test(html)) {
    warnings.push('sendBeacon, WebSocket, EventSource or a meta refresh detected; verify it needs no network.');
  }
  if (xhrCount > 0) {
    warnings.push('XMLHttpRequest usage detected; verify it does not require network or companion files.');
  }
  if (largeDataDownloadAnchors.length > 0) {
    warnings.push('Large data: download anchors detected; Blob URL downloads are preferred for large files.');
  }

  console.log(`Audit target: ${resolved}`);
  console.log(`File size:    ${sizeBytes} bytes (${formatMb(sizeBytes)})`);

  if (sizeBytes <= 10 * 1024 * 1024) {
    console.log('Size guide:   excellent');
  } else if (sizeBytes <= 30 * 1024 * 1024) {
    console.log('Size guide:   preferred range');
  } else if (sizeBytes <= 100 * 1024 * 1024) {
    console.log('Size guide:   large; justify with media, transcripts, or attachments');
  } else {
    console.log('Size guide:   oversized; consider compressed payload mode or splitting');
  }

  console.log(
    `Reference counts: remote=${buckets.remote.length}, remote-resources=${remoteResources.length}, root-absolute=${buckets.rootAbsolute.length}, local-text=${buckets.localText.length}, local-runtime=${buckets.localRuntime.length}, local-assets=${buckets.localAsset.length}, local-artifacts=${buckets.localArtifact.length}, local-other=${buckets.localOther.length}, data=${buckets.data.length}, blob=${buckets.blob.length}`,
  );
  console.log(
    `Behavior flags: external-scripts=${externalScripts.length}, external-stylesheets=${externalStylesheets.length}, modulepreload=${modulePreloads.length}, dynamic-imports=${dynamicImportCount}, local-dynamic-imports=${localDynamicImports.length}, fetch=${fetchCount}, local-fetch=${localFetches.length}, xhr=${xhrCount}, service-worker=${serviceWorkerCount}, history-api=${historyApiCount}, large-data-downloads=${largeDataDownloadAnchors.length}`,
  );

  printList('Local text/source references', buckets.localText);
  printList('Local runtime references', buckets.localRuntime);
  printList('Local asset references', buckets.localAsset);
  printList('Local artifact references', buckets.localArtifact);
  printList('Unclassified local references', buckets.localOther);
  printList('Root-absolute references', buckets.rootAbsolute);
  printList('Remote resource loads', remoteResources);
  printList('External scripts', externalScripts);
  printList('External stylesheets', externalStylesheets);
  printList('modulepreload links', modulePreloads);
  printList('Large data: download anchors', largeDataDownloadAnchors);

  if (blockers.length === 0 && warnings.length === 0) {
    console.log('Result: no structural blockers or warnings detected.');
    process.exit(0);
  }

  if (blockers.length > 0) {
    console.log('Blockers:');
    for (const issue of blockers) {
      console.log(`  - ${issue}`);
    }
  }

  if (warnings.length > 0) {
    console.log('Warnings:');
    for (const warning of warnings) {
      console.log(`  - ${warning}`);
    }
  }

  process.exit(options.strict && blockers.length > 0 ? 1 : 0);
}

main();
