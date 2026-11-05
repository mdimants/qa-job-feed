"""QA Jobs Board bezmaksas darbu plūsma.

Savāc jaunākos QA / testēšanas darbus no publiskiem avotiem un uzģenerē:
  out/jobs.xml  – Jobboardly XML Importer (Pro plāns, bez kredītiem)
  out/jobs.csv  – Jobboardly CSV Importer (rezerves variants)

Palaišana:  python3 feed.py
"""
import csv
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"
UA = {"User-Agent": "qajobboard-feed/1.0 (+https://www.qajobboard.com)"}
NOW = datetime.now(timezone.utc)

MAX_AGE_DAYS = 21          # vecākus darbus neņemam
MAX_PER_COMPANY = 4        # lai viens uzņēmums neaizpilda visu lapu
POST_LENGTH_DAYS = 30

# ---------- filtri ----------
QA_RE = re.compile(
    r"\b(qa|q\.a\.|quality assurance|sdet|sdet\w*|tester|testers|testing|"
    r"test (?:engineer|lead|manager|analyst|automation|architect|specialist|developer)|"
    r"test automation|automation tester|qa automation|qe|quality engineer\w*|software engineer in test|"
    r"developer in test|performance (?:test|engineer)|penetration tester|pentester)\b",
    re.I,
)
EXCLUDE_RE = re.compile(
    r"clinical|laborator|medical device|food|pharma|manufactur|supplier quality|"
    r"quality control|qc inspector|nurse|driver|warehouse|a/b test|test pilot|"
    r"drive test|hardware test technician|construction|welding|chemist|"
    r"data quality|quality of earnings|call quality|quality coach|quality specialist - customer|"
    r"electrical|mechatronic|mechanical|nuclear|network security|coordinator|handler|"
    r"\bhvac\b|civil|structural|battery|rf test|antenna|optical|validation technician",
    re.I,
)

CATEGORIES = [  # (regex, Jobboardly kategorija) – pirmais trāpījums uzvar
    (r"penetration|pentest", "Penetration Tester"),
    (r"performance|load test", "Performance Tester"),
    (r"sdet|engineer in test|developer in test", "Software Development Engineer in Test (SDET)"),
    (r"test manager|qa manager|head of (qa|quality)|director.*(qa|quality)", "Test Manager"),
    (r"qa lead|lead qa|quality lead", "QA Lead"),
    (r"test lead|lead test", "Test Lead"),
    (r"automation", "QA Automation Engineer"),
    (r"junior|entry|intern|graduate", "Junior QA Engineer"),
    (r"manual", "QA Manual Tester"),
    (r"analyst", "QA Analyst"),
    (r"senior|sr\.?|staff|principal", "Senior QA Engineer"),
    (r"test engineer", "Test Engineer"),
    (r"tester|testing", "Software Tester"),
    (r".", "QA Engineer"),
]


def category(title: str) -> str:
    for rx, name in CATEGORIES:
        if re.search(rx, title, re.I):
            return name
    return "QA Engineer"


def is_qa(title: str) -> bool:
    return bool(QA_RE.search(title)) and not EXCLUDE_RE.search(title)


