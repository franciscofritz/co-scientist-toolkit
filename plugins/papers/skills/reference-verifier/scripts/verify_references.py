#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27",
#     "rapidfuzz>=3",
#     "bibtexparser>=1.4,<2",
# ]
# ///
"""
Reference verifier: check each reference in a paper against authoritative
bibliographic databases (Crossref, OpenAlex, Semantic Scholar, arXiv).

Usage:
    uv run --script verify_references.py <input_file> [options]

uv installs the libraries listed above on first use.

See SKILL.md for full documentation.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
import warnings
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any
from urllib.parse import quote_plus

# --- Dependency imports with helpful errors --------------------------------

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx", file=sys.stderr)
    sys.exit(2)

try:
    from rapidfuzz import fuzz
except ImportError:
    print("ERROR: rapidfuzz is required. Install with: pip install rapidfuzz", file=sys.stderr)
    sys.exit(2)

# Optional: bibtexparser for cleaner .bib parsing
try:
    import bibtexparser
    HAS_BIBTEXPARSER = True
except ImportError:
    HAS_BIBTEXPARSER = False


# --- Constants -------------------------------------------------------------

CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 days
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "refverify"
CACHE_FILE_NAME = "cache-v2.json"  # v1 files may hold misses that were really failed lookups
HTTP_TIMEOUT = 20.0
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5

VERIFIED_THRESHOLD = 75
LOW_CONFIDENCE_THRESHOLD = 50

CROSSREF_BASE = "https://api.crossref.org"
OPENALEX_BASE = "https://api.openalex.org"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
ARXIV_BASE = "https://export.arxiv.org/api"


# --- Data structures -------------------------------------------------------

@dataclass
class Reference:
    """A parsed bibliographic entry from the input."""
    key: str                          # citation key (e.g. "smith2021quantum") or sequential ID for non-tex
    raw: str                          # original raw text of the entry
    source: str                       # "bib", "bbl"
    # Parsed fields (best-effort)
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)  # full author strings as parsed
    year: Optional[int] = None
    venue: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    entry_type: Optional[str] = None  # @article, @inproceedings, etc.
    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    """The outcome of verifying one Reference."""
    ref: Reference
    status: str                                    # see status taxonomy in SKILL.md
    score: Optional[float] = None
    matched_record: Optional[dict[str, Any]] = None
    matched_source: Optional[str] = None           # "crossref" | "openalex" | "semantic_scholar" | "arxiv"
    mismatches: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    candidates_tried: list[str] = field(default_factory=list)


# --- Lookup failures ------------------------------------------------------

class LookupFailed(Exception):
    """A service did not give an answer (network error, timeout, 429, 5xx, unreadable reply).

    This is different from a service answering that it has no record (HTTP 404, or a
    search with zero results). Only answers are cached; a failure never is.
    """


# --- Cache -----------------------------------------------------------------

class Cache:
    """Trivial JSON cache keyed by lookup signature."""

    def __init__(self, cache_dir: Path, enabled: bool = True):
        self.enabled = enabled
        self.cache_dir = cache_dir
        self.cache_file = cache_dir / CACHE_FILE_NAME
        self.data: dict[str, dict[str, Any]] = {}
        if enabled:
            cache_dir.mkdir(parents=True, exist_ok=True)
            if self.cache_file.exists():
                try:
                    self.data = json.loads(self.cache_file.read_text())
                except (json.JSONDecodeError, OSError):
                    self.data = {}

    @staticmethod
    def make_key(*parts: str) -> str:
        canon = "||".join((p or "").lower().strip() for p in parts)
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:24]

    def get(self, key: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        entry = self.data.get(key)
        if not entry:
            return None
        if time.time() - entry.get("cached_at", 0) > CACHE_TTL_SECONDS:
            return None
        return entry.get("value")

    def set(self, key: str, value: dict[str, Any]) -> None:
        if not self.enabled:
            return
        self.data[key] = {"cached_at": time.time(), "value": value}

    def flush(self) -> None:
        if not self.enabled:
            return
        try:
            self.cache_file.write_text(json.dumps(self.data))
        except OSError as e:
            warnings.warn(f"Could not write cache: {e}")


# --- BibTeX parsing --------------------------------------------------------

def _strip_braces(s: str) -> str:
    """Remove outermost balanced braces and convert LaTeX accents minimally."""
    s = s.strip()
    while s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
    # Strip nested braces around individual words (common in BibTeX titles)
    s = re.sub(r"\{([^{}]*)\}", r"\1", s)
    # Decode common LaTeX accents (very partial — full conversion would require a real parser)
    repls = [
        (r"\\'\{?([aeiouAEIOU])\}?", r"\1"),    # \'e -> e
        (r'\\"\{?([aeiouAEIOU])\}?', r"\1"),    # \"o -> o
        (r"\\`\{?([aeiouAEIOU])\}?", r"\1"),
        (r"\\\^\{?([aeiouAEIOU])\}?", r"\1"),
        (r"\\~\{?([nN])\}?", r"\1"),
        (r"\\&", "&"),
        (r"\\%", "%"),
        (r"~", " "),
        (r"--+", "-"),
    ]
    for pat, rep in repls:
        s = re.sub(pat, rep, s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_bibtex_authors(raw: str) -> list[str]:
    """Split a BibTeX author field on ' and ' (case-insensitive, word-boundary)."""
    raw = _strip_braces(raw)
    # BibTeX uses ' and ' (lowercase, surrounded by spaces) as the separator
    parts = re.split(r"\s+and\s+", raw)
    return [p.strip() for p in parts if p.strip()]


def parse_bib_file(path: Path) -> list[Reference]:
    """Parse a .bib file. Uses bibtexparser if available, falls back to a tolerant regex parser."""
    text = path.read_text(encoding="utf-8", errors="replace")
    refs = []

    if HAS_BIBTEXPARSER:
        try:
            db = bibtexparser.loads(text)
            for entry in db.entries:
                ref = Reference(
                    key=entry.get("ID", entry.get("id", f"_unnamed_{len(refs)}")),
                    raw=str(entry),
                    source="bib",
                    entry_type=entry.get("ENTRYTYPE", entry.get("entrytype")),
                    title=_strip_braces(entry["title"]) if "title" in entry else None,
                    year=_extract_year(entry.get("year")),
                    venue=_strip_braces(entry.get("journal") or entry.get("booktitle") or entry.get("publisher") or ""),
                    volume=entry.get("volume"),
                    pages=entry.get("pages"),
                    doi=_clean_doi(entry.get("doi")),
                    url=entry.get("url"),
                )
                if "author" in entry:
                    ref.authors = _parse_bibtex_authors(entry["author"])
                if not ref.venue:
                    ref.venue = None
                # arxiv ID often in 'eprint' or 'archiveprefix' fields
                if entry.get("eprint") and (entry.get("archiveprefix", "").lower() == "arxiv" or "arxiv" in (entry.get("url", "").lower())):
                    ref.arxiv_id = entry["eprint"]
                # also mine from URL
                if not ref.arxiv_id and ref.url:
                    m = re.search(r"arxiv\.org/(?:abs|pdf)/([\w\-./]+?)(?:v\d+)?(?:\.pdf)?$", ref.url)
                    if m:
                        ref.arxiv_id = m.group(1)
                refs.append(ref)
            return refs
        except Exception as e:
            warnings.warn(f"bibtexparser failed ({e}); falling back to regex parser")

    # Fallback: tolerant regex-based parser
    return _parse_bib_regex(text)


def _parse_bib_regex(text: str) -> list[Reference]:
    """Tolerant fallback BibTeX parser — handles most common cases."""
    refs = []
    # Match @entrytype{key, ... } with balanced braces
    i = 0
    while i < len(text):
        m = re.search(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text[i:])
        if not m:
            break
        entry_type = m.group(1).lower()
        if entry_type in ("string", "preamble", "comment"):
            i += m.end()
            continue
        key = m.group(2)
        start = i + m.end()
        # Find matching closing brace
        depth = 1
        j = start
        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        body = text[start:j-1]
        i = j

        # Parse field = value pairs
        fields: dict[str, str] = {}
        for fm in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|\d+)", body):
            fname, fval = fm.group(1).lower(), fm.group(2)
            if fval.startswith("{") or fval.startswith('"'):
                fval = fval[1:-1]
            fields[fname] = fval.strip()

        ref = Reference(
            key=key,
            raw=text[i-1:j],
            source="bib",
            entry_type=entry_type,
            title=_strip_braces(fields["title"]) if "title" in fields else None,
            year=_extract_year(fields.get("year")),
            venue=_strip_braces(fields.get("journal") or fields.get("booktitle") or fields.get("publisher") or "") or None,
            volume=fields.get("volume"),
            pages=fields.get("pages"),
            doi=_clean_doi(fields.get("doi")),
            url=fields.get("url"),
        )
        if "author" in fields:
            ref.authors = _parse_bibtex_authors(fields["author"])
        if fields.get("eprint") and "arxiv" in (fields.get("archiveprefix", "") + fields.get("url", "")).lower():
            ref.arxiv_id = fields["eprint"]
        refs.append(ref)
    return refs


def _extract_year(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    m = re.search(r"\b(1[89]\d{2}|20\d{2})\b", str(s))
    return int(m.group(1)) if m else None


def _clean_doi(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^doi:\s*", "", s, flags=re.IGNORECASE)
    return s.strip() or None


# --- .tex parsing ----------------------------------------------------------

def find_bib_for_tex(tex_path: Path) -> tuple[Optional[Path], Optional[Path]]:
    """Locate the .bib (preferred) or .bbl (fallback) for a .tex file."""
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    bib_match = re.search(r"\\bibliography\{([^}]+)\}", text)
    if bib_match:
        names = [n.strip() for n in bib_match.group(1).split(",")]
        for name in names:
            candidate = (tex_path.parent / (name if name.endswith(".bib") else name + ".bib"))
            if candidate.exists():
                return candidate, None
    # biblatex \addbibresource{file.bib}
    for m in re.finditer(r"\\addbibresource\{([^}]+)\}", text):
        candidate = tex_path.parent / m.group(1)
        if candidate.exists():
            return candidate, None
    # Fall back to .bbl with same stem
    bbl = tex_path.with_suffix(".bbl")
    if bbl.exists():
        return None, bbl
    # Or any .bib in the same dir
    bibs = list(tex_path.parent.glob("*.bib"))
    if len(bibs) == 1:
        return bibs[0], None
    return None, None


def parse_bbl_file(path: Path) -> list[Reference]:
    """Parse a .bbl file. Best-effort across common BibTeX styles."""
    text = path.read_text(encoding="utf-8", errors="replace")
    # Strip preamble before first \bibitem
    first = text.find("\\bibitem")
    if first == -1:
        warnings.warn(f"No \\bibitem entries found in {path}")
        return []
    text = text[first:]
    # Stop at \end{thebibliography}
    end = text.find("\\end{thebibliography}")
    if end != -1:
        text = text[:end]

    # Split on \bibitem
    chunks = re.split(r"\\bibitem", text)[1:]  # first split is empty
    refs = []
    for idx, chunk in enumerate(chunks):
        chunk = chunk.strip()
        # \bibitem[opt]{key} body
        m = re.match(r"(?:\[[^\]]*\])?\s*\{([^}]+)\}\s*(.*)", chunk, re.DOTALL)
        if not m:
            refs.append(Reference(key=f"bbl_{idx}", raw=chunk, source="bbl",
                                  parse_warnings=["could not parse \\bibitem header"]))
            continue
        key, body = m.group(1), m.group(2).strip()

        # Heuristic field extraction from formatted body
        ref = Reference(key=key, raw=body, source="bbl")
        ref.year = _extract_year(body)
        # DOI (rare in .bbl but possible)
        doi_m = re.search(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", body, re.IGNORECASE)
        if doi_m:
            ref.doi = doi_m.group(1).rstrip(".,;")
        # arXiv ID
        arx_m = re.search(r"arxiv:?\s*(\d{4}\.\d{4,5}(?:v\d+)?|[\w\-]+/\d{7}(?:v\d+)?)", body, re.IGNORECASE)
        if arx_m:
            ref.arxiv_id = arx_m.group(1)
        # Title — heuristic: most styles put title in \emph{...}, \textit{...}, or quoted
        title_m = (re.search(r"\\(?:emph|textit|newblock\s+\\textit)\{([^}]+)\}", body)
                   or re.search(r"``([^']+)''", body)
                   or re.search(r'"([^"]+)"', body))
        if title_m:
            ref.title = _strip_braces(title_m.group(1))
        # Author surnames — first chunk before first period or comma+space, rough
        # Try to grab everything up to the year
        if ref.year:
            pre_year = body.split(str(ref.year))[0]
            # Strip trailing punctuation and "(", common before year
            pre_year = re.sub(r"[\s\(]+$", "", pre_year)
            authors = re.split(r"\s+and\s+|,\s+(?=[A-Z])", pre_year)
            ref.authors = [_strip_braces(a) for a in authors if a.strip()][:10]
        ref.parse_warnings.append("parsed from .bbl — fields are heuristic")
        refs.append(ref)
    return refs


def extract_citations_from_tex_body(tex_path: Path) -> set[str]:
    """Return the set of citation keys actually \\cite'd in the body."""
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    # Strip comments
    text = re.sub(r"(?<!\\)%.*", "", text)
    # Match \cite, \citep, \citet, \citeauthor, \citeyear, \autocite, \parencite, \textcite, \footcite, \nocite
    pattern = r"\\(?:no|paren|text|foot|auto|smart)?cite[a-z*]*\s*(?:\[[^\]]*\])?\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}"
    keys = set()
    for m in re.finditer(pattern, text):
        for k in m.group(1).split(","):
            keys.add(k.strip())
    return keys


