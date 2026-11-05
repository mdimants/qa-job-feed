"""QA darba tirgus statistika bloga rakstiem un lapai "Remote QA companies".

Izmanto tos pašus avotus kā feed.py, bet bez ierobežojuma "max 6 darbi uz uzņēmumu",
lai skaitļi atspoguļotu reālo tirgu. Raksta out/insights.json.
"""
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import timedelta

import feed

OUT = feed.OUT

TOOLS = {
    "Playwright": r"\bplaywright\b", "Selenium": r"\bselenium\b", "Cypress": r"\bcypress\b",
    "Appium": r"\bappium\b", "Postman": r"\bpostman\b", "REST Assured": r"\brest[- ]?assured\b",
    "JMeter": r"\bjmeter\b", "k6": r"\bk6\b", "Gatling": r"\bgatling\b", "Cucumber/BDD": r"\bcucumber\b|\bbdd\b",
    "TestRail": r"\btestrail\b", "Jira": r"\bjira\b", "Jenkins": r"\bjenkins\b",
    "GitHub Actions": r"github actions", "Docker": r"\bdocker\b", "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "AWS": r"\baws\b", "SQL": r"\bsql\b", "WebdriverIO": r"webdriver\.?io\b|\bwdio\b",
    "Detox": r"\bdetox\b", "XCUITest": r"xcuitest", "Espresso": r"\bespresso\b",
    "AI / LLM testing": r"\bllms?\b|\bgenai\b|generative ai|\bai[- ]powered\b",
}
LANGS = {
    "Python": r"\bpython\b", "Java": r"\bjava\b(?!script)", "JavaScript": r"\bjavascript\b|\bjs\b",
    "TypeScript": r"\btypescript\b", "C#": r"c#|\.net\b", "Go": r"\bgolang\b", "Kotlin": r"\bkotlin\b",
    "Swift": r"\bswift\b", "Ruby": r"\bruby\b",
}
GIG_RE = re.compile(r"testers? wanted|freelance|crowd|evaluator|rater|annotat|\bLQA\b|CX Agent|upto \$", re.I)
GIG_CO = re.compile(r"^mercor$|lifelancer", re.I)
# aptuveni kursi uz USD (algu salīdzināšanai, ne precīzai grāmatvedībai)
USD = {"USD": 1, "EUR": 1.08, "GBP": 1.27, "CAD": 0.73, "AUD": 0.66, "INR": 0.012, "PLN": 0.25,
       "CHF": 1.13, "SEK": 0.095, "NOK": 0.093, "DKK": 0.145, "BRL": 0.18, "MXN": 0.055,
       "SGD": 0.74, "NZD": 0.6, "JPY": 0.0067, "ILS": 0.27, "CZK": 0.043, "RON": 0.22}
COUNTRIES = ["United States", "USA", "India", "United Kingdom", "UK", "Germany", "Canada", "Poland",
             "Spain", "Portugal", "Netherlands", "Romania", "Ukraine", "Brazil", "Mexico", "Argentina",
             "Colombia", "Philippines", "Australia", "France", "Ireland", "Israel", "Pakistan", "Serbia",
             "Bulgaria", "Greece", "Italy", "Sweden", "Lithuania", "Latvia", "Estonia", "Czech",
             "Hungary", "Turkey", "Egypt", "South Africa", "Nigeria", "Kenya", "Singapore", "Japan",
             "Vietnam", "Sri Lanka", "Bangladesh", "Switzerland", "Austria", "Belgium", "Denmark", "Finland"]
ALIAS = {"USA": "United States", "UK": "United Kingdom", "Czech": "Czechia"}


def company_name(n):
    n = n.strip()
    for _ in range(2):
        n = re.sub(r"[,\s]+(UK\s+)?(Limited|Ltd\.?|Inc\.?|LLC|GmbH|Pvt\.?|Pty\.?|Corporation|Corp\.?|Interactive)$", "", n, flags=re.I)
    return n.strip(" ,")


def annual_usd(j):
    try:
        lo = float(j["salary_min"] or 0)
        hi = float(j["salary_max"] or 0) or lo
    except ValueError:
        return None
    if not lo and not hi:
        return None
    mid = (lo + hi) / 2 if lo else hi
    rate = USD.get((j["currency"] or "USD").upper())
    if not rate:
        return None
    per = (j["salary_period"] or "year").lower()
    mult = {"year": 1, "month": 12, "week": 52, "day": 260, "hour": 2080}.get(per, 1)
    v = mid * mult * rate
    return v if 8_000 <= v <= 400_000 else None


def seniority(t):
    t = t.lower()
    if re.search(r"\b(junior|jr\.?|entry|graduate|intern|trainee|associate)\b", t):
        return "Junior"
    if re.search(r"\b(lead|principal|staff|head|manager|director|architect)\b", t):
        return "Lead / Manager"
    if re.search(r"\b(senior|sr\.?)\b", t):
        return "Senior"
    return "Mid-level"


