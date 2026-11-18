#!/usr/bin/env python3
"""Iknedēļas YouTube video „QA Jobs Weekly” (16:9, ~75 s).

Ņem https://www.qajobboard.com/jobs.json un out/insights.json, izveido
video/weekly/index.html (HyperFrames), renderē video/out/weekly-<datums>.mp4
un uzraksta video/out/weekly-<datums>.txt (virsraksts + apraksts YouTube).

Palaišana: python3 video/make_weekly.py [--no-render]
"""
import collections
import datetime as dt
import html
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_video import COUNTRY, NOT_SOFT, SOFT, money, where, PLUGIN_CLI  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "weekly")
OUT = os.path.join(HERE, "out")
ROOT = os.path.dirname(HERE)

INTRO, NUMS, ROLES, TOOLS, PAY, WHERE_, JOBS_EACH, OUTRO = 5, 9, 8, 8, 7, 8, 5, 7


def esc(s):
    return html.escape(str(s))


def week_data(jobs, ins):
    jobs = sorted(jobs, key=lambda j: j["published_at"], reverse=True)
    newest = dt.date.fromisoformat(jobs[0]["published_at"][:10])
    start = newest - dt.timedelta(days=6)
    week = [j for j in jobs if j["published_at"][:10] >= start.isoformat()]
    remote = sum(1 for j in week if j.get("location") == "remote")
    roles = collections.Counter(((j.get("categories") or [{}])[0] or {}).get("name") or "Other" for j in week)
    countries = collections.Counter()
    for j in week:
        for c in (j.get("location_limits") or [])[:1]:
            if c not in ("Worldwide",):
                countries[COUNTRY.get(c, c)] += 1
    # 10 darbi: dažādi uzņēmumi, programmatūras QA, priekšroka ar algu un remote
    def score(j):
        return (3 if money(j["salary"]) else 0) + (2 if j.get("location") == "remote" else 0) \
            + (1 if len(j["title"]) <= 48 else 0)
    top, seen = [], set()
    for j in sorted(week, key=score, reverse=True):
        c = (j.get("company") or {}).get("name", "")
        if not c or c in seen or len(j["title"]) > 60 or not SOFT.search(j["title"]) or NOT_SOFT.search(j["title"]):
            continue
        seen.add(c)
        top.append(j)
        if len(top) == 10:
            break
    return {
        "start": start, "end": newest, "total": len(jobs), "new": len(week),
        "companies": len({(j.get("company") or {}).get("name") for j in week}),
        "remote_pct": round(100 * remote / len(week)) if week else 0,
        "roles": roles.most_common(5), "countries": countries.most_common(5),
        "tools": [(t[0], t[2]) for t in ins.get("tools", [])[:6]],
        "salary": ins.get("salary_overall") or {}, "top": top,
    }


def bars(items, unit, cls):
    mx = max(v for _, v in items) or 1
    rows = []
    for i, (k, v) in enumerate(items):
        w = max(6, round(100 * v / mx))
        val = f"{v:g}{unit}"
        rows.append(f'<div class="row {cls}" id="{cls}{i}"><div class="lab">{esc(k)}</div>'
                    f'<div class="track"><div class="fill" style="width:{w}%"></div></div><div class="val">{esc(val)}</div></div>')
    return "".join(rows)


def job_card(j, n):
    m = money(j["salary"])
    sal = f'<div class="sal">{esc(m)}</div>' if m else ""
    return (f'<div class="jc"><div class="num">#{n}</div><div class="jt">{esc(j["title"])}</div>'
            f'<div class="co">{esc(j["company"]["name"])}</div><div class="wh">{esc(where(j))}</div>{sal}</div>')


