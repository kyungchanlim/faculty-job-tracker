#!/usr/bin/env python3
"""Normalize data/jobs.json. Safe on empty files."""
from __future__ import annotations
import argparse,json,re
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DEFAULT_JOBS=ROOT/'data/jobs.json'; TODAY=date.today().isoformat()
def clean(s): return re.sub(r'\s+',' ',str(s or '')).strip()
def infer_track(t):
    l=t.lower()
    if 'tenure-track' in l or 'tenure track' in l: return 'tenure-track'
    if 'visiting' in l: return 'visiting'
    if 'lecturer' in l or 'instructor' in l: return 'teaching'
    if 'open rank' in l: return 'open-rank'
    return 'faculty'
def infer_field(t):
    checks=[('security',r'security|cyber'),('systems',r'systems|distributed|operating systems|network|architecture'),('AI/ML',r'artificial intelligence|machine learning|deep learning|AI'),('software engineering',r'software engineering|programming languages'),('data science',r'data science|analytics'),('computer science',r'computer science|computing')]
    out=[label for label,pat in checks if re.search(pat,t,re.I)]
    return out or ['computing']
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--jobs',default=str(DEFAULT_JOBS)); args=ap.parse_args(); p=Path(args.jobs); p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists(): p.write_text('[]\n',encoding='utf-8')
    try: jobs=json.loads(p.read_text(encoding='utf-8'))
    except Exception: jobs=[]
    if not isinstance(jobs,list): jobs=[]
    for j in jobs:
        text=' '.join(clean(j.get(k)) for k in ['title','school','source','track'])
        for k in ['title','school','location','state','track','deadline','status']:
            if k in j: j[k]=clean(j.get(k))
        j['track']=j.get('track') or infer_track(text)
        if not isinstance(j.get('field'),list) or not j.get('field'): j['field']=infer_field(text)
        j['status']=j.get('status') or 'open'; j.setdefault('first_seen',TODAY); j.setdefault('last_seen',TODAY)
    p.write_text(json.dumps(jobs,indent=2,ensure_ascii=False),encoding='utf-8'); print(f'[OK] normalized {len(jobs)} jobs -> {p}')
if __name__=='__main__': main()
