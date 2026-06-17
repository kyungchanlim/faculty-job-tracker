#!/usr/bin/env python3
"""Collect likely CS faculty opening links from data/schools.csv into data/jobs.json.

Uses cs_jobs_url first, then falls back to generic faculty/career pages.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,sys,time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_SCHOOLS=ROOT/'data/schools.csv'; DEFAULT_JOBS=ROOT/'data/jobs.json'; DEFAULT_CANDIDATES=ROOT/'data/school_career_candidates.json'
TODAY=date.today().isoformat()
HEADERS={"User-Agent":"faculty-job-tracker/0.2 (+https://github.com/kyungchan626/faculty-job-tracker)"}
TITLE_RE=re.compile(r'assistant professor|associate professor|open rank|tenure[- ]track|tenured|faculty|professor|lecturer|instructor',re.I)
CS_RE=re.compile(r'computer science|computing|computer engineering|cyber|security|systems|software|artificial intelligence|machine learning|data science|information science|informatics',re.I)
NEG_RE=re.compile(r'admission|graduate program|tuition|student job|postdoc|postdoctoral|research assistant|teaching assistant|scholarship|news|event|seminar',re.I)

def clean(s): return re.sub(r'\s+',' ',str(s or '')).strip()
def norm_url(u):
    u=clean(u)
    return 'https://'+u if u and not u.startswith(('http://','https://')) else u
def fetch(url):
    url=norm_url(url)
    if not url: return ''
    try:
        r=requests.get(url,headers=HEADERS,timeout=25,allow_redirects=True)
        ct=r.headers.get('content-type','')
        if 'html' not in ct and 'text' not in ct: return ''
        r.raise_for_status(); return r.text[:3000000]
    except Exception as e:
        print(f'[WARN] fetch failed {url}: {e}', file=sys.stderr); return ''
def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def load_jobs(path):
    if not Path(path).exists(): return []
    try:
        obj=json.loads(Path(path).read_text(encoding='utf-8')); return obj if isinstance(obj,list) else []
    except Exception: return []
def save_json(path,obj): Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
def infer_rank(t):
    if re.search('assistant professor',t,re.I): return 'Assistant Professor'
    if re.search('associate professor',t,re.I): return 'Associate Professor'
    if re.search('open rank',t,re.I): return 'Open Rank'
    if re.search('lecturer',t,re.I): return 'Lecturer'
    if re.search('instructor',t,re.I): return 'Instructor'
    if re.search('professor',t,re.I): return 'Professor'
    return 'Faculty'
def infer_track(t):
    l=t.lower()
    if 'tenure-track' in l or 'tenure track' in l: return 'tenure-track'
    if 'visiting' in l: return 'visiting'
    if 'lecturer' in l or 'instructor' in l: return 'teaching'
    if 'open rank' in l: return 'open-rank'
    return 'faculty'
def fields(t):
    checks=[('security',r'security|cyber'),('systems',r'systems|distributed|operating systems|network|architecture'),('AI/ML',r'artificial intelligence|machine learning|deep learning|AI'),('software engineering',r'software engineering|programming languages'),('data science',r'data science|analytics'),('computer science',r'computer science|computing'),('computer engineering',r'computer engineering|computer architecture')]
    out=[label for label,pat in checks if re.search(pat,t,re.I)]
    return out or ['computing']
def deadline(t):
    m=re.search(r'(?:deadline|review[^.]{0,30}|apply by|applications? due)[^A-Za-z0-9]{0,20}([A-Z][a-z]+\s+\d{1,2},?\s+20\d{2}|\d{1,2}/\d{1,2}/20\d{2}|20\d{2}-\d{2}-\d{2})',t,re.I)
    return clean(m.group(1)) if m else ''
def make_id(school,title,url): return hashlib.sha256(f'{school}|{title}|{url}'.encode()).hexdigest()[:16]
def build_job(school,title,url,context,source_page):
    text=f'{title} {context}'; school_name=clean(school.get('school'))
    return {'id':make_id(school_name,title,url),'title':clean(title)[:220],'school':school_name,'location':clean(school.get('location')),'state':clean(school.get('state')),'school_rank':clean(school.get('usnews_cs_rank') or school.get('usnews_rank')),'rank':infer_rank(text),'track':infer_track(text),'field':fields(text),'deadline':deadline(context),'source':'CS/school career page','source_url':url,'source_page':source_page,'first_seen':TODAY,'last_seen':TODAY,'status':'open'}
def extract(school,page_url,html,strict):
    soup=BeautifulSoup(html,'html.parser'); out=[]
    for a in soup.find_all('a',href=True):
        title=clean(a.get_text(' ',strip=True)); href=urljoin(page_url,a['href']).split('#')[0]
        hay=f'{title} {href}'
        if not href.startswith('http') or NEG_RE.search(hay): continue
        th=TITLE_RE.search(hay); ch=CS_RE.search(hay)
        if (strict and th and ch) or ((not strict) and (th or ch)): out.append(build_job(school,title or 'Faculty opening',href,hay,page_url))
    page_text=clean(soup.get_text(' ',strip=True))[:10000]
    if TITLE_RE.search(page_text) and CS_RE.search(page_text) and not NEG_RE.search(page_text[:500]): out.append(build_job(school,'Faculty job search page',page_url,page_text,page_url))
    return out
def start_urls(school):
    urls=[]
    for k in ['cs_jobs_url','faculty_jobs_url','careers_url','cs_department_url','official_url']:
        u=norm_url(school.get(k,''))
        if u and u not in urls: urls.append(u)
    return urls
def merge(existing,new):
    d={j.get('id'):j for j in existing if j.get('id')}
    for j in new:
        if j['id'] in d:
            d[j['id']].update({k:v for k,v in j.items() if v not in ('',[],None)}); d[j['id']]['last_seen']=TODAY; d[j['id']]['status']='open'
        else: d[j['id']]=j
    return sorted(d.values(),key=lambda x:(int(x.get('school_rank') or 9999) if str(x.get('school_rank') or '').isdigit() else 9999,x.get('school',''),x.get('title','')))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--schools',default=str(DEFAULT_SCHOOLS)); ap.add_argument('--jobs',default=str(DEFAULT_JOBS)); ap.add_argument('--candidates',default=str(DEFAULT_CANDIDATES)); ap.add_argument('--strict',action='store_true'); ap.add_argument('--sleep',type=float,default=1.0); ap.add_argument('--limit',type=int,default=0); args=ap.parse_args()
    schools=read_csv(args.schools); schools=schools[:args.limit] if args.limit else schools
    allc=[]
    for i,school in enumerate(schools,1):
        print(f"[INFO] {i}/{len(schools)} {school.get('school')}")
        for url in start_urls(school):
            html=fetch(url)
            if not html: continue
            c=extract(school,url,html,args.strict)
            if c: print(f'  [FOUND] {len(c)} candidates from {url}')
            allc.extend(c); time.sleep(args.sleep)
    allc=list({c['id']:c for c in allc}.values())
    save_json(args.candidates,allc); merged=merge(load_jobs(args.jobs),allc); save_json(args.jobs,merged)
    print(f'[OK] wrote {len(allc)} candidates -> {args.candidates}'); print(f'[OK] wrote {len(merged)} merged jobs -> {args.jobs}')
if __name__=='__main__': main()