def expand_inputs(tex_path: Path, _seen: Optional[set[Path]] = None) -> str:
    """Recursively inline \\input{} and \\include{} for body-citation extraction."""
    if _seen is None:
        _seen = set()
    if tex_path in _seen or not tex_path.exists():
        return ""
    _seen.add(tex_path)
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"(?<!\\)%.*", "", text)
    def replace(m):
        name = m.group(1).strip()
        sub = tex_path.parent / (name if name.endswith(".tex") else name + ".tex")
        return expand_inputs(sub, _seen)
    text = re.sub(r"\\(?:input|include)\{([^}]+)\}", replace, text)
    return text


# --- Verification: API clients --------------------------------------------

class APIClient:
    """Async HTTP client wrapper with retries, polite-pool support, and rate limiting."""

    def __init__(self, contact_email: Optional[str], semantic_scholar_key: Optional[str]):
        self.contact_email = contact_email
        self.semantic_scholar_key = semantic_scholar_key
        ua = "ReferenceVerifier/1.0"
        if contact_email:
            ua += f" (mailto:{contact_email})"
        self.client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": ua})

    async def close(self):
        await self.client.aclose()

    async def _get(self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Optional[dict]:
        """GET and decode JSON.

        Returns the decoded JSON when the service answers, None when it answers 404
        (no such record), and raises LookupFailed when no answer could be had.
        """
        last_error = "no response"
        for attempt in range(MAX_RETRIES):
            try:
                r = await self.client.get(url, params=params, headers=headers)
                if r.status_code == 404:
                    return None
                if r.status_code == 429:
                    # Rate limited: back off harder
                    last_error = "HTTP 429 (rate limited)"
                    await asyncio.sleep((attempt + 2) * RETRY_BACKOFF_BASE * 2)
                    continue
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
                last_error = f"{type(e).__name__}: {e}"
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
            except ValueError as e:  # unreadable JSON in a 200 reply
                raise LookupFailed(f"{url}: unreadable reply ({e})") from e
        warnings.warn(f"Request to {url} failed after {MAX_RETRIES} attempts: {last_error}")
        raise LookupFailed(f"{url}: {last_error}")

    # ---- Crossref ----

    async def crossref_by_doi(self, doi: str) -> Optional[dict]:
        """The normalised record, None if Crossref has no such DOI; raises LookupFailed."""
        data = await self._get(f"{CROSSREF_BASE}/works/{quote_plus(doi)}")
        if data is None:
            return None
        if data.get("status") != "ok":
            raise LookupFailed(f"Crossref returned status {data.get('status')!r} for DOI {doi}")
        return _normalise_crossref(data["message"])

    async def crossref_search(self, title: str, author: Optional[str], year: Optional[int]) -> list:
        if not title:
            return []
        params = {"query.bibliographic": title, "rows": 5}
        if author:
            params["query.author"] = author
        data = await self._get(f"{CROSSREF_BASE}/works", params=params)
        if data is None:
            return []
        if data.get("status") != "ok":
            raise LookupFailed(f"Crossref search returned status {data.get('status')!r}")
        items = data.get("message", {}).get("items", [])
        return [_normalise_crossref(it) for it in items]

    # ---- OpenAlex ----

    async def openalex_search(self, title: str, author: Optional[str], year: Optional[int]) -> list:
        if not title:
            return []
        params = {"search": title, "per_page": 5}
        if self.contact_email:
            params["mailto"] = self.contact_email
        data = await self._get(f"{OPENALEX_BASE}/works", params=params)
        if data is None:
            return []
        return [_normalise_openalex(w) for w in data.get("results", [])]

    # ---- Semantic Scholar ----

    async def semantic_scholar_search(self, title: str) -> list:
        if not title:
            return []
        params = {
            "query": title,
            "limit": 5,
            "fields": "title,authors,year,venue,externalIds",
        }
        headers = {}
        if self.semantic_scholar_key:
            headers["x-api-key"] = self.semantic_scholar_key
        data = await self._get(f"{SEMANTIC_SCHOLAR_BASE}/paper/search", params=params, headers=headers)
        if data is None:
            return []
        return [_normalise_semantic_scholar(p) for p in data.get("data", [])]

    # ---- arXiv ----

    async def arxiv_lookup(self, arxiv_id: str) -> Optional[dict]:
        """The normalised record, None if arXiv has no such entry; raises LookupFailed."""
        # arXiv API returns Atom XML, not JSON
        url = f"{ARXIV_BASE}/query"
        params = {"id_list": arxiv_id, "max_results": 1}
        last_error = "no response"
        for attempt in range(MAX_RETRIES):
            try:
                r = await self.client.get(url, params=params)
                if r.status_code == 200:
                    return _parse_arxiv_atom(r.text)
                last_error = f"HTTP {r.status_code}"
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_error = f"{type(e).__name__}: {e}"
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
        raise LookupFailed(f"{url}: {last_error}")


# --- API result normalisation ---------------------------------------------

def _normalise_crossref(item: dict) -> dict:
    title = (item.get("title") or [""])[0]
    authors = []
    for a in item.get("author", []) or []:
        family = a.get("family", "")
        given = a.get("given", "")
        if family or given:
            authors.append(f"{given} {family}".strip())
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        d = item.get(k, {}).get("date-parts", [[None]])
        if d and d[0] and d[0][0]:
            year = d[0][0]
            break
    venue = (item.get("container-title") or [None])[0]
    return {
        "source": "crossref",
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "doi": item.get("DOI"),
        "volume": item.get("volume"),
        "pages": item.get("page"),
        "type": item.get("type"),
        "url": item.get("URL"),
    }


def _normalise_openalex(work: dict) -> dict:
    authors = [a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])]
    venue = None
    pl = work.get("primary_location") or {}
    if pl.get("source"):
        venue = pl["source"].get("display_name")
    return {
        "source": "openalex",
        "title": work.get("title", ""),
        "authors": [a for a in authors if a],
        "year": work.get("publication_year"),
        "venue": venue,
        "doi": (work.get("doi") or "").replace("https://doi.org/", "") or None,
        "type": work.get("type"),
        "url": work.get("doi") or work.get("id"),
    }


