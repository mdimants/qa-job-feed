"""Atrod, kuri uzņēmumi lieto Greenhouse / Lever / Ashby, un saglabā companies.json.

Palaiž retāk (piem. reizi mēnesī), kad gribi pievienot jaunus uzņēmumus:
    python3 discover.py
Kandidātus pievieno candidates.txt (viens slug rindā).
"""
import json
import pathlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).parent
UA = {"User-Agent": "qajobboard-feed/1.0 (+https://www.qajobboard.com)"}

ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json&limit=1",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "workable": "https://apply.workable.com/api/v1/widget/accounts/{slug}",
}
SR_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1"


def check(slug: str, ats: str):
    url = (SR_URL if ats == "smartrecruiters" else ENDPOINTS[ats]).format(slug=slug)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        if ats == "lever":
            ok = isinstance(data, list) and len(data) > 0
        elif ats == "smartrecruiters":
            ok = data.get("totalFound", 0) > 0
        else:
            ok = len(data.get("jobs", [])) > 0
        return (slug, ats) if ok else None
    except Exception:
        return None


def main():
    slugs = [s.strip().lower().replace(".", "") for s in (HERE / "candidates.txt").read_text().split()
             if s.strip() and not s.startswith("#")]
    slugs = sorted(set(slugs))
    tasks = [(s, a) for s in slugs for a in ENDPOINTS]
    sr = (HERE / "candidates_smartrecruiters.txt")
    if sr.exists():
        tasks += [(s.strip(), "smartrecruiters") for s in sr.read_text().split()
                  if s.strip() and not s.startswith("#")]
    with ThreadPoolExecutor(max_workers=16) as ex:
        found = [r for r in ex.map(lambda t: check(*t), tasks) if r]
    out = {}
    for slug, ats in found:
        out.setdefault(ats, []).append(slug)
    for a in out:
        out[a].sort()
    (HERE / "companies.json").write_text(json.dumps(out, indent=2))
    print({a: len(v) for a, v in out.items()}, "no", len(slugs), "kandidātiem")


if __name__ == "__main__":
    main()
