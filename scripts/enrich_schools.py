#!/usr/bin/env python3
"""Enrich data/schools.csv with official, CS department, and CS-specific job listing URLs.

This script is designed for the U.S. News top-200 CS school list.  It tries to find:
  - official_url: main university website
  - cs_department_url: CS / computing department homepage
  - cs_jobs_url: CS-department-specific faculty/job/open-positions page
  - faculty_jobs_url: generic university faculty/academic jobs page
  - careers_url: generic university HR/careers page

The most important column for this project is cs_jobs_url.  collect_school_career_pages.py
will use cs_jobs_url first, then fall back to generic faculty/career pages.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "schools.csv"
DEFAULT_OUT = ROOT / "data" / "schools_enriched.csv"

FIELDS = [
    "usnews_cs_rank", "school", "location", "city", "state", "tie",
    "official_url", "cs_department_url", "cs_jobs_url", "faculty_jobs_url", "careers_url",
    "source", "source_url", "source_file", "notes",
]

HEADERS = {
    "User-Agent": "faculty-job-tracker/0.3 (+https://github.com/kyungchan626/faculty-job-tracker; educational research)"
}

CS_KEYWORDS = [
    "computer science", "computing", "computer engineering", "informatics",
    "information science", "school of computing", "college of computing",
    "department of computer", "electrical engineering and computer science", "eecs",
]

CS_JOB_KEYWORDS = [
    "faculty positions", "faculty openings", "faculty jobs", "academic jobs",
    "open positions", "job openings", "employment", "careers", "hiring",
    "assistant professor", "associate professor", "tenure-track", "tenure track",
    "lecturer", "teaching faculty", "professor",
]

GENERIC_CAREER_KEYWORDS = [
    "jobs", "careers", "employment", "work at", "human resources", "talent acquisition",
]

NEGATIVE_KEYWORDS = [
    "student jobs", "student employment", "admissions", "admission", "tuition", "certificate",
    "online", "bootcamp", "scholarship", "giving", "alumni", "news", "events", "seminar",
    "undergraduate", "graduate program", "course catalog",
]

COMMON_CS_JOB_PATHS = [
    "jobs", "job", "careers", "career", "employment", "hiring", "openings", "open-positions",
    "positions", "faculty", "faculty-hiring", "faculty-openings", "faculty-positions",
    "about/jobs", "about/careers", "about/employment", "about/open-positions",
    "people/faculty-hiring", "people/faculty-openings", "department/jobs",
]


def clean(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def norm_url(u: str) -> str:
    u = clean(u)
    if u and not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def domain(u: str) -> str:
    n = urlparse(norm_url(u)).netloc.lower()
    return n[4:] if n.startswith("www.") else n


def same_domain(base: str, u: str) -> bool:
    b = domain(base)
    d = domain(u)
    return bool(b and d) and (d == b or d.endswith("." + b) or b.endswith("." + d))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        # Backward compatibility: older versions may have no cs_jobs_url column.
        for k in FIELDS:
            r.setdefault(k, "")
    return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    extra: list[str] = []
    for r in rows:
        for k in r:
            if k not in FIELDS and k not in extra:
                extra.append(k)
    fields = FIELDS + extra
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def get_json(url: str, params: dict[str, object]) -> dict:
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def wikidata_official_url(school: str) -> str:
    """Best-effort official URL lookup from Wikidata P856."""
    try:
        s = get_json(
            "https://www.wikidata.org/w/api.php",
            {"action": "wbsearchentities", "search": school, "language": "en", "format": "json", "limit": 8},
        )
        for item in s.get("search", []):
            qid = item.get("id")
            if not qid:
                continue
            e = get_json(
                "https://www.wikidata.org/w/api.php",
                {"action": "wbgetentities", "ids": qid, "props": "claims|labels|descriptions", "languages": "en", "format": "json"},
            )
            ent = e.get("entities", {}).get(qid, {})
            label = clean(ent.get("labels", {}).get("en", {}).get("value"))
            desc = clean(ent.get("descriptions", {}).get("en", {}).get("value"))
            if not re.search(r"university|college|institute|school", f"{label} {desc}", re.I):
                continue
            for c in ent.get("claims", {}).get("P856", []):
                v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(v, str) and v.startswith("http"):
                    return v.rstrip("/") + "/"
    except Exception as e:
        print(f"[WARN] Wikidata failed for {school}: {e}", file=sys.stderr)
    return ""


def fetch(url: str, *, max_chars: int = 2_000_000) -> str:
    url = norm_url(url)
    if not url:
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        ct = r.headers.get("content-type", "")
        if "html" not in ct and "text" not in ct:
            return ""
        r.raise_for_status()
        return r.text[:max_chars]
    except Exception as e:
        print(f"[WARN] fetch failed {url}: {e}", file=sys.stderr)
        return ""


def extract_links(base: str, *, allow_external: bool = False) -> list[tuple[str, str]]:
    html = fetch(base)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        text = clean(a.get_text(" ", strip=True))
        href = urljoin(base, a["href"]).split("#")[0]
        if not href.startswith("http"):
            continue
        if not allow_external and not same_domain(base, href):
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append((text, href))
    return out


def keyword_score(text: str, url: str, positive: list[str], negative: list[str] | tuple[str, ...] = ()) -> int:
    hay = f"{text} {url}".lower()
    s = 0
    text_l = text.lower()
    url_l = url.lower()
    for kw in positive:
        kw_l = kw.lower()
        if kw_l in text_l:
            s += 18
        elif kw_l in url_l:
            s += 10
        elif kw_l in hay:
            s += 6
    for kw in negative:
        if kw.lower() in hay:
            s -= 25
    # Prefer shorter, more canonical URLs.
    s -= min(urlparse(url).path.count("/"), 8)
    return s


def best_link(links: list[tuple[str, str]], pos: list[str], neg: list[str] | tuple[str, ...] = ()) -> str:
    ranked = [(keyword_score(t, u, pos, neg), u, t) for t, u in links]
    ranked = [x for x in ranked if x[0] > 0]
    if not ranked:
        return ""
    ranked.sort(reverse=True)
    return ranked[0][1]


def page_has_cs_job_signal(url: str) -> int:
    """Return a confidence score that a URL is a CS/computing job listing page."""
    html = fetch(url, max_chars=500_000)
    if not html:
        return 0
    soup = BeautifulSoup(html, "html.parser")
    title = clean(soup.title.get_text(" ", strip=True) if soup.title else "")
    text = clean(soup.get_text(" ", strip=True))[:40_000]
    hay = f"{title} {url} {text}".lower()
    score = 0
    if any(k in hay for k in ["assistant professor", "tenure-track", "tenure track", "faculty position", "faculty opening", "open positions"]):
        score += 35
    if any(k in hay for k in ["computer science", "computing", "computer engineering", "eecs", "informatics", "cybersecurity"]):
        score += 30
    if any(k in hay for k in ["jobs", "careers", "employment", "hiring", "openings", "positions"]):
        score += 15
    if any(k in hay for k in ["student employment", "admissions", "tuition", "course", "seminar"]):
        score -= 20
    return score


def guess_common_cs_job_paths(cs_url: str) -> str:
    """Try common CS department job-page paths under the CS department URL."""
    cs_url = norm_url(cs_url).rstrip("/") + "/"
    if not cs_url:
        return ""
    candidates: list[tuple[int, str]] = []
    for path in COMMON_CS_JOB_PATHS:
        u = urljoin(cs_url, path)
        sc = page_has_cs_job_signal(u)
        if sc >= 45:
            candidates.append((sc, u))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][1]


def find_cs_department_url(home: str) -> str:
    links = extract_links(home)
    return best_link(
        links,
        CS_KEYWORDS + ["cs", "cse", "eecs"],
        NEGATIVE_KEYWORDS,
    )


def find_generic_career_urls(home: str) -> tuple[str, str]:
    links = extract_links(home)
    careers = best_link(links, GENERIC_CAREER_KEYWORDS, ["student jobs", "student employment", "bookstore"])
    faculty = best_link(
        links,
        ["faculty jobs", "faculty careers", "academic jobs", "faculty positions", "open positions"],
        ["student"],
    )
    if careers and not faculty:
        faculty = best_link(
            extract_links(careers, allow_external=True),
            ["faculty", "academic", "professor", "tenure", "instructional", "search jobs", "job openings"],
            ["student employment"],
        )
    return careers, faculty


def find_cs_jobs_url(cs_url: str, generic_careers_url: str = "") -> str:
    """Find a CS/computing-specific job listing page.

    Priority:
      1. Direct links from CS department page with job/faculty keywords.
      2. One-hop links from promising CS pages.
      3. Common URL paths under CS department page.
      4. Generic career page only if it has both CS and faculty/job signals.
    """
    cs_url = norm_url(cs_url)
    if not cs_url:
        return ""

    links = extract_links(cs_url, allow_external=True)
    direct = best_link(
        links,
        CS_JOB_KEYWORDS,
        NEGATIVE_KEYWORDS,
    )
    if direct and page_has_cs_job_signal(direct) >= 30:
        return direct

    # Explore one hop from likely CS department subpages such as About, People, News, Faculty.
    promising = []
    for text, href in links:
        sc = keyword_score(text, href, ["jobs", "open positions", "faculty", "about", "people", "hiring", "careers"], NEGATIVE_KEYWORDS)
        if sc > 0:
            promising.append((sc, href))
    promising = sorted(promising, reverse=True)[:8]
    for _, href in promising:
        sublinks = extract_links(href, allow_external=True)
        candidate = best_link(sublinks, CS_JOB_KEYWORDS, NEGATIVE_KEYWORDS)
        if candidate and page_has_cs_job_signal(candidate) >= 30:
            return candidate

    common = guess_common_cs_job_paths(cs_url)
    if common:
        return common

    if generic_careers_url and page_has_cs_job_signal(generic_careers_url) >= 55:
        return generic_careers_url

    return ""


def likely_urls(home: str) -> dict[str, str]:
    home = norm_url(home)
    if not home:
        return {"cs_department_url": "", "cs_jobs_url": "", "faculty_jobs_url": "", "careers_url": ""}

    cs = find_cs_department_url(home)
    careers, faculty = find_generic_career_urls(home)
    cs_jobs = find_cs_jobs_url(cs, careers)

    return {
        "cs_department_url": cs,
        "cs_jobs_url": cs_jobs,
        "faculty_jobs_url": faculty,
        "careers_url": careers,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DEFAULT_IN))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--overwrite-schools", action="store_true")
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="Recompute URLs even when columns are already filled.")
    args = ap.parse_args()

    rows = read_rows(Path(args.input))
    rows = rows[: args.limit] if args.limit else rows

    for i, row in enumerate(rows, 1):
        school = row.get("school", "")
        print(f"[INFO] {i}/{len(rows)} {school}")

        if args.force or not row.get("official_url"):
            row["official_url"] = wikidata_official_url(school)
            time.sleep(args.sleep)

        guessed = likely_urls(row.get("official_url", ""))
        for k, v in guessed.items():
            if v and (args.force or not row.get(k)):
                row[k] = v

        if row.get("cs_jobs_url"):
            print(f"  [CS JOBS] {row['cs_jobs_url']}")
        elif row.get("faculty_jobs_url"):
            print(f"  [FALLBACK FACULTY JOBS] {row['faculty_jobs_url']}")
        time.sleep(args.sleep)

    write_rows(Path(args.out), rows)
    print(f"[OK] wrote {args.out}")
    if args.overwrite_schools:
        write_rows(Path(args.input), rows)
        print(f"[OK] overwrote {args.input}")


if __name__ == "__main__":
    main()
