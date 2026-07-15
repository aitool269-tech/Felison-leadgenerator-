# AFM Leadgenerator

Dashboard voor leads uit nieuwe AFM-vergunningen (inkomensverzekeringen, adviseren/bemiddelen).

## Demo-omgeving

- **https://afm-leadgenerator-demo.vercel.app** — toegangscode `demo` (of direct: `/?code=demo`).
- Apart Vercel-project (`afm-leadgenerator-demo`, link-config in `.vercel-demo/`) met env `DEMO_MODE=1`; zelfde codebase.
- Vult zichzelf bij elke koude start met fictieve data uit `demo_seed.py` (12 kantoren, 3 AM's, volledige funnel, tijdlijnen, meldingen). Geen database gekoppeld — wijzigingen verdwijnen vanzelf, de demo reset zichzelf.
- Demo bijwerken na code-wijzigingen: `mv .vercel .vercel-prod && mv .vercel-demo .vercel && npx vercel deploy --prod --yes && mv .vercel .vercel-demo && mv .vercel-prod .vercel`

## Online (Vercel)

- URL: **https://afm-leadgenerator.vercel.app** — toegangscode staat in `.toegangscode.txt` (env `APP_ACCESS_CODE` op Vercel).
- Project: `afm-leadgenerator` in team aitool269-techs-projects. Deploy: `npx vercel deploy --prod --yes` vanuit deze map.
- **Let op:** zonder gekoppelde database draait Vercel in demo-modus (data in `/tmp`, verdwijnt bij een koude start). Koppel eenmalig een gratis Neon Postgres: Vercel-dashboard → project → *Storage* → *Create Database* → Neon → Connect. Daarna redeployen; de app pakt `DATABASE_URL` automatisch op (zie `database.py`).

## Starten

```bash
cd afm-leadgenerator
python3 -m uvicorn app:app --port 8642
```

Open daarna http://localhost:8642

## Maandelijkse werkwijze

1. Download bij de AFM het R0443-rapport (**Nieuwe inkomensvergunningen**, .xlsx) en het register **financiele-dienstverleners** (.csv).
2. Tab **Import** → sleep beide bestanden erin → *Importeer*.
3. Het systeem: matcht op AFM-vergunningnummer + genormaliseerde naam, vult vestigingsplaats/handelsnamen aan uit de CSV, slaat al bekende vergunningnummers over, geocodeert via de gratis PDOK Locatieserver (plaats → provincie + kaartcoördinaten) en berekent de kwaliteitsscore.

## Kwaliteitsscore (A/B/C)

Basis 40 punten, daarna:
- Versheid vergunning: ≤45 dagen +25, ≤120 dagen +15
- Dienst "Adviseren / Bemiddelen" +10, anders −10 (bijv. gevolmachtigd agent)
- Beperkte vergunning (alleen betalingsbeschermers e.d.) −30
- B.V./N.V. +10
- Volledig adres +10, alleen plaats +5

Daarnaast een websitescan (knop in het leaddetail, max +15): bereikbaar +3; actief op verzuimverzekering +3, collectieve inkomensverzekeringen +3, personeelsverzekeringen +3; AOV/WIA/WGA genoemd +2; team-/contactpagina +1. De scan bekijkt de homepage plus max. 3 relevante subpagina's (diensten/zakelijk/verzuim e.d.) en stapelt niet bij herhaald scannen (basisscore blijft bewaard in `score_basis`).

A ≥ 70, B ≥ 50, C < 50. De uitleg per lead staat als tooltip op de scorebadge en in het leaddetail.

## Opvolgfunnel

Nieuw → Geclaimd → Benaderd → In gesprek → Aanstelling / Afgewezen / Geen interesse.
Elke statuswissel wordt gelogd met datum, AM en notitie. AM's beheer je in tab **Team**; hun kleur bepaalt de kaartweergave zodat het feitelijke werkgebied per AM zichtbaar wordt.

## E-mailnotificaties (Resend)

- `mail.py` verstuurt via Resend; zonder `RESEND_API_KEY` staat mail uit (app werkt gewoon, `meta.mail` = false, Instellingen toont een waarschuwing).
- Env vars op productie: `RESEND_API_KEY`, `MAIL_FROM` (bijv. `Leadgenerator Felison <leads@domein.nl>`), `APP_URL`, `CRON_SECRET`.
- Dagelijkse AM-digest: Vercel Cron roept `/api/cron/digest` aan (07:00 UTC, ma-vr; auth: `Bearer CRON_SECRET`). Alleen AM's mét e-mailadres (Team-beheer) en alleen als er acties zijn.
- Claim → directe mail naar marketing (adres in Instellingen) voor het presentje.
- Feedbackknop (zijbalk) → opslag in database + mail naar het feedback-adres uit Instellingen.

## Relatiecheck

Upload onder Instellingen een lijst bedrijfsnamen van bestaande relaties (.xlsx/.csv, kolom "naam" of eerste kolom; upload vervangt de lijst). Leads die op genormaliseerde naam matchen krijgen ⚠ "relatie?"; een AM bevestigt ("Bestaande relatie", eindstatus) of verwerpt ("geen match", komt niet terug) in het leaddetail. Matching draait bij elke upload én elke AFM-import.

## Data

- `leads.db` (SQLite) — alle leads, statushistorie, AM's en importlog. **Back-uppen = dit ene bestand kopiëren.**
- Ontdubbeling gaat op AFM-vergunningnummer over alle maanden heen.

## Nog niet gebouwd (bewuste keuzes)

- Geen login; AM kiest zijn naam bij het claimen.
- Website-verrijking is volautomatisch: na elke import zoekt de app per nieuwe lead de website via Serper (`SERPER_API_KEY` in `.env` lokaal / Vercel-env in productie) en scant die op inkomensthema's. Handmatig bijsturen kan altijd: juiste URL invullen in het leaddetail en op Scan klikken. Gidsen-sites (companyinfo, telefoonboek e.d.) worden gefilterd via een blocklist in `app.py`.
