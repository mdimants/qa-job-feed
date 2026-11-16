#!/usr/bin/env python3
"""Ikdienas LinkedIn video: 5 jauni QA darbi no qajobboard.com/jobs.json.

Izveido video/daily/index.html (HyperFrames), renderē to un saglabā
video/out/<datums>.mp4 un video/out/<datums>.txt (ieraksta teksts).

Palaišana: python3 video/make_video.py [--no-render]
"""
import datetime as dt
import html
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "daily")
OUT = os.path.join(HERE, "out")
PLUGIN_CLI = os.path.expanduser(
    "~/.claude/plugins/cache/hyperframes/hyperframes/0.8.209/skills/hyperframes/scripts/plugin-cli.mjs")

CUR = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "CA$", "AUD": "A$"}
COUNTRY = {"US": "USA", "GB": "UK", "IN": "India", "PL": "Poland", "DE": "Germany", "CA": "Canada",
           "NL": "Netherlands", "ES": "Spain", "BR": "Brazil", "MX": "Mexico", "PH": "Philippines",
           "PT": "Portugal", "FR": "France", "RO": "Romania", "UA": "Ukraine", "CO": "Colombia",
           "AR": "Argentina", "IE": "Ireland", "AU": "Australia", "SG": "Singapore", "JP": "Japan",
           "HU": "Hungary", "CZ": "Czechia", "IT": "Italy", "SE": "Sweden", "CH": "Switzerland", "AT": "Austria",
           "BE": "Belgium", "DK": "Denmark", "FI": "Finland", "NO": "Norway", "GR": "Greece", "LT": "Lithuania",
           "LV": "Latvia", "EE": "Estonia", "BG": "Bulgaria", "RS": "Serbia", "HR": "Croatia", "TR": "Turkey",
           "IL": "Israel", "AE": "UAE", "ZA": "South Africa", "EG": "Egypt", "NG": "Nigeria", "KE": "Kenya",
           "CL": "Chile", "PE": "Peru", "CR": "Costa Rica", "VN": "Vietnam", "MY": "Malaysia", "ID": "Indonesia",
           "TH": "Thailand", "PK": "Pakistan", "NZ": "New Zealand", "CN": "China", "KR": "South Korea"}

import re
SOFT = re.compile(r"\b(QA|SDET|Quality Assurance|Test(er|ing)?|Automation)\b", re.I)
NOT_SOFT = re.compile(r"penetration|metrology|manufactur|mechanical|clinical|food|supplier|welding|"
                      r"construction|laborator|chemical|electrical|hardware|pharma|medical device|call|support excellence|advocacy|clinical|GxP|GMP", re.I)


def money(s):
    lo, hi = s.get("minimum"), s.get("maximum")
    if not lo:
        return ""
    cur = lo.get("currency_iso", "USD")
    if cur not in CUR:
        return ""
    v, sch = lo["cents"] / 100, s.get("schedule") or "yearly"
    # Neticamas summas (piem. stundas likme atzīmēta kā gada) nerādām
    if (sch == "yearly" and not 15000 <= v <= 500000) or (sch == "monthly" and not 1000 <= v <= 40000) \
            or (sch == "hourly" and not 10 <= v <= 300):
        return ""
    sym = CUR.get(cur, cur + " ")

    def k(c):
        v = c / 100
        return f"{v/1000:.0f}k" if v >= 1000 else f"{v:.0f}"
    txt = sym + k(lo["cents"]) + (("–" + k(hi["cents"])) if hi and hi["cents"] != lo["cents"] else "")
    per = {"yearly": "/yr", "monthly": "/mo", "hourly": "/h"}.get(s.get("schedule") or "", "")
    return txt + per


def where(j):
    lim = [COUNTRY.get(x, x) for x in (j.get("location_limits") or [])]
    if j.get("location") == "remote":
        return "Remote · " + (", ".join(lim[:2]) if lim else "Worldwide")
    loc = (j.get("company") or {}).get("location") or ", ".join(lim[:1])
    return (j.get("location") or "").replace("onsite", "On-site").replace("hybrid", "Hybrid").title() + (" · " + loc if loc else "")


