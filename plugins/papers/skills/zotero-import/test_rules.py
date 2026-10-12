#!/usr/bin/env python3
"""Regression test for the name rules in scan_and_identify.py.

Run after ANY change to JUNK_NAME, REVIEW_NAME, REVIEW_DIR, ADMIN_DIR,
ADMIN_NAME or the ZOTERO_IMPORT_EXCLUDE handling, and before any bulk scan:

    python3 "${CLAUDE_SKILL_DIR}/test_rules.py"

The name rules need no Zotero library, no PDFs and no network. The later checks
(the 200-character title cap, the review-manuscript skip, deleting the database
copy, the --any-root refusal) build a small fake Zotero data folder and synthetic
PDFs in a temporary folder, with the network replaced by a recorder, so they never
touch the real library or any real file. The PDF checks need PyMuPDF and are
skipped, with a message, when it is missing. Each KEEP entry is a paper a past
rule wrongly excluded (or would have), taken from real paper titles or modelled
on them; each DROP entry is admin, student or review material a past rule let
through, with the names made up. Add to both lists whenever a scan turns up a
new miss, rather than fixing the rule without a test.
"""
import contextlib, importlib.util, io, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The tests must not depend on the tester's environment, so no extra pattern is
# set when the scanner is imported.
os.environ.pop("ZOTERO_IMPORT_EXCLUDE", None)

spec = importlib.util.spec_from_file_location("s", os.path.join(HERE, "scan_and_identify.py"))
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

# --bulk: Downloads and the Desktop -----------------------------------------
BULK_KEEP = [
    "Evaluating transformers as memory systems in reinforcement learning.pdf",   # "memo" in "memory"
    "Transcription factor binding prediction.pdf",                              # "transcript"
    "Smith et al_2022_A step-by-step tutorial on active inference and its application to empirical data.pdf",
    "Attention2017.pdf",                                                        # year glued to a word
    "Kalman - 2001 - A New Approach to Linear Filtering and Prediction Problems.pdf",
    "Benchmarks for offline reinforcement learning.pdf",                        # "marks" in "benchmarks"
    "Deep reinforcement learning from human feedback.pdf",
    "Applications of deep learning to physics.pdf",
    "An Evaluation Study of Intrinsic Motivation Techniques.pdf",
    "The Lottery Ticket Hypothesis.pdf",                                        # bare "ticket"
    "2024_Cultural Accumulation in Learning Agents.pdf",                        # year prefix, not an id
    "2504.13857v1.pdf", "s41593-024-01787-0.pdf", "1-s2.0-S0149763423004426-main.pdf",
    "9379-Article Text-68931-1-10-20200725.pdf", "JHEP10(2020)193.pdf", "PIIS0896627318308560.pdf",
    "Closed form solutions for linear RL.pdf",                                  # bare "form"
    "Physical Review Letters - Chaotic spinning billiards.pdf",                 # "letter"
    "Kool et al_2019_Attention, Learn to Solve Routing Problems.pdf",
    "Cardiology_final/Selected studies/Jones-2017-Perceived mHealth barriers.pdf",
    "Dark Matter Cosmology/axion cosmology.pdf",
    "Memory project/episodic memory.pdf", "Transcription papers/x.pdf",
]
BULK_DROP = [
    "Store eReceipt (2).pdf", "Term 1, Tutorial 3 Answers (2)_Extracted.pdf",
    "Tutorial 12 (2).pdf", "Itinerary ABC123.pdf", "Funding Statement _20240315.pdf",
    "acct_Statement_2025-03.pdf",                                               # \b fails across "_"
    "Short test 22 April 2022 Memo.pdf", "Workshop Agenda 2025.pdf",
    "Doe, Jane - Letters of Recommendation.pdf",
    "Application for parking permit.pdf",
    "Missing slip form for site visit.pdf",
    "CONF2025_paper_1234.pdf",                                                  # review, "_paper_"
    "12345_Learning_Policies_From_Demonstrations-2.pdf",                        # submission ids
    "070_Value_Functions_Spectral_Smith.pdf",
    "4_Planning_Under_Partial_Observability-2.pdf",                              # one-digit workshop id
    "Student feedback.pdf", "Examiner Report Jones.pdf",
    "Data Sharing Agreement.docx.pdf", "Liability Waiver_v2 Smith.pdf",
    "Gmail - Your Thursday evening trip with Uber.pdf",
    "Letter of Support for Applicant.docx.pdf", "Hotel Booking Confirmation 0412.pdf",
    "2_page_CV.pdf",
    "workshop-reviews/x.pdf", "AAAI reviews/x.pdf", "NeurIPS bids/x.pdf",
    "reviewingforsomeworkshop2024/x.pdf", "supplementary_material_conf25/x.pdf",
    # Deliberate: in bulk mode any folder named "review" is skipped, so a
    # "Literature review" folder is too. The rule's real catches were review
    # assignments and HR reviews. Accept the cost; revisit if one appears.
    "Literature review/paper.pdf",
    "expenses-old/anything.pdf", "APPLICATIONS 2026/cand.pdf", "Faculty recommendations/x.pdf",
    "123456/x.pdf", "Travel/x.pdf",
    "paymentforms/March/Travel claim form.pdf",
]