def _normalise_semantic_scholar(paper: dict) -> dict:
    authors = [a.get("name", "") for a in paper.get("authors", [])]
    ext = paper.get("externalIds", {}) or {}
    return {
        "source": "semantic_scholar",
        "title": paper.get("title", ""),
        "authors": [a for a in authors if a],
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "doi": ext.get("DOI"),
        "arxiv_id": ext.get("ArXiv"),
        "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}" if paper.get("paperId") else None,
    }


def _parse_arxiv_atom(xml: str) -> Optional[dict]:
    """Minimal Atom XML parser for arXiv results."""
    title_m = re.search(r"<entry>.*?<title>(.*?)</title>", xml, re.DOTALL)
    if not title_m:
        return None
    title = re.sub(r"\s+", " ", title_m.group(1)).strip()
    authors = re.findall(r"<author>\s*<name>(.*?)</name>", xml, re.DOTALL)
    pub_m = re.search(r"<published>(\d{4})", xml)
    year = int(pub_m.group(1)) if pub_m else None
    doi_m = re.search(r"<arxiv:doi[^>]*>(.*?)</arxiv:doi>", xml)
    return {
        "source": "arxiv",
        "title": title,
        "authors": [a.strip() for a in authors],
        "year": year,
        "doi": doi_m.group(1).strip() if doi_m else None,
        "venue": "arXiv",
    }