# ---------- palīgi ----------
def get(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def parse_date(v):
    if v in (None, ""):
        return None
    try:
        if isinstance(v, (int, float)) or str(v).isdigit():
            v = float(v)
            if v > 1e12:
                v /= 1000
            return datetime.fromtimestamp(v, timezone.utc)
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def job_type(v: str) -> str:
    v = (v or "").lower()
    if "part" in v:
        return "parttime"
    if "contract" in v or "freelance" in v:
        return "contract"
    if "intern" in v:
        return "internship"
    if "temp" in v:
        return "temporary"
    return "fulltime"


def loc_type(remote: bool, text: str = "") -> str:
    t = (text or "").lower()
    if "hybrid" in t:
        return "hybrid"
    if remote or "remote" in t:
        return "remote"
    return "onsite"


def job(**kw):
    base = dict(id="", title="", company="", company_url="", logo="", job_type="fulltime",
                location_type="onsite", office_location="", location_limits="", description="",
                apply_url="", salary_min="", salary_max="", currency="", salary_period="",
                date=None, source="")
    base.update(kw)
    base["title"] = html.unescape(base["title"]).strip()
    base["company"] = html.unescape(base["company"]).strip()
    return base


# ---------- avoti ----------
def src_greenhouse(slug):
    meta = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}")
    data = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    out = []
    for j in data.get("jobs", []):
        if not is_qa(j["title"]):
            continue
        loc = (j.get("location") or {}).get("name", "")
        out.append(job(id=f"gh-{slug}-{j['id']}", title=j["title"], company=meta.get("name") or slug,
                       location_type=loc_type(False, loc), office_location=loc,
                       description=html.unescape(j.get("content", "")), apply_url=j["absolute_url"],
                       date=parse_date(j.get("first_published") or j.get("updated_at")), source="greenhouse"))
    return out