def pick(jobs, n=5):
    jobs = sorted(jobs, key=lambda j: j["published_at"], reverse=True)
    newest = jobs[0]["published_at"][:10]
    cutoff = (dt.date.fromisoformat(newest) - dt.timedelta(days=3)).isoformat()
    recent = [j for j in jobs if j["published_at"][:10] >= cutoff]

    def score(j):
        return ((j.get("sticky") or j.get("highlighted")) and 10 or 0) + (3 if money(j["salary"]) else 0) \
            + (4 if re.search(r"SDET|Automation|QA Engineer|Software|Test Engineer|Playwright|Cypress|Selenium", j["title"], re.I) else 0) \
            + (2 if j.get("location") == "remote" else 0) + (1 if len(j["title"]) <= 48 else 0)
    out, seen = [], set()
    for j in sorted(recent, key=score, reverse=True):
        c = (j.get("company") or {}).get("name", "")
        if not c or c in seen or len(j["title"]) > 70 or not SOFT.search(j["title"]) or NOT_SOFT.search(j["title"]):
            continue
        seen.add(c)
        out.append(j)
        if len(out) == n:
            break
    return out, len(recent)


def card(i, j, start):
    t = html.escape(j["title"])
    c = html.escape(j["company"]["name"])
    w = html.escape(where(j))
    m = html.escape(money(j["salary"]))
    sal = f'<div class="sal">{m}</div>' if m else ""
    return f'''
      <div id="job{i}" class="clip job" data-start="{start}" data-duration="2" data-track-index="1">
        <div class="jin" id="jin{i}">
          <div class="num">{i}/5</div>
          <div class="jt">{t}</div>
          <div class="co">{c}</div>
          <div class="wh">{w}</div>
          {sal}
        </div>
      </div>'''