# --- Scoring ---------------------------------------------------------------

def _surname(name: str) -> str:
    """Best-effort surname extraction."""
    name = name.strip()
    if "," in name:
        # "Smith, John" -> "Smith"
        return name.split(",")[0].strip().lower()
    # "John Smith" or "J. Smith" -> "Smith"
    parts = name.split()
    if parts:
        return parts[-1].lower().strip(".,")
    return name.lower()


def score_match(ref: Reference, candidate: dict) -> tuple[float, list[str]]:
    """Score a candidate match against the parsed reference. Returns (score, mismatches)."""
    score = 0.0
    mismatches = []

    # Title similarity (0–60 points)
    if ref.title and candidate.get("title"):
        sim = fuzz.token_sort_ratio(ref.title.lower(), candidate["title"].lower()) / 100.0
        score += 60 * sim
        if sim < 0.85 and sim > 0.5:
            mismatches.append(f"title differs (sim={sim:.2f})")

    # Author surname overlap (0–25 points)
    if ref.authors and candidate.get("authors"):
        ref_surnames = {_surname(a) for a in ref.authors if a}
        cand_surnames = {_surname(a) for a in candidate["authors"] if a}
        if ref_surnames and cand_surnames:
            overlap = len(ref_surnames & cand_surnames) / max(len(ref_surnames), 1)
            score += 25 * overlap
            if overlap < 0.5:
                mismatches.append(f"author surnames differ (overlap={overlap:.2f})")

    # Year (0–15 points)
    if ref.year and candidate.get("year"):
        diff = abs(ref.year - candidate["year"])
        if diff == 0:
            score += 15
        elif diff == 1:
            score += 7
            mismatches.append(f"year off by 1 (cited {ref.year}, found {candidate['year']})")
        else:
            mismatches.append(f"year differs (cited {ref.year}, found {candidate['year']})")

    return score, mismatches


