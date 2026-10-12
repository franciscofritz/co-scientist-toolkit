#!/usr/bin/env python3
"""Scan folders for papers, identify them, and check them against Zotero.

Read-only with respect to Zotero: copies zotero.sqlite and opens the copy in
SQLite read-only mode. Writes only into the output directory.

    Project folder:     scan_and_identify.py <folder> <outdir> [--lib 1]
    Downloads/Desktop:  scan_and_identify.py ~/Downloads <outdir> --also ~/Desktop --bulk

The Zotero data directory is found from ZOTERO_DATA_DIR, else Zotero's own
setting, else ~/Zotero (see zotero_env.py).

Produces manifest.json (machine) and review.md (for the human to check before
anything is written to Zotero).

--bulk is for folders that mix papers with everything else. It never opens a
file whose name or folder marks it as admin, student material or a possible
paper under review. It accepts a paper only if it resolves to an external
record (DOI, arXiv id, or a Crossref/DataCite/OpenAlex title match) whose title is
printed on the file's own first page, and it never falls back to a bare
page-1 title. For papers already in Zotero it records whether Zotero holds a
PDF it can open, which decides whether the local copy may go.

Resumable: results are cached in <outdir>/cache.json by path, size and mtime.
A lookup that failed (rate limit, network) is not cached, so a rerun retries it.

Only a DOI, an arXiv id or a title string is sent to the bibliographic services
(Crossref, DataCite, OpenAlex, arXiv, Semantic Scholar), and a title is cut to its
first 200 characters. PDF text stays on this machine, and nothing here sends a
paper's text to an AI service. A PDF whose first page carries a review-manuscript
marker and which has no DOI or arXiv id is skipped before any lookup, so its title
goes nowhere.
"""
import argparse, difflib, importlib.util, json, os, re, shutil, sqlite3, sys, tempfile, time, unicodedata
import urllib.error, urllib.parse, urllib.request
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zotero_env import base_attachment_path, cleared_roots, data_dir, remove_db_copy

UA = "zotero-import/2.0 (Claude Code co-scientist-toolkit plugin)"
MIN_BYTES = 100_000          # below this it is a figure, a form or a fragment
MIN_PAGES = 4
CLEARED_ROOTS = cleared_roots()
MAX_TITLE_QUERY = 200        # characters of a title sent to any lookup service
# Bump when a rule that decides from the file's own contents changes, so results
# cached under the older rule are looked at again (the cache key includes it).
RULES_VERSION = 2


def query_text(title):
    """The part of a title that may leave this machine: its first 200 characters.
    Every title query to Crossref, DataCite and OpenAlex goes through this. A title
    is compared in full after the answer comes back; only the query is cut."""
    return (title or "")[:MAX_TITLE_QUERY]

JUNK_DIR = re.compile(r"/(node_modules|\.git|__pycache__|venv|\.venv|site-packages|"
                      r"expenses?|receipts?|Library/Caches|\.Trash|_Imported to Zotero[^/]*)/", re.I)
JUNK_NAME = re.compile(r"(^(fig\d|figure[-_ ]?\d|table[-_ ]?\d|plot|chart|logo|supplementary[-_ ]?fig)"
                       r"|moesm|_esm\b|supplement|appendi(x|ces))", re.I)

# --bulk only: decided on the name alone, and the file is never opened.
# Conference systems deliver submissions as <id>_<Title>.pdf, and a small
# workshop's ids start at 1, so one digit counts ("4_Planning_Under_...pdf"). A leading
# 19xx_/20xx_ is a year, as in ZotFile names, and does not count.
# Boundaries are letter boundaries, not \b. Filenames separate words with "_"
# as often as with spaces, and "_" is a word character, so \bstatement\b misses
# "acct_Statement_2025.pdf" and \bpaper\d+ misses "CONF2025_paper_1234.pdf".
# Letter boundaries also keep "memo" out of "memory", "transcript" out of
# "transcription" and "marks" out of "benchmarks", each of which would drop
# real papers. And no bare "ticket": that excludes the Lottery Ticket Hypothesis.
def _words(*ws):
    return r"(?<![A-Za-z])(" + "|".join(ws) + r")(?![A-Za-z])"


REVIEW_NAME = re.compile(r"^(?!(19|20)\d{2}_)\d{1,6}_[A-Za-z]"
                         r"|(?<![A-Za-z])(paper|submission)[_ -]?\d{2,5}(?!\d)", re.I)
REVIEW_DIR = re.compile(r"review|referee|submission|supplementary|openreview|neurips|"
                        r"aaai|ijcai|aistats|rejected_papers|camera.?ready|" + _words("icml", "iclr"),
                        re.I)
ADMIN_DIR = re.compile(r"expense|receipt|invoice|application|recommendation|assignment|marked|"
                       r"candidate|travel|finance|passport|contract|payslip|salary|booking|"
                       r"tutorial|examin|honours|admission|interview|evaluation|feedback|"
                       r"screenshots|payment|shortlist|logistics|poster|brand|^\d{5,}$|"
                       + _words("forms?", "statements?", "transcripts?", "claims?", "tax", "bank", "visa",
                                "quotes?", "memos?", "exams?", "tests?", "tut", "cv"), re.I)
ADMIN_NAME = re.compile(r"invoice|receipt|passport|boarding|itinerary|certificate|payslip|"
                        r"recommendation|booking|confirmation|assignment|contract|agreement|"
                        r"liability|examiner|report card|course[ _]evaluation|^gmail - |adobe scan|logistics|"
                        r"poster|brand guide|payment|"
                        r"^\S+[ _]feedback(?![A-Za-z])|"
                        r"(?<![A-Za-z])tut(orial)?[ _-]*\d|"
                        r"(claim|consent|registration|leave|slip|order|payment|request|nomination)"
                        r"[ _-]+form(?![A-Za-z])|"
                        r"(?<![A-Za-z])application[ _](for|form|checklist|letter)(?![A-Za-z])|"
                        r"(?<![A-Za-z])letters[ _]of(?![A-Za-z])|"
                        + _words("statement", "memo", "transcripts?", "letter", "cv", "resume",
                                 "quote", "minutes", "agenda", "proposal", "claims?", "visa",
                                 "marks?", "uber"), re.I)
