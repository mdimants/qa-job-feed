// Atjaunina jau publicētus bloga rakstus Jobboardly no GitHub repo.
// Palaid Chrome cilnē ar app.jobboardly.com (javascript_tool). Pirms tam iestati:
//   const SLUGS = ["qa-engineer-salary-2026"];
// posts.json ierakstā jābūt laukam "jb_id" (Jobboardly bloga raksta id).
// Publicēšanas datums netiek mainīts; maina nosaukumu, aprakstus, tagus un saturu.
const RAW = "https://raw.githubusercontent.com/mdimants/qa-job-feed/main/blog/";
const posts = await (await fetch(RAW + "posts.json?t=" + Date.now())).json();
const out = [];
for (const slug of SLUGS) {
  const p = posts.find(x => x.slug === slug);
  if (!p || !p.jb_id) { out.push(slug + ": nav posts.json vai jb_id"); continue; }
  const content = await (await fetch(RAW + "posts/" + slug + ".html?t=" + Date.now())).text();
  const d = new DOMParser().parseFromString(await (await fetch("/blog_posts/" + p.jb_id + "/edit")).text(), "text/html");
  const f = d.querySelector('form[action="/blog_posts/' + p.jb_id + '"]') || d.querySelector('form[action*="/blog_posts/"]');
  if (!f) { out.push(slug + ": forma nav atrasta"); continue; }
  const fd = new FormData(f);
  fd.set("blog_post[title]", p.title);
  fd.set("blog_post[excerpt]", p.excerpt);
  fd.set("blog_post[tags]", p.tags || "");
  fd.set("blog_post[meta_title]", p.meta_title || p.title);
  fd.set("blog_post[meta_description]", p.meta_description || p.excerpt);
  fd.set("blog_post[content]", content);
  fd.delete("blog_post[featured_image]");
  fd.delete("blog_post[open_graph_image]");
  const sub = f.querySelector("[type=submit][name]");
  if (sub) fd.set(sub.name, sub.value);
  const r = await fetch(f.getAttribute("action"), { method: "POST", body: fd });
  out.push(slug + ": " + r.status + " " + r.url.replace(/\?.*/, "").replace(/^https:\/\/[^/]+/, ""));
}
out.join("\n");
