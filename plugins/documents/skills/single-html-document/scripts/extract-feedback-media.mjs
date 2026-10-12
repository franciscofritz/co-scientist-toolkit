#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const USAGE = `Usage:
  node extract-feedback-media.mjs feedback.json --out extracted-feedback

Extracts base64 media attachments from a returned feedback workbook JSON file.
`;

function parseArgs(argv) {
  const args = [...argv];
  const input = args.shift();
  let outDir = null;

  while (args.length) {
    const arg = args.shift();
    if (arg === "--out") {
      outDir = args.shift();
    } else if (arg === "--help" || arg === "-h") {
      return { help: true };
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!input) return { help: true };

  return {
    input,
    outDir: outDir || `${path.basename(input, path.extname(input))}-media`,
  };
}

function safeFileName(value) {
  return String(value || "attachment")
    .replace(/[^\w.-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 140) || "attachment";
}

function extensionFor(attachment) {
  const fromName = path.extname(attachment.fileName || "");
  if (fromName) return fromName;

  if (attachment.mimeType === "image/png") return ".png";
  if (attachment.mimeType === "image/jpeg") return ".jpg";
  if (attachment.mimeType === "audio/webm") return ".webm";
  if (attachment.mimeType === "audio/mpeg") return ".mp3";
  if (attachment.mimeType === "audio/wav") return ".wav";

  return ".bin";
}

function getAttachments(feedback) {
  if (Array.isArray(feedback.attachments)) return feedback.attachments;

  if (Array.isArray(feedback.items)) {
    return feedback.items.flatMap((item) =>
      Array.isArray(item.attachments)
        ? item.attachments.map((attachment) => ({ ...attachment, itemId: attachment.itemId || item.id }))
        : []
    );
  }

  return [];
}

async function extractFeedbackMedia(input, outDir) {
  const raw = await readFile(input, "utf8");
  const feedback = JSON.parse(raw);
  const attachments = getAttachments(feedback);
  const extracted = [];
  const skipped = [];

  await mkdir(outDir, { recursive: true });

  for (const [index, attachment] of attachments.entries()) {
    if (!attachment.payload || attachment.payloadEncoding !== "base64") {
      skipped.push({
        id: attachment.id || null,
        reason: attachment.payloadMissing ? "payload missing" : "no base64 payload",
      });
      continue;
    }

    const itemPrefix = safeFileName(attachment.itemId || "feedback");
    const kind = safeFileName(attachment.kind || "media");
    const extension = extensionFor(attachment);
    const fallbackName = `${itemPrefix}-${String(index + 1).padStart(2, "0")}-${kind}${extension}`;
    const fileName = safeFileName(attachment.fileName || fallbackName);
    const outputPath = path.join(outDir, fileName.endsWith(extension) ? fileName : `${fileName}${extension}`);
    const buffer = Buffer.from(attachment.payload, "base64");

    await writeFile(outputPath, buffer);

    extracted.push({
      id: attachment.id || null,
      itemId: attachment.itemId || null,
      kind: attachment.kind || null,
      fileName: path.basename(outputPath),
      path: outputPath,
      mimeType: attachment.mimeType || null,
      bytes: buffer.byteLength,
    });
  }

  const manifest = {
    source: path.resolve(input),
    extractedAt: new Date().toISOString(),
    extracted,
    skipped,
  };
  const manifestPath = path.join(outDir, "manifest.json");

  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

  return { ...manifest, manifestPath };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.help) {
    process.stdout.write(USAGE);
    return;
  }

  const result = await extractFeedbackMedia(args.input, args.outDir);

  process.stdout.write(
    JSON.stringify(
      {
        extracted: result.extracted.length,
        skipped: result.skipped.length,
        output: path.resolve(args.outDir),
        manifest: result.manifestPath,
      },
      null,
      2
    )
  );
  process.stdout.write("\n");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

export { extractFeedbackMedia };