# --- Verification driver --------------------------------------------------

async def verify_one(ref: Reference, client: APIClient, cache: Cache) -> VerificationResult:
    """Verify a single reference, trying lookups in priority order."""
    result = VerificationResult(ref=ref, status="not_found")
    failed: list[str] = []  # lookups that got no answer; these are never cached

    # Unparseable check — no usable identifying info
    if not ref.title and not ref.doi and not ref.arxiv_id:
        result.status = "unparseable"
        result.notes.append("No title, DOI, or arXiv ID could be extracted from this entry.")
        return result

    # 1. DOI direct lookup
    if ref.doi:
        result.candidates_tried.append(f"crossref:doi:{ref.doi}")
        cache_key = Cache.make_key("doi", ref.doi)
        cached = cache.get(cache_key)
        candidate = None
        doi_answered = True
        if cached is not None:
            candidate = cached if cached else None
        else:
            try:
                candidate = await client.crossref_by_doi(ref.doi)
                cache.set(cache_key, candidate or {})
            except LookupFailed as e:
                doi_answered = False
                failed.append(f"crossref:doi:{ref.doi}")
                warnings.warn(f"Crossref lookup of DOI {ref.doi} failed: {e}")
        if candidate:
            score, mismatches = score_match(ref, candidate)
            # DOI lookup is authoritative — even with metadata mismatch, the work exists
            result.matched_record = candidate
            result.matched_source = "crossref"
            result.score = score
            result.mismatches = mismatches
            result.status = "verified" if not mismatches else "metadata_mismatch"
            return result
        elif doi_answered:
            result.notes.append(f"DOI {ref.doi} did not resolve via Crossref.")

    # 2. arXiv direct lookup
    if ref.arxiv_id:
        result.candidates_tried.append(f"arxiv:{ref.arxiv_id}")
        cache_key = Cache.make_key("arxiv", ref.arxiv_id)
        cached = cache.get(cache_key)
        candidate = None
        if cached is not None:
            candidate = cached if cached else None
        else:
            try:
                candidate = await client.arxiv_lookup(ref.arxiv_id)
                cache.set(cache_key, candidate or {})
            except LookupFailed as e:
                failed.append(f"arxiv:{ref.arxiv_id}")
                warnings.warn(f"arXiv lookup of {ref.arxiv_id} failed: {e}")
        if candidate:
            score, mismatches = score_match(ref, candidate)
            result.matched_record = candidate
            result.matched_source = "arxiv"
            result.score = score
            result.mismatches = mismatches
            result.status = "verified" if not mismatches else "metadata_mismatch"
            return result

    # 3. Fuzzy bibliographic search — try Crossref, OpenAlex, Semantic Scholar
    if not ref.title:
        if failed:
            result.status = "lookup_failed"
            result.notes.append("No title for a fuzzy search, and the DOI/arXiv lookup gave no answer.")
        else:
            result.status = "unparseable"
            result.notes.append("No title for fuzzy lookup; only DOI/arXiv attempted.")
        return result

    first_author_surname = _surname(ref.authors[0]) if ref.authors else None
    cache_key = Cache.make_key("fuzzy", ref.title, first_author_surname or "", str(ref.year or ""))
    cached = cache.get(cache_key)
    if cached is not None:
        # Cached fuzzy result
        if cached.get("status") == "found":
            result.matched_record = cached["record"]
            result.matched_source = cached["source"]
            result.score = cached["score"]
            result.mismatches = cached.get("mismatches", [])
            result.status = cached["final_status"]
        else:
            result.status = "not_found"
            result.notes.append("(cached) No match found across all sources.")
        return result

    best_candidate = None
    best_score = 0.0
    best_mismatches: list[str] = []
    best_source = None

    for source_name, fn in [
        ("crossref", lambda: client.crossref_search(ref.title, first_author_surname, ref.year)),
        ("openalex", lambda: client.openalex_search(ref.title, first_author_surname, ref.year)),
        ("semantic_scholar", lambda: client.semantic_scholar_search(ref.title)),
    ]:
        result.candidates_tried.append(source_name)
        try:
            candidates = await fn()
        except Exception as e:  # LookupFailed, or anything unexpected: no answer either way
            warnings.warn(f"{source_name} search failed for '{ref.title[:60]}': {e}")
            failed.append(source_name)
            continue
        if not candidates:
            continue
        for c in candidates:
            score, mismatches = score_match(ref, c)
            if score > best_score:
                best_score = score
                best_candidate = c
                best_mismatches = mismatches
                best_source = source_name
        # Early exit: high-confidence match found, no need to try further sources
        if best_score >= VERIFIED_THRESHOLD:
            break

    if best_candidate is None or best_score < LOW_CONFIDENCE_THRESHOLD:
        # Crossref and OpenAlex (and arXiv, for a cited arXiv ID) must have answered for a
        # "not found". Semantic Scholar alone failing, which it often does without an API key,
        # leaves the verdict standing but uncached, so a later run asks it again.
        core_failed = [f for f in failed if f != "semantic_scholar"]
        if core_failed:
            result.status = "lookup_failed"
            result.notes.append("No answer from: " + ", ".join(failed) + ". Not reported as not found.")
            return result
        result.status = "not_found"
        if failed:
            result.notes.append("Semantic Scholar could not be reached; Crossref and OpenAlex found no match.")
        else:
            cache.set(cache_key, {"status": "miss"})
        return result

    result.matched_record = best_candidate
    result.matched_source = best_source
    result.score = best_score
    result.mismatches = best_mismatches
    if best_score >= VERIFIED_THRESHOLD:
        result.status = "verified" if not best_mismatches else "metadata_mismatch"
    else:
        result.status = "low_confidence"

    if failed:
        result.notes.append("Result may be incomplete: no answer from " + ", ".join(failed) + ".")
        return result

    cache.set(cache_key, {
        "status": "found",
        "record": best_candidate,
        "source": best_source,
        "score": best_score,
        "mismatches": best_mismatches,
        "final_status": result.status,
    })
    return result


