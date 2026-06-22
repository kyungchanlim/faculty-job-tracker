#!/usr/bin/env python3
"""Remove obvious non-job links accidentally collected from department pages."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOBS = ROOT / 'data' / 'jobs.json'
POSITION_RE = re.compile(
    r'assistant professor|associate professor|full professor|open rank|tenure[- ]track|'
    r'tenured faculty|faculty (?:position|opening|search)|professor of|lecturer|instructor', re.I
)
NON_JOB_URL_RE = re.compile(
    r'/faculty-research/|/research(?:/|$)|[?&]fwp_research=|/people(?:/|$)|/directory(?:/|$)|/academics/faculty/|/(?:19|20)\d{2}/\d{2}/', re.I
)
JOB_URL_RE = re.compile(
    r'apply\.interfolio\.com|recruit\.ap\.|/jobs?/|/postings?/|job_?req|academic-positions|'
    r'faculty-(?:jobs|openings|positions)|open-positions|careers?\.', re.I
)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--jobs', default=str(DEFAULT_JOBS)); args=ap.parse_args()
    p=Path(args.jobs)
    jobs=json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    kept=[]; removed=[]
    for j in jobs:
        title=str(j.get('title') or '')
        url=str(j.get('source_url') or '')
        source=str(j.get('source') or '')
        bad = title.lower() == 'faculty job search page' or bool(NON_JOB_URL_RE.search(url))
        # School-page candidates must name a concrete position in the anchor text.
        if source == 'CS/school career page' and (not POSITION_RE.search(title) or not JOB_URL_RE.search(url)):
            bad = True
        (removed if bad else kept).append(j)
    # Deduplicate links that were discovered more than once from the same school.
    by_url = {}
    for j in kept:
        key = (str(j.get('school') or '').lower(), str(j.get('source_url') or '').rstrip('/').lower())
        old = by_url.get(key)
        if old is None or len(str(j.get('title') or '')) > len(str(old.get('title') or '')):
            by_url[key] = j
    kept = sorted(by_url.values(), key=lambda x: (int(x.get('school_rank') or 9999) if str(x.get('school_rank') or '').isdigit() else 9999, x.get('school',''), x.get('title','')))
    p.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'[OK] kept {len(kept)} jobs; removed {len(removed)} obvious non-job links')

if __name__ == '__main__': main()
