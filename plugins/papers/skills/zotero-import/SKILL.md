---
name: zotero-import
description: "Create a Zotero collection from a folder of downloaded papers, with real metadata rather than filenames. Use whenever the user wants papers from a project folder, Downloads, or a scrape put into Zotero. Identifies each PDF from its embedded metadata, DOI, arXiv ID or first-page title (read locally; no full text goes to Claude), skips what is already in the library, and imports stored copies. Triggers include: 'add these papers to Zotero', 'make a Zotero collection from this folder', 'import these PDFs into Zotero', 'get this project's papers into my library', 'file these papers', 'put the papers from X into Zotero'."
---

# Zotero import

Turn a folder of downloaded PDFs into a proper Zotero collection: identified,
deduplicated against the existing library, and imported as stored copies with
real metadata.

## The problem this solves

Dragging a folder of PDFs into Zotero can leave items titled
`2504.13857v1.pdf` with no authors, no year and no DOI. This skill identifies
each paper first and imports it with real metadata, so the library does not
fill with orphans.

## Setup

What it needs:

- Zotero 7 or later, on the same machine as the library. It was built and tested
  against Zotero 10.0.5 on macOS. The generated script uses `IOUtils`, which
  Zotero 6 does not have, so Zotero 6 will not run it. The Linux profile and
  process locations are handled but untested. Windows has not been tried.
- No Zotero connector, no Better BibTeX and no API key. The scanner reads a
  copy of the local database file, and the import runs inside the Zotero
  application, so there is nothing to sign in to.