async def verify_all(refs: list[Reference], client: APIClient, cache: Cache, concurrency: int) -> list[VerificationResult]:
    sem = asyncio.Semaphore(concurrency)

    async def bounded(r: Reference) -> VerificationResult:
        async with sem:
            return await verify_one(r, client, cache)

    return await asyncio.gather(*[bounded(r) for r in refs])


# --- Post-processing: duplicates, orphans, missing -------------------------

def find_duplicates(refs: list[Reference], results: list[VerificationResult]) -> set[str]:
    """Identify duplicate references by DOI or normalised title. Returns keys to flag."""
    seen_doi: dict[str, str] = {}
    seen_title: dict[str, str] = {}
    duplicates = set()
    for ref in refs:
        if ref.doi:
            doi_norm = ref.doi.lower().strip()
            if doi_norm in seen_doi:
                duplicates.add(ref.key)
            else:
                seen_doi[doi_norm] = ref.key
        if ref.title:
            title_norm = re.sub(r"\W+", "", ref.title.lower())[:100]
            if title_norm and title_norm in seen_title:
                duplicates.add(ref.key)
            else:
                seen_title[title_norm] = ref.key
    return duplicates


# --- Reporter --------------------------------------------------------------

STATUS_SYMBOLS = {
    "verified": "✅",
    "metadata_mismatch": "⚠️",
    "low_confidence": "⚠️",
    "not_found": "❌",
    "lookup_failed": "📡",
    "unparseable": "🔧",
    "duplicate": "🔁",
    "orphan": "👻",
    "missing": "🚫",
}

STATUS_LABELS = {
    "verified": "Verified",
    "metadata_mismatch": "Metadata mismatch",
    "low_confidence": "Low confidence",
    "not_found": "Not found",
    "lookup_failed": "Lookup failed (not checked)",
    "unparseable": "Unparseable",
    "duplicate": "Duplicate",
    "orphan": "Orphan (in bib, not cited)",
    "missing": "Missing (cited, not in bib)",
}


def render_report(
    results: list[VerificationResult],
    orphans: set[str],
    missing: set[str],
    input_path: Path,
    confidence_note: str,
) -> str:
    by_status: dict[str, list[VerificationResult]] = {}
    for r in results:
        by_status.setdefault(r.status, []).append(r)

    lines = []
    lines.append(f"# Reference verification report")
    lines.append(f"")
    lines.append(f"**Input:** `{input_path}`")
    lines.append(f"**Total references parsed:** {len(results)}")
    lines.append(f"**Confidence:** {confidence_note}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|---|---|")
    order = ["verified", "metadata_mismatch", "low_confidence", "not_found", "lookup_failed",
             "unparseable", "duplicate", "orphan", "missing"]
    for s in order:
        count = len(by_status.get(s, []))
        if s == "orphan":
            count = len(orphans)
        elif s == "missing":
            count = len(missing)
        if count > 0 or s == "verified":
            lines.append(f"| {STATUS_SYMBOLS[s]} {STATUS_LABELS[s]} | {count} |")
    lines.append("")

    # Issues requiring attention (everything that isn't verified)
    issue_statuses = ["not_found", "lookup_failed", "metadata_mismatch", "low_confidence", "unparseable", "duplicate"]
    has_issues = any(by_status.get(s) for s in issue_statuses) or orphans or missing
    if has_issues:
        lines.append("## Issues requiring attention")
        lines.append("")
        for s in issue_statuses:
            entries = by_status.get(s, [])
            if not entries:
                continue
            lines.append(f"### {STATUS_SYMBOLS[s]} {STATUS_LABELS[s]} ({len(entries)})")
            lines.append("")
            for r in entries:
                _render_issue(lines, r)
            lines.append("")

        if orphans:
            lines.append(f"### {STATUS_SYMBOLS['orphan']} {STATUS_LABELS['orphan']} ({len(orphans)})")
            lines.append("")
            for k in sorted(orphans):
                lines.append(f"- `{k}` — in bibliography but no `\\cite` found in body")
            lines.append("")

        if missing:
            lines.append(f"### {STATUS_SYMBOLS['missing']} {STATUS_LABELS['missing']} ({len(missing)})")
            lines.append("")
            for k in sorted(missing):
                lines.append(f"- `{k}` — `\\cite`d in body but no entry in bibliography")
            lines.append("")
    else:
        lines.append("## No issues found")
        lines.append("")
        lines.append("All references verified successfully.")
        lines.append("")

    # Verified references (collapsed)
    verified = by_status.get("verified", [])
    if verified:
        lines.append("<details>")
        lines.append(f"<summary><strong>✅ All verified references ({len(verified)})</strong></summary>")
        lines.append("")
        for r in verified:
            t = r.ref.title or "(no title)"
            authors = _format_authors(r.ref.authors)
            year = f" ({r.ref.year})" if r.ref.year else ""
            lines.append(f"- `{r.ref.key}` — {t} — {authors}{year} _[via {r.matched_source}, score={r.score:.0f}]_")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


