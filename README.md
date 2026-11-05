# QA Jobs Board – bezmaksas darbu plūsma

Katru dienu savāc svaigus QA / SDET / testēšanas darbus no publiskiem avotiem
(Himalayas, Arbeitnow, Remotive, Remote OK, Greenhouse/Lever/Ashby karjeras lapām)
un uzģenerē `out/jobs.xml` (Jobboardly XML Importer) un `out/jobs.csv` (CSV Importer).
Jobboardly kredīti netiek tērēti.

- `python3 feed.py` – uzģenerē plūsmu
- `python3 discover.py` – pārbauda `candidates.txt` un atjauno `companies.json`
- `.github/workflows/daily.yml` – palaiž katru dienu 07:00 pēc Rīgas laika

Iestatījumi `feed.py` sākumā: `MAX_AGE_DAYS`, `MAX_PER_COMPANY`, filtri `QA_RE` / `EXCLUDE_RE`.
