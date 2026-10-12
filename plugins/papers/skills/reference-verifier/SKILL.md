---
name: reference-verifier
description: "Verify the references/bibliography of an academic paper. Use this skill whenever the user wants to check, verify, validate, audit, or sanity-check the references, citations, or bibliography of a paper, manuscript, or preprint. Triggers include: 'verify references', 'check the bibliography', 'are these citations real', 'find hallucinated citations', 'check for fake references', 'validate the bib file', 'audit citations', 'check DOIs', 'are the references correct', any mention of LLM-fabricated or AI-hallucinated citations, or requests to confirm that cited works actually exist before submission. Works with .tex and .bib source, and with PDF and Word manuscripts, whose reference list Claude transcribes into a .bib first. Performs existence checks, metadata cross-validation, DOI resolution, and duplicate/orphan detection; it does NOT verify whether the cited paper actually supports the claim."
---

# Reference Verifier

Checks each reference in a paper against authoritative bibliographic databases (Crossref → OpenAlex → Semantic Scholar → arXiv) to catch fabricated references, metadata errors, broken DOIs, and bibliography hygiene issues.

**What this skill does:**
- Reads `.tex` and `.bib` source directly. For a PDF or Word manuscript, Claude first transcribes the reference list into a `.bib`, which the script then checks
- Existence verification: does the cited work actually exist?
- Metadata cross-validation: do title, authors, year, venue, volume/pages match an authoritative record?
- DOI/arXiv ID resolution
- Duplicate detection (same work cited under two keys)
- Orphan/missing detection (`.tex` only: entries in bibliography but not cited, or vice versa)

**What this skill does NOT do:**
- Semantic claim-support checking (whether the cited paper actually supports the surrounding claim)
- Style/formatting compliance (e.g., enforcing a specific citation style)
- Auto-correction of `.bib` entries (reports only; use `--suggest-fixes` for proposed diffs)

## When to use

- User wants to verify references before submission
- User suspects LLM-assisted writing may have introduced hallucinated citations
- User asks to check a `.bib` file, bibliography section, or reference list for accuracy
- Sanity-checking a manuscript that has gone through multiple revisions

## Quick start

```bash
uv run --script "${CLAUDE_SKILL_DIR}/scripts/verify_references.py" <input_file> [options]
```

Use `uv`, which installs the script's Python libraries on first use. They are listed at the top of the script. Don't run it with plain `python3`, which may lack them.

The script accepts `.tex`, `.bib` and `.bbl` input and detects the type by extension. For a PDF or Word file, first transcribe the reference list as described below. For a `.tex` project with a separate `.bib`, pass the `.tex` file. The script locates the `.bib` through `\bibliography{...}` and uses the `.bbl` if no `.bib` is found.

**Options:**
- `--output <path>`: write Markdown report to this path (default: `<input>_refs_report.md`)
- `--cache-dir <dir>`: override default cache location (`~/.cache/refverify/`)
- `--no-cache`: bypass the cache for this run
- `--concurrency <N>`: parallel API request limit (default: 5; raise carefully)
- `--check-body / --no-check-body`: control orphan/missing detection for `.tex` inputs (default: on if body available)
- `--suggest-fixes`: also write `<report>.diff.md`, replacing the report path's extension with `.diff.md`. For each `metadata_mismatch` and `low_confidence` entry, this Markdown file lists the title, year, DOI and venue suggested by the matched record.
- `--strict`: exit non-zero if any reference fails verification (useful in CI)
- `--transcribed-from <file>`: identify the PDF or Word file used to transcribe a `.bib`. The report's confidence line records this.

## Configuration

The script reads a contact email from `REFVERIFY_CONTACT_EMAIL`. If set, the script sends it to all four services in every request's User-Agent header, and as the `mailto` parameter for OpenAlex. Crossref and OpenAlex use it to assign requests to their faster polite pools. Set it once in your shell:

```bash
export REFVERIFY_CONTACT_EMAIL="your.email@institution.edu"
```

If no email is set, the script uses slower, lower-priority anonymous queries and warns once per run. Crossref and OpenAlex may rate-limit or deprioritise these requests under load.

Optionally set `SEMANTIC_SCHOLAR_API_KEY` if you have one. It raises the rate limit from ~1 req/s to ~100 req/s. Without a key, Semantic Scholar often returns HTTP 429 (rate limited). If Crossref and OpenAlex both searched without finding a match, the reference is still reported as `not_found`, with a note that Semantic Scholar could not be reached. It is not cached, so the next run queries Semantic Scholar again.

## Input handling

### `.tex` (preferred)

