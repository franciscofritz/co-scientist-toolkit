#!/usr/bin/env python3
"""After an import has run, check each scanned file against Zotero and move the
ones Zotero now holds into a single holding folder.

    verify_and_move.py <outdir>            # plan only: what would move, and why
    verify_and_move.py <outdir> --apply    # move them
    verify_and_move.py <outdir> --undo     # put everything back where it was
    verify_and_move.py <outdir> --any-root # also move files scanned from other folders

Verification is against the database, never against the import script's own
report. A file is cleared only when:

  - it was imported or attached: Zotero holds a STORED attachment of exactly
    this file's size on the matching item, and the file is present in storage;
  - it was already in Zotero: the item has a PDF Zotero can open that does not
    live in Downloads or on the Desktop;
  - it is a duplicate: the copy it duplicates was itself cleared;

and in every case no Zotero attachment links to the file itself.

Only files inside the cleared folders (Downloads and the Desktop, or the folders in
ZOTERO_IMPORT_CLEARED_ROOTS) are moved. A record scanned from any other folder is
held back, and the plan says so, unless --any-root is passed.

Nothing is deleted. Every move is logged to <outdir>/moves.json.

The Zotero data directory is found from ZOTERO_DATA_DIR, else Zotero's own
setting, else ~/Zotero. "Downloads or the Desktop" below means the folders in
ZOTERO_IMPORT_CLEARED_ROOTS (see zotero_env.py).
"""
import argparse, datetime, json, os, re, shutil, sqlite3, sys, tempfile, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zotero_env import base_attachment_path, cleared_roots, data_dir, remove_db_copy, zotero_running

HOME = os.path.expanduser("~")
CLEARED_ROOTS = cleared_roots()


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def snapshot_db(src, dst):
    """A consistent copy of a SQLite database that may be in WAL mode.

    Zotero 10 enables WAL: recent writes can sit in zotero.sqlite-wal until a
    checkpoint, so copying zotero.sqlite alone gives a stale snapshot (Zotero's
    developer notes say as much). Copy the -wal and -shm files with it, then
    checkpoint the COPY. The live files are only ever read."""
    for sfx in ("", "-wal", "-shm"):
        if os.path.exists(dst + sfx):
            os.remove(dst + sfx)
    for sfx in ("", "-wal", "-shm"):
        if os.path.exists(src + sfx):
            shutil.copy2(src + sfx, dst + sfx)
    con = sqlite3.connect(dst)
    con.execute("pragma wal_checkpoint(TRUNCATE)")
    con.close()


def load_library(scratch, lib):
    """Read what the library holds. The scratch copy of the database is deleted
    before this returns, also when it stops on an error."""
    if zotero_running():
        sys.exit("Zotero is running. Quit it so the database copy is consistent, then rerun.")
    zdir = data_dir()
    copy = os.path.join(scratch, "z_verify.sqlite")
    db = None
    try:
        snapshot_db(os.path.join(zdir, "zotero.sqlite"), copy)
        db = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
        if db.execute("pragma integrity_check;").fetchone()[0] != "ok":
            sys.exit("database copy failed integrity check")
        return _read_library(db, zdir, lib)
    finally:
        if db is not None:
            db.close()
        remove_db_copy(copy)