def src_lever(slug):
    out = []
    for j in get(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        if not is_qa(j["text"]):
            continue
        cat = j.get("categories") or {}
        loc = cat.get("location", "")
        desc = (j.get("description") or "") + "".join(
            f"<h3>{l.get('text','')}</h3><ul>{l.get('content','')}</ul>" for l in j.get("lists", [])
        ) + (j.get("additional") or "")
        sal = j.get("salaryRange") or {}
        out.append(job(id=f"lv-{slug}-{j['id']}", title=j["text"], company=slug.title(),
                       job_type=job_type(cat.get("commitment")),
                       location_type=loc_type(False, j.get("workplaceType", "") + " " + loc),
                       office_location=loc, description=desc, apply_url=j.get("hostedUrl"),
                       salary_min=sal.get("min", ""), salary_max=sal.get("max", ""),
                       currency=sal.get("currency", ""),
                       salary_period={"per-year-salary": "yearly", "per-month-salary": "monthly",
                                      "per-hour-wage": "hourly"}.get(sal.get("interval", ""), ""),
                       date=parse_date(j.get("createdAt")), source="lever"))
    return out


ASHBY_NAMES = {"1password": "1Password", "posthog": "PostHog", "openai": "OpenAI", "gitbook": "GitBook"}


def src_ashby(slug):
    data = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    out = []
    for j in data.get("jobs", []):
        if not j.get("isListed", True) or not is_qa(j["title"]):
            continue
        out.append(job(id=f"ab-{slug}-{j['id']}", title=j["title"],
                       company=ASHBY_NAMES.get(slug, slug.replace("-", " ").title()),
                       job_type=job_type(j.get("employmentType")),
                       location_type=loc_type(j.get("isRemote") and j.get("workplaceType") != "Hybrid",
                                              j.get("workplaceType", "") or ""),
                       office_location=j.get("location", ""), description=j.get("descriptionHtml", ""),
                       apply_url=j.get("jobUrl"), date=parse_date(j.get("publishedAt")), source="ashby"))
    return out


HIMALAYAS_QUERIES = ["qa engineer", "sdet", "software tester", "test automation", "quality assurance",
                     "qa analyst", "test engineer", "qa lead", "test manager", "performance tester"]


def src_himalayas(query):
    out = []
    for page in (1, 2):
        q = urllib.parse.quote(query)
        data = get(f"https://himalayas.app/jobs/api/search?q={q}&page={page}")
        for j in data.get("jobs", []):
            if not is_qa(j["title"]):
                continue
            limits = j.get("locationRestrictions") or []
            per = {"annual": "yearly", "month": "monthly", "hour": "hourly"}.get(j.get("salaryPeriod") or "", "yearly")
            out.append(job(id="hm-" + re.sub(r"\W+", "-", j.get("guid", j["title"]))[-80:] + "-" + str(j.get("pubDate")),
                           title=j["title"], company=j.get("companyName", ""), logo=j.get("companyLogo") or "",
                           job_type=job_type(j.get("employmentType")), location_type="remote",
                           location_limits=", ".join(limits), description=j.get("description", ""),
                           apply_url=j.get("applicationLink"),
                           salary_min=j.get("minSalary") or "", salary_max=j.get("maxSalary") or "",
                           currency=j.get("currency") or "", salary_period=per if j.get("minSalary") else "",
                           date=parse_date(j.get("pubDate")), source="himalayas"))
    return out


def src_remotive(query):
    data = get(f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(query)}")
    out = []
    for j in data.get("jobs", []):
        if not is_qa(j["title"]):
            continue
        loc = j.get("candidate_required_location", "")
        out.append(job(id=f"rm-{j['id']}", title=j["title"], company=j.get("company_name", ""),
                       logo=j.get("company_logo") or "", job_type=job_type(j.get("job_type")),
                       location_type="remote",
                       location_limits="" if loc.lower() in ("worldwide", "anywhere", "") else loc,
                       description=j.get("description", ""), apply_url=j.get("url"),
                       date=parse_date(j.get("publication_date")), source="remotive"))
    return out


def src_arbeitnow(page):
    data = get(f"https://www.arbeitnow.com/api/job-board-api?page={page}")
    out = []
    for j in data.get("data", []):
        if not is_qa(j["title"]):
            continue
        out.append(job(id=f"an-{j['slug']}", title=j["title"], company=j.get("company_name", ""),
                       job_type=job_type(" ".join(j.get("job_types") or [])),
                       location_type=loc_type(j.get("remote"), ""), office_location=j.get("location", ""),
                       description=j.get("description", ""), apply_url=j.get("url"),
                       date=parse_date(j.get("created_at")), source="arbeitnow"))
    return out


def src_remoteok(_):
    out = []
    for j in get("https://remoteok.com/api")[1:]:
        title = html.unescape(j.get("position", ""))
        if not is_qa(title):
            continue
        smin, smax = j.get("salary_min") or "", j.get("salary_max") or ""
        out.append(job(id=f"ro-{j['id']}", title=title, company=j.get("company", ""),
                       logo=j.get("company_logo") or "", location_type="remote",
                       location_limits=j.get("location", ""),
                       description=j.get("description", "") + '<p>Via <a href="https://remoteok.com">Remote OK</a></p>',
                       apply_url=j.get("url"), salary_min=smin or "", salary_max=smax or "",
                       currency="USD" if smin else "", salary_period="yearly" if smin else "",
                       date=parse_date(j.get("epoch")), source="remoteok"))
    return out


# ---------- galvenais ----------
def collect():
    companies = json.loads((HERE / "companies.json").read_text())
    tasks = [(src_greenhouse, s) for s in companies.get("greenhouse", [])]
    tasks += [(src_lever, s) for s in companies.get("lever", [])]
    tasks += [(src_ashby, s) for s in companies.get("ashby", [])]
    tasks += [(src_himalayas, q) for q in HIMALAYAS_QUERIES]
    tasks += [(src_remotive, q) for q in ("qa", "test", "sdet", "quality")]
    tasks += [(src_arbeitnow, p) for p in (1, 2, 3)]
    tasks += [(src_remoteok, None)]

    errors, jobs = [], []

    def run(t):
        fn, arg = t
        try:
            return fn(arg)
        except Exception as e:
            errors.append(f"{fn.__name__}({arg}): {e}")
            return []

    with ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(run, tasks):
            jobs.extend(res)
    return jobs, errors


def clean(jobs):
    cutoff = NOW - timedelta(days=MAX_AGE_DAYS)
    seen, per_company, out = set(), {}, []
    jobs = [j for j in jobs if j["apply_url"] and j["company"] and j["date"] and j["date"] >= cutoff]
    jobs.sort(key=lambda j: j["date"], reverse=True)
    for j in jobs:
        key = (re.sub(r"\W+", "", j["title"].lower()), re.sub(r"\W+", "", j["company"].lower()))
        if key in seen:
            continue
        seen.add(key)
        c = key[1]
        if per_company.get(c, 0) >= MAX_PER_COMPANY:
            continue
        per_company[c] = per_company.get(c, 0) + 1
        j["category"] = category(j["title"])
        if j["location_type"] != "remote" and not j["office_location"]:
            j["location_type"] = "remote"
        out.append(j)
    return out


def write_xml(jobs, path):
    rows = []
    for j in jobs:
        f = lambda k: escape(str(j.get(k) or ""))
        rows.append(
            "  <job>\n"
            f"    <id>{f('id')}</id>\n"
            f"    <title>{f('title')}</title>\n"
            f"    <company>{f('company')}</company>\n"
            f"    <company_url>{f('company_url')}</company_url>\n"
            f"    <company_logo>{f('logo')}</company_logo>\n"
            f"    <job_type>{f('job_type')}</job_type>\n"
            f"    <category>{f('category')}</category>\n"
            f"    <location_type>{f('location_type')}</location_type>\n"
            f"    <location>{f('office_location')}</location>\n"
            f"    <location_limits>{f('location_limits')}</location_limits>\n"
            f"    <apply_url>{f('apply_url')}</apply_url>\n"
            f"    <salary_min>{f('salary_min')}</salary_min>\n"
            f"    <salary_max>{f('salary_max')}</salary_max>\n"
            f"    <salary_currency>{f('currency')}</salary_currency>\n"
            f"    <salary_period>{f('salary_period')}</salary_period>\n"
            f"    <date_posted>{j['date'].strftime('%Y-%m-%d')}</date_posted>\n"
            f"    <description><![CDATA[{(j['description'] or '').replace(']]>', ']]&gt;')}]]></description>\n"
            "  </job>"
        )
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<jobs>\n' + "\n".join(rows) + "\n</jobs>\n",
                    encoding="utf-8")


