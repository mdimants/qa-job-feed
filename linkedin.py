"""QA Job Board LinkedIn ierakstu ģenerators – 3 ieraksti dienā.

Avots: https://www.qajobboard.com/jobs.json (lapas pašas darbi ar qajobboard saitēm).
Rezultāts:
  out/linkedin/YYYY-MM-DD.md  – cilvēkam lasāms (kopēt/ielīmēt)
  out/linkedin.json           – šodienas 3 ieraksti ar laikiem (automatizācijai: Make/Buffer/Zapier)

Palaišana:  python3 linkedin.py
"""
import json
import pathlib
import random
import re
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"
SITE = "https://www.qajobboard.com"
UA = {"User-Agent": "qajobboard-linkedin/1.0 (+https://www.qajobboard.com)"}
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()
RNG = random.Random(TODAY.toordinal())          # katru dienu cits, bet atkārtojams
TAGS = "#QAJobs #SoftwareTesting #QualityAssurance #SDET #TestAutomation"
SCHEDULE_UTC = ["06:00", "10:30", "15:30"]       # 08:00 / 12:30 / 17:30 Rīgā (ziemā)

TIPS = [
    ("Your QA CV in 30 seconds", "Recruiters skim. Put your test stack in the top 3 lines: language, framework, CI tool. Example: \"Python, Playwright, GitHub Actions\". Then one line with a number: \"Cut regression time from 2 days to 3 hours\"."),
    ("Manual tester to automation", "You don't need to learn everything. Pick one stack and ship one public project: Playwright + TypeScript, 10 real tests against a demo site, running in GitHub Actions. Put the link at the top of your CV."),
    ("The bug report that gets fixed", "Title = what is broken + where. Steps that anyone can repeat. Expected vs actual. One screenshot or video. Environment. Developers fix clear bugs first."),
    ("SDET interview prep", "Expect 3 things: a coding task (strings, arrays, maps), a test design question (\"how would you test a login page?\") and a framework question (page objects, waits, flaky tests). Practise saying your reasoning out loud."),
    ("Flaky tests", "A flaky test is a bug in the test, not bad luck. Usual causes: hard-coded waits, shared test data, test order, real network calls. Fix or quarantine it the same day; otherwise people stop trusting the suite."),
    ("API testing first", "UI tests are slow and fragile. Many teams now want QA engineers who test the API layer first: Postman or REST Assured or Playwright request. It is one of the most asked skills in the jobs on our board."),
    ("Junior QA: where to start", "Learn test design (equivalence classes, boundary values), basic SQL, Git, and one automation tool. Then test real apps and write bug reports. A portfolio of 5 good bug reports beats a certificate."),
    ("Salary talk", "Check the salary range before the first call. Many jobs on QA Job Board list salary. Answer \"what do you expect?\" with a range based on the market, not your last salary."),
    ("Remote QA jobs", "\"Remote\" often means \"remote within a country or time zone\". Read the location line before applying. On QA Job Board every remote job shows the allowed regions."),
    ("ISTQB: worth it?", "For some companies (banks, consulting, public sector) ISTQB Foundation is a filter. For startups, a GitHub project matters more. Check 10 jobs you want and count how many ask for it."),
    ("Test strategy in one page", "Scope, risks, test levels (unit/API/UI), environments, data, entry/exit criteria, who does what. If it doesn't fit on one page, nobody will read it."),
    ("Performance testing basics", "Start with one question: how many users, doing what, with what response time? Then pick a tool (k6, JMeter, Gatling). Measure before you optimise."),
    ("Accessibility testing", "Quick wins: keyboard-only navigation, visible focus, alt text, colour contrast, form labels. Tools: axe DevTools, Lighthouse. Few testers do this well, so it stands out on a CV."),
    ("Mobile QA", "Test on real devices for gestures, notifications, permissions, offline mode and app updates. Use emulators for wide coverage, real phones for the last check."),
    ("AI in QA", "Teams use AI to write test ideas, generate data and draft test code. The skill companies pay for is judging the output: is the test meaningful, does it really check the requirement?"),
]