def _format_authors(authors: list[str], n: int = 3) -> str:
    """Format an author list for display, using ' • ' to avoid comma confusion in 'Last, First' format."""
    if not authors:
        return ""
    shown = authors[:n]
    suffix = f" • +{len(authors) - n} more" if len(authors) > n else ""
    return " • ".join(shown) + suffix


def _render_issue(lines: list[str], r: VerificationResult) -> None:
    """Render one problematic reference as a Markdown block."""
    title = r.ref.title or "(no title parsed)"
    authors = _format_authors(r.ref.authors)
    year_str = f" ({r.ref.year})" if r.ref.year else ""

    lines.append(f"- **`{r.ref.key}`** — {title}")
    if authors:
        lines.append(f"  - Cited authors: {authors}{year_str}")
    if r.ref.doi:
        lines.append(f"  - Cited DOI: `{r.ref.doi}`")
    if r.ref.arxiv_id:
        lines.append(f"  - Cited arXiv: `{r.ref.arxiv_id}`")
    if r.ref.source == "bbl":
        lines.append(f"  - _Parsed from {r.ref.source} (extraction confidence reduced)_")

    if r.matched_record:
        m = r.matched_record
        lines.append(f"  - Best match (score {r.score:.0f}, via {r.matched_source}):")
        lines.append(f"    - Title: {m.get('title', '(none)')}")
        if m.get("authors"):
            lines.append(f"    - Authors: {_format_authors(m['authors'])}")
        if m.get("year"):
            lines.append(f"    - Year: {m['year']}")
        if m.get("doi"):
            lines.append(f"    - DOI: `{m['doi']}`")
        if m.get("venue"):
            lines.append(f"    - Venue: {m['venue']}")

    if r.mismatches:
        lines.append(f"  - **Mismatches:** {'; '.join(r.mismatches)}")
    if r.notes:
        for n in r.notes:
            lines.append(f"  - _{n}_")
    if r.status == "not_found":
        srcs = ", ".join(s for s in r.candidates_tried if not s.startswith("crossref:doi"))
        if srcs:
            lines.append(f"  - Searched: {srcs}")
        lines.append(f"  - **Action: verify with the author or remove. Could be a real reference not in indexed databases (book, thesis, grey literature) — but also a likely sign of fabrication.**")
    if r.status == "lookup_failed":
        tried = ", ".join(r.candidates_tried)
        if tried:
            lines.append(f"  - Tried: {tried}")
        lines.append("  - **Action: this reference was not checked, because a lookup got no answer (network or service error). It is not evidence of fabrication. Run the verifier again; nothing from the failed lookups was cached.**")


# --- Suggestions / diff generation ----------------------------------------

def generate_fix_suggestions(results: list[VerificationResult]) -> str:
    """Generate a human-readable diff of suggested bib fixes."""
    lines = ["# Suggested reference fixes\n"]
    lines.append("Apply these manually after review. Format: cited → suggested.\n\n")
    n = 0
    for r in results:
        if r.status not in ("metadata_mismatch", "low_confidence") or not r.matched_record:
            continue
        n += 1
        m = r.matched_record
        lines.append(f"## `{r.ref.key}`")
        lines.append("")
        if r.ref.title and m.get("title") and r.ref.title.lower() != m["title"].lower():
            lines.append(f"- title:")
            lines.append(f"  - cited: {r.ref.title}")
            lines.append(f"  - suggested: {m['title']}")
        if r.ref.year and m.get("year") and r.ref.year != m["year"]:
            lines.append(f"- year: {r.ref.year} → {m['year']}")
        if not r.ref.doi and m.get("doi"):
            lines.append(f"- doi: (missing) → {m['doi']}")
        if r.ref.venue and m.get("venue") and r.ref.venue.lower() != (m["venue"] or "").lower():
            lines.append(f"- venue:")
            lines.append(f"  - cited: {r.ref.venue}")
            lines.append(f"  - suggested: {m['venue']}")
        lines.append("")
    if n == 0:
        lines.append("\n_No suggestions to make — no entries in metadata_mismatch or low_confidence state._\n")
    return "\n".join(lines)


# --- Main ------------------------------------------------------------------