# project mode: review checks still apply, admin rules do not ---------------
PROJECT_KEEP = [
    "Smith_2026_Example_arXiv-2607.01736.pdf",
    "Literature review/paper.pdf",            # plural "reviews" only, in project mode
    "2024_Cultural Accumulation in Learning Agents.pdf",
    "Funding Statement.pdf",                  # admin rules are bulk-only
]
PROJECT_DROP = [
    "4_Planning_Under_Partial_Observability.pdf", "74_When_Do_Models_Help_.pdf",
    "workshop-reviews/anything.pdf", "referee reports/x.pdf",
    "fig1_loss_curves.pdf", "paper_appendices.pdf",
]

# ZOTERO_IMPORT_EXCLUDE: a pattern of the user's own, applied in --bulk only.
# The example is a student-number format, case-sensitive, which must not touch papers.
EXTRA = r"(?<![A-Za-z])[A-Z]{6}\d{3}(?!\d)"
EXTRA_BULK_DROP = ["MSc_ABCDEF001_as_at_15_03_2023.pdf", "UVWXYZ123 thesis.pdf"]
EXTRA_BULK_KEEP = ["Attention2017.pdf", "Kalman2001.pdf", "2504.13857v1.pdf"]
EXTRA_PROJECT_KEEP = ["UVWXYZ123 thesis.pdf"]     # bulk only


def check(names, root, bulk, want_excluded):
    bad = 0
    for n in names:
        why = s.excluded(os.path.join(root, n), root, bulk)
        if bool(why) != want_excluded:
            bad += 1
            print(f"  {'WRONGLY KEPT    ' if want_excluded else 'WRONGLY EXCLUDED'}  "
                  f"[{'bulk' if bulk else 'project'}]  {n}" + (f"   <- {why}" if why else ""))
    return bad


R = os.path.join(os.sep, "scan", "root")
bad = (check(BULK_KEEP, R, True, False) + check(BULK_DROP, R, True, True)
       + check(PROJECT_KEEP, R, False, False) + check(PROJECT_DROP, R, False, True))
total = len(BULK_KEEP) + len(BULK_DROP) + len(PROJECT_KEEP) + len(PROJECT_DROP)

# the extra pattern, set the way the environment variable sets it
s.EXTRA_EXCLUDE = re.compile(EXTRA)
bad += (check(EXTRA_BULK_DROP, R, True, True) + check(EXTRA_BULK_KEEP, R, True, False)
        + check(EXTRA_PROJECT_KEEP, R, False, False))
total += len(EXTRA_BULK_DROP) + len(EXTRA_BULK_KEEP) + len(EXTRA_PROJECT_KEEP)
s.EXTRA_EXCLUDE = None

# data-directory discovery: an explicit directory wins, and one without a
# zotero.sqlite is refused with a message rather than failing later
import zotero_env
with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "zotero.sqlite"), "w").close()
    os.environ["ZOTERO_DATA_DIR"] = d
    total += 1
    if zotero_env.data_dir() != os.path.abspath(d):
        bad += 1
        print("  data_dir() ignored ZOTERO_DATA_DIR")
    os.environ["ZOTERO_DATA_DIR"] = os.path.join(d, "nowhere")
    total += 1
    try:
        zotero_env.data_dir()
        bad += 1
        print("  data_dir() accepted a directory with no zotero.sqlite")
    except SystemExit as e:
        if "ZOTERO_DATA_DIR" not in str(e):
            bad += 1
            print("  data_dir() refused, but its message does not name ZOTERO_DATA_DIR")

