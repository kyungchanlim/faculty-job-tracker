#!/usr/bin/env python3
"""Optional external job-board collector placeholder. School crawler does the real work."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]; JOBS=ROOT/'data/jobs.json'
def main():
    JOBS.parent.mkdir(parents=True,exist_ok=True)
    if not JOBS.exists(): JOBS.write_text('[]\n',encoding='utf-8')
    try: obj=json.loads(JOBS.read_text(encoding='utf-8')); n=len(obj) if isinstance(obj,list) else 0
    except Exception: n=0
    print(f'[OK] collect_jobs placeholder; existing jobs: {n}')
if __name__=='__main__': main()
