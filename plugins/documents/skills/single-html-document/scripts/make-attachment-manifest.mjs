#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const MIME_TYPES = new Map([
  ['.csv', 'text/csv'],
  ['.doc', 'application/msword'],
  ['.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  ['.gif', 'image/gif'],
  ['.html', 'text/html'],
  ['.jpeg', 'image/jpeg'],
  ['.jpg', 'image/jpeg'],
  ['.json', 'application/json'],
  ['.md', 'text/markdown'],
  ['.mp3', 'audio/mpeg'],
  ['.mp4', 'video/mp4'],
  ['.pdf', 'application/pdf'],
  ['.png', 'image/png'],
  ['.ppt', 'application/vnd.ms-powerpoint'],
  ['.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'],
  ['.svg', 'image/svg+xml'],
  ['.txt', 'text/plain'],
  ['.tsv', 'text/tab-separated-values'],
  ['.webm', 'video/webm'],
  ['.webp', 'image/webp'],
  ['.xls', 'application/vnd.ms-excel'],
  ['.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
  ['.xml', 'application/xml'],
  ['.zip', 'application/zip'],
]);

function usage(exitCode = 1) {
  console.error(`Usage:
  node make-attachment-manifest.mjs --output <file.{json|ts}> [--root <dir>] [--gzip] <file-or-dir>...

Examples:
  node make-attachment-manifest.mjs --output attachments.generated.json media/attachments
  node make-attachment-manifest.mjs --output attachments.generated.ts --root media/attachments --gzip media/attachments
`);
  process.exit(exitCode);
}

function normalizeSlashes(value) {
  return value.split(path.sep).join('/');
}

function commonDirectory(paths) {
  if (paths.length === 0) {
    return process.cwd();
  }

  const [first, ...rest] = paths.map((filePath) => path.resolve(filePath).split(path.sep));
  let end = first.length;

  for (const parts of rest) {
    while (end > 0 && first.slice(0, end).join(path.sep) !== parts.slice(0, end).join(path.sep)) {
      end -= 1;
    }
  }

  return end === 0 ? process.cwd() : first.slice(0, end).join(path.sep);
}

function walkInputs(inputPath) {
  const resolved = path.resolve(inputPath);
  const stats = fs.statSync(resolved);

  if (stats.isFile()) {
    return [resolved];
  }

  if (stats.isDirectory()) {
    const files = [];
    for (const entry of fs.readdirSync(resolved, { withFileTypes: true })) {
      files.push(...walkInputs(path.join(resolved, entry.name)));
    }
    return files;
  }

  return [];
}

function mimeTypeFor(filePath) {
  return MIME_TYPES.get(path.extname(filePath).toLowerCase()) || 'application/octet-stream';
}

function attachmentId(relativePath) {
  const base = relativePath.replace(/\.[^.]+$/, '');
  return base
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'attachment';
}

function parseArgs(argv) {
  const args = {
    output: '',
    root: '',
    gzip: false,
    inputs: [],
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--output' || arg === '-o') {
      args.output = argv[index + 1] || '';
      index += 1;
      continue;
    }
    if (arg === '--root') {
      args.root = argv[index + 1] || '';
      index += 1;
      continue;
    }
    if (arg === '--gzip') {
      args.gzip = true;
      continue;
    }
    if (arg === '--help' || arg === '-h') {
      usage(0);
    }
    args.inputs.push(arg);
  }

  if (!args.output || args.inputs.length === 0) {
    usage(1);
  }

  return args;
}

function buildManifest(files, rootDir, gzip) {
  const attachments = files.map((filePath) => {
    const original = fs.readFileSync(filePath);
    const stored = gzip ? zlib.gzipSync(original) : original;
    const relativePath = normalizeSlashes(path.relative(rootDir, filePath));

    return {
      id: attachmentId(relativePath),
      fileName: path.basename(filePath),
      relativePath,
      mimeType: mimeTypeFor(filePath),
      originalSizeBytes: original.byteLength,
      storedSizeBytes: stored.byteLength,
      encoding: gzip ? 'gzip+base64' : 'base64',
      sha256: crypto.createHash('sha256').update(original).digest('hex'),
      payload: stored.toString('base64'),
    };
  });

  return {
    generatedAt: new Date().toISOString(),
    root: normalizeSlashes(path.resolve(rootDir)),
    attachmentCount: attachments.length,
    attachments,
  };
}

function writeManifest(outputPath, manifest) {
  const resolved = path.resolve(outputPath);
  fs.mkdirSync(path.dirname(resolved), { recursive: true });

  const body = JSON.stringify(manifest, null, 2);
  if (resolved.endsWith('.ts')) {
    fs.writeFileSync(
      resolved,
      `export const attachmentManifest = ${body} as const;\n`,
      'utf8',
    );
    return;
  }

  fs.writeFileSync(resolved, `${body}\n`, 'utf8');
}

function main() {
  const { output, root, gzip, inputs } = parseArgs(process.argv.slice(2));
  const files = [...new Set(inputs.flatMap((input) => walkInputs(input)).sort())];

  if (files.length === 0) {
    console.error('No input files found.');
    process.exit(1);
  }

  const rootDir = root ? path.resolve(root) : commonDirectory(files);
  const manifest = buildManifest(files, rootDir, gzip);

  writeManifest(output, manifest);

  const totalOriginal = manifest.attachments.reduce((sum, item) => sum + item.originalSizeBytes, 0);
  const totalStored = manifest.attachments.reduce((sum, item) => sum + item.storedSizeBytes, 0);
  const ratio = totalOriginal === 0 ? 1 : totalStored / totalOriginal;

  console.log(`Wrote ${manifest.attachmentCount} attachment records to ${path.resolve(output)}`);
  console.log(`Original bytes: ${totalOriginal}`);
  console.log(`Stored bytes:   ${totalStored}`);
  console.log(`Storage ratio:  ${ratio.toFixed(3)}`);
}

main();
