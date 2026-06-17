#!/usr/bin/env python3
"""Collect CS faculty openings from external job boards.

This complements school-specific scraping.  It is intentionally best-effort:
HigherEdJobs and Inside Higher Ed sometimes block automated requests from CI, so
failures are logged as warnings and the workflow continues.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "data" / "external_sources.json"
DEFAULT_SCHOOLS = ROOT / "data" / "schools.csv"
DEFAULT_JOBS = ROOT / "data" / "jobs.json"
DEFAULT_CANDIDATES = ROOT / "data" / "external_job_candidates.json"
TODAY = date.today().isoformat()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; faculty-job-tracker/0.4; educational research)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TITLE_RE = re.compile(
    r"assistant professor|associate professor|open rank|tenure[- ]track|tenured|"
    r"faculty position|faculty opening|professor of|lecturer|instructor",
    re.I,
)
CS_RE = re.compile(
    r"computer science|computing|computer engineering|cybersecurity|cyber security|"
    r"software engineering|data science|artificial intelligence|machine learning|"
    r"information science|informatics|systems|security",
    re.I,
)
NEG_RE = re.compile(
    r"admission|tuition|online degree|student job|graduate assistant|research assistant|"
    r"teaching assistant|postdoc|postdoctoral|scholarship|sponsored|advertisement|"
    r"alert|saved job|login|sign in|employer|resume|career advice",
    re.I,
)

SCHOOL_SUFFIX_RE = re.compile(
    r"\s*[-–—|]\s*(?:HigherEdJobs|Inside Higher Ed|Chronicle.*|Careers.*)$", re.I
)


def clean(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def norm_url(u: str) -> str:
    u = clean(u)
    if u and not u.startswith(("http://", "https://")):
        return "https://" + u
    return u


def fetch(url: str, timeout: int = 15) -> str:
    url = norm_url(url)
    if not url:
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        ct = r.headers.get("content-type", "")
        if "html" not in ct and "text" not in ct:
            return ""
        r.raise_for_status()
        return r.text[:4_000_000]
    except Exception as e:
        print(f"[WARN] external fetch failed {url}: {e}", file=sys.stderr)
        return ""


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj
    except Exception:
        return default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")



def load_schools(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def find_tracked_school(text: str, schools: list[dict[str, str]]) -> dict[str, str]:
    low = text.lower()
    for s in schools:
        name = clean(s.get("school"))
        if name and name.lower() in low:
            return s
    # Handle common shortened names in job-board snippets.
    aliases = {
        "MIT": "Massachusetts Institute of Technology",
        "Georgia Tech": "Georgia Institute of Technology",
        "UC Berkeley": "University of California--Berkeley",
        "UCLA": "University of California--Los Angeles",
        "UC San Diego": "University of California--San Diego",
        "UC Irvine": "University of California--Irvine",
        "UC Santa Barbara": "University of California--Santa Barbara",
        "UNC Chapel Hill": "University of North Carolina--Chapel Hill",
        "UT Austin": "University of Texas--Austin",
        "Texas A&M": "Texas A&M University--College Station",
    }
    for alias, full in aliases.items():
        if alias.lower() in low:
            for s in schools:
                if clean(s.get("school")).lower() == full.lower():
                    return s
    return {}

def make_id(source: str, title: str, url: str) -> str:
    return hashlib.sha256(f"external|{source}|{title}|{url}".encode()).hexdigest()[:16]


def infer_track(text: str) -> str:
    l = text.lower()
    if "tenure-track" in l or "tenure track" in l:
        return "tenure-track"
    if "visiting" in l:
        return "visiting"
    if "lecturer" in l or "instructor" in l:
        return "teaching"
    if "open rank" in l:
        return "open-rank"
    return "faculty"


def infer_rank(text: str) -> str:
    if re.search(r"assistant professor", text, re.I):
        return "Assistant Professor"
    if re.search(r"associate professor", text, re.I):
        return "Associate Professor"
    if re.search(r"open rank", text, re.I):
        return "Open Rank"
    if re.search(r"lecturer", text, re.I):
        return "Lecturer"
    if re.search(r"instructor", text, re.I):
        return "Instructor"
    if re.search(r"professor", text, re.I):
        return "Professor"
    return "Faculty"


def infer_fields(text: str) -> list[str]:
    checks = [
        ("security", r"security|cyber"),
        ("systems", r"systems|distributed|operating systems|network|architecture"),
        ("AI/ML", r"artificial intelligence|machine learning|deep learning|\bAI\b"),
        ("software engineering", r"software engineering|programming languages"),
        ("data science", r"data science|analytics"),
        ("computer science", r"computer science|computing"),
        ("computer engineering", r"computer engineering|computer architecture"),
    ]
    out = [label for label, pat in checks if re.search(pat, text, re.I)]
    return out or ["computing"]


def infer_deadline(text: str) -> str:
    m = re.search(
        r"(?:deadline|review[^.]{0,30}|apply by|applications? due)[^A-Za-z0-9]{0,20}"
        r"([A-Z][a-z]+\s+\d{1,2},?\s+20\d{2}|\d{1,2}/\d{1,2}/20\d{2}|20\d{2}-\d{2}-\d{2})",
        text,
        re.I,
    )
    return clean(m.group(1)) if m else ""


def looks_like_job(title: str, href: str, context: str) -> bool:
    hay = f"{title} {href} {context}"
    if NEG_RE.search(hay):
        return False
    # Strict enough to avoid ads, broad enough for external job boards.
    return bool(TITLE_RE.search(hay) and CS_RE.search(hay))


def canonical_title(title: str) -> str:
    title = clean(title)
    title = SCHOOL_SUFFIX_RE.sub("", title)
    title = re.sub(r"\s+\|\s+.*$", "", title)
    return title[:240]


def build_job(source_name: str, source_page: str, title: str, href: str, context: str, schools: list[dict[str, str]] | None = None) -> dict:
    text = f"{title} {context}"
    school = find_tracked_school(text, schools or [])
    return {
        "id": make_id(source_name, title, href),
        "title": canonical_title(title) or "Faculty opening",
        "school": clean(school.get("school")),
        "location": clean(school.get("location")),
        "state": clean(school.get("state")),
        "school_rank": clean(school.get("usnews_cs_rank") or school.get("usnews_rank")),
        "rank": infer_rank(text),
        "track": infer_track(text),
        "field": infer_fields(text),
        "deadline": infer_deadline(text),
        "source": source_name,
        "source_url": href,
        "source_page": source_page,
        "first_seen": TODAY,
        "last_seen": TODAY,
        "status": "open",
    }


def nearby_text(a) -> str:
    chunks = [clean(a.get_text(" ", strip=True))]
    for parent in list(a.parents)[:4]:
        txt = clean(parent.get_text(" ", strip=True))
        if txt and len(txt) > len(chunks[0]):
            chunks.append(txt[:1200])
    return " ".join(chunks)


def extract_jobs_from_html(source_name: str, source_url: str, html: str, schools: list[dict[str, str]]) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        title = clean(a.get_text(" ", strip=True))
        if not title or len(title) < 8:
            continue
        href = urljoin(source_url, a["href"]).split("#")[0]
        if not href.startswith("http"):
            continue
        ctx = nearby_text(a)
        if not looks_like_job(title, href, ctx):
            continue
        key = (canonical_title(title).lower(), href)
        if key in seen:
            continue
        seen.add(key)
        out.append(build_job(source_name, source_url, title, href, ctx, schools))
    return out


def merge_jobs(existing: list[dict], new_jobs: list[dict]) -> list[dict]:
    merged = {j.get("id"): j for j in existing if j.get("id")}
    for j in new_jobs:
        jid = j.get("id")
        if not jid:
            continue
        if jid in merged:
            old = merged[jid]
            old.update({k: v for k, v in j.items() if v not in ("", [], None)})
            old["last_seen"] = TODAY
            old["status"] = "open"
        else:
            merged[jid] = j
    return sorted(merged.values(), key=lambda x: (x.get("source", ""), x.get("title", "")))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default=str(DEFAULT_SOURCES))
    ap.add_argument("--jobs", default=str(DEFAULT_JOBS))
    ap.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    ap.add_argument("--schools", default=str(DEFAULT_SCHOOLS))
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    sources = load_json(Path(args.sources), [])
    if not isinstance(sources, list):
        sources = []
    if args.limit:
        sources = sources[: args.limit]

    schools = load_schools(Path(args.schools))
    candidates: list[dict] = []
    for i, src in enumerate(sources, 1):
        name = clean(src.get("source") or src.get("name") or "External job board")
        url = norm_url(src.get("url", ""))
        print(f"[INFO] external {i}/{len(sources)} {name}: {url}")
        html = fetch(url)
        if not html:
            time.sleep(args.sleep)
            continue
        found = extract_jobs_from_html(name, url, html, schools)
        print(f"  [FOUND] {len(found)} external candidates")
        candidates.extend(found)
        time.sleep(args.sleep)

    # Deduplicate external candidates before merging.
    candidates = list({j["id"]: j for j in candidates}.values())
    save_json(Path(args.candidates), candidates)

    existing = load_json(Path(args.jobs), [])
    if not isinstance(existing, list):
        existing = []
    merged = merge_jobs(existing, candidates)
    save_json(Path(args.jobs), merged)
    print(f"[OK] wrote {len(candidates)} candidates -> {args.candidates}")
    print(f"[OK] wrote {len(merged)} merged jobs -> {args.jobs}")


if __name__ == "__main__":
    main()
