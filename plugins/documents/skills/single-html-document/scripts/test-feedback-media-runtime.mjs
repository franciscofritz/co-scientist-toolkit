import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const source = await readFile(new URL("./feedback-media-runtime.js", import.meta.url), "utf8");
const context = {
  Blob,
  Date,
  Math,
  console,
  crypto: {
    randomUUID: () => "00000000-0000-4000-8000-000000000000",
  },
  setTimeout,
};
context.globalThis = context;

vm.createContext(context);
vm.runInContext(source, context);

const runtime = context.FeedbackMediaRuntime.createFeedbackMediaRuntime();

assert.equal(
  runtime.createTextAnnotation({ itemId: "section-1", quote: "Selected text", note: "" }),
  null,
);

const annotation = runtime.createTextAnnotation({
  itemId: "section-1",
  targetId: "section-1-block-2",
  sourceRef: "pages/section-1.md",
  quote: "  Selected   text  ",
  note: "",
  contextBefore: "Before",
  contextAfter: "After",
  startOffset: 4,
  endOffset: 17,
  ranges: [{ blockId: "section-1-block-2", startOffset: 4, endOffset: 17 }],
  requireNote: false,
});

assert.equal(annotation.itemId, "section-1");
assert.equal(annotation.targetId, "section-1-block-2");
assert.equal(annotation.sourceRef, "pages/section-1.md");
assert.equal(annotation.quote, "Selected text");
assert.equal(annotation.note, "");
assert.equal(annotation.startOffset, 4);
assert.equal(annotation.ranges.length, 1);

assert.equal(
  runtime.createTextEditRecord({
    itemId: "section-1",
    targetId: "draft-purpose",
    originalText: "No change",
    editedText: "No change",
  }),
  null,
);

const edit = runtime.createTextEditRecord({
  itemId: "section-1",
  targetId: "draft-purpose",
  sourceRef: "pages/purpose.md#draft-purpose",
  originalText: "This sentence can be edited.",
  editedText: "This sentence has been tightened.",
});

assert.equal(edit.targetId, "draft-purpose");
assert.equal(edit.sourceRef, "pages/purpose.md#draft-purpose");
assert(edit.diff.some((part) => part.op === "delete"));
assert(edit.diff.some((part) => part.op === "insert"));

const exported = runtime.buildInteractionExport({
  documentId: "demo-document",
  reviewer: "reader",
  annotations: [annotation],
  edits: [edit],
});

assert.equal(exported.singleHtmlDocumentFeedbackVersion, 1);
assert.equal(exported.documentId, "demo-document");
assert.equal(exported.annotations.length, 1);
assert.equal(exported.edits.length, 1);
assert(exported.encodedSizeBytes > 0);
