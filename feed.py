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
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"
UA = {"User-Agent": "qajobboard-feed/1.0 (+https://www.qajobboard.com)"}
NOW = datetime.now(timezone.utc)

MAX_AGE_DAYS = 45          # darbi, kas vēl atvērti avotā; Jobboardly glabā 60 d., dzēš, kad pazūd no plūsmas
MAX_PER_COMPANY = 6        # lai viens uzņēmums neaizpilda visu lapu
HIMALAYAS_MAX_PAGES = 60   # 20 darbi lapā
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
    r"\bhvac\b|civil|structural|battery|rf test|antenna|optical|validation technician|"
    r"linguist|language|translat|transcri|annotat|rater|evaluator|data qa|ai trainer|"
    r"writing|writer|tutor|bilingual|native speaker|freelance tester in|testers wanted",
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
                     "qa analyst", "test engineer", "qa lead", "test manager", "performance tester",
                     "qa automation", "quality engineer", "automation tester", "manual tester",
                     "software engineer in test", "qa specialist", "test analyst", "mobile qa", "game tester"]


def src_himalayas(query):
    out = []
    for page in range(1, HIMALAYAS_MAX_PAGES + 1):
        q = urllib.parse.quote(query)
        data = None
        for wait in (2, 5, 15, 30):          # Himalayas reizēm atbild 503 – mēģinām vēlreiz
            try:
                data = get(f"https://himalayas.app/jobs/api/search?q={q}&page={page}")
                break
            except Exception:
                time.sleep(wait)
        if data is None:
            break                            # paturam jau savāktās lapas
        time.sleep(0.8)
        if not data.get("jobs"):
            break
        for j in data.get("jobs", []):
            if not is_qa(j["title"]):
                continue
            limits = j.get("locationRestrictions") or []
            per = {"annual": "yearly", "month": "monthly", "hour": "hourly"}.get(j.get("salaryPeriod") or "", "yearly")
            out.append(job(id="hm-" + re.sub(r"\W+", "-", j.get("guid", j["title"]))[-80:] + "-" + str(j.get("pubDate")),
                           title=j["title"], company=j.get("companyName", ""), logo=j.get("companyLogo") or "",
                           job_type=job_type(j.get("employmentType")), location_type="remote",
                           location_limits=norm_limits(limits, True), description=j.get("description", ""),
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


def src_smartrecruiters(slug):
    out, seen = [], set()
    for q in ("test", "qa", "quality"):
        data = get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?q={q}&limit=100")
        for j in data.get("content", []):
            if j["id"] in seen or not is_qa(j["name"]):
                continue
            seen.add(j["id"])
            loc = j.get("location") or {}
            place = ", ".join(x for x in (loc.get("city"), loc.get("country", "").upper()) if x)
            remote = loc.get("remote") or loc.get("fullyRemote")
            out.append(job(id=f"sr-{slug}-{j['id']}", title=j["name"],
                           company=(j.get("company") or {}).get("name", slug),
                           job_type=job_type((j.get("typeOfEmployment") or {}).get("label", "")),
                           location_type=loc_type(remote, "hybrid" if loc.get("hybrid") else ""),
                           office_location=place,
                           description=f"<p>{html.escape(j['name'])} at {html.escape((j.get('company') or {}).get('name', slug))}.</p>"
                                       f"<p>Location: {html.escape(place or 'Remote')}</p>"
                                       f"<p>See the full job description and apply on the company careers page.</p>",
                           apply_url=f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                           date=parse_date(j.get("releasedDate")), source="smartrecruiters"))
    return out


def src_jobicy(_):
    out = []
    for j in get("https://jobicy.com/api/v2/remote-jobs?count=100").get("jobs", []):
        if not is_qa(j.get("jobTitle", "")):
            continue
        geo = j.get("jobGeo", "")
        out.append(job(id=f"jc-{j['id']}", title=html.unescape(j["jobTitle"]), company=j.get("companyName", ""),
                       logo=j.get("companyLogo") or "", job_type=job_type(" ".join(j.get("jobType") or [])),
                       location_type="remote",
                       location_limits="" if geo.lower() in ("anywhere", "") else geo,
                       description=j.get("jobDescription", ""), apply_url=j.get("url"),
                       date=parse_date(j.get("pubDate")), source="jobicy"))
    return out


def src_workingnomads(_):
    out = []
    for j in get("https://www.workingnomads.com/api/exposed_jobs/"):
        if not is_qa(j.get("title", "")):
            continue
        out.append(job(id="wn-" + re.sub(r"\W+", "-", j.get("url", ""))[-60:], title=j["title"],
                       company=j.get("company_name", ""), location_type="remote",
                       location_limits=j.get("location", "") if j.get("location", "").lower() != "anywhere" else "",
                       description=j.get("description", ""), apply_url=j.get("url"),
                       date=parse_date(j.get("pub_date")), source="workingnomads"))
    return out


# ---------- galvenais ----------
def collect():
    companies = json.loads((HERE / "companies.json").read_text())
    tasks = [(src_greenhouse, s) for s in companies.get("greenhouse", [])]
    tasks += [(src_lever, s) for s in companies.get("lever", [])]
    tasks += [(src_ashby, s) for s in companies.get("ashby", [])]
    tasks += [(src_smartrecruiters, s) for s in companies.get("smartrecruiters", [])]
    tasks += [(src_jobicy, None), (src_workingnomads, None)]
    tasks += [(src_remotive, q) for q in ("qa", "test", "sdet", "quality")]
    tasks += [(src_arbeitnow, p) for p in range(1, 11)]
    tasks += [(src_remoteok, None)]

    errors, jobs = [], []

    def run(t):
        fn, arg = t
        try:
            return fn(arg)
        except Exception as e:
            errors.append(f"{fn.__name__}({arg}): {e}")
            return []

    # Himalayas – lēnāk (2 paralēli), lai neatsakās ar 503; pārējie avoti paralēli
    with ThreadPoolExecutor(max_workers=2) as hx, ThreadPoolExecutor(max_workers=12) as ex:
        hfut = hx.map(run, [(src_himalayas, q) for q in HIMALAYAS_QUERIES])
        for res in ex.map(run, tasks):
            jobs.extend(res)
        for res in hfut:
            jobs.extend(res)
    return jobs, errors


# Jobboardly saprot vienu valsti vai reģionu (Worldwide, Europe, LATAM, EMEA, APAC...).
# Gari valstu saraksti tiek saglabāti kā teksts, un Google JobPosting tad trūkst applicantLocationRequirements.
_R = lambda t: {x.strip() for x in t.split(";")}
REG_EUROPE = _R("Albania;Andorra;Austria;Belarus;Belgium;Bosnia and Herzegovina;Bulgaria;Croatia;Cyprus;Czechia;Czech Republic;Denmark;Estonia;Faroe Islands;Finland;France;Germany;Gibraltar;Greece;Guernsey;Holy See (Vatican City State);Hungary;Iceland;Ireland;Isle of Man;Italy;Jersey;Kosovo;Latvia;Liechtenstein;Lithuania;Luxembourg;Malta;Moldova;Monaco;Montenegro;Netherlands;North Macedonia;Norway;Poland;Portugal;Romania;Russian Federation;Russia;San Marino;Serbia;Slovakia;Slovenia;Spain;Svalbard and Jan Mayen;Sweden;Switzerland;Ukraine;United Kingdom;Åland Islands;Armenia;Georgia;Azerbaijan;Turkey")
REG_LATAM = _R("Anguilla;Antigua and Barbuda;Argentina;Aruba;Bahamas;Barbados;Belize;Bermuda;Bolivia;Bonaire;Sint Eustatius and Saba;Brazil;Cayman Islands;Chile;Colombia;Costa Rica;Cuba;Curaçao;Dominica;Dominican Republic;Ecuador;El Salvador;Falkland Islands (Malvinas);French Guiana;Grenada;Guadeloupe;Guatemala;Guyana;Haiti;Honduras;Jamaica;Martinique;Mexico;Montserrat;Nicaragua;Panama;Paraguay;Peru;Puerto Rico;Saint Barthélemy;Saint Kitts and Nevis;Saint Lucia;Saint Martin (French part);Saint Vincent and the Grenadines;Sint Maarten (Dutch part);South Georgia and the South Sandwich Islands;Suriname;Trinidad and Tobago;Turks and Caicos Islands;Uruguay;Venezuela;Virgin Islands")
REG_NA = _R("United States;USA;Canada;Greenland;Saint Pierre and Miquelon;United States Minor Outlying Islands")
REG_MEA = _R("Algeria;Angola;Bahrain;Benin;Botswana;Burkina Faso;Burundi;Cabo Verde;Cameroon;Central African Republic;Chad;Comoros;Congo;Côte d'Ivoire;Djibouti;Egypt;Equatorial Guinea;Eritrea;Eswatini;Ethiopia;Gabon;Gambia;Ghana;Guinea;Guinea-Bissau;Iran;Iraq;Israel;Jordan;Kenya;Kuwait;Lebanon;Lesotho;Liberia;Libya;Madagascar;Malawi;Mali;Mauritania;Mauritius;Mayotte;Morocco;Mozambique;Namibia;Niger;Nigeria;Oman;Palestine;Qatar;Rwanda;Réunion;Saint Helena;Sao Tome and Principe;Saudi Arabia;Senegal;Seychelles;Sierra Leone;Somalia;South Africa;South Sudan;Sudan;Syrian Arab Republic;Tanzania;Togo;Tunisia;Uganda;United Arab Emirates;Western Sahara;Yemen;Zambia;Zimbabwe")
REG_APAC = _R("Afghanistan;American Samoa;Australia;Bangladesh;Bhutan;British Indian Ocean Territory;Brunei Darussalam;Cambodia;China;Christmas Island;Cocos (Keeling) Islands;Cook Islands;Fiji;French Polynesia;Guam;Hong Kong;India;Indonesia;Japan;Kazakhstan;Kiribati;Kyrgyzstan;Lao People's Democratic Republic;Macao;Malaysia;Maldives;Marshall Islands;Micronesia;Mongolia;Myanmar;Nauru;Nepal;New Caledonia;New Zealand;Niue;Norfolk Island;Northern Mariana Islands;Pakistan;Palau;Papua New Guinea;Philippines;Pitcairn;Samoa;Singapore;Solomon Islands;South Korea;Sri Lanka;Taiwan;Tajikistan;Thailand;Timor-Leste;Tokelau;Tonga;Turkmenistan;Tuvalu;Uzbekistan;Vanuatu;Vietnam;Wallis and Futuna")
REGIONS = {"Europe": REG_EUROPE, "LATAM": REG_LATAM, "North America": REG_NA, "EMEA": REG_MEA, "APAC": REG_APAC}


def norm_limits(limits, remote):
    """Pārvērš valstu sarakstu vienā vērtībā, ko Jobboardly saprot."""
    if isinstance(limits, (list, tuple)):
        parts = [str(x).strip() for x in limits if str(x).strip()]
    else:
        parts = [x.strip() for x in str(limits or "").split(",") if x.strip()]
    if not parts:
        return "Worldwide" if remote else ""
    if len(parts) < 5:
        return ", ".join(parts)
    count = {r: len(set(parts) & cs) for r, cs in REGIONS.items()}
    known = sum(count.values())
    used = [r for r, n in count.items() if n]
    if known == 0:
        return ", ".join(parts)
    if known >= 100 or len(used) >= 3:
        return "Worldwide"
    if set(used) == {"Europe", "EMEA"}:
        return "EMEA"
    if set(used) == {"LATAM", "North America"}:
        return "LATAM" if count["LATAM"] > count["North America"] else "North America"
    return max(count, key=count.get)


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
        j["location_limits"] = norm_limits(j.get("location_limits"), j["location_type"] == "remote")
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


RAW = OUT / "raw_jobs.json"  # tikai GitHub Action iekšienē, netiek commitots


def save_raw(raw):
    RAW.write_text(json.dumps([{**j, "date": j["date"].isoformat() if j["date"] else None} for j in raw]))


def load_raw():
    out = []
    for j in json.loads(RAW.read_text()):
        j["date"] = datetime.fromisoformat(j["date"]) if j["date"] else None
        out.append(j)
    return out


def main():
    OUT.mkdir(exist_ok=True)
    raw, errors = collect()
    save_raw(raw)
    jobs = clean(raw)
    write_xml(jobs, OUT / "jobs.xml")
    write_csv(jobs, OUT / "jobs.csv")
    by_src = {}
    for j in jobs:
        by_src[j["source"]] = by_src.get(j["source"], 0) + 1
    last24 = sum(1 for j in jobs if j["date"] >= NOW - timedelta(days=1))
    remote = sum(1 for j in jobs if j["location_type"] == "remote")
    print(f"{len(jobs)} darbi (remote: {remote}, no {len(raw)} atrastajiem), pēdējās 24h: {last24}. Avoti: {by_src}")
    if errors:
        print(f"{len(errors)} kļūdas, piem.: {errors[:3]}")


if __name__ == "__main__":
    main()
