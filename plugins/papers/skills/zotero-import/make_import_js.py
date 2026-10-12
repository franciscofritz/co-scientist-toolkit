#!/usr/bin/env python3
"""Turn an approved manifest into a Zotero Run-JavaScript import script.

    python3 make_import_js.py <outdir> "<collection name>" [--include unidentified]
    python3 make_import_js.py <outdir> "" --plan <outdir>/collections-plan.json --attach-missing

Emits <outdir>/import.js. It only adds: collections, new items with their
stored attachments, and (with --attach-missing) a stored PDF on an existing
item that has none. It never merges, converts, moves or deletes an existing item,
which is the only class of Zotero operation that has proven safe to automate here.
If attaching the PDF fails for an item the script has just created, that new item
is moved to the Trash (not erased), so a rerun can add the paper properly.
A manifest record with review_manuscript set is never imported.

--plan maps file paths to collection paths ("Reinforcement learning/Offline
RL"), so one import can file papers into several collections, nested with "/".
Papers the plan does not mention go into "<collection name>", or stay unfiled
if that is "".

The script is idempotent. A paper whose DOI or title is already in the target
library is skipped, an existing item that has meanwhile gained a PDF is left
alone, and collections are reused by name under the same parent. Running it
twice cannot duplicate anything.
"""
import argparse, json, os, shutil, subprocess, sys

