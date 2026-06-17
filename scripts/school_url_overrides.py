#!/usr/bin/env python3
"""Curated stable official/CS department URL hints for high-priority CS schools.

The crawler still validates/follows links from these pages.  These hints prevent the
slow/fragile search step from starting from an empty URL for well-known institutions.
"""
from __future__ import annotations

# Only use stable official and department homepages here unless the job page is very stable.
# Leave job URLs blank when uncertain; enrich_schools.py will discover job links from the CS page.
KNOWN_SCHOOL_URLS: dict[str, dict[str, str]] = {
    "carnegie mellon university": {
        "official_url": "https://www.cmu.edu/",
        "cs_department_url": "https://www.cs.cmu.edu/",
    },
    "massachusetts institute of technology": {
        "official_url": "https://www.mit.edu/",
        "cs_department_url": "https://www.eecs.mit.edu/",
        "careers_url": "https://hr.mit.edu/careers",
    },
    "stanford university": {
        "official_url": "https://www.stanford.edu/",
        "cs_department_url": "https://cs.stanford.edu/",
    },
    "university of california--berkeley": {
        "official_url": "https://www.berkeley.edu/",
        "cs_department_url": "https://eecs.berkeley.edu/",
    },
    "university of illinois--urbana-champaign": {
        "official_url": "https://illinois.edu/",
        "cs_department_url": "https://cs.illinois.edu/",
    },
    "princeton university": {
        "official_url": "https://www.princeton.edu/",
        "cs_department_url": "https://www.cs.princeton.edu/",
        "faculty_jobs_url": "https://dof.princeton.edu/academicjobs",
    },
    "cornell university": {
        "official_url": "https://www.cornell.edu/",
        "cs_department_url": "https://www.cs.cornell.edu/",
    },
    "georgia institute of technology": {
        "official_url": "https://www.gatech.edu/",
        "cs_department_url": "https://www.cc.gatech.edu/",
    },
    "university of washington": {
        "official_url": "https://www.washington.edu/",
        "cs_department_url": "https://www.cs.washington.edu/",
    },
    "university of texas--austin": {
        "official_url": "https://www.utexas.edu/",
        "cs_department_url": "https://www.cs.utexas.edu/",
    },
    "university of michigan--ann arbor": {
        "official_url": "https://umich.edu/",
        "cs_department_url": "https://eecs.engin.umich.edu/",
    },
    "california institute of technology": {
        "official_url": "https://www.caltech.edu/",
        "cs_department_url": "https://www.cms.caltech.edu/",
    },
    "university of california--san diego": {
        "official_url": "https://ucsd.edu/",
        "cs_department_url": "https://cse.ucsd.edu/",
    },
    "university of maryland--college park": {
        "official_url": "https://www.umd.edu/",
        "cs_department_url": "https://www.cs.umd.edu/",
    },
    "columbia university": {
        "official_url": "https://www.columbia.edu/",
        "cs_department_url": "https://www.cs.columbia.edu/",
    },
    "purdue university--west lafayette": {
        "official_url": "https://www.purdue.edu/",
        "cs_department_url": "https://www.cs.purdue.edu/",
    },
    "university of california--los angeles": {
        "official_url": "https://www.ucla.edu/",
        "cs_department_url": "https://www.cs.ucla.edu/",
    },
    "university of wisconsin--madison": {
        "official_url": "https://www.wisc.edu/",
        "cs_department_url": "https://www.cs.wisc.edu/",
    },
    "harvard university": {
        "official_url": "https://www.harvard.edu/",
        "cs_department_url": "https://seas.harvard.edu/computer-science",
        "careers_url": "https://hr.harvard.edu/careers",
    },
    "university of pennsylvania": {
        "official_url": "https://www.upenn.edu/",
        "cs_department_url": "https://www.cis.upenn.edu/",
    },
    "johns hopkins university": {
        "official_url": "https://www.jhu.edu/",
        "cs_department_url": "https://www.cs.jhu.edu/",
    },
    "university of chicago": {
        "official_url": "https://www.uchicago.edu/",
        "cs_department_url": "https://cs.uchicago.edu/",
    },
    "university of southern california": {
        "official_url": "https://www.usc.edu/",
        "cs_department_url": "https://www.cs.usc.edu/",
    },
    "yale university": {
        "official_url": "https://www.yale.edu/",
        "cs_department_url": "https://cpsc.yale.edu/",
    },
    "duke university": {
        "official_url": "https://duke.edu/",
        "cs_department_url": "https://www.cs.duke.edu/",
    },
    "university of massachusetts--amherst": {
        "official_url": "https://www.umass.edu/",
        "cs_department_url": "https://www.cics.umass.edu/",
    },
    "brown university": {
        "official_url": "https://www.brown.edu/",
        "cs_department_url": "https://cs.brown.edu/",
    },
    "new york university": {
        "official_url": "https://www.nyu.edu/",
        "cs_department_url": "https://cs.nyu.edu/",
    },
    "northwestern university": {
        "official_url": "https://www.northwestern.edu/",
        "cs_department_url": "https://www.mccormick.northwestern.edu/computer-science/",
    },
    "rice university": {
        "official_url": "https://www.rice.edu/",
        "cs_department_url": "https://cs.rice.edu/",
    },
    "university of california--irvine": {
        "official_url": "https://uci.edu/",
        "cs_department_url": "https://ics.uci.edu/",
    },
    "university of california--santa barbara": {
        "official_url": "https://www.ucsb.edu/",
        "cs_department_url": "https://cs.ucsb.edu/",
    },
    "university of north carolina--chapel hill": {
        "official_url": "https://www.unc.edu/",
        "cs_department_url": "https://cs.unc.edu/",
    },
    "northeastern university": {
        "official_url": "https://www.northeastern.edu/",
        "cs_department_url": "https://www.khoury.northeastern.edu/",
    },
    "university of colorado--boulder": {
        "official_url": "https://www.colorado.edu/",
        "cs_department_url": "https://www.colorado.edu/cs/",
    },
    "university of virginia": {
        "official_url": "https://www.virginia.edu/",
        "cs_department_url": "https://engineering.virginia.edu/departments/computer-science",
    },
    "virginia tech": {
        "official_url": "https://www.vt.edu/",
        "cs_department_url": "https://cs.vt.edu/",
    },
    "ohio state university": {
        "official_url": "https://www.osu.edu/",
        "cs_department_url": "https://cse.osu.edu/",
    },
    "pennsylvania state university--university park": {
        "official_url": "https://www.psu.edu/",
        "cs_department_url": "https://www.eecs.psu.edu/",
    },
    "texas a&m university--college station": {
        "official_url": "https://www.tamu.edu/",
        "cs_department_url": "https://engineering.tamu.edu/cse/",
    },
    "university of california--davis": {
        "official_url": "https://www.ucdavis.edu/",
        "cs_department_url": "https://cs.ucdavis.edu/",
    },
    "university of minnesota--twin cities": {
        "official_url": "https://twin-cities.umn.edu/",
        "cs_department_url": "https://cse.umn.edu/cs",
    },
    "arizona state university": {
        "official_url": "https://www.asu.edu/",
        "cs_department_url": "https://scai.engineering.asu.edu/",
    },
    "rutgers university--new brunswick": {
        "official_url": "https://www.rutgers.edu/",
        "cs_department_url": "https://www.cs.rutgers.edu/",
    },
    "stony brook university--suny": {
        "official_url": "https://www.stonybrook.edu/",
        "cs_department_url": "https://www.cs.stonybrook.edu/",
    },
    "boston university": {
        "official_url": "https://www.bu.edu/",
        "cs_department_url": "https://www.bu.edu/cs/",
    },
    "north carolina state university": {
        "official_url": "https://www.ncsu.edu/",
        "cs_department_url": "https://www.csc.ncsu.edu/",
    },
    "university of utah": {
        "official_url": "https://www.utah.edu/",
        "cs_department_url": "https://www.cs.utah.edu/",
    },
    "vanderbilt university": {
        "official_url": "https://www.vanderbilt.edu/",
        "cs_department_url": "https://engineering.vanderbilt.edu/eecs/",
    },
    "washington university in st. louis": {
        "official_url": "https://wustl.edu/",
        "cs_department_url": "https://cse.wustl.edu/",
    },
}