def _read_library(db, zdir, lib):
    fl = {r[0]: r[1] for r in db.execute("select fieldID, fieldName from fields")}
    trash = {r[0] for r in db.execute("select itemID from deletedItems")}
    inlib = {r[0]: r[1] for r in db.execute("select itemID, key from items where libraryID=?", (lib,))
             if r[0] not in trash}
    # Papers are matched against the same item types the scanner treats as papers,
    # so the scanner, the import script and this check share one definition. A
    # saved webpage with a paper's title is not the paper: a journal-page save
    # once made a paper look present, and its PDF would never have been cleared.
    regular = {r[0] for r in db.execute(
        """select i.itemID from items i join itemTypes t using(itemTypeID)
           where i.libraryID=? and t.typeName in ('journalArticle','preprint','conferencePaper','book','bookSection','thesis','report','document','manuscript','magazineArticle','newspaperArticle')""", (lib,))}
    bykey = {k: i for i, k in inlib.items()}

    doi, title = {}, {}
    for iid, fid, val in db.execute("""select id.itemID, id.fieldID, idv.value from itemData id
                                       join itemDataValues idv on idv.valueID=id.valueID"""):
        if iid not in inlib or iid not in regular:
            continue
        if fl[fid] == "DOI":
            doi.setdefault(val.lower().strip(), set()).add(iid)
        elif fl[fid] == "title":
            title.setdefault(norm(val), set()).add(iid)

    storage, base = os.path.join(zdir, "storage"), base_attachment_path()
    pdfs = {}          # parent itemID -> [(stored?, fullpath, exists, size)]
    linked = set()     # every file any Zotero attachment links to, in any library
    for aid, parent, lm, path, ctype, akey in db.execute(
            """select ia.itemID, ia.parentItemID, ia.linkMode, ia.path, ia.contentType, i.key
               from itemAttachments ia join items i using(itemID)"""):
        if aid in trash or not path:
            continue
        if path.startswith("storage:"):
            full, stored = os.path.join(storage, akey, path[8:]), True
        elif path.startswith("attachments:"):
            full, stored = (os.path.join(base, path[12:]) if base else ""), False
        else:
            full, stored = path, False
        if not stored and full:
            linked.add(os.path.abspath(full))
        if parent in inlib and ctype == "application/pdf":
            ex = bool(full) and os.path.exists(full)
            pdfs.setdefault(parent, []).append((stored, full, ex, os.path.getsize(full) if ex else -1))
    return doi, title, bykey, pdfs, linked


def items_for(rec, doi, title, bykey):
    """Every item that could be this paper: by key if the scan recorded one, else
    by DOI and by title. More than one is normal (a paper saved twice), and only
    checking the first found is how a cleared file gets held back."""
    if rec.get("zotero_key"):
        k = bykey.get(rec["zotero_key"])
        return {k} if k is not None else set()
    md = rec.get("metadata") or {}
    return (doi.get((md.get("DOI") or "").lower().strip(), set())
            | title.get(norm(rec.get("title")), set()))


def in_cleared_root(path, roots=None):
    """Is this file inside one of the folders the skill is meant to clear?"""
    roots = CLEARED_ROOTS if roots is None else roots
    real = os.path.realpath(path)
    for r in roots:
        r = os.path.realpath(r)
        if real == r or real.startswith(r.rstrip(os.sep) + os.sep):
            return True
    return False


def plan_moves(man, verdict, linked, dest, any_root=False, roots=None):
    """Which files move, and why the others are held back. A file outside the
    cleared folders is held back unless any_root is set."""
    plan, held = [], {}
    roots = CLEARED_ROOTS if roots is None else roots
    outside = ("scanned from outside " + ", ".join(roots)
               + " (pass --any-root to move these too)")
    for r in man:
        if r["path"] not in verdict:
            continue
        ok, why = verdict[r["path"]]
        if ok and os.path.abspath(r["path"]) in linked:
            ok, why = False, "a Zotero attachment links to this file"
        if ok and not os.path.exists(r["path"]):
            ok, why = False, "file no longer at this path"
        if ok and not any_root and not in_cleared_root(r["path"], roots):
            ok, why = False, outside
        if ok:
            rel = os.path.relpath(r["path"], os.path.dirname(r["root"]))   # keeps Downloads/ or Desktop/
            plan.append({"from": r["path"], "to": os.path.join(dest, rel), "why": why,
                         "bytes": r["bytes"]})
        else:
            held[why] = held.get(why, 0) + 1
    return plan, held


