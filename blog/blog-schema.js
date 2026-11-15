<!-- qajobboard blog schema v1 -->
<script>
(function () {
  function meta(n) { var m = document.querySelector('meta[name="' + n + '"],meta[property="' + n + '"]'); return m ? m.content : ""; }
  function run() {
    var p = location.pathname, old0 = document.getElementById("qjb-blog-schema");
    if (!/^\/blog\/[^\/]+$/.test(p)) { if (old0) old0.remove(); return; }
    var h1 = document.querySelector("h1"); if (!h1) return;
    var url = "https://www.qajobboard.com" + p;
    var txt = (document.querySelector("article") || document.body).innerText || "";
    var d = (txt.match(/(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}/) || [])[0];
    var iso = d ? new Date(d + " 12:00 UTC").toISOString().slice(0, 10) : undefined;
    var graph = [{
      "@type": "BlogPosting", "@id": url + "#article", "headline": h1.innerText.trim(),
      "description": meta("description"), "url": url, "mainEntityOfPage": url,
      "image": meta("og:image") || undefined, "datePublished": iso, "dateModified": iso,
      "author": { "@type": "Organization", "name": "QA Job Board", "url": "https://www.qajobboard.com/" },
      "publisher": { "@id": "https://www.qajobboard.com/#org" }
    }];
    var faq = [], hs = document.querySelectorAll("h2");
    for (var i = 0; i < hs.length; i++) {
      if (!/frequently asked questions/i.test(hs[i].innerText)) continue;
      var el = hs[i].nextElementSibling, q = null;
      while (el && el.tagName !== "H2") {
        if (el.tagName === "H3") q = el.innerText.trim();
        else if (q && el.tagName === "P") { faq.push({ "@type": "Question", "name": q, "acceptedAnswer": { "@type": "Answer", "text": el.innerText.trim() } }); q = null; }
        el = el.nextElementSibling;
      }
    }
    if (faq.length) graph.push({ "@type": "FAQPage", "@id": url + "#faq", "mainEntity": faq });
    var s = document.createElement("script"); s.type = "application/ld+json"; s.id = "qjb-blog-schema";
    s.text = JSON.stringify({ "@context": "https://schema.org", "@graph": graph });
    var old = document.getElementById("qjb-blog-schema"); if (old) old.remove();
    document.head.appendChild(s);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run); else run();
  document.addEventListener("turbo:load", run);
})();
</script>
<!-- /qajobboard blog schema -->