def detect_input_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".tex",):
        return "tex"
    if ext in (".bib",):
        return "bib"
    if ext in (".pdf", ".docx", ".doc"):
        raise ValueError(
            f"{ext} is not read directly: transcribe its reference list into a .bib "
            f"and run on that, with --transcribed-from {path.name} (see SKILL.md)"
        )
    if ext in (".bbl",):
        return "bbl"
    raise ValueError(f"Unsupported input extension: {ext}")


async def main_async(args) -> int:
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        input_type = detect_input_type(input_path)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    body_text_for_citations: Optional[str] = None
    confidence_note = "high (parsed from .bib source)"

    # --- Extract references based on input type
    if input_type == "tex":
        bib_path, bbl_path = find_bib_for_tex(input_path)
        if bib_path:
            print(f"Found bibliography: {bib_path}")
            refs = parse_bib_file(bib_path)
        elif bbl_path:
            print(f"Found .bbl (no .bib available): {bbl_path}")
            refs = parse_bbl_file(bbl_path)
            confidence_note = "medium (parsed from .bbl — fields are heuristic)"
        else:
            print(f"ERROR: Could not find .bib or .bbl for {input_path}", file=sys.stderr)
            return 2
        if args.check_body:
            body_text_for_citations = expand_inputs(input_path)

    elif input_type == "bib":
        refs = parse_bib_file(input_path)

    elif input_type == "bbl":
        refs = parse_bbl_file(input_path)
        confidence_note = "medium (parsed from .bbl — fields are heuristic)"

    if args.transcribed_from:
        confidence_note = (f"medium (entries transcribed by Claude from {args.transcribed_from}; "
                           f"check flagged entries against the original)")

    if not refs:
        print("ERROR: No references extracted from input.", file=sys.stderr)
        return 2

    print(f"Parsed {len(refs)} reference(s). Verifying...")

    # --- Set up cache and HTTP client
    cache_dir = Path(args.cache_dir) if args.cache_dir else DEFAULT_CACHE_DIR
    cache = Cache(cache_dir, enabled=not args.no_cache)

    contact_email = os.environ.get("REFVERIFY_CONTACT_EMAIL")
    if not contact_email:
        warnings.warn("REFVERIFY_CONTACT_EMAIL not set; using anonymous Crossref pool (slower).")
    semantic_scholar_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    client = APIClient(contact_email, semantic_scholar_key)
    try:
        results = await verify_all(refs, client, cache, args.concurrency)
    finally:
        await client.close()
        cache.flush()

    # --- Detect duplicates and apply
    duplicate_keys = find_duplicates(refs, results)
    for r in results:
        if r.ref.key in duplicate_keys and r.status == "verified":
            r.status = "duplicate"

    # --- Detect orphans/missing for tex inputs with body
    orphans: set[str] = set()
    missing: set[str] = set()
    if body_text_for_citations:
        cited_keys = extract_citations_from_tex_body(input_path)
        # Re-extract from expanded text
        cited_keys |= set(re.findall(r"\\(?:no|paren|text|foot|auto|smart)?cite[a-z*]*\s*(?:\[[^\]]*\])?\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", body_text_for_citations))
        # Flatten comma-separated
        flat_cited = set()
        for k in cited_keys:
            for sub in k.split(","):
                flat_cited.add(sub.strip())
        bib_keys = {r.key for r in refs}
        orphans = bib_keys - flat_cited
        missing = flat_cited - bib_keys

    # --- Render report
    report = render_report(results, orphans, missing, input_path, confidence_note)
    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_refs_report.md")
    output_path.write_text(report)
    print(f"\nReport written to: {output_path}")

    if args.suggest_fixes:
        fixes_path = output_path.with_suffix(".diff.md")
        fixes_path.write_text(generate_fix_suggestions(results))
        print(f"Fix suggestions written to: {fixes_path}")

    # Summary to stdout
    counts = {s: 0 for s in STATUS_SYMBOLS}
    for r in results:
        counts[r.status] += 1
    counts["orphan"] = len(orphans)
    counts["missing"] = len(missing)
    print("\nSummary:")
    for s in ["verified", "metadata_mismatch", "low_confidence", "not_found", "lookup_failed",
              "unparseable", "duplicate", "orphan", "missing"]:
        if counts[s]:
            print(f"  {STATUS_SYMBOLS[s]} {STATUS_LABELS[s]}: {counts[s]}")

    if args.strict:
        non_verified = sum(c for s, c in counts.items() if s != "verified")
        if non_verified > 0:
            return 1
    return 0


def main():
    p = argparse.ArgumentParser(
        description="Verify the references of an academic paper against bibliographic databases.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("input", help="Input file: .tex, .bib or .bbl")
    p.add_argument("--transcribed-from", metavar="FILE",
                   help="The PDF or Word file the .bib was transcribed from; named in the report")
    p.add_argument("--output", help="Output Markdown report path")
    p.add_argument("--cache-dir", help=f"Cache directory (default: {DEFAULT_CACHE_DIR})")
    p.add_argument("--no-cache", action="store_true", help="Bypass the cache")
    p.add_argument("--concurrency", type=int, default=5, help="Parallel API request limit")
    p.add_argument("--check-body", dest="check_body", action="store_true", default=True,
                   help="Check for orphan/missing citations in tex body (default: on)")
    p.add_argument("--no-check-body", dest="check_body", action="store_false",
                   help="Skip body citation check")
    p.add_argument("--suggest-fixes", action="store_true",
                   help="Emit suggested bib fixes alongside the report")
    p.add_argument("--strict", action="store_true",
                   help="Exit non-zero if any reference is not verified")
    args = p.parse_args()

    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
