# CS Faculty Job Tracker

Static GitHub Pages tracker for U.S. News CS 200-school list plus CS/faculty job openings.

## Data files

- `data/usnews_cs_top200_from_copy.json`: extracted school list source.
- `data/schools.csv`: canonical school table used by scripts.
- `data/external_sources.json`: external job-board search pages to scan.
- `data/jobs.json`: merged job candidates.

## Daily GitHub Action

The workflow does the following:

1. Ensures `data/schools.csv` exists.
2. Enriches missing school URLs using curated stable hints, Wikidata, and public links.
3. Collects external job-board candidates from HigherEdJobs / Inside Higher Ed URLs listed in `data/external_sources.json`.
4. Collects candidates from school CS/faculty/career pages.
5. Rebuilds `docs/index.html`, `docs/jobs.json`, and `docs/schools.json`.
6. Commits changes back to `main`.

## Local run

```bash
pip install -r requirements.txt
python scripts/enrich_schools.py --overwrite-schools --sleep 0.2
python scripts/collect_jobs.py --sleep 0.2
python scripts/collect_school_career_pages.py --strict --sleep 0.2
python scripts/enrich_jobs.py
python scripts/build_site.py
python -m http.server 8000 -d docs
```

Then open `http://localhost:8000`.

## Notes

Some job boards and university HR pages block automated requests from GitHub Actions with 403, 405, SSL, timeout, or bot-protection pages. The scripts log these as warnings and continue. Add or edit job-board search URLs in `data/external_sources.json` when you find better search pages.