def build(jobs, total_jobs, day):
    datestr = dt.date.fromisoformat(day).strftime("%B %-d")
    cards = "".join(card(i + 1, j, 2.5 + i * 2) for i, j in enumerate(jobs))
    tweens = "\n".join(
        f'tl.fromTo("#jin{i+1}", {{y: 60, opacity: 0}}, {{y: 0, opacity: 1, duration: 0.35, ease: "power3.out"}}, {2.5 + i*2});'
        f'tl.to("#jin{i+1}", {{y: -40, opacity: 0, duration: 0.25, ease: "power2.in"}}, {2.5 + i*2 + 1.72});'
        for i in range(len(jobs)))
    return f'''<!doctype html>
<html lang="en" data-resolution="square">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      :root {{ --ground: #0b1324; --card: #131f38; --ink: #ffffff; --muted: #9fb0cc; --accent: #22c55e; --font-display: Inter; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1080px; overflow: hidden; background: var(--ground); }}
      #root {{ width: 100%; height: 100%; position: relative; font-family: var(--font-display); color: var(--ink); }}
      .brand {{ position: absolute; left: 96px; top: 84px; font-size: 34px; font-weight: 700; letter-spacing: -0.01em; }}
      .brand b {{ color: var(--accent); }}
      .scene {{ position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; padding: 0 96px; }}
      .kicker {{ font-size: 40px; color: var(--accent); font-weight: 700; margin-bottom: 24px; }}
      .hook {{ transform-origin: left center; font-size: 112px; line-height: 1.02; font-weight: 900; letter-spacing: -0.035em; }}
      .sub {{ font-size: 38px; color: var(--muted); margin-top: 32px; }}
      .job {{ position: absolute; inset: 0; display: flex; align-items: center; padding: 0 96px; }}
      .jin {{ width: 100%; background: var(--card); border-radius: 36px; padding: 64px; border-left: 12px solid var(--accent); }}
      .num {{ font-size: 30px; color: var(--muted); font-weight: 700; margin-bottom: 20px; }}
      .jt {{ font-size: 64px; line-height: 1.08; font-weight: 900; letter-spacing: -0.02em; }}
      .co {{ font-size: 44px; margin-top: 28px; font-weight: 700; }}
      .wh {{ font-size: 36px; color: var(--muted); margin-top: 14px; }}
      .sal {{ display: inline-block; margin-top: 30px; font-size: 40px; font-weight: 700; color: #04140a; background: var(--accent); padding: 10px 24px; border-radius: 14px; }}
      .url {{ font-size: 76px; font-weight: 900; color: var(--accent); letter-spacing: -0.02em; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="15" data-width="1080" data-height="1080">
      <div id="brand" class="clip brand" data-start="0" data-duration="15" data-track-index="3">QA Job <b>Board</b></div>
      <div id="intro" class="clip scene" data-start="0" data-duration="2.5" data-track-index="0">
        <div class="kicker" id="kick">{html.escape(datestr)} · New QA jobs</div>
        <div class="hook" id="hook">5 QA jobs<br/>hiring now</div>
        <div class="sub" id="sub">QA · SDET · Test automation</div>
      </div>
      {cards}
      <div id="outro" class="clip scene" data-start="12.5" data-duration="2.5" data-track-index="0">
        <div class="kicker" id="ok">{total_jobs:,} QA jobs, updated daily</div>
        <div class="url" id="ourl">qajobboard.com</div>
        <div class="sub" id="osub">Free for job seekers · Hiring? Post a job</div>
      </div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#hook", {{scale: 0.96}}, {{scale: 1, duration: 2.2, ease: "power1.out"}}, 0);
      tl.fromTo("#sub", {{opacity: 0.4}}, {{opacity: 1, duration: 0.6}}, 0.2);
      tl.to(["#kick", "#hook", "#sub"], {{opacity: 0, y: -30, duration: 0.25, ease: "power2.in"}}, 2.22);
      {tweens}
      tl.fromTo(["#ok", "#ourl", "#osub"], {{opacity: 0, y: 40}}, {{opacity: 1, y: 0, duration: 0.4, stagger: 0.12, ease: "power3.out"}}, 12.5);
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''


def caption(jobs, day):
    lines = [f"🎬 5 QA jobs hiring now ({dt.date.fromisoformat(day).strftime('%B %-d')})", ""]
    for j in jobs:
        m = money(j["salary"])
        lines.append(f"▪️ {j['title']} – {j['company']['name']} · {where(j)}" + (f" · {m}" if m else ""))
        lines.append(f"   {j['links']['self']}")
    lines += ["", "All QA, SDET and test automation jobs: https://www.qajobboard.com/jobs",
              "Hiring QA engineers? Post a job: https://www.qajobboard.com/pricing", "",
              "#QAJobs #SoftwareTesting #SDET #TestAutomation #Hiring"]
    return "\n".join(lines)


def main():
    day = dt.date.today().isoformat()
    req = urllib.request.Request("https://www.qajobboard.com/jobs.json", headers={"User-Agent": "qa-feed-video"})
    jobs = json.load(urllib.request.urlopen(req, timeout=60))
    chosen, _ = pick(jobs)
    if len(chosen) < 5:
        sys.exit(f"Par maz jaunu darbu: {len(chosen)}")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(PROJ, "index.html"), "w") as f:
        f.write(build(chosen, len(jobs), day))
    txt = os.path.join(OUT, f"{day}.txt")
    with open(txt, "w") as f:
        f.write(caption(chosen, day))
    print("Teksts:", txt)
    if "--no-render" in sys.argv:
        return
    mp4 = os.path.join(OUT, f"{day}.mp4")
    subprocess.run(["node", PLUGIN_CLI, "check", "--json"], cwd=PROJ, check=False)
    subprocess.run(["node", PLUGIN_CLI, "render", "--output", mp4], cwd=PROJ, check=True)
    print("Video:", mp4)


if __name__ == "__main__":
    main()