Source input is the most reliable. The script:
1. Reads the `.tex` file and locates `\bibliography{file1,file2}` to find `.bib` files
2. If no `.bib` is referenced or found, parses the `.bbl`. One heuristic parser handles every style: it splits entries on `\bibitem` and guesses the year, DOI, arXiv ID, title (from `\emph`, `\textit` or quotation marks) and authors (from the text before the year). Every entry parsed this way has a parse warning, and the report's confidence line says `medium`
3. Parses `.bib` entries with a tolerant BibTeX parser (handles concatenation, string macros, common quirks)
4. If `--check-body` is enabled, scans the `.tex` body for `\cite{...}`, `\citep{...}`, `\citet{...}`, `\citeauthor{...}`, `\autocite{...}`, etc., to detect orphans and missing citations

### PDF and Word files

The script refuses PDF and Word input with exit code 2. Transcribe the reference list into a `.bib`, then check it:

1. Get the text. For a PDF, run `pdftotext -layout <file>.pdf -`. If `pdftotext` is missing or produces garbled text, use the Read tool. For Word, run `pandoc -t plain --wrap=none <file>.docx`. On a Mac without pandoc, use `textutil -convert txt -stdout <file>.docx`; it prints list numbers as bullets, so count the items to recover the numbering. If the PDF is a published paper rather than the user's own manuscript, the licence hook's rules apply to reading it, including its reference list.
2. Find the reference list and write one BibTeX entry per item to `<file>.transcribed.bib`, beside the original. Copy each field exactly as printed: authors, title, journal or venue, volume, number, pages, year, and any DOI or arXiv ID. Put a DOI in `doi = {...}`. Put an arXiv ID in `eprint = {...}` with `archiveprefix = {arXiv}`. The parser reads identifiers only from those fields, or an arXiv ID from an arxiv.org link in `url`; it ignores identifiers in `note`, `howpublished` or the title. Do not correct anything, fill gaps from memory or look anything up, as the check is meant to find errors in the manuscript. Use `--` for page ranges and `and` between authors. Key each entry by its citation in the text: `ref1` for `[1]`, or `maldacena1999` for "(Maldacena, 1999)". Omit fields not given in the list.
3. Compare the entry count with the numbered or listed items. If they differ, fix the transcription.
4. Run the script on the `.bib` with `--transcribed-from <file>.pdf` (or `.docx`). Tell the user that Claude transcribed the entries and that a flagged entry should be checked against the original before correction.

## Verification logic

For each parsed reference, the script attempts identification in this order:

1. **DOI present** → Crossref `works/{doi}` (authoritative, no fuzzy matching needed)
2. **arXiv ID present** → arXiv API direct lookup
3. **Otherwise** → fuzzy bibliographic search:
   - Crossref `works?query.bibliographic=...` with title + first author
   - OpenAlex `works?search=...`
   - Semantic Scholar `graph/v1/paper/search`

Each fuzzy-search candidate is scored out of 100:
- Title, 0 to 60: `rapidfuzz.fuzz.token_sort_ratio` of the two lowercased titles, divided by 100 and multiplied by 60
- Authors, 0 to 25: the share of the cited surnames that appear among the candidate's surnames (not Jaccard: extra authors on the candidate cost nothing), multiplied by 25
- Year, 0 to 15: +15 if equal, +7 if one year apart, else 0

A score >= 75 gives `verified` if no mismatch was recorded, or `metadata_mismatch` otherwise. A score of 50 to 74 gives `low_confidence`; below 50, no match is recorded. A mismatch is recorded if title similarity is between 0.5 and 0.85, fewer than half the cited surnames are found, or the years differ. A DOI or arXiv ID match is accepted as the work regardless of score, with status `verified` if no mismatch was recorded or `metadata_mismatch` otherwise.

Distinguish a failed lookup from a service reporting no record. Network errors, timeouts, HTTP 429 after retries, 5xx replies and unreadable replies are failures. HTTP 404 and searches with zero results are answers. The script caches only answers, never failures. If no match is found and a Crossref, OpenAlex or arXiv lookup failed, the status is `lookup_failed`, never `not_found`. If only Semantic Scholar failed, the status is `not_found` with a note, and the result is not cached.

### URL liveness gotchas (non-DOI links)

When checking raw URLs (reports, blog posts, institutional pages) rather than DOIs:

- **HTTP 403 does not mean dead.** Many think-tank and institutional sites bot-block curl and plain
  fetchers while serving browsers fine. Before
  declaring a link broken, cross-confirm existence via a web search that surfaces the same URL, or a
  browser-grade fetch. Record "exists, bot-blocked" rather than "broken".
- **Follow 301s to the new canonical and cite that.** Institutional URLs rot by rebrand, not only by
  404: when an organisation renames, its old paths often 301 to a new domain. The old link "works"
  today; the new one is the durable citation.