CSV_HEADER = ["Job title", "Job type", "Company name", "Company URL", "Company logo", "Job location",
              "Office location", "Location limits", "Description", "Apply URL", "Apply email", "Salary min",
              "Salary maximum", "Salary currency", "Salary schedule", "Highlighted", "Sticky", "Post length",
              "Post state", "Date posted", "Category name"]


def write_csv(jobs, path):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
        for j in jobs:
            has_sal = bool(j["salary_min"] and j["currency"] and j["salary_period"])
            w.writerow([j["title"], j["job_type"], j["company"], j["company_url"], j["logo"],
                        j["location_type"], j["office_location"], j["location_limits"], j["description"],
                        j["apply_url"], "",
                        j["salary_min"] if has_sal else "", j["salary_max"] if has_sal else "",
                        j["currency"] if has_sal else "", j["salary_period"] if has_sal else "",
                        "false", "false", POST_LENGTH_DAYS, "published",
                        j["date"].strftime("%Y-%m-%d"), j["category"]])


def main():
    OUT.mkdir(exist_ok=True)
    raw, errors = collect()
    jobs = clean(raw)
    write_xml(jobs, OUT / "jobs.xml")
    write_csv(jobs, OUT / "jobs.csv")
    by_src = {}
    for j in jobs:
        by_src[j["source"]] = by_src.get(j["source"], 0) + 1
    last24 = sum(1 for j in jobs if j["date"] >= NOW - timedelta(days=1))
    print(f"{len(jobs)} darbi (no {len(raw)} atrastajiem), pēdējās 24h: {last24}. Avoti: {by_src}")
    if errors:
        print(f"{len(errors)} kļūdas, piem.: {errors[:3]}")


if __name__ == "__main__":
    main()