def decide(rec, doi, title, bykey, pdfs):
    """Status names follow scan_and_identify.py: new, title only,
    already in Zotero (+ zotero_key, zotero_has_pdf), duplicate within this folder."""
    st = rec["status"]
    iids = items_for(rec, doi, title, bykey)
    if not iids:
        return False, "no matching item in Zotero"
    att = [a for i in iids for a in pdfs.get(i, [])]
    exact = any(s and ex and size == rec["bytes"] for s, _, ex, size in att)
    if st in ("new", "title only") or (st == "already in Zotero" and not rec.get("zotero_has_pdf")):
        if exact:
            return True, "stored copy of this exact file is in Zotero"
        return False, "Zotero has no stored copy of this file (import not run, or failed)"
    if st == "already in Zotero":
        if exact or any(ex and not full.startswith(CLEARED_ROOTS) for _, full, ex, _ in att):
            return True, "spare: Zotero already holds its own PDF of this paper"
        return False, "Zotero's copy is missing or lives in Downloads/Desktop"
    return False, "not a candidate"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", action="store_true")
    ap.add_argument("--any-root", action="store_true",
                    help="also move files scanned from folders other than Downloads and the "
                         "Desktop (see ZOTERO_IMPORT_CLEARED_ROOTS); without it they are held back")
    ap.add_argument("--lib", type=int, default=1)
    ap.add_argument("--dest", default=os.path.join(
        HOME, "Downloads", f"_Imported to Zotero {datetime.date.today().isoformat()}"))
    ap.add_argument("--scratch", default=tempfile.gettempdir(),
                    help="where the read-only copy of the Zotero database is made")
    a = ap.parse_args()
    log_p = os.path.join(a.outdir, "moves.json")

    if a.undo:
        moves = json.load(open(log_p))
        back = 0
        for m in moves:
            if os.path.exists(m["to"]) and not os.path.exists(m["from"]):
                os.makedirs(os.path.dirname(m["from"]), exist_ok=True)
                shutil.move(m["to"], m["from"])
                back += 1
        print(f"moved {back} of {len(moves)} files back")
        return

    man = json.load(open(os.path.join(a.outdir, "manifest.json")))
    doi, title, bykey, pdfs, linked = load_library(a.scratch, a.lib)

    verdict = {}
    for r in man:
        if r["status"] in ("new", "title only", "already in Zotero"):
            verdict[r["path"]] = decide(r, doi, title, bykey, pdfs)
    for r in man:
        if r["status"] == "duplicate within this folder":
            ok, why = verdict.get(r["dup_of"], (False, ""))
            verdict[r["path"]] = (ok, "duplicate of a cleared copy" if ok
                                  else "the copy it duplicates is not cleared")

    plan, held = plan_moves(man, verdict, linked, a.dest, a.any_root)

    reasons = {}
    for m in plan:
        reasons[m["why"]] = reasons.get(m["why"], 0) + 1
    if a.any_root:
        print("--any-root is set: files from outside " + ", ".join(CLEARED_ROOTS) + " may be moved.")
    print(f"cleared to move: {len(plan)}   ->   {a.dest}")
    for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"   {v:>5}  {k}")
    print(f"held back: {sum(held.values())}")
    for k, v in sorted(held.items(), key=lambda x: -x[1]):
        print(f"   {v:>5}  {k}")
    if any(k.startswith("scanned from outside") for k in held):
        print("   Files outside the cleared folders stay where they are; --any-root moves them.")
    json.dump(plan, open(os.path.join(a.outdir, "move-plan.json"), "w"), indent=1)

    if not a.apply:
        print("\nplan only. Rerun with --apply to move.")
        return

    moves = json.load(open(log_p)) if os.path.exists(log_p) else []
    done = bad = 0
    for m in plan:
        dst = m["to"]
        stem, ext = os.path.splitext(dst)
        k = 1
        while os.path.exists(dst):
            dst = f"{stem} ({k}){ext}"
            k += 1
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(m["from"], dst)
        if os.path.exists(dst) and os.path.getsize(dst) == m["bytes"] and not os.path.exists(m["from"]):
            moves.append({"from": m["from"], "to": dst})
            done += 1
        else:
            bad += 1
            print("CHECK:", m["from"])
    json.dump(moves, open(log_p, "w"), indent=1)
    print(f"\nmoved {done}, problems {bad}. Log: {log_p}  (undo with --undo)")


if __name__ == "__main__":
    main()
