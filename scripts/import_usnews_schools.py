#!/usr/bin/env python3
"""Import the extracted U.S. News CS ranking JSON/CSV/TXT into data/schools.csv."""
from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "schools.csv"
DEFAULT_SOURCE_URL = "https://www.usnews.com/best-graduate-schools/top-computer-science-schools/computer-science-rankings"
FIELDS = ["usnews_cs_rank","school","location","city","state","tie","official_url","cs_department_url","cs_jobs_url","faculty_jobs_url","careers_url","source","source_url","source_file","notes"]
STATE_ABBR = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())

SKIP_NAMES = {"Advertisement","ADVERTISING","U.S. News Grad Compass","Comcast","Milk Bone"}

def clean(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()

def clean_rank(x: Any) -> str:
    m = re.search(r"\d+", clean(x)); return m.group(0) if m else ""

def split_location(location: str) -> tuple[str,str]:
    location=clean(location).replace(' ,', ',')
    m=re.match(r"^(.*?),\s*([A-Z]{2})$", location)
    if m: return clean(m.group(1)), m.group(2)
    if location in STATE_ABBR: return "", location
    return "", ""

def norm(raw: dict[str, Any]) -> dict[str,str]:
    lower={str(k).strip().lower():v for k,v in raw.items()}
    rank=clean_rank(lower.get('usnews_cs_rank') or lower.get('usnews_rank') or lower.get('rank'))
    school=clean(lower.get('school') or lower.get('name') or lower.get('institution') or lower.get('institution_name'))
    location=clean(lower.get('location') or lower.get('city_state'))
    city=clean(lower.get('city')); state=clean(lower.get('state'))
    if not (city and state):
        c,s=split_location(location); city=city or c; state=state or s
    tie_val=lower.get('tie','')
    tie='true' if tie_val is True or clean(tie_val).lower() in {'true','1','yes','tie','(tie)'} else 'false'
    out={k:'' for k in FIELDS}
    out.update({
        'usnews_cs_rank':rank, 'school':school, 'location':location or ', '.join(x for x in [city,state] if x),
        'city':city, 'state':state, 'tie':tie,
        'source':clean(lower.get('source')) or 'U.S. News 2026 Best Computer Science Schools',
        'source_url':clean(lower.get('source_url')) or DEFAULT_SOURCE_URL,
        'source_file':clean(lower.get('source_file')),
        'official_url':clean(lower.get('official_url')), 'cs_department_url':clean(lower.get('cs_department_url')),
        'cs_jobs_url':clean(lower.get('cs_jobs_url')), 'faculty_jobs_url':clean(lower.get('faculty_jobs_url')), 'careers_url':clean(lower.get('careers_url')),
        'notes':clean(lower.get('notes')),
    })
    return out

def load_json(path: Path) -> list[dict[str,str]]:
    obj=json.loads(path.read_text(encoding='utf-8'))
    if isinstance(obj, dict):
        for k in ['schools','items','data','results']:
            if isinstance(obj.get(k), list): obj=obj[k]; break
    if not isinstance(obj, list): raise ValueError('JSON must be a list or contain schools/items/data/results')
    return [norm(x) for x in obj if isinstance(x, dict)]

def load_csv(path: Path) -> list[dict[str,str]]:
    with path.open(newline='', encoding='utf-8-sig') as f: return [norm(r) for r in csv.DictReader(f)]

def load_txt(path: Path) -> list[dict[str,str]]:
    lines=[clean(x) for x in path.read_text(encoding='utf-8', errors='ignore').splitlines()]
    lines=[x for x in lines if x]
    rows=[]
    for i,line in enumerate(lines):
        if not re.fullmatch(r"#\d+", line): continue
        rank=clean_rank(line); school=''; loc=''
        for j in range(i-1, max(-1,i-8), -1):
            cand=lines[j]
            if re.fullmatch(r"[A-Z]{2}", cand) or re.search(r",\s*[A-Z]{2}$", cand): loc=cand
            elif len(cand)>3 and not cand.startswith('Profile Image') and cand not in SKIP_NAMES:
                school=cand; break
        if school: rows.append(norm({'usnews_cs_rank':rank,'school':school,'location':loc,'source_file':path.name}))
    return rows

def dedupe(rows):
    out=[]; seen=set()
    for r in rows:
        school=clean(r.get('school')); rank=clean_rank(r.get('usnews_cs_rank'))
        if not school or not rank or school in SKIP_NAMES: continue
        key=school.lower()
        if key in seen: continue
        seen.add(key); out.append(r)
    out.sort(key=lambda r:int(clean_rank(r.get('usnews_cs_rank')) or 999999))
    return out

def write(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=FIELDS); w.writeheader();
        for r in rows: w.writerow({k:r.get(k,'') for k in FIELDS})

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input', required=True); ap.add_argument('--out', default=str(DEFAULT_OUT)); ap.add_argument('--top-n', type=int, default=200); args=ap.parse_args()
    p=Path(args.input)
    rows=load_json(p) if p.suffix.lower()=='.json' else load_csv(p) if p.suffix.lower()=='.csv' else load_txt(p)
    rows=dedupe(rows)[:args.top_n]; write(Path(args.out), rows); print(f'[OK] wrote {len(rows)} schools -> {args.out}')
if __name__=='__main__': main()
