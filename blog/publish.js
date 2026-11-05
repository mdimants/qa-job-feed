// Publicē bloga rakstus Jobboardly no GitHub repo.
// Palaid Chrome cilnē ar app.jobboardly.com (javascript_tool). Mainīgais SLUGS jāiestata pirms tam:
//   const SLUGS = ["qa-engineer-salary-2026"];
// Raksts tiek izlaists, ja raksts ar šādu nosaukumu jau eksistē.
const RAW = "https://raw.githubusercontent.com/mdimants/qa-job-feed/main/blog/";
const posts = await (await fetch(RAW + "posts.json?t=" + Date.now())).json();
const listHtml = await (await fetch("/blog_posts")).text();
const out = [];
for (const slug of SLUGS) {
  const p = posts.find(x => x.slug === slug);
  if (!p) { out.push(slug + ": nav posts.json"); continue; }
  if (listHtml.includes(p.title) || listHtml.includes(p.title.replace(/&/g, "&amp;").replace(/'/g, "&#39;"))) { out.push(slug + ": jau eksistē"); continue; }
  const content = await (await fetch(RAW + "posts/" + slug + ".html?t=" + Date.now())).text();
  const d = new DOMParser().parseFromString(await (await fetch("/blog_posts/new")).text(), "text/html");
  const f = d.querySelector('form[action="/blog_posts"]');
  const fd = new FormData(f);
  fd.set("blog_post[title]", p.title);
  fd.set("blog_post[slug]", p.slug);
  fd.set("blog_post[excerpt]", p.excerpt);
  fd.set("blog_post[state]", "published");
  fd.set("blog_post[published_at]", (p.published || new Date().toISOString().slice(0, 10)) + "T08:00");
  fd.set("blog_post[tags]", p.tags || "");
  fd.set("blog_post[meta_title]", p.meta_title || p.title);
  fd.set("blog_post[meta_description]", p.meta_description || p.excerpt);
  fd.set("blog_post[content]", content);
  fd.delete("blog_post[featured_image]");
  fd.delete("blog_post[open_graph_image]");
  fd.set("commit", "Save");
  const r = await fetch("/blog_posts", { method: "POST", body: fd });
  out.push(slug + ": " + r.status + " " + r.url.replace(/\?.*/, ""));
}
out.join("\n");