# Patterns of your own for --bulk, from ZOTERO_IMPORT_EXCLUDE: a student-number
# format, a course code, an HR form prefix. Matched against file names and folder
# names, case-sensitively unless the pattern starts with (?i). Test a pattern
# against real paper names before relying on it (see test_rules.py): a
# case-insensitive student-number pattern once dropped "Attention2017".
def _extra_exclude():
    pat = os.environ.get("ZOTERO_IMPORT_EXCLUDE", "").strip()
    try:
        return re.compile(pat) if pat else None
    except re.error as e:
        sys.exit(f"ZOTERO_IMPORT_EXCLUDE is not a valid regular expression: {e}")


EXTRA_EXCLUDE = _extra_exclude()

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
ARX_TEXT = re.compile(r"ar[Xx]iv[-:_\s]*(\d{4}\.\d{4,5})")
ARX_BARE = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?\b")
# page furniture that is never a title: arXiv stamps, subject classes, licences
STAMP = re.compile(r"(ar[Xx]iv[:\s]*(submit|\d{4}\.\d{4,5})|\[(cs|stat|math|physics|q-bio|eess)\."
                   r"|creativecommons|doi\.org|©|\bpreprint\b.*\bunder review\b)", re.I)

CROSSREF_TYPES = {"journal-article": "journalArticle", "proceedings-article": "conferencePaper",
                  "posted-content": "preprint", "book-chapter": "bookSection", "book": "book",
                  "report": "report", "dissertation": "thesis"}


# ---------------------------------------------------------------- network

class LookupFailed(Exception):
    """The service did not answer. Kept distinct from "no such record": a rate
    limit that reads as "not found" files a paper as unidentified, and once
    cached it would never be retried. Seen twice, with two different shapes of
    rate limit (a "Rate exceeded." body, and an HTTP 429)."""


_down = {}   # host -> time until which it is treated as unavailable
# Minimum gap between calls to one host, enforced across worker threads.
# arXiv asks for one call every 3 s; OpenAlex allows 10 a second.
_PACE = {"export.arxiv.org": 3.1, "api.semanticscholar.org": 1.1,
         "api.openalex.org": 0.12, "api.crossref.org": 1.0,
         "api.datacite.org": 0.1}
# Services cap concurrent requests as well as their rate. Crossref's anonymous
# pool says so in its headers (x-rate-limit-limit: 1 per 1s,
# x-concurrency-limit: 1) and answers a second simultaneous request with 429:
# ten workers were eight over, and all of them sat in backoff.
_CONC = {"api.crossref.org": 1, "export.arxiv.org": 1,
         "api.semanticscholar.org": 1, "api.openalex.org": 2, "api.datacite.org": 4}
_sems = {}


def _sem(host):
    with _glock:
        return _sems.setdefault(host, threading.BoundedSemaphore(_CONC.get(host, 4)))
_last, _locks, _glock = {}, {}, threading.Lock()


def _pace(host):
    gap = _PACE.get(host, 0)
    if not gap:
        return
    with _glock:
        lk = _locks.setdefault(host, threading.Lock())
    with lk:
        wait = _last.get(host, 0) + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[host] = time.time()


