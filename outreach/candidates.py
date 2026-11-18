#!/usr/bin/env python3
"""Atlasa uzņēmumus, kurus šodien uzrunāt ar piedāvājumu likt darbus QA Job Board.

Ņem https://www.qajobboard.com/jobs.json, atstāj uzņēmumus ar programmatūras QA darbu,
kas publicēts pēdējās 10 dienās, izlaiž lielos uzņēmumus un jau uzrunātos
(outreach/contacted.csv, tikai lokāli, nav git). Izvada JSON sarakstu.

Palaišana: python3 outreach/candidates.py [skaits]
"""
import csv
import http.client
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
CONTACTED = os.path.join(HERE, "contacted.csv")

SOFT = re.compile(r"\b(QA|SDET|Quality Assurance|Test(er|ing)?|Automation)\b", re.I)
NOT_SOFT = re.compile(r"penetration|metrology|manufactur|mechanical|clinical|food|supplier|welding|construction|"
                      r"laborator|chemical|electrical|hardware|pharma|medical device|call cent|GxP|GMP|advocacy|reliability|photonics|environmental|device", re.I)
# Lielie uzņēmumi un konsultāciju milži par sludinājumu nemaksās
BIG = re.compile(r"nvidia|google|amazon|microsoft|apple|meta|oracle|ibm|sap\b|^sas$|bosch|cgi\b|expleo|alten|"
                 r"accenture|capgemini|deloitte|infosys|wipro|tcs|tata|cognizant|hcl|peraton|leidos|lockheed|"
                 r"raytheon|boeing|siemens|ericsson|nokia|intel\b|cisco|dell|hp\b|salesforce|adobe|jpmorgan|"
                 r"citi|wells fargo|bank of america|walmart|uber|netflix|spotify|epam|globallogic|luxoft|"
                 r"booz allen|general dynamics|northrop|saic|caci|mantech|avaya|dexcom|fortrea|jabil|^icf$|valtech|"
                 r"compass uol|kainos|ubisoft|^sofi$|okta|openai|airbnb|tether|upwork|software mind|pearson|experian|genpact|sumup|trivago|airwallex|mercury insurance", re.I)


def contacted():
    if not os.path.exists(CONTACTED):
        return set()
    with open(CONTACTED) as f:
        return {r["company"].strip().lower() for r in csv.DictReader(f)}


def load_jobs():
    """jobs.json ir ~25 MB un dažreiz atgriež 502 vai pārtrūkst: mēģina vairākas reizes."""
    req = urllib.request.Request("https://www.qajobboard.com/jobs.json", headers={"User-Agent": "qa-feed-outreach"})
    for attempt in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=180).read())
        except (urllib.error.URLError, http.client.IncompleteRead, TimeoutError) as e:
            if attempt == 3:
                raise
            print(f"# jobs.json kļūda ({e}), mēģinu vēlreiz", file=sys.stderr)
            time.sleep(15 * (attempt + 1))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    jobs = load_jobs()
    newest = max(j["published_at"][:10] for j in jobs)
    cutoff = (dt.date.fromisoformat(newest) - dt.timedelta(days=10)).isoformat()
    per_company = Counter(j["company"]["name"] for j in jobs if j.get("company"))
    done = contacted()
    by = defaultdict(list)
    for j in jobs:
        c = (j.get("company") or {}).get("name", "").strip()
        t = j["title"]
        if (not c or j["published_at"][:10] < cutoff or not SOFT.search(t) or NOT_SOFT.search(t)
                or BIG.search(c) or per_company[c] > 6 or c.lower() in done
                or j.get("highlighted") or j.get("sticky")):
            continue
        by[c].append(j)
    out = []
    for c, js in by.items():
        js.sort(key=lambda j: j["published_at"], reverse=True)
        j = js[0]
        apply = j.get("application_link") or ""
        host = urlparse(apply).netloc
        out.append({
            "company": c,
            "company_location": j["company"].get("location") or "",
            "open_qa_jobs": len(js),
            "job_title": j["title"],
            "job_url": j["links"]["self"],
            "apply_link": apply,
            "apply_host": host,
            "published": j["published_at"][:10],
            "remote": j.get("location") == "remote",
        })
    # Vispirms tie, kam vairāk QA darbu un tiešs ATS/karjeras saites hosts (ne agregators)
    agg = re.compile(r"himalayas|arbeitnow|remoteok|jobicy|workingnomads|linkedin|indeed", re.I)
    out.sort(key=lambda r: (r["open_qa_jobs"], not agg.search(r["apply_host"]), r["published"]), reverse=True)
    print(json.dumps(out[:n], ensure_ascii=False, indent=1))
    print(f"# kandidāti kopā: {len(out)}, jau uzrunāti: {len(done)}", file=sys.stderr)


if __name__ == "__main__":
    main()