- **Match the fetched title against the claimed work**, not just the status code. A 200 response for the
  wrong paper (from moved slugs or reused IDs) is worse than a 404, as nothing flags the error.
  Compare the result of `curl | grep '<title>'` with the citation text for a quick check.

## Status taxonomy

Each reference is classified into exactly one of:

| Status | Symbol | Meaning |
|---|---|---|
| `verified` | ✅ | High-confidence match; metadata agrees |
| `metadata_mismatch` | ⚠️ | Match found but ≥1 field disagrees (which fields are listed) |
| `low_confidence` | ⚠️ | Best match below threshold; top candidate shown for human review |
| `not_found` | ❌ | Every lookup answered, but none returned a plausible match (possibly fabricated) |
| `lookup_failed` | 📡 | No match found, but a Crossref, OpenAlex or arXiv lookup failed because of a network or service error or rate limit. The reference was not fully checked; this is not evidence of fabrication. Run it again |
| `unparseable` | 🔧 | Could not extract structured fields from the entry |
| `duplicate` | 🔁 | Same work cited under two keys (only the later occurrence flagged) |
| `orphan` | 👻 | In bibliography but not cited in body (`.tex` only) |
| `missing` | 🚫 | Cited in body but absent from bibliography (`.tex` only) |

## Output format

The report is a single Markdown file structured as:

```
# Reference verification report
## Summary
| Status | Count |
| --- | --- |
| ✅ Verified | 42 |
| ⚠️ Metadata mismatch | 3 |
| ⚠️ Low confidence | 2 |
| ❌ Not found | 1 |
| 📡 Lookup failed (not checked) | 0 |
| 🔧 Unparseable | 0 |
| 🔁 Duplicate | 1 |
| 👻 Orphan | 0 |
| 🚫 Missing | 0 |

**Total references:** 49
**Confidence:** high (parsed from .bib source)

## Issues requiring attention

### ❌ Not found
- **smith2024quantum** — "Quantum entanglement in non-Hermitian systems"
  Authors: J. Smith, A. Doe (2024)
  Searched: Crossref, OpenAlex, Semantic Scholar, arXiv — no match
  *Likely fabricated. Verify with the author or remove.*

### ⚠️ Metadata mismatch
- **jones2021topology** — DOI matches but year disagrees
  Cited: 2021 → Crossref: 2020
  Cited authors: M. Jones → Crossref: M. Jones, R. Patel
  ...

## All verified references
(collapsed by default — full list)
```

## Caching

The cache defaults to `~/.cache/refverify/cache-v2.json`. Its keys are `(normalised_title, first_author_surname, year)` for fuzzy lookups, `doi` for direct DOI lookups and the arXiv ID for arXiv lookups. It stores service answers, including "no record", but never failed lookups, so offline checks do not leave cached `not_found` verdicts. A fuzzy result is not cached if any of its three searches failed. The older `cache.json` in the same folder is not read. Entries expire after 30 days. Re-running the verifier on a revised draft is therefore fast: only new or changed entries require network requests.

To force a fresh run, use `--no-cache`. To clear the cache entirely:
```bash
rm -rf ~/.cache/refverify/
```

## Failure modes and limitations

- **Field coverage is uneven.** Crossref is strongest for journal articles with DOIs, OpenAlex has broader coverage including some non-DOI works, and Semantic Scholar is best for CS/ML. arXiv is the only reliable source for preprints without DOIs. The sequence of fallback services handles most cases, but real works in books, theses and grey literature may be absent from every database and still receive `not_found`. Treat `not_found` as "needs human review", not as "definitely fabricated". Report a `lookup_failed` reference as unchecked, never as missing: it has not been checked at all. Re-run before drawing any conclusion.
- **Transcription can slip.** For a PDF or Word file, a flag may come from a transcription error rather than the manuscript. Check each flagged entry against the original before correcting it, and use `.tex` or `.bib` source when it exists.
- **Author name disambiguation is hard.** "J. Smith" is not unique. The scorer uses surname overlap rather than full-name matching, which is more robust to initials/middle-name variations but less precise.
- **Title fuzzy matching has failure modes.** Very short titles ("Attention is all you need") and titles with subtitles can confuse the matcher. The composite score threshold is conservative; expect occasional `low_confidence` flags on legitimate references.
- **Crossref has lag.** Recently published papers (within ~2 weeks) may not be indexed yet. If a recent reference flags as `not_found`, check arXiv or the publisher's site directly.

## Re-running after fixes

Workflow for iterating:
1. Run the verifier; review the report
2. Fix flagged entries in the source `.bib` or manuscript. For PDF or Word input, fix the transcribed `.bib` too.
3. Re-run; cached entries are skipped, so this is fast
4. Iterate until the summary table shows only `verified` (and optionally accepted `low_confidence` cases)

For CI integration, use `--strict` to fail the build on any non-verified reference.
