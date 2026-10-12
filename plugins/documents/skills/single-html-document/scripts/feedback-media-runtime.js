/* Feedback workbook browser helper.
   Copy or import this into the source JavaScript for standalone review forms,
   then strip comments when packaging the final single HTML file. */
(function attachFeedbackMediaRuntime(globalScope) {
  "use strict";

  function createId(prefix) {
    if (globalScope.crypto && typeof globalScope.crypto.randomUUID === "function") {
      return `${prefix}-${globalScope.crypto.randomUUID()}`;
    }

    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  function extensionFor(file, fallback) {
    const extension = (file.name || "").split(".").pop();
    return extension && extension !== file.name ? extension : fallback;
  }

  function createFeedbackMediaRuntime(options = {}) {
    const dbName = options.dbName || "feedback-media";
    const storeName = options.storeName || "attachments";
    const memoryMedia = new Map();

    function warn(message) {
      if (typeof options.onWarning === "function") options.onWarning(message);
    }

    function openMediaDb() {
      return new Promise((resolve, reject) => {
        if (!("indexedDB" in globalScope)) {
          reject(new Error("IndexedDB is not available."));
          return;
        }

        const request = globalScope.indexedDB.open(dbName, 1);

        request.onupgradeneeded = () => {
          request.result.createObjectStore(storeName, { keyPath: "id" });
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    }

    async function saveMediaAttachment(record, blob) {
      try {
        const db = await openMediaDb();

        await new Promise((resolve, reject) => {
          const tx = db.transaction(storeName, "readwrite");
          tx.objectStore(storeName).put({ ...record, blob });
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        });

        return { ...record, storage: "indexeddb" };
      } catch (error) {
        memoryMedia.set(record.id, { ...record, blob });
        warn("Attached media will be lost if this page is closed before saving.");
        return { ...record, storage: "memory" };
      }
    }

    async function loadMediaAttachment(id) {
      if (memoryMedia.has(id)) return memoryMedia.get(id);

      const db = await openMediaDb();

      return new Promise((resolve, reject) => {
        const tx = db.transaction(storeName, "readonly");
        const request = tx.objectStore(storeName).get(id);

        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
      });
    }

    async function deleteMediaAttachment(id) {
      memoryMedia.delete(id);

      try {
        const db = await openMediaDb();

        await new Promise((resolve, reject) => {
          const tx = db.transaction(storeName, "readwrite");
          tx.objectStore(storeName).delete(id);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        });
      } catch (error) {
        warn("Stored media could not be removed from this browser, but it will be omitted from the feedback export.");
      }
    }

    async function collectFileAttachment({ itemId, kind, file, fallbackExtension }) {
      if (!file) return null;

      const record = {
        id: createId(`${itemId}-${kind}`),
        itemId,
        kind,
        fileName: file.name || `${itemId}-${kind}.${extensionFor(file, fallbackExtension || "bin")}`,
        mimeType: file.type || "application/octet-stream",
        sizeBytes: file.size,
        createdAt: new Date().toISOString(),
      };

      return saveMediaAttachment(record, file);
    }

    async function collectScreenshotFile(itemId, file) {
      if (!file || !file.type.startsWith("image/")) return null;
      return collectFileAttachment({
        itemId,
        kind: "screenshot",
        file,
        fallbackExtension: "png",
      });
    }

    async function collectPastedScreenshot(itemId, clipboardData) {
      const imageItem = Array.from(clipboardData.items || []).find((item) =>
        item.type.startsWith("image/")
      );

      if (!imageItem) return null;
      return collectScreenshotFile(itemId, imageItem.getAsFile());
    }

    async function collectVoiceFile(itemId, file) {
      if (!file || !file.type.startsWith("audio/")) return null;
      return collectFileAttachment({
        itemId,
        kind: "voice-note",
        file,
        fallbackExtension: "webm",
      });
    }

    async function startVoiceRecording({ itemId, maxDurationMs = 60_000, onComplete }) {
      if (!("MediaRecorder" in globalScope) || !globalScope.navigator?.mediaDevices) {
        warn("Recording is not available in this browser. Upload an audio file instead.");
        return null;
      }

      const stream = await globalScope.navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new globalScope.MediaRecorder(stream);
      const chunks = [];

      recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      });

      recorder.addEventListener("stop", async () => {
        stream.getTracks().forEach((track) => track.stop());

        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunks, { type: mimeType });
        const file = new File([blob], `${itemId}-voice-note.webm`, { type: mimeType });
        const attachment = await collectVoiceFile(itemId, file);

        if (typeof onComplete === "function") onComplete(attachment);
      });

      recorder.start();
      globalScope.setTimeout(() => {
        if (recorder.state === "recording") recorder.stop();
      }, maxDurationMs);

      return recorder;
    }

    function blobToBase64(blob) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = () => {
          const dataUrl = String(reader.result);
          resolve(dataUrl.slice(dataUrl.indexOf(",") + 1));
        };
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
      });
    }

    function createTextAnnotation({
      itemId,
      targetId,
      sourceRef = "",
      quote,
      note,
      contextBefore = "",
      contextAfter = "",
      startOffset = null,
      endOffset = null,
      ranges = [],
      requireNote = true,
    }) {
      const idBase = targetId || itemId;
      const trimmedQuote = String(quote || "").replace(/\s+/g, " ").trim();
      const trimmedNote = String(note || "").trim();

      if (!idBase || !trimmedQuote || (requireNote && !trimmedNote)) return null;

      const annotation = {
        id: createId(`${idBase}-annotation`),
        itemId: itemId || targetId,
        targetId: targetId || itemId,
        sourceRef,
        quote: trimmedQuote,
        note: trimmedNote,
        contextBefore,
        contextAfter,
        createdAt: new Date().toISOString(),
      };

      if (Number.isFinite(startOffset)) annotation.startOffset = startOffset;
      if (Number.isFinite(endOffset)) annotation.endOffset = endOffset;
      if (Array.isArray(ranges) && ranges.length) annotation.ranges = ranges;

      return annotation;
    }

    function tokenizeForDiff(text, granularity) {
      const value = String(text || "");
      if (granularity === "line") return value.split(/(\n)/).filter((token) => token !== "");
      return value.match(/\s+|[^\s]+/g) || [];
    }

    function compactDiff(ops) {
      const compacted = [];
      for (const op of ops) {
        if (!op.text) continue;
        const previous = compacted[compacted.length - 1];
        if (previous && previous.op === op.op) previous.text += op.text;
        else compacted.push({ ...op });
      }
      return compacted;
    }

    function diffTokens(originalTokens, editedTokens) {
      const maxCells = 120_000;
      if (originalTokens.length * editedTokens.length > maxCells) {
        return compactDiff([
          { op: "delete", text: originalTokens.join("") },
          { op: "insert", text: editedTokens.join("") },
        ]);
      }

      const rows = originalTokens.length + 1;
      const cols = editedTokens.length + 1;
      const table = Array.from({ length: rows }, () => Array(cols).fill(0));

      for (let i = originalTokens.length - 1; i >= 0; i -= 1) {
        for (let j = editedTokens.length - 1; j >= 0; j -= 1) {
          table[i][j] =
            originalTokens[i] === editedTokens[j]
              ? table[i + 1][j + 1] + 1
              : Math.max(table[i + 1][j], table[i][j + 1]);
        }
      }

      const ops = [];
      let i = 0;
      let j = 0;

      while (i < originalTokens.length && j < editedTokens.length) {
        if (originalTokens[i] === editedTokens[j]) {
          ops.push({ op: "equal", text: originalTokens[i] });
          i += 1;
          j += 1;
        } else if (table[i + 1][j] >= table[i][j + 1]) {
          ops.push({ op: "delete", text: originalTokens[i] });
          i += 1;
        } else {
          ops.push({ op: "insert", text: editedTokens[j] });
          j += 1;
        }
      }

      while (i < originalTokens.length) {
        ops.push({ op: "delete", text: originalTokens[i] });
        i += 1;
      }
      while (j < editedTokens.length) {
        ops.push({ op: "insert", text: editedTokens[j] });
        j += 1;
      }

      return compactDiff(ops);
    }

    function createTextEditRecord({
      itemId,
      targetId,
      sourceRef = "",
      originalText,
      editedText,
      granularity = "word",
    }) {
      const idBase = targetId || itemId;
      const original = String(originalText || "");
      const edited = String(editedText || "");

      if (!idBase || original === edited) return null;

      return {
        id: createId(`${idBase}-edit`),
        itemId: itemId || targetId,
        targetId: targetId || itemId,
        sourceRef,
        originalText: original,
        editedText: edited,
        diffGranularity: granularity,
        diff: diffTokens(tokenizeForDiff(original, granularity), tokenizeForDiff(edited, granularity)),
        createdAt: new Date().toISOString(),
      };
    }

    function buildInteractionExport({
      documentId,
      reviewer = "anonymous",
      annotations = [],
      edits = [],
      extra = {},
    }) {
      const payload = {
        singleHtmlDocumentFeedbackVersion: 1,
        documentId: documentId || "",
        generatedAt: new Date().toISOString(),
        reviewer,
        annotations,
        edits,
        ...extra,
      };
      return {
        ...payload,
        encodedSizeBytes: new Blob([JSON.stringify(payload)]).size,
      };
    }

    async function buildFeedbackExport(draft, exportOptions = {}) {
      const attachments = [];
      const includeMedia = exportOptions.includeMedia !== false;

      for (const attachment of draft.attachments || []) {
        if (!includeMedia) {
          attachments.push({ ...attachment, payloadOmitted: true });
          continue;
        }

        const stored = await loadMediaAttachment(attachment.id);

        if (!stored?.blob) {
          attachments.push({ ...attachment, payloadMissing: true });
          continue;
        }

        attachments.push({
          ...attachment,
          payloadEncoding: "base64",
          payload: await blobToBase64(stored.blob),
        });
      }

      const payload = {
        feedbackSchemaVersion: draft.feedbackSchemaVersion || 2,
        generatedAt: new Date().toISOString(),
        reviewer: draft.reviewer || "anonymous",
        items: draft.items || [],
        attachments,
        mediaIncluded: attachments.every((item) => !item.payloadMissing && !item.payloadOmitted),
      };

      const encodedSizeBytes = new Blob([JSON.stringify(payload)]).size;
      const maxPayloadBytes = exportOptions.maxPayloadBytes || null;

      if (maxPayloadBytes && encodedSizeBytes > maxPayloadBytes && includeMedia) {
        return buildFeedbackExport(draft, { ...exportOptions, includeMedia: false });
      }

      return { ...payload, encodedSizeBytes };
    }

    return {
      buildFeedbackExport,
      buildInteractionExport,
      collectFileAttachment,
      collectPastedScreenshot,
      collectScreenshotFile,
      createTextEditRecord,
      createTextAnnotation,
      deleteMediaAttachment,
      collectVoiceFile,
      loadMediaAttachment,
      saveMediaAttachment,
      startVoiceRecording,
    };
  }

  globalScope.FeedbackMediaRuntime = { createFeedbackMediaRuntime };
})(typeof window !== "undefined" ? window : globalThis);
