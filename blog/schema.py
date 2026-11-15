"""Pievieno bloga rakstiem JSON-LD (BlogPosting + FAQPage).

FAQ tiek nolasīts no raksta sadaļas <h2>Frequently asked questions</h2>:
katrs <h3>jautājums</h3> + nākamais <p>atbilde</p>.
JSON-LD tiek ielikts raksta beigās starp <!--schema--> un <!--/schema-->,
tāpēc skriptu var palaist atkārtoti.

Palaišana: python blog/schema.py            (visi raksti)
           python blog/schema.py slug ...   (tikai norādītie)
"""
import html
import json
import pathlib
import re
import sys

BLOG = pathlib.Path(__file__).parent
SITE = "https://www.qajobboard.com"
MARK = re.compile(r"\n?<!--schema-->.*?<!--/schema-->\n?", re.S)


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def faq(body):
    m = re.search(r"<h2>Frequently asked questions</h2>(.*?)(?=<h2|$)", body, re.S | re.I)
    if not m:
        return []
    return [(text(q), text(a)) for q, a in re.findall(r"<h3>(.*?)</h3>\s*<p>(.*?)</p>", m.group(1), re.S)]


def build(post, body):
    url = f"{SITE}/blog/{post['slug']}"
    graph = [{
        "@type": "BlogPosting",
        "@id": url + "#article",
        "headline": post["title"],
        "description": post.get("meta_description") or post["excerpt"],
        "url": url,
        "mainEntityOfPage": url,
        "datePublished": post["published"],
        "dateModified": post.get("updated", post["published"]),
        "author": {"@type": "Organization", "name": "QA Job Board", "url": SITE + "/"},
        "publisher": {"@id": SITE + "/#org"},
        "keywords": post.get("tags", ""),
        "wordCount": len(text(body).split()),
    }]
    qa = faq(body)
    if qa:
        graph.append({
            "@type": "FAQPage",
            "@id": url + "#faq",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa],
        })
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    return f'\n<!--schema--><script type="application/ld+json">{data}</script><!--/schema-->\n'


def main(slugs):
    posts = json.loads((BLOG / "posts.json").read_text())
    for p in posts:
        if slugs and p["slug"] not in slugs:
            continue
        f = BLOG / "posts" / f"{p['slug']}.html"
        if not f.exists():
            continue
        body = MARK.sub("", f.read_text()).rstrip() + "\n"
        f.write_text(body + build(p, body))
        print(p["slug"], "faq:", len(faq(body)))


if __name__ == "__main__":
    main(sys.argv[1:])