def get(url, timeout=25, tries=4):
    host = urllib.parse.urlsplit(url).netloc
    if _down.get(host, 0) > time.time():
        raise LookupFailed(f"{host} unavailable until {time.strftime('%H:%M', time.localtime(_down[host]))}")
    delay = 10
    for attempt in range(tries):
        try:
            with _sem(host):                      # released before any backoff sleep
                _pace(host)
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = r.read().decode("utf-8", "replace")
            if "Rate exceeded" in body[:300]:
                raise urllib.error.HTTPError(url, 429, "Rate exceeded", None, None)
            _down.pop(host, None)
            return body
        except urllib.error.HTTPError as e:
            if e.code in (400, 404, 410):
                return ""                                  # a real "no such record"
            ra = e.headers.get("Retry-After") if e.headers else None
            ra = int(ra) if ra and str(ra).isdigit() else None
            if e.code == 429 and ra and ra > 120:
                # A quota, not a burst. OpenAlex meters anonymous use (about
                # a hundred searches a day) and
                # answered with a Retry-After of hours.
                # Sleeping on that parks every worker; close the host instead.
                _down[host] = time.time() + ra
                raise LookupFailed(f"{host} quota exhausted; reopens in {ra // 3600}h{(ra % 3600) // 60:02d}m")
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(ra if ra else delay)
                delay *= 2
                continue
            _down[host] = time.time() + 600
            raise LookupFailed(f"HTTP {e.code} from {host}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            _down[host] = time.time() + 600
            raise LookupFailed(f"{type(e).__name__} from {host}")
    raise LookupFailed(f"no answer from {host}")


def getjson(url):
    body = get(url)
    return json.loads(body) if body.strip() else None


def _save(obj, path):
    """Write-then-rename, so a kill mid-write cannot leave a truncated file."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def similar(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


# ---------------------------------------------------------------- the library

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


def library_index(scratch, lib):
    """Everything already in the chosen library, by DOI and by title, and for
    each item whether Zotero holds a PDF it can open. A PDF only counts if the
    file exists outside the cleared roots (Downloads and the Desktop unless
    ZOTERO_IMPORT_CLEARED_ROOTS says otherwise), which are what --bulk clears.

    The scratch copy of the database is deleted before this returns, also when
    it stops on an error: it holds the whole library and nothing needs it later."""
    zdir = data_dir()
    src = os.path.join(zdir, "zotero.sqlite")
    copy = os.path.join(scratch, "z_import_check.sqlite")
    db = None
    try:
        snapshot_db(src, copy)
        db = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
        if db.execute("pragma integrity_check;").fetchone()[0] != "ok":
            sys.exit("zotero.sqlite copy failed integrity check - close Zotero and retry")
        return _read_index(db, zdir, lib)
    finally:
        if db is not None:
            db.close()
        remove_db_copy(copy)


def _read_index(db, zdir, lib):
    fl = {r[0]: r[1] for r in db.execute("select fieldID, fieldName from fields")}
    trash = {r[0] for r in db.execute("select itemID from deletedItems")}
    BIBTYPES = ('journalArticle', 'preprint', 'conferencePaper', 'book', 'bookSection', 'thesis',
                'report', 'document', 'manuscript', 'magazineArticle', 'newspaperArticle')
    qmarks = ",".join("?" * len(BIBTYPES))
    inlib = {r[0]: r[1] for r in db.execute(
        f"""select i.itemID, i.key from items i join itemTypes t using(itemTypeID)
            where i.libraryID=? and t.typeName in ({qmarks})""", (lib, *BIBTYPES))
        if r[0] not in trash}

    storage, base = os.path.join(zdir, "storage"), base_attachment_path()
    has_pdf = set()
    for aid, parent, path, ctype, akey in db.execute(
            """select ia.itemID, ia.parentItemID, ia.path, ia.contentType, i.key
               from itemAttachments ia join items i using(itemID)"""):
        if aid in trash or parent not in inlib or ctype != "application/pdf" or not path:
            continue
        if path.startswith("storage:"):
            full = os.path.join(storage, akey, path[8:])
        elif path.startswith("attachments:"):
            full = os.path.join(base, path[12:]) if base else ""
        else:
            full = path
        if full and os.path.exists(full) and not full.startswith(CLEARED_ROOTS):
            has_pdf.add(parent)

    dois, titles = {}, {}
    for iid, fid, val in db.execute("""select id.itemID, id.fieldID, idv.value from itemData id
                                       join itemDataValues idv on idv.valueID=id.valueID"""):
        if iid not in inlib:
            continue
        rec = {"key": inlib[iid], "has_pdf": iid in has_pdf}
        if fl[fid] == "DOI":
            dois[val.lower().strip()] = rec
        elif fl[fid] == "title":
            titles[norm(val)] = rec
    colls = sorted(r[0] for r in db.execute(
        "select collectionName from collections where libraryID=?", (lib,)))
    return dois, titles, colls


# ---------------------------------------------------------------- the file

def pdf_probe(path):
    """Embedded metadata, page count, and the text of page 1. Never more."""
    import fitz
    d = fitz.open(path)
    meta = d.metadata or {}
    pages = d.page_count
    text = d[0].get_text()[:8000] if pages else ""
    d.close()
    return meta, pages, text


def title_from_page1(path):
    """The largest text on page 1 is almost always the title. Local only: no lookup."""
    import fitz
    try:
        d = fitz.open(path)
        page = d[0]
        W = page.rect.width
        spans = []
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                # arXiv stamps the submission id vertically down the left margin.
                # It is often the largest text on the page and is never the title.
                if abs(l.get("dir", (1, 0))[0]) < 0.9:
                    continue
                for sp in l.get("spans", []):
                    t = sp["text"].strip()
                    if not t or STAMP.search(t):
                        continue
                    if sp["bbox"][2] < W * 0.12:      # hugging the left edge
                        continue
                    spans.append((round(sp["size"], 1), sp["bbox"][1], t))
        d.close()
    except Exception:
        return ""
    if not spans:
        return ""
    top = max(s[0] for s in spans)
    title = re.sub(r"\s+", " ", " ".join(t for sz, y, t in sorted(spans, key=lambda x: x[1])
                                          if sz == top)).strip()
    if len(title) < 20 or len(title) > 300:
        return ""
    if re.match(r"(?i)^(abstract|introduction|contents|preprint|submitted)\b", title):
        return ""
    if STAMP.search(title) or len(re.findall(r"[A-Za-z]{3,}", title)) < 3:
        return ""
    return title


# A page-1 title is very often not a title. Old scans, JSTOR cover sheets and
# running headers all get picked up, and the result reads like metadata while
# being useless. Most "title only" records of published papers come from page-1
# extraction polluted this way.
DIRTY = re.compile(r"(?i)(author\(s\)|\bsource\s*:|\bresearch (paper|article)\b|"
                   r"\babstract\b|\bdownloaded from\b|\ball use subject\b|jstor|"
                   r"^\s*\d{1,2}\s*[.)]\s+|\bvol\.?\s*\d+|\bpp?\.\s*\d+)")


def clean_title(t):
    """Strip the furniture that page-1 extraction drags in with a title."""
    if not t:
        return t
    t = re.sub(r"(?i)\bauthor\(s\).*$", "", t)         # JSTOR cover sheet
    t = re.sub(r"(?i)\bsource\s*:.*$", "", t)
    t = re.sub(r"(?i)^\s*research (paper|article)\b[:\s-]*", "", t)
    t = re.sub(r"(?i)\babstract\b.*$", "", t)          # title ran into the abstract
    t = re.sub(r"^\s*\d{1,2}\s*[.)]\s+", "", t)        # book chapter number
    t = re.sub(r"(?i),?\s*(british journal|the philosophical review|journal of)\b.*$", "", t)
    t = re.sub(r"\s+", " ", t).strip(" ,.;:-")
    return t


# Signs on page 1 that a PDF is a paper at all. In --bulk, a file with no
# identifier and none of these is not looked up: that keeps forms, letters and
# slides off the network, which is faster and sends fewer titles of personal
# documents to third-party services.
PAPERISH = re.compile(r"(?<![A-Za-z])(abstract|keywords|introduction|references|bibliography|"
                      r"proceedings|journal|conference|arxiv|doi|preprint|author\(s\)|"
                      r"corresponding author|published)(?![A-Za-z])", re.I)


def looks_like_paper(text):
    return bool(PAPERISH.search(text or ""))


# Review manuscripts. A file name can miss one: a PDF named "draft.pdf" can be a
# manuscript sent for review. The papers plugin's licence check (tools/license-check)
# recognises these from the first page: a marker such as "Anonymous Authors", and no
# DOI or arXiv id. The same patterns are used here so the two agree. The list is read
# from that module when it can be found from this folder; the copy below is its
# REVIEW_MARKERS in plugins/papers/tools/license-check/license_check.py (the plugin
# installs both together), kept so the skill still works when that file is absent.
_REVIEW_MARKERS_COPY = [
    r"\bManuscript Draft\b", r"\bFor Peer Review\b", r"\bAnonymous Authors?\b",
    r"\bAnonymous Author\(s\)", r"under (?:double|single)[\s\-]blind review",
    r"\bConfidential (?:Review|Reviewer)", r"\bdo not distribute\b", r"\bManuscript ID\b",
    r"\bManuscript Number\b", r"\bSubmission (?:ID|#|Number)\b",
    r"Under review as a (?:conference|workshop) paper",
]


def _review_markers():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(here, "..", "..", "tools", "license-check", "license_check.py"))
    try:
        spec = importlib.util.spec_from_file_location("license_check_markers", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        markers = list(mod.REVIEW_MARKERS)
        if markers:
            return markers
    except Exception:
        pass
    return list(_REVIEW_MARKERS_COPY)


REVIEW_RE = re.compile("|".join(_review_markers()), re.I)


def review_manuscript_marker(meta, text, filename):
    """The review marker found on page 1 when this PDF looks like a manuscript under
    review, else "". It must carry a marker and have no DOI or arXiv id anywhere the
    scanner looks (page 1, the embedded metadata, the file name): a published paper
    can print "Manuscript ID", but it also has an identifier. A file that is caught
    here is never looked up, so its title goes to no service."""
    m = REVIEW_RE.search(re.sub(r"\s+", " ", text or ""))
    if not m or candidate_ids(meta, text, filename):
        return ""
    return m.group(0)


def title_on_page(title, text):
    """Is this title printed on this page? It stops a DOI that belongs to a cited
    work, or to the book a chapter came from, being taken as the file's own.
    Scores words rather than strings so line-break hyphenation is tolerated."""
    t, p = norm(title), norm(text)
    if not t or not p:
        return False
    if t in p:
        return True
    words = [w for w in t.split() if len(w) > 3]
    if len(words) < 2:
        return False
    toks = set(p.split())
    return sum(w in toks for w in words) / len(words) >= 0.8


def candidate_ids(meta, text, filename):
    """Every identifier the file carries, strongest first. The filename counts:
    `Smith_2026_Example_arXiv-2607.01736.pdf` carries its arXiv id nowhere
    else, and a bare `2504.13857v1.pdf` is an arXiv download."""
    blob = text + " " + json.dumps(meta) + " " + filename
    out = [("arxiv", m.group(1)) for m in ARX_TEXT.finditer(blob)]
    m = ARX_BARE.match(filename)
    if m:
        out.append(("arxiv", m.group(1)))
    for m in DOI_RE.finditer(blob):
        doi = m.group(0).rstrip(".,;)")
        if "arxiv." in doi.lower():
            out.append(("arxiv", doi.lower().split("arxiv.")[-1]))
        else:
            out.append(("doi", doi))
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq[:4]


# ---------------------------------------------------------------- the lookups

def from_crossref(doi):
    w = getjson(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")
    if not w or "message" not in w:
        return None
    w = w["message"]
    parts = (w.get("published-print") or w.get("published-online")
             or w.get("issued") or {}).get("date-parts", [[None]])[0]
    it = CROSSREF_TYPES.get(w.get("type"), "journalArticle")
    md = {
        "itemType": it,
        "title": re.sub(r"<[^>]+>", "", (w.get("title") or [""])[0]).strip(),
        "creators": [{"firstName": a.get("given", ""), "lastName": a.get("family", "")}
                     for a in w.get("author", []) if a.get("family")],
        "date": "-".join(str(x) for x in parts if x),
        "DOI": w.get("DOI", ""),
        "volume": w.get("volume", ""), "issue": w.get("issue", ""),
        "pages": w.get("page", ""), "url": w.get("URL", ""),
        "abstractNote": re.sub(r"<[^>]+>", "", w.get("abstract", "") or "")[:2000],
    }
    md["proceedingsTitle" if it == "conferencePaper" else "publicationTitle"] = \
        (w.get("container-title") or [""])[0]
    return md


def from_s2_arxiv(aid):
    """Semantic Scholar, for when arXiv's API is rate-limiting.

    arXiv's PDF downloads and API queries share one rate budget, and the
    block can outlast 100 s. S2 carries the same core metadata."""
    bare = re.sub(r"v\d+$", "", aid)
    r = getjson("https://api.semanticscholar.org/graph/v1/paper/ARXIV:"
                f"{bare}?fields=title,authors,year,externalIds")
    if not r or not r.get("title"):
        return None
    creators = []
    for a in r.get("authors", []):
        bits = a["name"].strip().rsplit(" ", 1)
        creators.append({"firstName": bits[0] if len(bits) > 1 else "", "lastName": bits[-1]})
    return {
        "itemType": "preprint", "title": r["title"], "creators": creators,
        "date": str(r.get("year") or ""), "DOI": f"10.48550/arXiv.{bare}",
        "repository": "arXiv", "archiveID": f"arXiv:{bare}",
        "url": f"https://arxiv.org/abs/{bare}", "abstractNote": "",
    }


def from_datacite_arxiv(aid):
    """Every arXiv paper has a DataCite DOI, 10.48550/arXiv.<id>, and DataCite
    answers in under a second with title, authors, date and abstract. arXiv's
    own API allows one call per 3 s and can be far slower, so it is the
    fallback, not the first call."""
    bare = re.sub(r"v\d+$", "", aid)
    r = getjson(f"https://api.datacite.org/dois/10.48550/arxiv.{bare}")
    a = ((r or {}).get("data") or {}).get("attributes") or {}
    title = " ".join((((a.get("titles") or [{}])[0]).get("title") or "").split())
    if not title:
        return None
    creators = []
    for c in a.get("creators") or []:
        fam, giv = c.get("familyName"), c.get("givenName") or ""
        if not fam:
            bits = (c.get("name") or "").split(",", 1)
            fam, giv = bits[0].strip(), (bits[1].strip() if len(bits) > 1 else "")
        if fam:
            creators.append({"firstName": giv, "lastName": fam})
    date = next((d.get("date") for d in a.get("dates") or [] if d.get("dateType") == "Submitted"),
                None) or str(a.get("publicationYear") or "")
    abstract = next((d.get("description") for d in a.get("descriptions") or []
                     if d.get("descriptionType") == "Abstract"), "") or ""
    return {
        "itemType": "preprint", "title": title, "creators": creators, "date": date[:10],
        "DOI": f"10.48550/arXiv.{bare}", "repository": "arXiv", "archiveID": f"arXiv:{bare}",
        "url": f"https://arxiv.org/abs/{bare}", "abstractNote": " ".join(abstract.split())[:2000],
    }


def from_arxiv(aid):
    try:
        md = from_datacite_arxiv(aid)
        if md:
            return md
    except LookupFailed:
        pass                                  # DataCite down: try arXiv itself
    try:
        xml = get(f"http://export.arxiv.org/api/query?id_list={aid}")
    except LookupFailed:
        # arXiv exhausted its retries (429 or a "Rate exceeded." body). Semantic
        # Scholar next; if that fails too, LookupFailed propagates and the file
        # is retried on the next run instead of being filed as unidentified.
        return from_s2_arxiv(aid)
    e = re.search(r"<entry>(.*?)</entry>", xml, re.S)
    if not e or "<title>Error</title>" in e.group(1):
        return None
    e = e.group(1)
    grab = lambda t: (re.search(rf"<{t}>(.*?)</{t}>", e, re.S) or [None, ""])[1]
    creators = []
    for n in re.findall(r"<name>(.*?)</name>", e, re.S):
        bits = n.strip().rsplit(" ", 1)
        creators.append({"firstName": bits[0] if len(bits) > 1 else "", "lastName": bits[-1]})
    return {
        "itemType": "preprint",
        "title": " ".join(grab("title").split()),
        "creators": creators,
        "date": grab("published")[:10],
        "DOI": f"10.48550/arXiv.{aid}",
        "repository": "arXiv", "archiveID": f"arXiv:{aid}",
        "url": f"https://arxiv.org/abs/{aid}",
        "abstractNote": " ".join(grab("summary").split())[:2000],
    }


def from_openalex(w):
    creators = []
    for a in w.get("authorships", []):
        name = ((a.get("author") or {}).get("display_name") or "").strip()
        if name:
            bits = name.rsplit(" ", 1)
            creators.append({"firstName": bits[0] if len(bits) > 1 else "", "lastName": bits[-1]})
    src = ((w.get("primary_location") or {}).get("source") or {})
    it = ("preprint" if w.get("type") == "preprint"
          else "conferencePaper" if src.get("type") == "conference" else "journalArticle")
    abstract = ""
    inv = w.get("abstract_inverted_index") or {}
    if inv:
        abstract = " ".join(word for _, word in sorted((p, wd) for wd, ps in inv.items()
                                                         for p in ps))[:2000]
    md = {
        "itemType": it,
        "title": (w.get("title") or w.get("display_name") or "").strip(),
        "creators": creators,
        "date": str(w.get("publication_date") or w.get("publication_year") or ""),
        "DOI": (w.get("doi") or "").replace("https://doi.org/", ""),
        "url": (w.get("primary_location") or {}).get("landing_page_url") or "",
        "abstractNote": abstract,
    }
    md[{"preprint": "repository", "conferencePaper": "proceedingsTitle"}.get(it, "publicationTitle")] = \
        src.get("display_name") or ""
    return md


def crossref_by_title(title, loose=False):
    """Look a title up in Crossref.

    `loose=True` is for titles read off page 1, which are routinely padded with
    headers and cover-sheet text. Global similarity is the wrong test for those:
    "PLACE, U. T., Is consciousness a brain process , British Journal of
    Psychology" scores badly against the real title while *containing* it
    exactly. So accept on containment as well, which recovers the padded cases
    without loosening the test for clean input."""
    if not title or len(title) < 20:
        return None
    for q_title in filter(None, {title, clean_title(title)}):
        r = getjson("https://api.crossref.org/works?"
                    + urllib.parse.urlencode({"query.bibliographic": query_text(q_title), "rows": 3}))
        for w in ((r or {}).get("message") or {}).get("items", []):
            nt, nq = norm((w.get("title") or [""])[0]), norm(q_title)
            if not nt or len(nt) < 15:
                continue
            if difflib.SequenceMatcher(None, nt, nq).ratio() >= 0.92:
                return from_crossref(w["DOI"])
            if loose and nt in nq and len(nt) >= 0.4 * len(nq):   # sits inside a padded title
                return from_crossref(w["DOI"])
    return None


def openalex_by_title(title):
    """OpenAlex indexes NeurIPS, ICML and PMLR papers that carry no DOI and so
    are invisible to Crossref. Strict similarity only."""
    for q_title in filter(None, {title, clean_title(title)}):
        r = getjson("https://api.openalex.org/works?"
                    + urllib.parse.urlencode({"search": query_text(q_title), "per-page": 5}))
        for w in (r or {}).get("results", []):
            if similar(w.get("title") or w.get("display_name") or "", q_title) >= 0.92:
                return from_openalex(w)
    return None


PAPER_TYPES = {"Preprint", "JournalArticle", "ConferencePaper", "Book", "BookChapter",
               "Report", "Dissertation"}     # not Text, Audiovisual, Dataset, Software, Event
DATACITE_TYPES = {"Preprint": "preprint", "JournalArticle": "journalArticle",
                  "ConferencePaper": "conferencePaper", "Dissertation": "thesis",
                  "Book": "book", "BookChapter": "bookSection", "Report": "report"}


def _datacite_md(a, doi):
    """Zotero metadata from a DataCite record's attributes."""
    title = " ".join((((a.get("titles") or [{}])[0]).get("title") or "").split())
    creators = []
    for c in a.get("creators") or []:
        if c.get("nameType") == "Organizational" or re.search(
                r"(?i)conference|symposium|workshop|society|association|proceedings", c.get("name") or ""):
            continue                     # a conference listed as a creator is not an author
        fam, giv = c.get("familyName"), c.get("givenName") or ""
        if not fam:
            bits = (c.get("name") or "").split(",", 1)
            fam, giv = bits[0].strip(), (bits[1].strip() if len(bits) > 1 else "")
        if fam:
            creators.append({"firstName": giv, "lastName": fam})
    date = next((d.get("date") for d in a.get("dates") or []
                 if d.get("dateType") in ("Submitted", "Issued")), None) or str(a.get("publicationYear") or "")
    abstract = " ".join((next((d.get("description") for d in a.get("descriptions") or []
                               if d.get("descriptionType") == "Abstract"), "") or "").split())[:2000]
    arx = re.match(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", doi, re.I)
    if arx:
        aid = arx.group(1)
        return {"itemType": "preprint", "title": title, "creators": creators, "date": date[:10],
                "DOI": f"10.48550/arXiv.{aid}", "repository": "arXiv", "archiveID": f"arXiv:{aid}",
                "url": f"https://arxiv.org/abs/{aid}", "abstractNote": abstract}
    it = DATACITE_TYPES.get((a.get("types") or {}).get("resourceTypeGeneral") or "", "document")
    md = {"itemType": it, "title": title, "creators": creators, "date": date[:10], "DOI": doi,
          "url": a.get("url") or f"https://doi.org/{doi}", "abstractNote": abstract}
    pub = a.get("publisher")
    pub = pub.get("name") if isinstance(pub, dict) else pub
    if pub:
        md["repository" if it == "preprint" else "publicationTitle"] = pub
    return md


def datacite_by_title(title):
    """DataCite registers every arXiv DOI, so a title search here finds the arXiv
    version of NeurIPS, ICML and ICLR papers whose proceedings PDFs carry
    neither a DOI nor an arXiv stamp, and which Crossref does not index. Strict
    similarity, as for Crossref; the page-1 title and author checks still apply."""
    for q_title in filter(None, {title, clean_title(title)}):
        words = " ".join(w for w in re.sub(r"[^\w\s]", " ", query_text(q_title)).split() if len(w) > 2)
        if len(words.split()) < 3:
            continue
        r = getjson("https://api.datacite.org/dois?"
                    + urllib.parse.urlencode({"query": f"titles.title:({words})", "page[size]": 5}))
        # DataCite registers much more than papers under a paper's title: talk
        # recordings (Underline, 10.48448/...), slides, datasets, code. A
        # conference paper once matched the video of its own talk, whose first
        # "author" was the conference. Accept arXiv records first, then paper
        # types only.
        hits = []
        for d in (r or {}).get("data") or []:
            a = d.get("attributes") or {}
            if similar(((a.get("titles") or [{}])[0].get("title") or ""), q_title) < 0.92:
                continue
            doi = d.get("id") or ""
            kind = (a.get("types") or {}).get("resourceTypeGeneral") or ""
            if doi.lower().startswith("10.48550/arxiv."):
                hits.append((0, a, doi))
            elif kind in PAPER_TYPES:
                hits.append((1, a, doi))
        if hits:
            _, a, doi = min(hits, key=lambda h: h[0])
            return _datacite_md(a, doi)
    return None


def generic_match(md_title, page1_title):
    """A resolved title much shorter than the paper's own is a wrong match until
    checked: loose matching once turned arXiv 2006.01107 ("Model-Based
    Reinforcement Learning with Value-Targeted Regression") into a bare
    "Model-Based Reinforcement Learning". Every word of the short title is on
    page 1, so title_on_page cannot catch it."""
    p1 = clean_title(page1_title or "")
    if not p1 or DIRTY.search(page1_title or ""):
        return False
    return len(norm(md_title)) < 0.8 * len(norm(p1)) and similar(md_title, p1) < 0.92


def authors_on_page(md, text):
    """Does at least one of the record's author surnames appear on page 1?

    A title search can land on a different work that shares a generic title:
    "Introduction to Artificial Intelligence" matches a 2018 Springer textbook
    and every set of course notes with that heading, and every word of it is on
    the page, so title_on_page cannot tell them apart. The authors can. Papers
    print their authors on page 1; JSTOR cover sheets do too."""
    page = " " + norm(text) + " "
    for c in md.get("creators") or []:
        sur = norm(c.get("lastName", ""))
        # The whole surname, as a phrase. Matching any one word of it let a
        # conference parsed as a surname ("International Conference on
        # Autonomous Agents and Multi-Agent Systems 2020") pass on "agents"
        # and "systems", which are on page 1 of every multi-agent paper.
        if len(sur) < 3 or re.search(r"\d", sur) or len(sur.split()) > 4:
            continue                    # not a person's surname
        # Affiliation markers are often set inline, so the text reads "Smitha",
        # "Jonesb" (Elsevier), or "Zhang1". Allow one trailing letter
        # after surnames of five letters or more, and digits after any. Shorter
        # surnames must match exactly: "lev" plus two letters is "level".
        tail = r"[a-z]?" if len(sur.replace(" ", "")) >= 5 else ""
        if re.search(r"(?<![a-z])" + re.escape(sur) + tail + r"\d*(?![a-z])", page):
            return True
    return False


def resolve(p1, meta, text, filename, strict):
    """Metadata for this file, confirmed by finding its title on the file's page 1.
    Returns (metadata, how, note). Raises LookupFailed if a service did not answer,
    including when the only source left unconsulted was a closed OpenAlex: a
    "no match" reached without it is provisional (a conference extended
    abstract can be findable only there) and must be retried, not cached."""
    openalex_closed = None
    textless = len(text.strip()) < 200
    for kind, val in candidate_ids(meta, text, filename):
        if kind == "arxiv":
            md = from_arxiv(val)
        else:
            md = from_crossref(val)
        if not md or not md.get("title"):
            continue
        if title_on_page(md["title"], text):
            return md, f"{kind}:{val}", None
        if textless and not strict:
            return md, f"{kind}:{val}", "no text layer, title not checked against the page"
    for guess, loose in ((p1, True), ((meta.get("title") or "").strip(), False)):
        if not guess or len(guess) < 20:
            continue
        # Each source in turn until one verifies. Stopping at the first source
        # with any candidate let one wrong Crossref top hit turn a real paper
        # into a cached "not a paper" without DataCite or OpenAlex being asked.
        for source in ("crossref", "datacite", "openalex"):
            try:
                md = (crossref_by_title(guess, loose=loose) if source == "crossref"
                      else datacite_by_title(guess) if source == "datacite"
                      else openalex_by_title(guess))
            except LookupFailed as e:
                if source != "openalex":
                    raise
                openalex_closed = str(e)
                continue
            # A title search is weaker evidence than an identifier printed in the
            # file, so it must also find an author, not only the title.
            if md and md.get("title") and title_on_page(md["title"], text) \
                    and not generic_match(md["title"], p1) and authors_on_page(md, text):
                return md, "title search", None
    if openalex_closed:
        raise LookupFailed(f"no match in Crossref or DataCite; OpenAlex not consulted ({openalex_closed})")
    return None, None, None


# ---------------------------------------------------------------- the scan

def excluded(path, root, bulk):
    """Decide on the name alone whether a file may be opened at all."""
    fn = os.path.basename(path)
    if JUNK_NAME.search(fn):
        return "figure or supplement"
    # Review checks apply in every mode, not only --bulk: a project folder can
    # hold review assignments too.
    if REVIEW_NAME.search(fn):
        return "conference submission name (possible paper under review)"
    for d in os.path.relpath(os.path.dirname(path), root).split(os.sep):
        # plural "reviews", so a project's "Literature review" folder still scans
        if re.search(r"(?<![A-Za-z])reviews(?![A-Za-z])|referee|reviewing", d, re.I):
            return f"review folder '{d}'"
    if not bulk:
        return None
    for d in os.path.relpath(os.path.dirname(path), root).split(os.sep):
        if d in (".", ""):
            continue
        if REVIEW_DIR.search(d):
            return f"review-related folder '{d}'"
        if ADMIN_DIR.search(d):
            return f"admin or student folder '{d}'"
    if ADMIN_NAME.search(fn):
        return "admin or student file name"
    if EXTRA_EXCLUDE:
        for d in os.path.relpath(os.path.dirname(path), root).split(os.sep):
            if EXTRA_EXCLUDE.search(d):
                return f"ZOTERO_IMPORT_EXCLUDE matches folder '{d}'"
        if EXTRA_EXCLUDE.search(fn):
            return "ZOTERO_IMPORT_EXCLUDE matches file name"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("outdir")
    ap.add_argument("--also", action="append", default=[], help="another folder to scan")
    ap.add_argument("--bulk", action="store_true",
                    help="mixed folders such as Downloads: exclusions on, external records only")
    ap.add_argument("--lib", type=int, default=1, help="Zotero libraryID (1 = personal)")
    ap.add_argument("--scratch", default=tempfile.gettempdir(),
                    help="where the read-only copy of the Zotero database is made")
    ap.add_argument("--workers", type=int, default=6,
                    help="parallel lookups; per-host pacing still applies")
    a = ap.parse_args()
    try:
        import fitz  # noqa: F401  (PyMuPDF reads page 1 of each PDF, locally)
    except ImportError:
        sys.exit("PyMuPDF is not installed for this Python. See Setup in SKILL.md.")
    os.makedirs(a.outdir, exist_ok=True)
    roots = [os.path.abspath(os.path.expanduser(r)) for r in [a.folder] + a.also]

    dois, titles, colls = library_index(a.scratch, a.lib)
    print(f"library {a.lib}: {len(dois)} DOIs, {len(titles)} titles already present", flush=True)

    cache_p = os.path.join(a.outdir, "cache.json")
    cache = {}
    if os.path.exists(cache_p):
        try:
            cache = json.load(open(cache_p))
        except json.JSONDecodeError:
            print("cache.json unreadable (killed mid-write?); starting it afresh", flush=True)

    files = []
    for root in roots:
        for dirpath, dirs, fns in os.walk(root):
            if JUNK_DIR.search(dirpath + "/"):
                dirs[:] = []
                continue
            files += [(root, os.path.join(dirpath, fn)) for fn in fns if fn.lower().endswith(".pdf")]
    print(f"{len(files)} PDFs under {', '.join(roots)}", flush=True)

    out, pending = [], []
    for i, (root, p) in enumerate(sorted(files, key=lambda x: x[1]), 1):
        try:
            st = os.stat(p)
        except OSError:
            continue
        rec = {"path": p, "root": root, "file": os.path.basename(p), "bytes": st.st_size}
        ck = f"{p}|{st.st_size}|{int(st.st_mtime)}|{int(a.bulk)}|r{RULES_VERSION}"
        out.append(rec)
        # Exclusion rules run BEFORE the cache, so a rule tightened after a file
        # was cached still reaches it. The other way round, a review paper
        # cached under an older rule would keep its lookup result for ever.
        why = excluded(p, root, a.bulk)
        if why:
            rec.update(status="excluded", note=why)
            cache[ck] = {"status": "excluded", "note": why}
            continue
        if ck in cache and cache[ck].get("status") != "excluded":
            rec.update(cache[ck])
            continue
        if st.st_size < MIN_BYTES:
            rec.update(status="skipped", note="under 100 KB")
        else:
            # All PDF work stays on this thread: PyMuPDF is not thread-safe.
            # Only the network lookups go to the worker pool.
            try:
                meta, pages, text = pdf_probe(p)
                rec["pages"] = pages
                marker = review_manuscript_marker(meta, text, rec["file"])
                if marker:
                    # Decided from page 1 before any lookup: nothing about this
                    # file, its title included, leaves the machine.
                    rec.update(status="skipped", review_manuscript=True,
                               note=f"possible manuscript under review: page 1 says '{marker}' "
                                    "and the file has no DOI or arXiv id; not looked up, not imported")
                elif pages < MIN_PAGES:
                    rec.update(status="skipped", note=f"only {pages} pages")
                elif a.bulk and not candidate_ids(meta, text, rec["file"]) and not looks_like_paper(text):
                    rec.update(status="unidentified",
                               note="page 1 shows no sign of being a paper; not looked up")
                else:
                    pending.append((rec, ck, meta, text, title_from_page1(p)))
                    continue
            except Exception as e:
                rec.update(status="unreadable", note=str(e)[:80])
        cache[ck] = {k: v for k, v in rec.items() if k not in ("path", "root", "file", "bytes")}
        if i % 500 == 0:
            print(f"  read {i}/{len(files)}; {len(pending)} need a lookup", flush=True)
    _save(cache, cache_p)
    print(f"{len(pending)} files need a lookup; {a.workers} workers", flush=True)

    def work(item):
        rec, ck, meta, text, p1 = item
        try:
            md, how, note = resolve(p1, meta, text, rec["file"], strict=a.bulk)
            if md:
                rec.update(status="new", title=md["title"], metadata=md, via=how)
                if note:
                    rec["note"] = note
            elif not a.bulk and p1:
                # Not in any index: a draft, report or thesis. Its own title
                # beats a filename, so take it and say so.
                t = clean_title(p1) or p1
                rec.update(status="title only", title=t,
                           metadata={"itemType": "manuscript", "title": t, "creators": []},
                           note="title read from page 1; no external record"
                                + ("  ** looks like page furniture, check it **"
                                   if DIRTY.search(p1) else ""))
            elif not a.bulk:
                rec.update(status="unidentified",
                           note="no identifier, and no title readable from page 1")
            else:
                rec.update(status="unidentified", note="no external record whose title is on page 1")
        except LookupFailed as e:
            rec.update(status="lookup failed", note=str(e))
        except Exception as e:
            rec.update(status="unreadable", note=f"{type(e).__name__}: {str(e)[:70]}")
        return rec, ck

    done = ident = fails = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for fut in as_completed([ex.submit(work, it) for it in pending]):
            rec, ck = fut.result()
            done += 1
            ident += rec["status"] == "new"
            fails += rec["status"] == "lookup failed"
            if rec["status"] != "lookup failed":
                cache[ck] = {k: v for k, v in rec.items() if k not in ("path", "root", "file", "bytes")}
            if done % 25 == 0 or done == len(pending):
                _save(cache, cache_p)
                print(f"  looked up {done}/{len(pending)}  resolved {ident}"
                      + (f"  lookup failures {fails}" if fails else ""), flush=True)
    _save(cache, cache_p)

    # the library check is never cached: the library changes between runs
    for rec in out:
        if rec.get("status") in ("new", "already in Zotero") and rec.get("metadata"):
            md = rec["metadata"]
            hit = dois.get((md.get("DOI") or "").lower()) or titles.get(norm(md["title"]))
            if hit:
                rec.update(status="already in Zotero", zotero_key=hit["key"],
                           zotero_has_pdf=hit["has_pdf"])
            else:
                rec["status"] = "new"
                rec.pop("zotero_key", None)
                rec.pop("zotero_has_pdf", None)

    # Several copies of one paper are normal, and rarely equally well identified.
    # Keep the richest; the rest may go once the kept copy is safely in Zotero.
    # Group fuzzily and across statuses: one copy can resolve by DOI to
    # "Thermodynamics of Prediction" while another yields "The thermodynamics of
    # prediction", and OCR damage ("ar+ficial") survives normalisation. Two
    # different DOIs veto a merge, which keeps "Part I" and "Part II" apart.
    def quality(r):
        md = r.get("metadata") or {}
        return (r["status"] == "already in Zotero", bool(md.get("DOI")), bool(md.get("creators")),
                bool(md.get("date")), r.get("pages", 0), r["bytes"])
    kept = [r for r in out if r["status"] in ("new", "title only", "already in Zotero")
            and r.get("title")]
    groups, keys = [], []
    for r in kept:
        k, d = norm(r["title"]), ((r.get("metadata") or {}).get("DOI") or "").lower()
        for gi, (k2, d2) in enumerate(keys):
            if d and d2 and d != d2:
                continue
            if (d and d == d2) or k == k2 or difflib.SequenceMatcher(None, k, k2).ratio() >= 0.85:
                groups[gi].append(r)
                break
        else:
            keys.append((k, d))
            groups.append([r])
    for g in groups:
        if len(g) < 2:
            continue
        best = max(g, key=quality)
        for r in g:
            if r is not best:
                r.update(status="duplicate within this folder", dup_of=best["path"],
                         note="kept: " + os.path.basename(best["path"]))

    json.dump(out, open(os.path.join(a.outdir, "manifest.json"), "w"), indent=1)
    json.dump(colls, open(os.path.join(a.outdir, "existing-collections.json"), "w"), indent=1)

    by = {}
    for r in out:
        by.setdefault(r["status"], []).append(r)
    suspect = [r for r in out if r["status"] in ("new", "title only")
               and r.get("title") and DIRTY.search(r["title"])]
    L = ["# Papers found\n",
         f"Scanned {', '.join(roots)}. Nothing has been written to Zotero and nothing moved.\n",
         "**Read the titles below, not only the counts.** A clean count and "
         "`0 failed` are compatible with importing duplicates and with titles "
         "that are cover-sheet text rather than titles.\n",
         "| Status | Count |\n|---|---:|"]
    for k in sorted(by, key=lambda k: -len(by[k])):
        L.append(f"| {k} | {len(by[k])} |")
    if "lookup failed" in by:
        L.append(f"\n**{len(by['lookup failed'])} lookups failed** (rate limit or network). "
                 "They are not cached: rerun the same command to retry them.\n")
    if suspect:
        L.append(f"\n## ** {len(suspect)} title(s) look like page furniture **\n")
        for r in suspect:
            L.append(f"- {r['title'][:96]}  ·  `{r['file']}`")
    for k in ["new", "already in Zotero", "title only"]:
        if k not in by:
            continue
        L.append(f"\n## {k} ({len(by[k])})\n")
        for r in sorted(by[k], key=lambda r: r.get("title", "")):
            extra = ("" if k != "already in Zotero"
                     else "  ·  Zotero has a PDF" if r.get("zotero_has_pdf") else "  ·  **no PDF in Zotero**")
            L.append(f"- {r['title'][:96]}  ·  `{r['file']}`{extra}")
    held_back = [r for r in out if r.get("review_manuscript")]
    if held_back:
        L.append(f"\n## skipped: possible manuscripts under review ({len(held_back)})\n")
        L.append("Page 1 carries a review marker and the file has no DOI or arXiv id. "
                 "These were not looked up and will not be imported. Only the file name is shown.\n")
        for r in held_back:
            L.append(f"- `{r['file']}`  ·  {r['note']}")
    if not a.bulk:
        for k in ["unidentified", "duplicate within this folder", "skipped", "unreadable"]:
            rows = [r for r in by.get(k, []) if not r.get("review_manuscript")]
            if rows:
                L.append(f"\n## {k} ({len(rows)})\n")
                for r in rows:
                    L.append(f"- `{r['file']}`" + (f"  ·  {r['note']}" if r.get("note") else ""))
    if "excluded" in by:
        L.append("\n## excluded, by reason (never opened)\n")
        reasons = {}
        for r in by["excluded"]:
            k = re.sub(r"'.*'", "'…'", r["note"])
            reasons[k] = reasons.get(k, 0) + 1
        for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
            L.append(f"- {v}  {k}")
    open(os.path.join(a.outdir, "review.md"), "w").write("\n".join(L))
    print(f"\nwrote {a.outdir}/manifest.json and review.md")
    print("   " + "  ".join(f"{k}={len(v)}" for k, v in sorted(by.items(), key=lambda x: -len(x[1]))))


if __name__ == "__main__":
    main()