# --------------------------------------------------------------------------
# Checks that need a fake Zotero folder, synthetic PDFs, or a recorded network.

def expect(cond, msg):
    global total, bad
    total += 1
    if not cond:
        bad += 1
        print("  FAILED  " + msg)


def make_fake_zotero(zdir, items=(), drop_table=None):
    """A minimal zotero.sqlite in zdir. items: (itemID, key, title, [(attachID, attachKey,
    filename, bytes)]). Attachment files are written under storage/<attachKey>/."""
    os.makedirs(zdir, exist_ok=True)
    con = sqlite3.connect(os.path.join(zdir, "zotero.sqlite"))
    con.executescript("""
        create table fields(fieldID integer primary key, fieldName text);
        create table deletedItems(itemID integer primary key);
        create table itemTypes(itemTypeID integer primary key, typeName text);
        create table items(itemID integer primary key, key text, libraryID int, itemTypeID int);
        create table itemAttachments(itemID integer primary key, parentItemID int, linkMode int,
                                     path text, contentType text);
        create table itemDataValues(valueID integer primary key, value text);
        create table itemData(itemID int, fieldID int, valueID int);
        create table collections(collectionName text, libraryID int);
        insert into fields values (1, 'title'), (2, 'DOI');
        insert into itemTypes values (1, 'journalArticle'), (2, 'attachment');
    """)
    vid = 0
    for iid, key, title, atts in items:
        con.execute("insert into items values (?,?,?,?)", (iid, key, 1, 1))
        vid += 1
        con.execute("insert into itemDataValues values (?,?)", (vid, title))
        con.execute("insert into itemData values (?,?,?)", (iid, 1, vid))
        for aid, akey, fn, nbytes in atts:
            con.execute("insert into items values (?,?,?,?)", (aid, akey, 1, 2))
            con.execute("insert into itemAttachments values (?,?,?,?,?)",
                        (aid, iid, 0, "storage:" + fn, "application/pdf"))
            os.makedirs(os.path.join(zdir, "storage", akey), exist_ok=True)
            with open(os.path.join(zdir, "storage", akey, fn), "wb") as f:
                f.write(b"x" * nbytes)
    if drop_table:
        con.execute(f"drop table {drop_table}")
    con.commit()
    con.close()


def leftovers(folder, stem):
    return sorted(f for f in os.listdir(folder) if f.startswith(stem))


# 1. a title query to any lookup service carries at most 200 characters ------
LONG = ("Quantum gravity of imaginary flamingos and spectral teapots " * 8).strip()   # 479 characters
seen = []
real_getjson = s.getjson
s.getjson = lambda url: seen.append(url) or None
try:
    s.crossref_by_title(LONG)
    s.openalex_by_title(LONG)
    s.datacite_by_title(LONG)
    n_direct = len(seen)
    # the title read from the PDF's embedded metadata goes through resolve()
    seen.clear()
    s.resolve("", {"title": LONG}, "page text with no identifier", "x.pdf", strict=False)
    n_meta = len(seen)
    # and so does the title read off page 1
    seen.append("--- page 1 ---")
    s.resolve(LONG[:290], {}, "page text with no identifier", "x.pdf", strict=False)
finally:
    s.getjson = real_getjson


def title_queries(urls):
    out = []
    for u in urls:
        if u.startswith("---"):
            continue
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(u).query)
        for key in ("query.bibliographic", "search", "query"):
            for v in q.get(key, []):
                if key == "query":                       # DataCite: titles.title:(words)
                    v = v[len("titles.title:("):-1]
                out.append(v)
    return out


qs = title_queries(seen)
expect(n_direct == 3 and n_meta >= 3, "expected a request to each of three services per title")
expect(len(qs) >= 6 and all(len(q) <= 200 for q in qs),
       f"a title query longer than 200 characters was sent: {[len(q) for q in qs]}")
expect(max(len(q) for q in qs) > 100, "title queries were not sent at all")