EMPLOYER_POSTS = [
    "Hiring a QA engineer, SDET or tester? Post your job on QA Job Board: it goes to QA professionals only, is sent in our job email and indexed in Google for Jobs. From $99 for 30 days.",
    "Most job boards show your QA role between sales and marketing jobs. QA Job Board shows it only to people who test software for a living. Post a QA job from $99.",
    "Need testers fast? A Featured post on QA Job Board stays pinned to the top for 30 days, is sent to our QA job email list and shared on this page. $199.",
]


def get_jobs():
    req = urllib.request.Request(f"{SITE}/jobs.json", headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = json.loads(r.read())
    jobs = []
    for j in raw:
        try:
            pub = datetime.fromisoformat(j["published_at"]).astimezone(timezone.utc)
        except Exception:
            continue
        comp = j.get("company") or {}
        sal = j.get("salary") or {}
        limits = [x for x in (j.get("location_limits") or []) if x and x != "Worldwide"]
        jobs.append(dict(
            title=re.sub(r"\s+", " ", j["title"]).strip(),
            company=(comp.get("name") or "").strip(),
            city=(comp.get("location") or "").strip(),
            remote=j.get("location") == "remote",
            where=", ".join(limits) if limits else "Worldwide",
            url=(j.get("links") or {}).get("self", f"{SITE}/jobs"),
            pub=pub,
            cat=((j.get("categories") or [{}])[0] or {}).get("name", ""),
            smin=((sal.get("minimum") or {}).get("cents") or 0) / 100 or None,
            smax=((sal.get("maximum") or {}).get("cents") or 0) / 100 or None,
            sched=sal.get("schedule"),
            cur=(sal.get("minimum") or {}).get("currency_iso") or "",
        ))
    return jobs


CODES = {"US": "USA", "GB": "UK", "UK": "UK", "IN": "India", "DE": "Germany", "PL": "Poland", "ES": "Spain",
         "PT": "Portugal", "FR": "France", "NL": "Netherlands", "CA": "Canada", "BR": "Brazil", "MX": "Mexico",
         "AR": "Argentina", "PH": "Philippines", "JO": "Jordan", "GR": "Greece", "RO": "Romania", "UA": "Ukraine",
         "LV": "Latvia", "LT": "Lithuania", "EE": "Estonia", "IT": "Italy", "IE": "Ireland", "AU": "Australia",
         "IL": "Israel", "PK": "Pakistan", "EG": "Egypt", "ZA": "South Africa", "CO": "Colombia", "CL": "Chile",
         "SE": "Sweden", "DK": "Denmark", "NO": "Norway", "FI": "Finland", "CH": "Switzerland", "AT": "Austria",
         "BE": "Belgium", "CZ": "Czechia", "HU": "Hungary", "BG": "Bulgaria", "RS": "Serbia", "HR": "Croatia",
         "TR": "Turkey", "AE": "UAE", "SG": "Singapore", "JP": "Japan", "VN": "Vietnam", "ID": "Indonesia",
         "MY": "Malaysia", "NZ": "New Zealand", "LK": "Sri Lanka", "NG": "Nigeria", "KE": "Kenya"}
EUROPE = {"Germany", "France", "Spain", "Poland", "Portugal", "Netherlands", "Italy", "Austria", "Belgium",
          "Sweden", "Romania", "Latvia", "Lithuania", "Estonia", "United Kingdom", "Ireland", "Greece"}


def where_short(where):
    parts = [CODES.get(p.strip(), p.strip()) for p in where.split(",") if p.strip()]
    if len(parts) <= 3:
        return ", ".join(parts)
    if len(EUROPE & set(parts)) >= 5 and not {"USA", "United States", "Canada", "India", "Brazil", "Mexico",
                                                "Philippines", "Australia", "China", "Japan", "Nigeria"} & set(parts):
        return "Europe"
    latam = {"Mexico", "Brazil", "Argentina", "Colombia", "Chile", "Peru", "Uruguay", "Costa Rica", "Ecuador"}
    if len(latam & set(parts)) >= 4 and len(parts) <= 50:
        return "Americas"
    if len(parts) > 40:
        return "Worldwide"
    return f"{len(parts)} countries"


def place(j):
    return f"Remote ({where_short(j['where'])})" if j["remote"] else (j["city"] or "On-site")


def salary(j):
    if not j["smin"]:
        return ""
    lo = f"{int(float(j['smin'])):,}"
    hi = f"–{int(float(j['smax'])):,}" if j["smax"] and j["smax"] != j["smin"] else ""
    per = {"yearly": "/year", "monthly": "/month", "hourly": "/hour"}.get(j["sched"] or "", "")
    return f"{lo}{hi} {j['cur']}{per}".strip()


GIG_RE = re.compile(r"testers? wanted|freelance tester|crowd|evaluator|rater|annotat", re.I)


HISTORY = OUT / "linkedin_used.json"   # darbi, kas jau bijuši ierakstos pēdējās 14 dienās
try:
    USED = {u: d for u, d in json.loads(HISTORY.read_text()).items()
            if d >= (TODAY - timedelta(days=14)).isoformat() and d != TODAY.isoformat()}
except (FileNotFoundError, ValueError):
    USED = {}
TODAY_USED = set()


def pick(jobs, n, cond=lambda j: True, days=3):
    """Jaunākie darbi, ne vairāk kā 1 no uzņēmuma, bez tiem, kas jau rādīti pēdējās 14 dienās."""
    jobs = [j for j in jobs if not GIG_RE.search(j["title"])]
    fresh = [j for j in jobs if j["url"] not in USED and j["url"] not in TODAY_USED]
    if len([j for j in fresh if cond(j)]) >= n:
        jobs = fresh
    pool = [j for j in jobs if cond(j) and j["pub"] >= NOW - timedelta(days=days) and j["company"]]
    if len(pool) < n:
        pool = [j for j in jobs if cond(j) and j["company"]]
    pool.sort(key=lambda j: j["pub"], reverse=True)
    out, seen = [], set()
    for j in pool:
        if j["company"].lower() in seen:
            continue
        seen.add(j["company"].lower())
        out.append(j)
        if len(out) == n:
            break
    TODAY_USED.update(j["url"] for j in out)
    return out


def line(j):
    s = salary(j)
    return f"▪️ {j['title']} – {j['company']} · {place(j)}" + (f" · {s}" if s else "")


def post_remote(jobs):
    sel = pick(jobs, 6, lambda j: j["remote"])
    body = "\n".join(line(j) for j in sel)
    return ("🌍 New remote QA jobs today\n\n" + body +
            f"\n\nAll remote QA, SDET and testing jobs:\n{SITE}/s/remote-jobs\n\n{TAGS} #RemoteJobs")


def post_job_of_day(jobs):
    cands = pick(jobs, 15, days=2)
    with_sal = [j for j in cands if salary(j)]
    j = (with_sal or cands)[RNG.randrange(len(with_sal or cands))]
    TODAY_USED.add(j["url"])
    s = salary(j)
    return (f"🔥 QA job of the day\n\n{j['title']}\n🏢 {j['company']}\n📍 {place(j)}" +
            (f"\n💰 {s}" if s else "") +
            f"\n\nApply here 👇\n{j['url']}\n\nKnow someone who would fit? Tag them in the comments.\n\n{TAGS}")


def post_theme(jobs):
    wd = TODAY.weekday()  # 0 = pirmdiena
    if wd == 0:
        sel = pick(jobs, 5, lambda j: re.search(r"sdet|in test", j["title"], re.I))
        return ("🧪 SDET jobs this week\n\n" + "\n".join(line(j) for j in sel) +
                f"\n\nMore SDET jobs:\n{SITE}/s/software-development-engineer-in-test-sdet-jobs\n\n{TAGS}")
    if wd == 1:
        sel = pick(jobs, 5, lambda j: re.search(r"junior|entry|graduate|intern|trainee|student", j["title"], re.I), days=14)
        return ("🎓 Junior and entry-level QA jobs\n\nYour first QA job is the hardest to get. These companies are hiring juniors right now:\n\n" +
                "\n".join(line(j) for j in sel) + f"\n\nAll junior QA jobs:\n{SITE}/s/junior-qa-engineer-jobs\n\n{TAGS} #JuniorQA")
    if wd == 2:
        sel = pick(jobs, 5, lambda j: bool(salary(j)), days=7)
        return ("💰 QA jobs with the salary in the ad\n\nNo guessing, the pay is listed:\n\n" + "\n".join(line(j) for j in sel) +
                f"\n\nFind more on {SITE}/jobs\n\n{TAGS} #SalaryTransparency")
    if wd == 3:
        countries = Counter(j["where"] for j in jobs if j["remote"] and j["where"] != "Worldwide")
        top = [c for c, _ in countries.most_common(6)]
        country = top[RNG.randrange(len(top))] if top else "Europe"
        sel = pick(jobs, 5, lambda j: country in j["where"] or country in j["city"], days=14)
        return (f"📍 Remote QA jobs you can do from {where_short(country)}\n\n" + "\n".join(line(j) for j in sel) +
                f"\n\nSearch by country on {SITE}/jobs\n\n{TAGS}")
    if wd == 4:
        return f"📣 For hiring managers\n\n{EMPLOYER_POSTS[RNG.randrange(len(EMPLOYER_POSTS))]}\n\n👉 {SITE}/pricing\n\n#Hiring #QAHiring #SoftwareTesting"
    if wd == 5:
        week = [j for j in jobs if j["pub"] >= NOW - timedelta(days=7)]
        rem = sum(1 for j in week if j["remote"])
        top = Counter(j["company"] for j in week if j["company"]).most_common(5)
        cats = Counter(j["cat"] for j in week if j["cat"]).most_common(3)
        return (f"📊 QA job market this week\n\n{len(week)} new QA and testing jobs on QA Job Board\n{rem} of them remote\n\n"
                "Most hiring:\n" + "\n".join(f"▪️ {c} ({n})" for c, n in top) +
                "\n\nMost wanted roles:\n" + "\n".join(f"▪️ {c} ({n})" for c, n in cats) +
                f"\n\nSee all: {SITE}/jobs\n\n{TAGS}")
    title, text = TIPS[TODAY.toordinal() % len(TIPS)]
    return (f"💡 QA career tip: {title}\n\n{text}\n\nWhat would you add? 👇\n\n"
            f"New QA jobs every day: {SITE}/jobs\n\n{TAGS} #CareerTips")


def main():
    jobs = get_jobs()
    posts = [
        {"time_utc": SCHEDULE_UTC[0], "type": "remote_roundup", "text": post_remote(jobs)},
        {"time_utc": SCHEDULE_UTC[1], "type": "job_of_the_day", "text": post_job_of_day(jobs)},
        {"time_utc": SCHEDULE_UTC[2], "type": "theme", "text": post_theme(jobs)},
    ]
    USED.update({u: TODAY.isoformat() for u in TODAY_USED})
    HISTORY.write_text(json.dumps(USED, indent=0))
    (OUT / "linkedin").mkdir(parents=True, exist_ok=True)
    (OUT / "linkedin.json").write_text(json.dumps({"date": TODAY.isoformat(), "posts": posts},
                                                  ensure_ascii=False, indent=2), encoding="utf-8")
    md = f"# LinkedIn ieraksti {TODAY.isoformat()}\n\n" + "\n\n".join(
        f"## {p['time_utc']} UTC – {p['type']}\n\n```\n{p['text']}\n```" for p in posts)
    (OUT / "linkedin" / f"{TODAY.isoformat()}.md").write_text(md + "\n", encoding="utf-8")
    print(f"{len(jobs)} darbi; uzģenerēti 3 ieraksti → out/linkedin/{TODAY.isoformat()}.md")


if __name__ == "__main__":
    main()