TEMPLATE = r'''// Import papers into Zotero.  Generated - do not hand-edit.
//
// Run inside Zotero:  Tools -> Developer -> Run JavaScript
// TICK the "Run as async function" checkbox.
//
// ADDITIONS ONLY: %(n_new)d new items, %(n_attach)d PDFs attached to existing items
// that have none, and the collections they go into. Nothing existing is
// merged, converted, moved or deleted, so this cannot repeat the annotation
// loss caused by convertLinkedFileToStoredFile. Files are COPIED into Zotero
// storage; the originals stay where they are until verify_and_move.py says so.
// The one removal: if the PDF cannot be attached to an item this run has just
// created, that new item (which has no PDF) is moved to the Trash.
//
// Leave DRY_RUN = true for the first run. It is safe to run twice.

const DRY_RUN = true;
// 0 = personal library. A number > 0 is a Zotero libraryID, which for a shared
// project is usually what you want: attachments then reach the co-authors
// rather than sitting in one person's library.
const TARGET_LIBRARY_ID = %(lib)s;

const PAPERS = %(papers)s;

const lib = TARGET_LIBRARY_ID || Zotero.Libraries.userLibraryID;
if (!Zotero.Libraries.exists(lib)) {
  return "No library with id " + lib + " in this Zotero. Nothing done.";
}
if (lib !== Zotero.Libraries.userLibraryID && !Zotero.Libraries.get(lib).editable) {
  return "Library " + lib + " is not editable by you. Nothing done.";
}
const out = ["target library: " + lib + "  (" + Zotero.Libraries.get(lib).name + ")"];

const norm = s => (s || "").normalize("NFKD").toLowerCase()
  .replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();

// What the library holds right now, not at scan time: it drifts (a sync can
// bring items in between scan and run), and an earlier run may have happened.
// Paper types only, the same list the scanner uses: a saved webpage with a
// paper's title is not the paper, and counting it silently skipped one.
const present = new Set();
for (const row of await Zotero.DB.queryAsync(
    "SELECT f.fieldName AS f, v.value AS v FROM items i JOIN itemTypes t USING(itemTypeID) "
  + "JOIN itemData d USING(itemID) "
  + "JOIN fields f USING(fieldID) JOIN itemDataValues v USING(valueID) "
  + "WHERE i.libraryID=? AND f.fieldName IN ('DOI','title') "
  + "AND t.typeName IN ('journalArticle','preprint','conferencePaper','book','bookSection','thesis','report','document','manuscript','magazineArticle','newspaperArticle') "
  + "AND i.itemID NOT IN (SELECT itemID FROM deletedItems)", lib)) {
  present.add(row.f === "DOI" ? "doi:" + row.v.toLowerCase().trim() : "t:" + norm(row.v));
}

// collections by path, reused by name under the same parent, created if absent
const collCache = {};
let collsCreated = 0;
async function collectionFor(path) {
  if (!path) return null;
  if (collCache[path] !== undefined) return collCache[path];
  let parentID = null, id = null;
  for (const name of path.split("/").map(s => s.trim()).filter(Boolean)) {
    let c = Zotero.Collections.getByLibrary(lib, true)
      .find(x => x.name === name && (x.parentID || null) === parentID);
    if (!c) {
      if (DRY_RUN) { out.push("would create collection: " + path); collCache[path] = -1; return -1; }
      c = new Zotero.Collection();
      c.libraryID = lib;
      c.name = name;
      if (parentID) c.parentID = parentID;
      await c.saveTx();
      collsCreated++;
    }
    parentID = id = c.id;
  }
  collCache[path] = id;
  return id;
}

const before = (await Zotero.DB.columnQueryAsync(
  "SELECT COUNT(*) FROM items WHERE libraryID=?", lib))[0];
const annBefore = (await Zotero.DB.columnQueryAsync(
  "SELECT COUNT(*) FROM itemAnnotations a JOIN items i USING(itemID) WHERE i.libraryID=?", lib))[0];

let added = 0, attached = 0, skipped = 0, failed = 0;
for (const p of PAPERS) {
  let stub = null;   // the new item once saved, until its PDF is attached
  try {
    if (!(await IOUtils.exists(p.path))) { out.push("MISSING  " + p.path); failed++; continue; }
    const cid = await collectionFor(p.collection);

    if (p.mode === "attach") {
      const parent = await Zotero.Items.getByLibraryAndKeyAsync(lib, p.key);
      if (!parent) { out.push("FAIL  no item " + p.key); failed++; continue; }
      let hasPdf = false;
      for (const a of Zotero.Items.get(parent.getAttachments())) {
        if (a.attachmentContentType === "application/pdf" && await a.fileExists()) hasPdf = true;
      }
      if (hasPdf) { out.push("skip, now has a PDF  " + p.title.slice(0, 64)); skipped++; continue; }
      if (DRY_RUN) { out.push("would attach  " + p.title.slice(0, 70)); attached++; continue; }
      await Zotero.Attachments.importFromFile({ file: p.path, libraryID: lib, parentItemID: parent.id });
      out.push("attached  " + p.title.slice(0, 70));
      attached++;
      continue;
    }

    const doi = (p.fields && p.fields.DOI || "").toLowerCase().trim();
    if (!p.force && ((doi && present.has("doi:" + doi)) || present.has("t:" + norm(p.title)))) {
      out.push("skip, already in library  " + p.title.slice(0, 60)); skipped++; continue;
    }
    if (DRY_RUN) {
      out.push("would add  " + p.title.slice(0, 70) + (p.collection ? "   -> " + p.collection : "")
        + (p.tags && p.tags.length ? "   [" + p.tags.join("; ") + "]" : ""));
      added++; continue;
    }
    const item = new Zotero.Item(p.itemType || "journalArticle");
    item.libraryID = lib;
    for (const [f, v] of Object.entries(p.fields || {})) {
      if (v) { try { item.setField(f, v); } catch (e) {} }   // field not valid for this type
    }
    if (p.creators && p.creators.length) {
      item.setCreators(p.creators.map(c => ({
        firstName: c.firstName || "", lastName: c.lastName || "", creatorType: "author"
      })));
    }
    if (cid) item.setCollections([cid]);
    for (const t of (p.tags || [])) item.addTag(t);
    await item.saveTx();
    stub = item;
    await Zotero.Attachments.importFromFile({ file: p.path, libraryID: lib, parentItemID: item.id });
    stub = null;
    present.add("t:" + norm(p.title));
    if (doi) present.add("doi:" + doi);
    out.push("added  " + p.title.slice(0, 70));
    added++;
  } catch (e) {
    // If importFromFile threw after the item was saved, the item has no PDF. Move
    // that item, which this run created a moment ago, to the Trash so that a rerun
    // can add the paper properly. It is left alone if it has gained an attachment.
    let note = "";
    if (stub) {
      try {
        if (stub.getAttachments().length === 0) {
          stub.deleted = true;
          await stub.saveTx();
          note = "   (the item made for it, which has no PDF, was moved to the Trash)";
        } else {
          note = "   (item kept: it has an attachment)";
        }
      } catch (e2) {
        note = "   (the item made for it has no PDF and could not be removed: " + e2 + ")";
      }
    }
    out.push("FAIL  " + p.path.split("/").pop() + "  " + e + note);
    failed++;
  }
}

const after = (await Zotero.DB.columnQueryAsync(
  "SELECT COUNT(*) FROM items WHERE libraryID=?", lib))[0];
const annAfter = (await Zotero.DB.columnQueryAsync(
  "SELECT COUNT(*) FROM itemAnnotations a JOIN items i USING(itemID) WHERE i.libraryID=?", lib))[0];

return (DRY_RUN ? "DRY RUN - nothing changed\n\n" : "APPLIED\n\n")
  + "added: " + added + "   attached: " + attached + "   skipped: " + skipped
  + "   failed: " + failed + "   collections created: " + collsCreated + "\n"
  + "items: " + before + " -> " + after + "\n"
  + "annotations: " + annBefore + " -> " + annAfter
  + (annBefore === annAfter ? "   OK, none lost\n\n"
                            : "   *** " + (annBefore - annAfter) + " LOST - RESTORE THE BACKUP ***\n\n")
  + out.join("\n");
'''

FIELDS = ["title", "date", "DOI", "url", "abstractNote", "publicationTitle",
          "proceedingsTitle", "volume", "issue", "pages", "repository", "archiveID", "rights"]

