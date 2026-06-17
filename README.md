# CS Faculty Job Tracker

GitHub Pages tracker for assistant-professor / faculty openings at U.S. News CS 200-school set.

## Data file used by the code

The repo is matched to this extracted U.S. News file:

```text
data/usnews_cs_top200_from_copy.json
```

The crawler/build scripts use this canonical CSV:

```text
data/schools.csv
```

If you only have the JSON file, generate `data/schools.csv` with:

```bash
python scripts/import_usnews_schools.py \
  --input data/usnews_cs_top200_from_copy.json \
  --out data/schools.csv \
  --top-n 200
```

## School URL enrichment

`enrich_schools.py` now tries to collect these URLs for each school:

```text
official_url          # main university website
cs_department_url     # CS / computing department homepage
cs_jobs_url           # CS-specific jobs/open-positions/faculty-hiring page
faculty_jobs_url      # generic faculty/academic jobs page
careers_url           # generic HR/careers page
```

`cs_jobs_url` is the preferred source for the tracker.  If it is missing, the job collector falls back to `faculty_jobs_url`, `careers_url`, `cs_department_url`, and finally `official_url`.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Find official/CS/CS-jobs/career URLs. Review data/schools.csv after this.
python scripts/enrich_schools.py --overwrite-schools --sleep 1.0

# Collect job candidates and build site.
python scripts/collect_school_career_pages.py --strict --sleep 1.0
python scripts/enrich_jobs.py
python scripts/build_site.py

python -m http.server 8000 -d docs
```

Open:

```text
http://localhost:8000
```

## Useful options

Recompute URLs even if columns are already filled:

```bash
python scripts/enrich_schools.py --overwrite-schools --force --sleep 1.0
```

Test only the first 10 schools:

```bash
python scripts/enrich_schools.py --overwrite-schools --limit 10 --sleep 1.0
python scripts/collect_school_career_pages.py --strict --limit 10 --sleep 1.0
python scripts/build_site.py
```

Higher recall, more noise:

```bash
python scripts/collect_school_career_pages.py --sleep 1.0
```

## GitHub Pages

Use:

```text
Settings -> Pages -> Deploy from a branch -> main / docs
```

The workflow `.github/workflows/daily_update.yml` runs once per day.  It updates `data/schools.csv` with CS job listing URLs, collects job openings, and rebuilds the static site.

## Files

```text
data/usnews_cs_top200_from_copy.json   # original extracted source list data
data/usnews_cs_top200_from_copy.csv    # same data in CSV
data/schools.csv                       # canonical input for all scripts
scripts/import_usnews_schools.py       # JSON/CSV/TXT -> data/schools.csv
scripts/enrich_schools.py              # add official/CS/CS-jobs/career URLs
scripts/collect_school_career_pages.py # collect candidate faculty openings
scripts/enrich_jobs.py                 # normalize jobs.json
scripts/build_site.py                  # build docs/index.html
```

## Notes

- `enrich_schools.py` is heuristic. Run it once, then manually fix important `official_url`, `cs_department_url`, and `cs_jobs_url` values in `data/schools.csv`.
- `collect_school_career_pages.py --strict` requires both faculty/rank keywords and CS-related keywords. Remove `--strict` for higher recall and more noise.
- Always verify openings on the official posting page before applying.
