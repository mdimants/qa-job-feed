# Darba devēju uzruna: QA Job Board

Mērķis: uzņēmumi un personāla atlases aģentūras liek QA darbus pie mums par maksu.

Piedāvājums: 50% atlaide pirmajam sludinājumam ar kodu **QAJOBBOARD** (Jobboardly kupons, 200 izmantošanas reizes, pircējs to ievada pats).
- Standard: $99 → $49.50 (30 dienas).
- Featured: $199 → $99.50 (piesprausts augšā, iekļauts darbu e-pastā, publicēts LinkedIn).

## Process (katru darba dienu)
1. `python3 outreach/candidates.py 30` atlasa uzņēmumus ar svaigu programmatūras QA darbu mūsu vietnē. Tiek izlaisti lielie uzņēmumi un jau uzrunātie.
2. Katram uzņēmumam atrod **publiski norādītu** darba e-pastu:
   - pašā darba sludinājumā;
   - uzņēmuma karjeras vai kontaktu lapā (jobs@, careers@, talent@, recruiting@, hr@; mazam uzņēmumam derīgs arī hello@ vai info@);
   - vai uzņēmuma vietnē publiski norādītu personāla atlases speciālista vai dibinātāja e-pastu.
   E-pastus nekad neuzmin un nesastāda pēc parauga (vards.uzvards@...). Ja e-pasta nav, uzņēmumu izlaid un ieraksti `no_email`.
3. Izveido Gmail **melnrakstu** (nenosūta). Nosūta Mārcis pats.
4. Ieraksta `outreach/contacted.csv` (tikai lokāli, nav git): `date,company,email,source_url,job_url,status,draft_id`.
5. Pēc 5 darba dienām, ja nav atbildes, vienu reizi sagatavo īsu atgādinājuma melnrakstu tajā pašā sarakstē. Vairāk nekā 2 e-pastus vienam uzņēmumam nesūta.

## E-pasta sagatave (angliski, vienkāršs teksts)
Temats: `Your {job_title} role on QA Job Board`

```
Hi {vārds vai "{Company} team"},

Your {job_title} opening is already listed on QA Job Board, a job board only for software testers and QA engineers:
{job_url}

It's one of 2,000+ QA jobs on the board right now. If you want it to stand out to testers who are actively looking, you can post it as a featured job: it's pinned to the top of the board, sent in our QA job alert email and shared on our LinkedIn page.

For your first post we're offering 50% off with the code QAJOBBOARD, so a featured post is $99.50 instead of $199 (a standard 30-day post is $49.50):
https://www.qajobboard.com/pricing

If you post it directly, we'll remove the imported copy so there's no duplicate.

Happy to answer any questions, just reply to this email.

Best,
Mārcis Dimants
Founder, QA Job Board
https://www.qajobboard.com

P.S. Not the right person or not interested? Reply "no" and I won't email you again.
```

Noteikumi:
- Vienu personalizētu teikumu var pievienot pēc pirmās rindkopas (piemēram, ja uzņēmumam ir vairāki QA darbi: „You also have {n} other QA roles open.”). Neizdomā faktus par uzņēmumu.
- Ja uzņēmums ir personāla atlases aģentūra, otro rindkopu pielāgo: „If you regularly hire QA engineers for clients, ...”.
- Bez pielikumiem un attēliem. Saites tikai uz qajobboard.com.

## Atgādinājums (pēc 5 darba dienām)
```
Hi {vārds vai "{Company} team"},

Just following up on my note about your {job_title} role. The 50% code QAJOBBOARD still works for your first post: https://www.qajobboard.com/pricing

If now isn't a good time, no worries, I won't follow up again.

Mārcis
```