def license_check_command():
    """The papers plugin's license-check, as an argv prefix, or None if it is not installed.
    From this skill's folder it sits at ../../tools/license-check; failing that, the
    plugin puts a `license-check` command on the Bash tool's PATH."""
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.normpath(os.path.join(here, "..", "..", "tools", "license-check",
                                           "license_check.py"))
    if os.path.isfile(script):
        return [sys.executable, script]
    exe = shutil.which("license-check")
    return [exe] if exe else None


LICENSE_CHECK = license_check_command()


def rights_for(md, path):
    """Zotero's Rights field from the licence check: the PDF itself, which carries its own
    licence statement, or failing that the DOI. Blank if the check is missing or fails."""
    if not LICENSE_CHECK:
        return ""
    for target in (path, md.get("DOI")):
        if not target or (target == path and not os.path.isfile(path)):
            continue
        try:
            r = subprocess.run(LICENSE_CHECK + ["check", target, "--rights"],
                               capture_output=True, text=True, timeout=40)
            if r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            pass
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("name", help='collection for papers the plan does not place ("" = unfiled)')
    ap.add_argument("--include", nargs="*", default=[],
                    help="extra statuses to include beyond new/title only")
    ap.add_argument("--only-identified", action="store_true",
                    help="import only papers with a DOI or arXiv id")
    ap.add_argument("--plan", help="JSON {file path: collection path}")
    ap.add_argument("--attach-missing", action="store_true",
                    help="attach the local PDF to items already in Zotero that have none")
    ap.add_argument("--lib", type=int, default=0,
                    help="target Zotero libraryID; 0 = personal. Use the group "
                         "libraryID for a shared project so co-authors get the files.")
    a = ap.parse_args()

    man = json.load(open(os.path.join(a.outdir, "manifest.json")))
    plan = json.load(open(a.plan)) if a.plan else {}
    # "title only" carries a real title read from the paper's own first page,
    # which is proper metadata. "unidentified" has no title at all and is
    # excluded unless explicitly asked for.
    wanted = {"new", "title only"} | set(a.include)
    papers = []
    for r in man:
        md = r.get("metadata") or {}
        if r.get("review_manuscript"):
            continue          # possible manuscript under review: never imported, whatever --include says
        coll = plan.get(r["path"], a.name)
        if (r.get("status") == "already in Zotero" and a.attach_missing
                and not r.get("zotero_has_pdf") and r.get("zotero_key")):
            papers.append({"mode": "attach", "key": r["zotero_key"], "path": r["path"],
                           "title": md.get("title") or r["file"], "collection": None})
            continue
        if r.get("status") not in wanted:
            continue
        if a.only_identified and not md.get("DOI"):
            continue
        if not md.get("rights"):
            md["rights"] = rights_for(md, r["path"])
        papers.append({
            "mode": "new",
            "path": r["path"],
            "title": " ".join((md.get("title") or r["file"]).split()),
            "itemType": md.get("itemType", "journalArticle"),
            # Crossref titles can carry embedded line breaks and runs of spaces
            # ("Generative\n   AI\n   Is Neither Just Another\n   IT"); collapse them.
            "fields": {f: " ".join(str(md[f]).split()) for f in FIELDS if md.get(f)}
                      or {"title": r["file"]},
            "creators": md.get("creators", []),
            "collection": coll or None,
            # Optional manifest field, set by a per-import patch script:
            # provenance for items filed without a collection.
            "tags": [t for t in r.get("tags", []) if t],
            # set by a patch after checking by hand that a same-titled library item is a
            # different work (generic book titles collide: two different textbooks can
            # both be called "Quantum Field Theory")
            "force": bool(r.get("force")),
        })
    if not papers:
        raise SystemExit("nothing to import - no manifest entries with status " + str(sorted(wanted)))

    # The script embeds absolute paths and is run by hand, possibly days later.
    # A staging folder under /tmp or /var/folders will have been swept by then
    # and every import fails at once, so refuse to generate rather than emit a
    # script with a fuse in it.
    volatile = [p["path"] for p in papers
                if p["path"].startswith(("/tmp/", "/private/tmp/", "/var/folders/"))]
    if volatile:
        raise SystemExit(
            f"{len(volatile)} of {len(papers)} paths are under /tmp or /var/folders, which "
            f"the OS clears.\ne.g. {volatile[0]}\nMove the files somewhere durable, repoint "
            f"the manifest, and regenerate.")

    n_new = sum(p["mode"] == "new" for p in papers)
    n_att = len(papers) - n_new
    js = TEMPLATE % {"n_new": n_new, "n_attach": n_att, "lib": a.lib,
                     "papers": json.dumps(papers, indent=1)}
    p = os.path.join(a.outdir, "import.js")
    open(p, "w").write(js)
    colls = sorted({x["collection"] for x in papers if x.get("collection")})
    print(f"wrote {p}  ({n_new} new, {n_att} to attach, {len(colls)} collections)")


if __name__ == "__main__":
    main()