- Python 3 (tested with 3.10) and PyMuPDF, which reads page 1 of each PDF.
  Install it once into the plugin's data folder, which survives plugin updates
  (the plugin's own folder is replaced on each update):

  ```
  python3 -m venv "${CLAUDE_PLUGIN_DATA}/zotero-import-venv"
  "${CLAUDE_PLUGIN_DATA}/zotero-import-venv/bin/pip" install pymupdf
  ```

  The commands below use that environment's `python`. Nothing else is
  installed: the rest is the standard library.
- Internet access to Crossref, DataCite, OpenAlex, arXiv and Semantic Scholar.
  None needs an account, and no email address is sent.
- Optional: this plugin's `license-check`, which fills the Rights field of new
  items. Without it the field stays blank.

Settings, all optional, as environment variables in front of a command:

| Variable | Default | Meaning |
|---|---|---|
| `ZOTERO_DATA_DIR` | the data directory in Zotero's own settings, else `~/Zotero` | The folder holding `zotero.sqlite` and `storage/`. Zotero > Settings > Advanced > Files and Folders shows where it is. |
| `ZOTERO_IMPORT_CLEARED_ROOTS` | `~/Downloads` and `~/Desktop` | Folders that `verify_and_move.py` may clear. It moves only files inside them unless `--any-root` is passed. A PDF held by Zotero inside these folders does not count as Zotero's own copy. Separate multiple folders with `:`. |
| `ZOTERO_IMPORT_EXCLUDE` | none | A regular expression for `--bulk` scans. A file or folder name that matches is skipped without being opened. Use it for patterns of your own, such as a student-number format or a course code. It is case-sensitive unless it starts with `(?i)`. |

Keep each import's working files (manifest, cache, review, generated script) in
its own folder under `${CLAUDE_PLUGIN_DATA}/imports/`. It is called `<outdir>`
below.

## Hard constraints

These are operating constraints, not style preferences.

1. **Never write to `zotero.sqlite` in Zotero's data directory.** Reads go
   through a read-only copy of the database, which the scripts make. Writes are
   scripts for Zotero's Run JavaScript window, which execute inside Zotero: the
   dry run first, shown to the user, then live only after the user says go in
   chat. The user runs them by pasting (step 4).
2. **Additions only.** This skill creates collections, items and attachments,
   and may attach a stored PDF to an existing item that has none
   (`--attach-missing`). It must never merge, convert, move or delete an
   existing item. `Zotero.Attachments.convertLinkedFileToStoredFile` in
   particular destroys annotations unpredictably. Do not reach for it.
3. **Scope by `libraryID`.** A Zotero database holds the personal library
   (libraryID 1) and one library for each group the user belongs to. Never file
   anything into someone else's library. **For a shared project, ask which
   library before importing.** A co-authored reading list put into the personal
   library reaches nobody, and moving items between libraries afterwards is a
   copy in the Zotero UI, not something this skill may automate (see
   constraint 2). List the libraries and offer the group one:
   `select l.libraryID, g.name from libraries l left join groups g using(libraryID)`,
   run on a copy of the database. Pass the number to `make_import_js.py --lib N`,
   and to `scan_and_identify.py --lib N` and `verify_and_move.py --lib N` so
   that the duplicate check looks in the same library.
4. **Stored copies, never linked files.** `importFromFile` copies into Zotero's
   storage. Linked files break when the folder they point to is moved, renamed
   or no longer synced.
5. **Never put files into the data directory's `storage/` folder directly.**
   Let Zotero do it.
6. **Papers under peer review are off limits.** Many venues forbid LLM involvement in reviewing.
   In every mode, the scanner skips files named like conference submissions and folders named
   for reviewing or refereeing without opening them. It reads page 1 of every other PDF locally.
   It skips a PDF if that page has a review-manuscript marker (for example "Anonymous Authors",
   "For Peer Review" or "Manuscript ID", using the licence check's patterns) and no DOI or arXiv ID
   is found in the page-1 text, embedded metadata or file name. No skipped file's title is sent
   to a lookup service, and `make_import_js.py` never imports it. `review.md` lists the file name
   and reason only. These name and marker checks do not guarantee detection: a manuscript with
   an ordinary name and no marker passes, as does one with any DOI on page 1, including a cited
   work's DOI. Keep assigned-review PDFs out of scanned folders. If in doubt, ask.

## Licences: what Claude reads

The papers plugin keeps the full text of subscription papers away from Claude
and from every other AI service. This skill is built so that it never needs it.

- The scripts read each PDF's embedded metadata and page 1 locally, with
  PyMuPDF. Claude does not open the PDFs. What Claude sees is `review.md` and
  `manifest.json`: file names, statuses, titles, authors, DOIs, dates and
  abstracts that Crossref, DataCite, OpenAlex or arXiv returned.
- The scanner identifies a paper from its embedded metadata or a DOI or arXiv ID in the file name, metadata or
  page 1. If those are absent, it uses the title extracted from page 1. Only the identifier or title
  string leaves the machine, sent to bibliographic indexes, not AI services. Titles are limited
  to their first 200 characters before sending. Page text is never sent. With `--bulk`, files
  with no identifier and no sign of being papers are not looked up, so personal document titles
  are not sent over the network.
- When a file comes back `unidentified`, or `title only` with a doubtful title,
  do not read the PDF to find out what it is. Use the file name, ask the user,
  or search the web for a title you already have. If the user wants a paper
  read for some other purpose, the papers plugin's licence check decides
  (`license-check check <pdf>`), and it will refuse a subscription paper.
- New items get Zotero's Rights field from `license-check`, which reads the
  PDF's own licence statement, else the DOI's record, and sends only a DOI or
  arXiv ID to look a paper up. It is blank when the check is not installed or
  finds nothing.

## Procedure

### 1. Scan and identify

Close Zotero first so the database copy is complete. Check whether it is open with
`python3 "${CLAUDE_SKILL_DIR}/zotero_env.py" running`. Both the scanner and
`verify_and_move.py` delete their scratch database copies when they finish.

```
"${CLAUDE_PLUGIN_DATA}/zotero-import-venv/bin/python" "${CLAUDE_SKILL_DIR}/scan_and_identify.py" <folder> <outdir>
"${CLAUDE_PLUGIN_DATA}/zotero-import-venv/bin/python" "${CLAUDE_SKILL_DIR}/scan_and_identify.py" ~/Downloads <outdir> --also ~/Desktop --bulk
```

Walks the folder(s), drops the obvious non-papers (under 100 KB, under 4 pages,
figure, supplement and appendix files, `expenses/`, `node_modules/` and
friends), then for each survivor reads only the embedded metadata and page 1 to
find a DOI or arXiv ID, in the text, the metadata or the filename. Resolves an
arXiv ID through DataCite (arXiv's own API, then Semantic Scholar, as
fallbacks) and a DOI through Crossref, then falls back to a title search on
Crossref, DataCite and OpenAlex (OpenAlex covers NeurIPS, ICML and PMLR papers
that have no DOI). A title search accepts only 0.92 similarity, or containment
inside a padded page-1 title, and its match must also have one of its authors'
surnames on page 1.

Every resolution must find its own title on the file's page 1. (The one
exception: in project mode, an identifier found for a file with no text layer is
accepted with a note saying the title was not checked.) A DOI printed on
page 1 can belong to a cited work, or to the book a chapter came from, and a
title search can return a shorter, more generic title whose words all appear on
the page. `title_on_page` catches the first and `generic_match` the second.

`--bulk` is for folders that mix papers with everything else, such as
Downloads and the Desktop. It decides on the name alone, without opening the
file, to skip admin, HR and student material and anything that looks like a
submission under review (`12345_Title.pdf`, `..._paper_1234.pdf`, review and
conference folders). `ZOTERO_IMPORT_EXCLUDE` adds your own patterns to those.
And it never falls back to a bare page-1 title: in Downloads, a PDF with no
external record is a draft, a form or a student's work, and it stays where it
is.

Results are cached in `<outdir>/cache.json`, so an interrupted or partly
rate-limited scan resumes where it stopped. Failed lookups are not cached:
rerun the same command until `lookup failed` reaches zero.

Before any lookup, the scanner also skips PDFs with a review-manuscript marker on page 1 and no
DOI or arXiv ID (constraint 6). It then compares files with the existing library by DOI and
normalised title, and assigns these labels:

| Status | Meaning |
|---|---|
| `new` | resolved to an external record whose title is on page 1, and not already in the library |
| `title only` | project mode only: no external record, but a title was read from page 1. **Treat as suspect, not as done** (below) |
| `already in Zotero` | already in the library. `zotero_has_pdf` says whether Zotero holds a PDF it can open; if not, `--attach-missing` attaches this one |
| `duplicate within this folder` | another copy of a paper listed elsewhere in the scan; `dup_of` names the kept copy |
| `unidentified` | no external record whose title is on page 1 (in project mode, and no title readable from page 1 either). Excluded by default |
| `excluded` | `--bulk` only: never opened, decided on the name. `note` says why |
| `lookup failed` | a service did not answer (rate limit, network). Not cached; rerun |
| `skipped` / `unreadable` | Too short, not a readable PDF, or a possible manuscript under review (`review_manuscript` is set and `note` gives the reason). Never looked up or imported |

Writes `manifest.json` and `review.md`. Manifest records are
`{path, root, file, bytes, pages, status, title, note, via, metadata{itemType,title,creators,date,DOI,...}}`,
plus `zotero_key` and `zotero_has_pdf` on `already in Zotero` records and `dup_of`
on duplicates. Check those key names before writing a verification script
against it.

### 2. Show the user `review.md` and stop

Read the titles at this checkpoint, not just the counts. A result of `0 failed` can still include
duplicates or titles extracted from cover-sheet text.

Review every remaining `title only` record. The scanner retries Crossref with containment scoring
on the page-1 title and resolves most of them, but the rest still need checking. Many are published
papers with DOIs whose extracted titles include a JSTOR cover sheet, running header, citation line
or opening words of the abstract. Removing that text often resolves the paper in one Crossref
query. `review.md` flags titles that still appear to contain such text. Resolve those entries
before importing.

Name the files listed under "skipped: possible manuscripts under review" and leave them alone.
Do not open them to identify them.

`unidentified` is a three-way choice: exclude, include as-is, or resolve by
hand, and the third is usually right. These are mostly recognisable papers, and
what an index cannot find (a poorly indexed journal, say) can be entered by hand
from the file name or the user's own knowledge. Offer all three, and say which
files they are, because "six unidentified" invites "ignore them" while naming
the files does not. Do not open the PDFs to find out (see "Licences" above).

Unpublished drafts, internal notes and student work will nearly all come back as
`title only`. That is the correct answer for them, not a failure.

Say plainly how many are already in the library; that number is often most of
the folder, and it saves the user importing a pile of duplicates.

### 3. Generate the import script

```
"${CLAUDE_PLUGIN_DATA}/zotero-import-venv/bin/python" "${CLAUDE_SKILL_DIR}/make_import_js.py" <outdir> "Collection name"
"${CLAUDE_PLUGIN_DATA}/zotero-import-venv/bin/python" "${CLAUDE_SKILL_DIR}/make_import_js.py" <outdir> "" --plan <outdir>/collections-plan.json --attach-missing
```

Add `--include unidentified` only if the user asked for it. `--plan` is a JSON
map from file path to collection path (`"Reinforcement learning/Offline RL"`,
nested with `/`), for filing one import into several collections. Papers it
does not mention go into the named collection, or stay unfiled if the name is
`""`. `--attach-missing` adds the file's PDF to items already in Zotero that
have none. A manifest record may carry a `tags` list, and each new item gets
those tags; the dry run prints them. Use it for provenance when items go in
unfiled (for example `source: Papers/Reading`). New items get Zotero's Rights
field from `license-check` (see "Licences" above), unless the manifest already
sets `rights`.

Set tags, exclusions and hand-fixed metadata in a `patches.py` beside the scan,
keyed by filename, and rerun it after every scan, because a rescan rewrites
`manifest.json` and would silently drop hand edits. It is a short script the
session writes for each import. For example:

```python
import json, os, sys, unicodedata
path = os.path.join(sys.argv[1], "manifest.json")      # <outdir>
man = json.load(open(path))
nfc = lambda s: unicodedata.normalize("NFC", s)         # file names can be NFD
for r in man:
    name = nfc(r["file"])
    if name == "meeting-notes.pdf":
        r["status"], r["note"] = "excluded", "not a paper"
    elif name.startswith("Smith 2021"):
        r["force"] = True                               # same title as a different work in the library
    elif name.startswith("Reading group"):
        r["tags"] = ["source: reading group"]
json.dump(man, open(path, "w"), indent=1)
```

The generated script is idempotent. A paper whose DOI or title is in the target
library at run time is skipped, an item that has gained a PDF since the scan is
left alone, and collections are reused by name under the same parent. Running
it twice, or after a sync has brought items in, duplicates nothing.

### 4. Run it: dry run, then live on the user's word

Zotero must be open for this step. Ask the user to open `<outdir>/import.js`, copy its contents,
then choose Tools > Developer > Run JavaScript in Zotero, paste, tick "Run as async function"
and run it. The generated script is a dry run (`const DRY_RUN = true;`) and changes nothing.
Before they run it, predict the counts from the live library so that any mismatch is apparent.
Ask them to paste the report back. Only after the user says go in chat, ask them to change the
line to `const DRY_RUN = false;` and run it again. If a tool in your setup can run JavaScript
inside Zotero, follow the same rules: dry run first, live only on the user's go in chat.

If PDF attachment fails for an item the script has just created, the script moves that new item
without a PDF to the Trash and reports this on its `FAIL` line. A rerun can then add the paper
properly. This cleanup was checked with a simulated failure, not in live Zotero. If a `FAIL` line
says the item could not be removed, find items without attachments in the target collection or
under the import's tag, and trash them.

Assess whether a backup is needed and tell the user.

- A plain import into a newly created collection needs no backup. Undo it with Delete Collection
  and Items, which moves the new items to the Trash. If the dry run says the collection already
  exists, deleting it would also trash its earlier items. In that case, undo using the import's
  tag or Date Added.
- Give unfiled imports a tag, as there is no collection to delete. Undo using the `source:` tag
  assigned by the patch file (select it in Zotero), or sort by Date Added and trash the new items.
- Back up before using `--attach-missing`. It adds PDFs to existing library items, so deleting a
  collection does not undo it.
- Back up before any operation that edits or merges existing items. This skill does neither.

Back up while Zotero is running. Never ask the user to quit it for the backup. Run
`await Zotero.DB.backUpDatabase({suffix: "<name>", force: true})` in Run JavaScript, then run
`pragma integrity_check` on `<data directory>/zotero.sqlite.<name>.bak`.

### 5. Verify against the database, not the script's own output

Check the result independently of the script's success count and annotations-before-and-after
line. Both are necessary but insufficient. After the run, close Zotero as in step 1, take a fresh
copy of `zotero.sqlite` and check:

- the collection exists and holds the expected number of items
- every new item has a title that is not a filename, and an attachment whose
  file is present in the data directory's `storage/` folder
- the library-wide annotation count is unchanged

"0 failed" means no exception was thrown. It does not mean the operation did
what it was for.

### 6. Clearing the source folder (Downloads, the Desktop)

Close Zotero for this step. `verify_and_move.py` refuses to run while it is open.

```
"${CLAUDE_PLUGIN_DATA}/zotero-import-venv/bin/python" "${CLAUDE_SKILL_DIR}/verify_and_move.py" <outdir>            # plan only
"${CLAUDE_PLUGIN_DATA}/zotero-import-venv/bin/python" "${CLAUDE_SKILL_DIR}/verify_and_move.py" <outdir> --apply    # move
"${CLAUDE_PLUGIN_DATA}/zotero-import-venv/bin/python" "${CLAUDE_SKILL_DIR}/verify_and_move.py" <outdir> --undo     # put back
```

The script checks each scanned file against a fresh database copy. It moves only files Zotero
now holds to `~/Downloads/_Imported to Zotero <date>/`, unless `--dest` specifies another folder,
and preserves their original subpaths. A file is cleared only if Zotero has a stored attachment
of exactly its size (for imported and attached files), already had its own PDF outside the
cleared folders (for spares), or the file duplicates a cleared copy. A file is never cleared if any Zotero attachment links to it.

The script moves only files in Downloads and the Desktop, or the folders set by
`ZOTERO_IMPORT_CLEARED_ROOTS`. It holds back records scanned from other folders, including project
and staging folders, and reports their count in the plan. `--any-root` removes this restriction.
Only the user should decide to use it.

Run the plan-only command first. Show the user how many files would move, why each group is
cleared, and which files are held back and why. Run `--apply` only after the user says go in chat.
Approval for the import (step 4) does not authorise moving files. Nothing is deleted. The user
empties the holding folder when satisfied, and every move is logged to `moves.json`.

## Pitfalls

Follow these rules when running the skill. Each includes the reason for the instruction.

### Reading the file

- Search file names as well as text and embedded metadata for identifiers. In
  `Smith_2026_Example_arXiv-2607.01736.pdf`, the arXiv ID may appear only in the file name.
- Remove rotated lines and text against the left edge before using the largest text on page 1
  as the title. arXiv's submission stamp is printed vertically in the margin, often in the
  largest font. It is never the title.
- Treat every page-1 title as suspect. Extraction can include JSTOR cover sheets, running
  headers, citation lines and the opening words of abstracts. Check containment with
  `crossref_by_title(..., loose=True)` as well as similarity. The real title may be contained
  exactly within a longer extracted string that scores poorly on similarity.
- Treat a resolved title much shorter and more generic than the page-1 string as a wrong match
  until checked (`generic_match`). A title such as "Model-Based Reinforcement Learning" may
  match part of a longer title. All its words can appear on page 1, so `title_on_page` cannot
  detect the error.
- Match an author's whole surname as a phrase, never individual words from it. A conference
  listed as a creator may contain words such as "agents" and "systems", which appear on page 1
  of many papers.
- When matching surnames on page 1, allow one trailing letter for surnames of five letters or
  more, and trailing digits for any surname. Elsevier-style layouts print affiliation markers
  inline ("Smitha"). Shorter surnames must match exactly, as "lev" plus two letters is "level".
- Use letter boundaries in name rules, never `\b`. Underscores count as word characters, so
  `\bstatement\b` misses `acct_Statement_2025.pdf` and `\bpaper\d+` misses
  `CONF2025_paper_1234.pdf`.
- Test every name rule against real paper names. Substring rules can exclude real papers:
  `memo` matches "memory", `transcript` matches "transcription", `marks` matches "benchmarks",
  and `ticket` matches "The Lottery Ticket Hypothesis". A case-insensitive student-number
  pattern can match "Attention2017". After any rule change, and after setting
  `ZOTERO_IMPORT_EXCLUDE`, run `python3 "${CLAUDE_SKILL_DIR}/test_rules.py"` before a bulk scan.
  Add any new incorrect exclusion to its lists. Name-rule tests need no library or PDFs.
- Keep the resolution check in bulk scans. Name rules prevent some files from being opened,
  which matters for papers under review, but cannot catch everything. A liability waiver or
  examiner's report is prevented from being imported because it has no external record whose
  title appears on its first page.
- Normalise file names on both sides of a patch match with `unicodedata` (NFC). Cloud-synced
  folders may use decomposed (NFD) accents, so a patch keyed on "Müller" typed in NFC will not
  match without normalisation.

### Looking papers up

- Query DataCite first for an arXiv ID. Every arXiv paper has the DataCite DOI
  `10.48550/arXiv.<id>`. `api.datacite.org` returns its title, authors, date and abstract in under
  a second. arXiv's API allows one call per 3 s and can be much slower. Use it and Semantic
  Scholar (`/graph/v1/paper/ARXIV:<id>`) as fallbacks.
- Space arXiv PDF downloads 3 s apart when staging requires them (see arxiv-fetcher). Downloads
  and API queries share a rate budget, so rapid downloads can cause later lookups to return
  "Rate exceeded." If several files with arXiv IDs in their names return `title only` or
  `unidentified`, suspect rate limiting, not missing metadata. The scanner retries after
  10, 20, then 40 s, or the server's `Retry-After`, before using Semantic Scholar as a fallback.
- Treat both rate-limit responses as failed lookups: a 200 response with a "Rate exceeded."
  body, and HTTP 429. Give failures their own status and never cache them, or the paper remains
  recorded as unidentified. When arXiv is rate-limited, Semantic Scholar often is too.
- Do not quote the title in an arXiv API `ti:` query. `search_query=ti:"some title"` returns zero
  results without an error. Use an unquoted query, which ranks results loosely, and accept
  matches only after checking title similarity.
- Read each free service's rate-limit headers before choosing concurrency. Crossref's anonymous
  pool returns `x-rate-limit-limit: 1`, `x-rate-limit-interval: 1s` and `x-concurrency-limit: 1`.
  A second simultaneous request receives 429. The faster "polite pool" requires an email in
  every request, so do not add one without asking the user. OpenAlex permits roughly a hundred
  anonymous searches a day, then returns 429 with a `Retry-After` of hours. The scanner limits
  concurrency per host and spaces requests. It treats a `Retry-After` over two minutes as
  "closed for this run" and does not wait that long.
- Do not use DBLP as a source or work around its bot detection. It returns a proof-of-work
  "not a bot" page to scripts.
- In DataCite title searches, accept arXiv records first, then paper types only. Remove
  `Organizational` creators. DataCite also registers talks, slides and datasets under paper
  titles, and a conference talk recording is not the paper.
- Query each source (Crossref, DataCite, OpenAlex) in turn until one verifies the paper. Do not
  stop at the first candidate: a wrong top result can end the search, leaving a cached
  negative result.
- Treat "no match" as provisional unless every source was queried. If OpenAlex was not queried
  because its quota was exhausted, return `lookup failed` so the next run retries. Otherwise,
  a paper found only there, such as a conference extended abstract, would remain cached as
  unidentified.
- Run name-based exclusion rules before checking the cache. The cache key includes path, size,
  modification time and mode. If the cache were checked first, a tightened rule would not be
  applied to cached files. The review-manuscript check requires page 1, so it runs after the
  cache lookup. The key therefore also includes `RULES_VERSION`. Raise `RULES_VERSION` in
  `scan_and_identify.py` whenever that kind of rule changes, so old results are checked again.

### Deduplicating

- Use the same definition of "a paper already in the library" in the scanner, import script
  and verifier: items of the scanner's paper types, excluding attachments, notes and other
  item types. Matching every database title roughly doubles the titles checked and can skip
  real papers as "already in Zotero". Different definitions can make a saved webpage with a
  paper's title count as new to the scanner but present to the import script, leaving the
  PDF in Downloads indefinitely. The verifier checks every matching paper item, not only
  the first.
- When a paper appears several times, group copies by title and keep the record with the
  identifier. Otherwise, you may import the copy with the poorest metadata and discard the
  better one.
- Group duplicates by fuzzy matching of final titles across statuses. A DOI-resolved copy may
  have the title "Thermodynamics of Prediction" while another has the page-1 title
  "The thermodynamics of prediction". Normalisation does not repair OCR errors such as
  "ar+ficial". Two different DOIs prevent a merge, keeping "Part I" and "Part II" separate.
- Check the existing item's authors when a file is skipped solely because of a generic title,
  such as "Quantum Field Theory". If it is a different work, set `"force": true` on the manifest
  record in `patches.py`. Also check before adding another copy: a book already held under a
  short or garbled title, such as "Active inference", may not be recognised, allowing a third
  copy to be added.
- Exclude a file in the patch file after importing it as a non-paper type such as `blogPost`
  or `webpage`. The duplicate check does not include these types, so a later dry run offers
  to add the item again. Before every rerun, predict the dry-run count from the live library
  so that a mismatch is apparent.
- Treat the duplicate check as current only at the time of the scan. Opening Zotero can sync
  new items, and a previously generated script may already have been run live. If either has
  happened, rescan or reconcile before running. Otherwise, the import duplicates items and
  can create a second collection with the same name.

### Choosing what to import

- Report off-topic titles found at the checkpoint to the folder's owner, and exclude them.
  Silent exclusion leaves mistaken downloads in the project folder.
- Use a verified bibliography in preference to every scanner heuristic. If the project has a
  `refs.bib` checked against Crossref or another index (reference-verifier does this), "the project's papers"
  usually means its citation list. Intersect the folder's arXiv IDs with the bib's eprint fields
  to distinguish project papers from unrelated reading. Offer to fetch the bibliography's PDFs
  by ID with arxiv-fetcher, and patch the manifest from the bib rather than Crossref title
  matches. Account for these parsing problems: fields may be double-quoted rather than braced,
  and nested maths braces in a title (`${\cal N}=4$`) break naive field regexes. Read such an
  entry with plain grep and patch that record literally. Old-style `hep-th/NNNNNNN` IDs contain
  a slash. Substitute it before using the ID as a file name, or curl writes into a nonexistent
  directory.
- If a project contains arXiv source directories, fetch the paper PDFs by ID into staging.
  Those directories contain only `.tex` files and figure PDFs, with the identifier in the
  directory name. The junk filter correctly excludes figure PDFs. Their presence does not
  mean the paper PDFs are on disk.
- Stage papers from several project folders together, as they are usually spread across
  folders. Hardlink them into one staging folder with `ln src dst`, falling back to `cp`, and
  scan it. Hardlinks need no extra disk space and leave originals untouched; one scan gives
  one manifest and one collection. Keep staging somewhere durable. Delete it only after the
  live import has run and step 5 has checked the result, as the import script reads staged
  paths. `verify_and_move.py` operates on staged copies, not originals. It holds them back
  unless `--any-root` is passed, as staging is outside Downloads and the Desktop. Before
  deleting a hardlinked staged file, check that `stat -f %l` on macOS, or `stat -c %h` on Linux,
  gives a link count above 1, showing that the original remains.
- Keep every file named by the generated script in a durable location. The script contains
  absolute paths and is run manually later. If a staging folder under `/tmp` has been cleared
  by then, every import fails. `make_import_js.py` refuses to generate from `/tmp`,
  `/private/tmp` or `/var/folders`.

### Verifying

- Count annotations independently before and after import, using the same query on both
  database copies. Do not use the script's number as your reference. The script counts only
  the target library, while `select count(*) from itemAnnotations` counts every personal and
  group library. Use a pre-import copy for the first count. Comparing different scopes can
  falsely suggest that annotations were lost.
- Read the database only through `snapshot_db()`. Zotero 10 uses WAL mode, so recent writes
  may be in `zotero.sqlite-wal`. Copying `zotero.sqlite` alone can give a stale snapshot and
  falsely report new papers as missing. `snapshot_db()` copies the database with its `-wal`
  and `-shm` files, then checkpoints the copy. Copy all three files for backups too. Never write to the live files; only read them.
- Check a folder for review material before using it as a test fixture. Scans read each PDF's
  first page and print its title, which would expose review assignments. In every mode, the
  checks cover submission-style names, folders named `reviews`, `referee` or `reviewing`, and
  review markers on page 1. Build fixtures in a scratch folder using papers already public.
- Read the scripts and check their modification times before rewriting them. Take a copy
  first, then merge changes rather than replacing the scripts. Another session may have added
  the Semantic Scholar fallback, title cleaning, containment matching or fuzzy deduplication.
  A rewrite from memory could remove those fixes.

## Notes

- Lookups use a worker-thread pool (`--workers`, default 6). Minimum gaps per host are 3.1 s
  for arXiv, as requested, 1.1 s for Semantic Scholar and 0.12 s for OpenAlex. PDF reading
  remains on the main thread because PyMuPDF is not thread-safe. A large Downloads scan can
  take hours. Tell the user how long it will take before starting.
- The cache is written by write-then-rename, so killing a scan cannot truncate
  it. Run long scans in the background with their output sent to a log file (on
  macOS under `caffeinate -i`, so the Mac does not sleep); an empty log means
  "not finished", never "died".
- Crossref is not given an email address. Do not add one without asking the
  user.
- Zotero must be closed for steps 1, 5 and 6, and open for step 4. The scanner checks the
  integrity of its database copy and stops if the check fails. `verify_and_move.py` refuses
  to run while Zotero is open.
- Check whether Zotero is running with
  `python3 "${CLAUDE_SKILL_DIR}/zotero_env.py" running`. It prints "Zotero is running" or
  "Zotero is not running" and exits 0 when running. `verify_and_move.py` uses the same helper.
  A plain `ps | grep -i zotero` can give false positives from folder names.