# 2. a page-1 review marker without a DOI or arXiv id is skipped -------------
page_no_doi = "Title of a draft\nAnonymous Author(s)\nAffiliation withheld\nAbstract. We study things."
page_doi = page_no_doi + "\ndoi:10.1234/synthetic.5678"
expect(s.review_manuscript_marker({}, page_no_doi, "draft.pdf").lower().startswith("anonymous author"),
       "'Anonymous Author(s)' with no DOI was not recognised as a review manuscript")
expect(s.review_manuscript_marker({}, page_doi, "draft.pdf") == "",
       "a marker with a DOI on page 1 must not skip the file")
expect(s.review_manuscript_marker({"title": "x", "subject": "10.1234/synthetic.5678"}, page_no_doi, "draft.pdf") == "",
       "a marker with a DOI in the metadata must not skip the file")
expect(s.review_manuscript_marker({}, page_no_doi, "paper_arXiv-2607.01736.pdf") == "",
       "a marker with an arXiv id in the file name must not skip the file")
expect(s.review_manuscript_marker({}, page_no_doi.replace("Anonymous Author(s)", "A. Author"), "draft.pdf") == "",
       "a page with no marker was skipped")
expect(s.review_manuscript_marker({}, "For Peer\n  Review only", "draft.pdf") != "",
       "a marker split across lines was missed")      # whitespace is flattened first
lc_path = os.path.normpath(os.path.join(HERE, "..", "..", "tools", "license-check", "license_check.py"))
if os.path.isfile(lc_path):
    lc_spec = importlib.util.spec_from_file_location("lc", lc_path)
    lc = importlib.util.module_from_spec(lc_spec)
    lc_spec.loader.exec_module(lc)
    expect(s._REVIEW_MARKERS_COPY == lc.REVIEW_MARKERS and s.REVIEW_RE.pattern == lc.REVIEW_RE.pattern,
           "the scanner's review markers differ from license_check.py's REVIEW_MARKERS")
else:
    print("  (license_check.py not found beside this skill; marker agreement not checked)")

# 3. the same through a whole scan: no lookup for the review file, no import ----
try:
    import fitz
except ImportError:
    fitz = None
    print("  (PyMuPDF missing: the PDF-based checks were skipped)")