def countries_of(j):
    text = f'{j["office_location"]} {j["location_limits"]}'
    found = set()
    for c in COUNTRIES:
        if re.search(r"\b" + re.escape(c) + r"\b", text, re.I):
            found.add(ALIAS.get(c, c))
    return found


def pct(n, d):
    return round(100 * n / d, 1) if d else 0


def main():
    feed.MAX_PER_COMPANY = 10**9
    if feed.RAW.exists() and feed.RAW.stat().st_mtime > __import__("time").time() - 6 * 3600:
        raw, errors = feed.load_raw(), []
    else:
        raw, errors = feed.collect()
    jobs = feed.clean(raw)
    n = len(jobs)
    remote = [j for j in jobs if j["location_type"] == "remote"]
    remote_ok = [j for j in remote if not GIG_RE.search(j["title"]) and not GIG_CO.search(j["company"])]
    last7 = [j for j in jobs if j["date"] >= feed.NOW - timedelta(days=7)]

    # uzņēmumi ar remote QA darbiem
    comp = defaultdict(lambda: {"jobs": 0, "titles": Counter(), "url": "", "logo": "", "where": Counter(),
                                "salaries": []})
    for j in remote_ok:
        c = comp[company_name(j["company"])]
        c["jobs"] += 1
        c["titles"][j["title"]] += 1
        c["url"] = c["url"] or j["company_url"]
        c["logo"] = c["logo"] or j["logo"]
        parts = [x.strip() for x in (j["location_limits"] or "").split(",") if x.strip()]
        w = "Worldwide" if not parts else (", ".join(parts) if len(parts) <= 3 else f"{len(parts)} countries")
        c["where"][w[:60]] += 1
        s = annual_usd(j)
        if s:
            c["salaries"].append(s)
    top_remote = []
    for name, c in sorted(comp.items(), key=lambda kv: -kv[1]["jobs"]):
        top_remote.append({
            "company": name, "remote_jobs": c["jobs"], "url": c["url"], "logo": c["logo"],
            "example_titles": [t for t, _ in c["titles"].most_common(3)],
            "where": [w for w, _ in c["where"].most_common(2)],
            "median_salary_usd": round(statistics.median(c["salaries"]), -3) if c["salaries"] else None,
        })

    # algas
    by_cat = defaultdict(list)
    by_sen = defaultdict(list)
    sal_all = []
    for j in jobs:
        s = annual_usd(j)
        if not s:
            continue
        sal_all.append(s)
        by_cat[j["category"]].append(s)
        by_sen[seniority(j["title"])].append(s)

    def summ(v):
        v = sorted(v)
        return {"n": len(v), "p25": round(v[len(v) // 4], -3), "median": round(statistics.median(v), -3),
                "p75": round(v[3 * len(v) // 4], -3)} if len(v) >= 5 else None

    # rīki un valodas
    tools, langs = Counter(), Counter()
    with_desc = [j for j in jobs if len(j["description"]) > 300]
    for j in with_desc:
        d = re.sub(r"<[^>]+>", " ", j["description"]).lower() + " " + j["title"].lower()
        for k, rx in TOOLS.items():
            if re.search(rx, d):
                tools[k] += 1
        for k, rx in LANGS.items():
            if re.search(rx, d):
                langs[k] += 1

    ctry = Counter()
    for j in jobs:
        for c in countries_of(j):
            ctry[c] += 1

    data = {
        "generated": feed.NOW.strftime("%Y-%m-%d"),
        "total_jobs": n,
        "raw_found": len(raw),
        "remote_jobs": len(remote),
        "remote_share": pct(len(remote), n),
        "new_last_7_days": len(last7),
        "companies": len({j["company"] for j in jobs}),
        "remote_companies": len(comp),
        "categories": Counter(j["category"] for j in jobs).most_common(),
        "seniority": Counter(seniority(j["title"]) for j in jobs).most_common(),
        "job_types": Counter(j["job_type"] for j in jobs).most_common(),
        "salary_disclosed_share": pct(len(sal_all), n),
        "salary_overall": summ(sal_all),
        "salary_by_category": {k: summ(v) for k, v in by_cat.items() if summ(v)},
        "salary_by_seniority": {k: summ(v) for k, v in by_sen.items() if summ(v)},
        "jobs_with_description": len(with_desc),
        "tools": [(k, v, pct(v, len(with_desc))) for k, v in tools.most_common()],
        "languages": [(k, v, pct(v, len(with_desc))) for k, v in langs.most_common()],
        "countries": ctry.most_common(30),
        "top_remote_companies": top_remote[:150],
        "sources_errors": len(errors),
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "insights.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"{n} darbi, {len(remote)} remote, {len(comp)} remote uzņēmumi, algas {len(sal_all)}, "
          f"apraksti {len(with_desc)} → out/insights.json")


if __name__ == "__main__":
    main()
