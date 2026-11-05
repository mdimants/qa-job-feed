"""Uzbūvē HTML lapai /best-software-companies-to-work-for no out/insights.json.

Rezultāts: out/companies_page.html (ielīmējams Jobboardly custom page laukā "content")
un out/companies_page.json (title, meta_title, meta_description, content).
"""
import html
import json
import pathlib
import re
from datetime import datetime

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"
SITE = "https://www.qajobboard.com"


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def money(v):
    return f"${v/1000:.0f}k" if v else ""


def main():
    d = json.loads((OUT / "insights.json").read_text())
    month = datetime.strptime(d["generated"], "%Y-%m-%d").strftime("%B %Y")
    day = datetime.strptime(d["generated"], "%Y-%m-%d").strftime("%B %-d, %Y")
    year = d["generated"][:4]
    comps = [c for c in d["top_remote_companies"] if c["remote_jobs"] >= 1][:60]
    e = html.escape

    rows = []
    for i, c in enumerate(comps, 1):
        name = e(c["company"])
        link = f'<a href="{e(c["url"])}" rel="nofollow noopener" target="_blank">{name}</a>' if c["url"] else name
        titles = ", ".join(e(t) for t in c["example_titles"][:2])
        where = e(", ".join(w for w in c["where"] if w)) or "Worldwide"
        sal = money(c["median_salary_usd"])
        rows.append(f"<tr><td>{i}</td><td><strong>{link}</strong></td><td>{c['remote_jobs']}</td>"
                    f"<td>{titles}</td><td>{where}</td><td>{sal or '–'}</td></tr>")

    tools = ", ".join(f"{t} ({p}%)" for t, _, p in d["tools"][:5])
    top3 = ", ".join(e(c["company"]) for c in comps[:3])
    so = d.get("salary_overall") or {}
    content = f"""
<p><em>Updated {day}. Data from {d['total_jobs']:,} open QA and software testing jobs we track every day.</em></p>
<p>Looking for a QA, SDET or software testing job you can do from home? Below are the software companies with the most
<strong>open remote QA roles right now</strong>, ranked by live job count. Unlike generic "best places to work" lists,
this page is rebuilt from real job posts, so every company on it is hiring testers today.</p>

<h2>Remote QA hiring at a glance ({month})</h2>
<ul>
<li><strong>{d['remote_jobs']:,}</strong> of {d['total_jobs']:,} open QA jobs are remote ({d['remote_share']}%).</li>
<li><strong>{d['remote_companies']:,}</strong> companies are hiring remote QA engineers and testers.</li>
<li><strong>{d['new_last_7_days']:,}</strong> new QA jobs were posted in the last 7 days.</li>
{f"<li>Median advertised QA salary: <strong>{money(so.get('median'))}</strong> per year (USD equivalent, {d['salary_disclosed_share']}% of posts show pay).</li>" if so else ""}
<li>Most requested tools: {e(tools)}.</li>
</ul>

<h2>Top {len(comps)} companies hiring remote QA engineers</h2>
<p>Companies with the most open remote QA roles right now are {top3}. Click a company to see its careers page,
or browse all <a href="{SITE}/s/remote-jobs">remote QA jobs</a> on QA Job Board.</p>
<table>
<thead><tr><th>#</th><th>Company</th><th>Open remote QA jobs</th><th>Example roles</th><th>Where you can work from</th><th>Median pay*</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
<p><small>* Median of advertised salaries converted to USD per year, shown only when the company publishes pay.
Rankings change daily as jobs open and close.</small></p>

<h2>How to get hired at these companies</h2>
<ol>
<li><strong>Match the tool stack.</strong> Across all QA job posts, the most requested tools are {e(tools)}. Put the ones you know in your resume headline.</li>
<li><strong>Check the location limits.</strong> "Remote" often means remote within one country or time zone. The table shows where each company hires.</li>
<li><strong>Apply early.</strong> Remote QA roles get many applicants in the first week. <a href="{SITE}/jobs">Set up a QA job alert</a> to get new jobs by email.</li>
</ol>

<h2>Browse QA jobs by role</h2>
<ul>
<li><a href="{SITE}/s/qa-automation-engineer-jobs">QA Automation Engineer jobs</a></li>
<li><a href="{SITE}/s/software-development-engineer-in-test-sdet-jobs">SDET jobs</a></li>
<li><a href="{SITE}/s/senior-qa-engineer-jobs">Senior QA Engineer jobs</a></li>
<li><a href="{SITE}/s/junior-qa-engineer-jobs">Junior QA jobs</a></li>
<li><a href="{SITE}/s/qa-manual-tester-jobs">Manual QA Tester jobs</a></li>
</ul>

<h2>Hiring QA engineers?</h2>
<p>Reach QA professionals directly: <a href="{SITE}/pricing">post a QA job</a> on QA Job Board from $99 for 30 days.
Your job goes to our QA job alert subscribers and our LinkedIn community.</p>
"""
    page = {
        "title": f"Best Software Companies Hiring Remote QA Engineers in {year}",
        "meta_title": f"{len(comps)} Companies Hiring Remote QA Engineers ({month})",
        "meta_description": (f"{d['remote_companies']:,} companies are hiring remote QA engineers and testers right now. "
                             f"See who has the most open remote QA, SDET and automation jobs. Updated {day}."),
        "content": re.sub(r"\n\s*\n", "\n", content).strip(),
    }
    (OUT / "companies_page.json").write_text(json.dumps(page, ensure_ascii=False, indent=1))
    (OUT / "companies_page.html").write_text(page["content"])
    print(page["meta_title"], len(page["content"]))


if __name__ == "__main__":
    main()