def build(d):
    t = 0
    scenes, tw = [], []

    def scene(sid, dur, inner, extra=""):
        nonlocal t
        scenes.append(f'<div id="{sid}" class="clip scene" data-start="{t}" data-duration="{dur}" data-track-index="0"><div class="drift" id="d{sid}">{inner}</div></div>')
        tw.append(f'tl.fromTo("#d{sid}", {{scale: 1, x: 0}}, {{scale: 1.035, x: -12, duration: {dur}, ease: "none"}}, {t});')
        tw.append(f'tl.fromTo("#{sid} .in", {{y: 50, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.5, stagger: 0.12, ease: "power3.out"}}, {t + 0.1});')
        if extra:
            tw.append(extra.replace("@T", str(t)))
        tw.append(f'tl.to("#{sid} .in", {{opacity: 0, y: -30, duration: 0.3, ease: "power2.in"}}, {t + dur - 0.35});')
        t += dur

    rng = f'{d["start"].strftime("%B %-d")} – {d["end"].strftime("%B %-d, %Y")}'
    scene("intro", INTRO, f'<div class="in kicker">QA Jobs Weekly · {esc(rng)}</div>'
          f'<div class="in hook">The QA job market<br/>this week</div>'
          f'<div class="in sub">QA · SDET · Test automation · Data from {d["total"]:,} open jobs</div>')
    scene("nums", NUMS, '<div class="in kicker">This week on QA Job Board</div><div class="grid">'
          f'<div class="in stat"><b>{d["new"]:,}</b><span>new QA jobs</span></div>'
          f'<div class="in stat"><b>{d["companies"]:,}</b><span>companies hiring</span></div>'
          f'<div class="in stat"><b>{d["remote_pct"]}%</b><span>fully remote</span></div>'
          f'<div class="in stat"><b>{d["total"]:,}</b><span>open jobs in total</span></div></div>')
    grow = 'tl.fromTo("#@ID .fill", {scaleX: 0}, {scaleX: 1, duration: 0.8, stagger: 0.1, ease: "power2.out"}, @T + 0.4);'
    scene("roles", ROLES, '<div class="in kicker">Most posted roles this week</div>'
          f'<div class="in bars">{bars(d["roles"], "", "r")}</div>', grow.replace("@ID", "roles"))
    scene("tools", TOOLS, '<div class="in kicker">Tools employers ask for (% of job descriptions)</div>'
          f'<div class="in bars">{bars(d["tools"], "%", "t")}</div>', grow.replace("@ID", "tools"))
    s = d["salary"]
    if s.get("median"):
        scene("pay", PAY, '<div class="in kicker">Advertised QA salary (median)</div>'
              f'<div class="in big">${s["median"]/1000:.0f}k</div>'
              f'<div class="in sub">Middle half: ${s["p25"]/1000:.0f}k – ${s["p75"]/1000:.0f}k · based on {s["n"]} jobs that publish pay</div>')
    if d["countries"]:
        scene("where", WHERE_, '<div class="in kicker">Where the new jobs are</div>'
              f'<div class="in bars">{bars(d["countries"], "", "c")}</div>', grow.replace("@ID", "where"))
    top = d["top"]
    for k in range(0, len(top), 2):
        pair = top[k:k + 2]
        cards = "".join(f'<div class="in">{job_card(j, k + i + 1)}</div>' for i, j in enumerate(pair))
        scene(f"jobs{k//2}", JOBS_EACH, f'<div class="in kicker">Top QA jobs this week · {k+1}–{k+len(pair)} of {len(top)}</div><div class="pair">{cards}</div>')
    scene("outro", OUTRO, f'<div class="in kicker">{d["total"]:,} QA jobs, updated daily</div>'
          '<div class="in url">qajobboard.com</div>'
          '<div class="in sub">Free job alerts for testers · Hiring QA engineers? Post a job</div>')
    total = t
    return total, f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      :root {{ --ground: #0b1324; --card: #131f38; --ink: #ffffff; --muted: #9fb0cc; --accent: #22c55e; --font-display: Inter; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: var(--ground); }}
      #root {{ width: 100%; height: 100%; position: relative; font-family: var(--font-display); color: var(--ink); }}
      .brand {{ position: absolute; left: 140px; top: 90px; font-size: 38px; font-weight: 700; }}
      .brand b {{ color: var(--accent); }}
      .scene {{ position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; padding: 120px 160px 90px; }}
      .drift {{ width: 100%; transform-origin: 30% 50%; }}
      .kicker {{ font-size: 40px; color: var(--accent); font-weight: 700; margin-bottom: 36px; }}
      .hook {{ font-size: 128px; line-height: 1.02; font-weight: 900; letter-spacing: -0.035em; }}
      .sub {{ font-size: 38px; color: var(--muted); margin-top: 36px; }}
      .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 36px 60px; }}
      .stat {{ background: var(--card); border-radius: 28px; padding: 40px 48px; border-left: 10px solid var(--accent); }}
      .stat b {{ display: block; font-size: 96px; font-weight: 900; letter-spacing: -0.03em; }}
      .stat span {{ font-size: 36px; color: var(--muted); }}
      .bars {{ display: flex; flex-direction: column; gap: 26px; }}
      .row {{ display: grid; grid-template-columns: 560px 1fr 160px; align-items: center; gap: 32px; }}
      .lab {{ font-size: 40px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
      .track {{ height: 44px; background: var(--card); border-radius: 12px; overflow: hidden; }}
      .fill {{ height: 100%; background: var(--accent); border-radius: 12px; transform-origin: left center; }}
      .val {{ font-size: 40px; font-weight: 800; text-align: right; }}
      .big {{ font-size: 220px; font-weight: 900; letter-spacing: -0.04em; color: var(--accent); }}
      .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 48px; }}
      .jc {{ background: var(--card); border-radius: 32px; padding: 52px; border-left: 12px solid var(--accent); min-height: 520px; }}
      .num {{ font-size: 32px; color: var(--muted); font-weight: 700; margin-bottom: 18px; }}
      .jt {{ font-size: 54px; line-height: 1.1; font-weight: 900; letter-spacing: -0.02em; }}
      .co {{ font-size: 40px; margin-top: 26px; font-weight: 700; }}
      .wh {{ font-size: 32px; color: var(--muted); margin-top: 12px; }}
      .sal {{ display: inline-block; margin-top: 28px; font-size: 36px; font-weight: 700; color: #04140a; background: var(--accent); padding: 10px 22px; border-radius: 14px; }}
      .url {{ font-size: 140px; font-weight: 900; color: var(--accent); letter-spacing: -0.03em; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1920" data-height="1080">
      <div id="brand" class="clip brand" data-start="0" data-duration="{total}" data-track-index="3">QA Job <b>Board</b></div>
      {"".join(scenes)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join(tw)}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''


def caption(d, chapters):
    rng = f'{d["start"].strftime("%B %-d")} – {d["end"].strftime("%B %-d, %Y")}'
    lines = [f"QA Jobs Weekly ({rng}): {d['new']:,} new QA, SDET and test automation jobs", "",
             f"This week on QA Job Board: {d['new']:,} new QA jobs from {d['companies']:,} companies, "
             f"{d['remote_pct']}% fully remote, {d['total']:,} open QA jobs in total.", "", "Chapters:"]
    lines += chapters
    lines += ["", "Top QA jobs this week:"]
    for j in d["top"]:
        m = money(j["salary"])
        lines.append(f"- {j['title']} – {j['company']['name']} · {where(j)}" + (f" · {m}" if m else ""))
        lines.append(f"  {j['links']['self']}")
    lines += ["", "All QA, SDET and test automation jobs: https://www.qajobboard.com/jobs",
              "Free QA job alerts: https://www.qajobboard.com",
              "Hiring QA engineers? Post a job: https://www.qajobboard.com/pricing", "",
              "#QAJobs #SoftwareTesting #SDET #TestAutomation"]
    return "\n".join(lines)


def chapters(d):
    t, out = 0, []
    names = [("Intro", INTRO), ("This week in numbers", NUMS), ("Most posted roles", ROLES), ("Tools employers ask for", TOOLS)]
    if d["salary"].get("median"):
        names.append(("QA salaries", PAY))
    if d["countries"]:
        names.append(("Where the jobs are", WHERE_))
    names.append(("Top 10 QA jobs this week", JOBS_EACH * ((len(d["top"]) + 1) // 2)))
    names.append(("Find your next QA job", OUTRO))
    for n, dur in names:
        out.append(f"{t//60}:{t%60:02d} {n}")
        t += dur
    return out


def main():
    req = urllib.request.Request("https://www.qajobboard.com/jobs.json", headers={"User-Agent": "qa-feed-video"})
    jobs = json.load(urllib.request.urlopen(req, timeout=180))
    ins = json.load(open(os.path.join(ROOT, "out", "insights.json")))
    d = week_data(jobs, ins)
    if len(d["top"]) < 6:
        sys.exit(f"Par maz darbu nedēļas video: {len(d['top'])}")
    day = dt.date.today().isoformat()
    os.makedirs(OUT, exist_ok=True)
    total, page = build(d)
    with open(os.path.join(PROJ, "index.html"), "w") as f:
        f.write(page)
    with open(os.path.join(OUT, f"weekly-{day}.txt"), "w") as f:
        f.write(caption(d, chapters(d)))
    print(f"Ilgums {total} s; teksts video/out/weekly-{day}.txt")
    if "--no-render" in sys.argv:
        return
    mp4 = os.path.join(OUT, f"weekly-{day}.mp4")
    subprocess.run(["node", PLUGIN_CLI, "check", "--json"], cwd=PROJ, check=False)
    subprocess.run(["node", PLUGIN_CLI, "render", "--output", mp4], cwd=PROJ, check=True)
    print("Video:", mp4)


if __name__ == "__main__":
    main()
