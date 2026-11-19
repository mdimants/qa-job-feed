#!/usr/bin/env python3
"""Atlasa uzņēmumus, kurus šodien uzrunāt ar piedāvājumu likt darbus QA Job Board.

Ņem https://www.qajobboard.com/jobs.json, atstāj uzņēmumus ar programmatūras QA darbu,
kas publicēts pēdējās 30 dienās, izlaiž lielos uzņēmumus un jau uzrunātos
(outreach/contacted.csv, tikai lokāli, nav git). Izvada JSON sarakstu.

Palaišana:
  python3 outreach/candidates.py [skaits]               A grupa: 1–6 QA darbi (noklusēti)
  python3 outreach/candidates.py --group b [skaits]     B grupa: 7+ QA darbi, aģentūras un outsourcing
  python3 outreach/candidates.py --group paid [skaits]  nesen samaksāti QA sludinājumi We Work Remotely
"""
import csv
import html
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
                 r"compass uol|kainos|ubisoft|^sofi$|okta|openai|airbnb|tether|upwork|software mind|pearson|experian|genpact|sumup|trivago|airwallex|mercury insurance|"
                 r"discord|mercor|pole to win|^side$|ciklum|endava|^ci&t$|abbvie|scopely|veeva|riot games|zscaler|jetbrains|"
                 r"delivery hero|binance|transperfect|canonical|conduent|^continental$|duolingo|^toast$|jfrog|epic games|nubank|"
                 r"hilton|hearst|keywords studios|livanova|fortive|agilent", re.I)


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


AGENCY = re.compile(r"recruit|staffing|talent|consult|personnel|resourc|placement|headhunt|agency|outsourc|\bstaff\b", re.I)
MULTI_MIN = 7  # no tik QA darbiem uzņēmums ir B grupā (A grupa ņem tikai līdz 6)


def recent_soft(jobs, days=30):
    newest = max(j["published_at"][:10] for j in jobs)
    cutoff = (dt.date.fromisoformat(newest) - dt.timedelta(days=days)).isoformat()
    return [j for j in jobs if (j.get("company") or {}).get("name", "").strip()
            and j["published_at"][:10] >= cutoff and SOFT.search(j["title"]) and not NOT_SOFT.search(j["title"])]


def group_b(n):
    """B grupa: uzņēmumi un aģentūras ar 7+ QA darbiem (piedāvājums: vairāku sludinājumu paka)."""
    jobs = load_jobs()
    per_company = Counter(j["company"]["name"] for j in jobs if j.get("company"))
    done = contacted()
    by = defaultdict(list)
    for j in recent_soft(jobs):
        c = j["company"]["name"].strip()
        if (per_company[c] < MULTI_MIN or BIG.search(c) or c.lower() in done
                or j.get("highlighted") or j.get("sticky")):
            continue
        by[c].append(j)
    out = []
    for c, js in by.items():
        js.sort(key=lambda j: j["published_at"], reverse=True)
        hosts = Counter(urlparse(j.get("application_link") or "").netloc for j in js)
        out.append({
            "company": c,
            "agency": bool(AGENCY.search(c)),
            "open_qa_jobs": len(js),
            "remote_share": round(sum(j.get("location") == "remote" for j in js) / len(js), 2),
            "sample_titles": list(dict.fromkeys(j["title"] for j in js))[:3],
            "job_url": js[0]["links"]["self"],
            "apply_link": js[0].get("application_link") or "",
            "apply_hosts": [h for h, _ in hosts.most_common(3)],
            "published": js[0]["published_at"][:10],
        })
    out.sort(key=lambda r: (r["open_qa_jobs"], r["published"]), reverse=True)
    print(json.dumps(out[:n], ensure_ascii=False, indent=1))
    print(f"# B grupa kopā: {len(out)}, jau uzrunāti: {len(done)}", file=sys.stderr)


WWR_FEEDS = ["remote-jobs", "categories/remote-programming-jobs", "categories/remote-full-stack-programming-jobs",
             "categories/remote-back-end-programming-jobs", "categories/remote-front-end-programming-jobs",
             "categories/remote-devops-sysadmin-jobs", "categories/remote-product-jobs"]


def tag(item, name):
    m = re.search(rf"<{name}>(.*?)</{name}>", item, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def paid(n):
    """Uzņēmumi, kas nesen samaksāja par QA sludinājumu We Work Remotely (no ~$299). Pierādīti pircēji."""
    done = contacted()
    seen = {}
    for feed in WWR_FEEDS:
        req = urllib.request.Request(f"https://weworkremotely.com/{feed}.rss", headers={"User-Agent": "Mozilla/5.0"})
        try:
            xml = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"# {feed}: {e}", file=sys.stderr)
            continue
        for item in xml.split("<item>")[1:]:
            company, _, position = tag(item, "title").partition(": ")
            if not position or not SOFT.search(position) or NOT_SOFT.search(position):
                continue
            if BIG.search(company) or company.lower() in done:
                continue
            link = tag(item, "link")
            if link in seen:
                continue
            site = re.search(r"<strong>URL:</strong>\s*<a href=\"([^\"]+)\"", tag(item, "description"))
            pub = tag(item, "pubDate")
            try:
                pub = dt.datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z").date().isoformat()
            except ValueError:
                pass
            seen[link] = {
                "company": company,
                "job_title": position,
                "wwr_url": link,
                "company_site": site.group(1) if site else "",
                "region": tag(item, "region"),
                "published": pub,
                "source": "weworkremotely (paid)",
            }
    out = sorted(seen.values(), key=lambda r: r["published"], reverse=True)
    print(json.dumps(out[:n], ensure_ascii=False, indent=1))
    print(f"# maksas sludinājumu kandidāti: {len(out)}", file=sys.stderr)


def main():
    args = sys.argv[1:]
    group = "a"
    if "--group" in args:
        i = args.index("--group")
        group = args[i + 1].lower()
        del args[i:i + 2]
    n = int(args[0]) if args else 25
    if group == "b":
        return group_b(n)
    if group == "paid":
        return paid(n)
    jobs = load_jobs()
    newest = max(j["published_at"][:10] for j in jobs)
    cutoff = (dt.date.fromisoformat(newest) - dt.timedelta(days=30)).isoformat()
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
