# QA Jobs Board – LinkedIn stratēģija

Lapa: https://www.linkedin.com/company/qa-jobs-board (1 699 sekotāji, nov. 2026)

## Kāda ir situācija tagad
- Pēdējais ieraksts bija pirms 4 nedēļām.
- Ieraksti bija automātiski: saite uz vienu darbu un no apraksta nokopēts teksts. Tiem ir 0–1 reakcija.
- LinkedIn maz rāda ierakstus, kas sastāv tikai no saites bez paša teksta. Tos nedalās un nekomentē.

## Mērķi (90 dienas)
| Rādītājs | Tagad | Pēc 30 d. | Pēc 90 d. |
|---|---|---|---|
| Sekotāji | 1 699 | 2 200 | 4 000 |
| Ieraksti nedēļā | 0 | 21 | 21 |
| Klikšķi uz lapu mēnesī | ~0 | 500 | 2 000 |
| E-pasta abonenti (no LinkedIn) | 203 | 300 | 600 |
| Uzņēmumi, kas uzrunāti caur LinkedIn | 0 | 30 | 100 |

## 3 ieraksti dienā (gatavus ģenerē `linkedin.py`)
| Laiks (Rīga) | Ieraksts | Kāpēc |
|---|---|---|
| 08:00 | 🌍 Jauni remote QA darbi (6 darbi, 1 saite) | Remote darbus meklē visvairāk visās valstīs |
| 12:30 | 🔥 Dienas QA darbs (ar algu, ja ir) | Viens konkrēts darbs: cilvēki atzīmē draugus |
| 17:30 | Dienas tēma (skat. zemāk) | Dažādība, lai sekotāji nenogurst |

**Dienas tēmas:** P – SDET darbi · O – Junior/entry darbi · T – darbi ar norādītu algu · C – remote darbi vienā valstī · Pk – darba devējiem ($99/$199) · S – nedēļas statistika · Sv – karjeras padoms.

## Noteikumi
1. **Saturs pašā ierakstā.** Darbu sarakstam jābūt redzamam bez klikšķa. Saite tikai viena, ieraksta beigās.
2. **Pirmie 60 minūtes pēc ieraksta:** atbildi uz katru komentāru. Tas palielina ieraksta sasniedzamību.
3. **3–5 tēmturi**, vienmēr #QAJobs #SoftwareTesting + 1–3 pēc tēmas.
4. **Atzīmē uzņēmumus** „Dienas darbā” (@uzņēmums). Daži padalās ar ierakstu, un tas ir bezmaksas sasniedzamība un iemesls uzrunāt pārdošanai.
5. **Personīgais profils pastiprina.** Pārpublicē 1 ierakstu dienā no sava profila ar 1 teikumu no sevis. Personīgie profili sasniedz 5–10× vairāk nekā uzņēmumu lapas.

## Kā audzēt sekotājus (bez maksas)
- **Uzaicini kontaktus sekot lapai.** LinkedIn dod 250 bezmaksas ielūgumus mēnesī: Lapa → „Grow” → „Invite to follow”. Uzaicini QA, testētājus un rekrutētājus no saviem kontaktiem. Izmanto visus 250 katru mēnesi.
- **Paldies jaunajiem sekotājiem.** Reizi nedēļā ieraksts: „Welcome to 37 new QA professionals this week 👋”.
- **Saite no lapas un e-pastiem.** Pievieno LinkedIn pogu e-pasta veidnē un lapas kājenē (tā jau ir).
- **Grupas.** Reizi nedēļā dalies ar nedēļas statistikas ierakstu Software Testing / QA grupās (Ministry of Testing, Software Testing & QA, ISTQB). Nesūti spamu, tikai saturu.
- **LinkedIn Newsletter.** Lapā izveido „QA Jobs Weekly” biļetenu. Visi sekotāji saņem paziņojumu, un abonenti saņem e-pastu no LinkedIn. Tas ir labākais bezmaksas kanāls, ko lielākā daļa darbu lapu neizmanto. Saturs ir sestdienas statistika un 10 labākie nedēļas darbi.
- **Darbinieku ieraksti.** Pievieno sev lapu kā darba vietu (Founder, QA Jobs Board). Tad tavi kontakti redz lapu tavā profilā.

## Kā pārvērst LinkedIn naudā
- Katrs **„Dienas darbs”** ar atzīmētu uzņēmumu ir iemesls uzrunāt: „We featured your QA role to 1,700 QA followers today. Want it pinned on QA Job Board for 30 days? First post free / 50% off.”
- **Piektdienas ieraksts darba devējiem** ved uz /pricing. Kupons `QAJOBBOARD` dod −50%.
- **Komentētāji, kas ir rekrutētāji vai HR**: pievieno sarakstam un uzrunā personīgi.

## Automatizācija
- Katru dienu 07:00 (Rīga) GitHub Action izveido `out/linkedin.json` un `out/linkedin/DATUMS.md`. Tajos ir 3 gatavi ieraksti.
- **Publicēšana (izvēlies vienu):**
  1. **Make.com (bezmaksas, 1 000 operāciju mēnesī).** Scenārijs 3× dienā nolasa `linkedin.json` no GitHub un publicē ar moduli „LinkedIn → Create a Company Text Post”. Pilnībā automātiski, vienreiz jāpieslēdz LinkedIn konts.
  2. **Buffer (Essentials, ~$6/mēn).** Rindā ievieto 3 ierakstus dienā, un tu tos tikai apstiprini.
  3. **Manuāli.** Atver `out/linkedin/DATUMS.md` GitHub, nokopē un ielīmē. Apmēram 3 minūtes dienā.
- Iesaku **sākt ar 3. variantu 1–2 nedēļas**, lai redzētu, kuri ieraksti strādā, un tad pārslēgties uz Make.