if fitz:
    def make_pdf(path, title, extra_lines):
        d = fitz.open()
        pg = d.new_page()
        pg.insert_text((50, 90), title, fontsize=14)
        pg.insert_text((72, 140), extra_lines, fontsize=11)
        d.new_page().insert_text((72, 90), "second page", fontsize=11)
        d.save(path)
        d.close()

    with tempfile.TemporaryDirectory() as work:
        zdir, papers, outdir, scratch = (os.path.join(work, n) for n in ("zotero", "papers", "out", "scratch"))
        os.makedirs(papers)
        os.makedirs(scratch)
        make_fake_zotero(zdir)
        REVIEW_TITLE = "Confidential Orbital Mechanics Of Hidden Walruses"
        make_pdf(os.path.join(papers, "draft.pdf"), REVIEW_TITLE,
                 "Anonymous Author(s)\nAffiliation withheld\nAbstract. Synthetic text.")
        make_pdf(os.path.join(papers, "plain.pdf"), "Quantum Gravity Of Imaginary Flamingos And Spectral Teapots",
                 "A. Author\nAbstract. Synthetic text.")
        make_pdf(os.path.join(papers, "withdoi.pdf"), "Published Marmalade Dynamics In Coastal Lighthouses",
                 "A. Author\nManuscript ID 4417\ndoi:10.1234/synthetic.5678\nAbstract. Synthetic text.")
        saved = (s.MIN_BYTES, s.MIN_PAGES, s.getjson)
        calls = []
        s.MIN_BYTES, s.MIN_PAGES = 0, 1
        s.getjson = lambda url: calls.append(url) or None
        old_env, old_argv = os.environ.get("ZOTERO_DATA_DIR"), sys.argv
        os.environ["ZOTERO_DATA_DIR"] = zdir
        sys.argv = ["scan_and_identify.py", papers, outdir, "--scratch", scratch, "--workers", "1"]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                s.main()
        finally:
            s.MIN_BYTES, s.MIN_PAGES, s.getjson = saved
            sys.argv = old_argv
            if old_env is None:
                os.environ.pop("ZOTERO_DATA_DIR", None)
            else:
                os.environ["ZOTERO_DATA_DIR"] = old_env
        man = {r["file"]: r for r in json.load(open(os.path.join(outdir, "manifest.json")))}
        review_md = open(os.path.join(outdir, "review.md")).read()
        joined = " ".join(calls).lower()
        expect(man["draft.pdf"]["status"] == "skipped" and man["draft.pdf"].get("review_manuscript"),
               f"the review manuscript was not skipped: {man['draft.pdf']}")
        expect("walruses" not in joined and "orbital" not in joined,
               "the review manuscript's title went to a lookup service")
        expect("teapots" in joined, "the recorder saw no title query for an ordinary paper (the check is blind)")
        expect(man["withdoi.pdf"]["status"] != "skipped" and "10.1234" in joined,
               "a marker with a DOI wrongly stopped the lookup")
        expect("possible manuscripts under review" in review_md and "`draft.pdf`" in review_md
               and "walruses" not in review_md.lower(),
               "review.md does not list the skipped review manuscript by file name only")
        expect(man["plain.pdf"]["status"] == "title only", "an ordinary paper was not handled as before")
        expect(not leftovers(scratch, "z_import_check"),
               f"the database copy was left in the scratch folder: {leftovers(scratch, 'z_import_check')}")

        # make_import_js never imports the review manuscript, even with --include skipped
        mj_spec = importlib.util.spec_from_file_location("mj", os.path.join(HERE, "make_import_js.py"))
        mj = importlib.util.module_from_spec(mj_spec)
        mj_spec.loader.exec_module(mj)
        fake = [{"path": "/Users/example/Papers/draft.pdf", "root": "/Users/example/Papers", "file": "draft.pdf",
                 "bytes": 1, "status": "skipped", "review_manuscript": True, "title": "Hidden Walruses"},
                {"path": "/Users/example/Papers/ok.pdf", "root": "/Users/example/Papers", "file": "ok.pdf",
                 "bytes": 1, "status": "new", "title": "An Ordinary Paper",
                 "metadata": {"itemType": "journalArticle", "title": "An Ordinary Paper", "creators": [],
                              "rights": "test"}}]
        mjdir = os.path.join(work, "mj")
        os.makedirs(mjdir)
        json.dump(fake, open(os.path.join(mjdir, "manifest.json"), "w"))
        old_argv = sys.argv
        sys.argv = ["make_import_js.py", mjdir, "", "--include", "skipped"]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                mj.main()
        finally:
            sys.argv = old_argv
        js = open(os.path.join(mjdir, "import.js")).read()
        expect("An Ordinary Paper" in js and "draft.pdf" not in js and "Walruses" not in js,
               "import.js includes the review manuscript")
        node = shutil.which("node")
        if node:
            chk = os.path.join(work, "check.js")
            open(chk, "w").write("(async function(){\n" + js + "\n})\n")
            r = subprocess.run([node, "--check", chk], capture_output=True, text=True)
            expect(r.returncode == 0, "import.js does not parse: " + r.stderr[:300])
            expect("stub.deleted = true" in js and "moved to the Trash" in js, "the stub cleanup is missing from import.js")

# 4. the database copies are deleted, also after an error --------------------
import verify_and_move as vm
vm.zotero_running = lambda: False          # the real Zotero may be open while the tests run
with tempfile.TemporaryDirectory() as work:
    zdir, scratch = os.path.join(work, "zotero"), os.path.join(work, "scratch")
    os.makedirs(scratch)
    make_fake_zotero(zdir, [(1, "AAAAAAAA", "Synthetic Alpha Paper", [(2, "BBBBBBBB", "alpha.pdf", 10)])])
    old_env = os.environ.get("ZOTERO_DATA_DIR")
    os.environ["ZOTERO_DATA_DIR"] = zdir
    try:
        s.library_index(scratch, 1)
        expect(not leftovers(scratch, "z_import_check"), "scan: the database copy was kept after a normal run")
        vm.load_library(scratch, 1)
        expect(not leftovers(scratch, "z_verify"), "verify: the database copy was kept after a normal run")
        for name, fn, stem in (("scan", s.library_index, "z_import_check"), ("verify", vm.load_library, "z_verify")):
            broken = os.path.join(work, "broken-" + name)
            make_fake_zotero(broken, [(1, "AAAAAAAA", "Synthetic Alpha Paper", [])], drop_table="itemAttachments")
            os.environ["ZOTERO_DATA_DIR"] = broken
            try:
                fn(scratch, 1)
                expect(False, f"{name}: a broken database did not raise")
            except sqlite3.Error:
                pass
            expect(not leftovers(scratch, stem), f"{name}: the database copy was kept after an error")
    finally:
        if old_env is None:
            os.environ.pop("ZOTERO_DATA_DIR", None)
        else:
            os.environ["ZOTERO_DATA_DIR"] = old_env

