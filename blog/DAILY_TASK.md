# Ikdienas bloga uzdevums (Claude scheduled task)

Grafiks: katru dienu 09:00 pēc vietējā laika. Uzdevuma ID: qajobboard-blog-diena.

Ko uzdevums dara katru dienu:
1. Izpilda `git pull` un pārbauda, vai out/insights.json ir svaigs. GitHub Action to atjauno 04:00 UTC.
2. Izvēlas tēmu pēc blog/TOPICS.md nedēļas ritma.
3. Uzraksta HTML rakstu blog/posts/<slug>.html (900–1 600 vārdu, vismaz 3 skaitļi no insights.json, bez izdomātiem skaitļiem) un pievieno to blog/posts.json.
4. Pārbauda rakstu: garums, saites atgriež 200, slug nedublējas. Pēc tam izpilda commit un push.
5. Chrome cilnē app.jobboardly.com/blog_posts palaiž blog/publish.js. Tad atjauno custom page 6988 no out/companies_page.json.
6. Ar curl pārbauda, vai raksts un lapa atveras, un lietotājam uzraksta īsu kopsavilkumu.