# 5. --any-root: files from outside Downloads and the Desktop stay put ---------
with tempfile.TemporaryDirectory() as work:
    cleared, other, dest = (os.path.join(work, n) for n in ("Downloads", "Project", "holding"))
    os.makedirs(os.path.join(cleared, "sub"))
    os.makedirs(other)
    recs = []
    for folder, root, name in ((cleared, cleared, "a.pdf"), (os.path.join(cleared, "sub"), cleared, "b.pdf"),
                               (other, other, "c.pdf")):
        path = os.path.join(folder, name)
        open(path, "wb").write(b"x" * 10)
        recs.append({"path": path, "root": root, "file": name, "bytes": 10, "status": "new", "title": name})
    verdict = {r["path"]: (True, "stored copy of this exact file is in Zotero") for r in recs}
    plan, held = vm.plan_moves(recs, verdict, set(), dest, any_root=False, roots=(cleared,))
    expect(sorted(os.path.basename(m["from"]) for m in plan) == ["a.pdf", "b.pdf"],
           f"files inside the cleared folder should move: {plan}")
    expect(sum(held.values()) == 1 and any("--any-root" in k for k in held), f"the outside file was not held back: {held}")
    plan, held = vm.plan_moves(recs, verdict, set(), dest, any_root=True, roots=(cleared,))
    expect(len(plan) == 3 and not held, "--any-root should let all three move")

    # the whole script, as a dry run and then applied, on a fake library
    zdir, outdir, scratch = (os.path.join(work, n) for n in ("zotero", "out", "scratch"))
    os.makedirs(scratch)
    os.makedirs(outdir)
    make_fake_zotero(zdir, [(1, "AAAAAAA1", "a.pdf", [(11, "BBBBBBB1", "a.pdf", 10)]),
                            (2, "AAAAAAA2", "b.pdf", [(12, "BBBBBBB2", "b.pdf", 10)]),
                            (3, "AAAAAAA3", "c.pdf", [(13, "BBBBBBB3", "c.pdf", 10)])])
    json.dump(recs, open(os.path.join(outdir, "manifest.json"), "w"))

    def run_vm(*args):
        buf, old_argv = io.StringIO(), sys.argv
        sys.argv = ["verify_and_move.py", outdir, "--scratch", scratch, "--dest", dest, "--lib", "1", *args]
        try:
            with contextlib.redirect_stdout(buf):
                vm.main()
        finally:
            sys.argv = old_argv
        return buf.getvalue()

    saved_roots, old_env = vm.CLEARED_ROOTS, os.environ.get("ZOTERO_DATA_DIR")
    vm.CLEARED_ROOTS = (cleared,)
    os.environ["ZOTERO_DATA_DIR"] = zdir
    try:
        text = run_vm()
        expect("cleared to move: 2" in text and "--any-root" in text and "scanned from outside" in text,
               "the plan output does not say that the outside file is refused:\n" + text)
        run_vm("--apply")
        expect(os.path.exists(os.path.join(other, "c.pdf")) and not os.path.exists(os.path.join(cleared, "a.pdf")),
               "--apply moved the outside file, or did not move the inside one")
        text = run_vm("--any-root", "--apply")
        expect(not os.path.exists(os.path.join(other, "c.pdf")) and "--any-root is set" in text,
               "--any-root did not move the outside file")
        expect(not leftovers(scratch, "z_verify"), "verify: the database copy was kept after the run")
    finally:
        vm.CLEARED_ROOTS = saved_roots
        if old_env is None:
            os.environ.pop("ZOTERO_DATA_DIR", None)
        else:
            os.environ["ZOTERO_DATA_DIR"] = old_env


print(f"{total} cases, {bad} wrong")
sys.exit(1 if bad else 0)
