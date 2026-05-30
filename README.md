# Job Outreach — Charter skipper + deckhand (Franko + cura)

Autonomni sustav koji svaki dan šalje 20 personaliziranih mailova charter firmama, crew agencijama, brokerima, day-tour operatorima, sailing školama, flotilla firmama, marinama, yacht klubovima, job boardovima i superyacht management firmama — primarno Palma de Mallorca, fallback Italija/Francuska/Karibi.

Sustav radi kao **single Claude routine** (CronCreate), bez n8n. State u Google Sheet `Charter_Outreach`. CV (1 zajednički PDF za par) u Google Drive folderu `Charter_CVs`.

## Setup (one-time)

1. **Update OAuth scopes** — `python setup/02_extend_gmail_scope.py` → otvori browser, re-consent za `gmail.send` + `drive.readonly`. Token se prepisuje u `croatian-dmc-suite/token.json`.
2. **Create Sheet** — `python setup/01_create_sheet.py` → kreira `Charter_Outreach` u Driveu, ispiše Sheet ID. Stavi ID u `data/config.env`.
3. **Upload CV** — User stavi `couple_cv.pdf` u Drive folder `Charter_CVs`. Setup script ispiše folder ID.
4. **Fill personal info** — User popuni `data/personal_info.yaml` (bio, jezici, iskustvo, dnevne ture).
5. **Set secrets** — `.env`: `GMAIL_APP_PASSWORD`, `SERPER_API_KEY` (lead discovery), `FIRECRAWL_API_KEY` (page scraping).
6. **Seed leads** — `python setup/03_seed_initial_leads.py` → ~130 leadova (100 Med + 30 Karibi) u Sheet.
7. **Pilot send** — `python setup/pilot_send.py` → pošalji 3 maila sebi (DRY_RUN=true) → vizualna verifikacija → onda `--live` za 3 stvarnih.
8. **Create routine** — `python setup/04_create_routine.py` → CronCreate, prvi fire = pilot mode (3 maila).
9. **Approve pilot** — Nakon 24h, ako pilot OK, user u Sheet → Config tab → `pilot_approved=TRUE`. Sustav onda nastavlja 20/dan.

## Operations

- **Daily fire 09:00 CET**: routine se budi, ako `ready` leadova < 40 → discovery (Faza A), zatim šalje 20 mailova (Faza B).
- **Replies**: user gleda Gmail inbox ručno. Bez auto reply watch.
- **Geo eskalacija**: kad u current tieru <30 ready leadova → Config tab `current_tier` se inkrementira (Palma → Balearic → Italija → Francuska → Karibi).
- **Stopping the routine**: `python setup/stop_routine.py` ili Sheet → Config → `paused=TRUE`.

## Files

- `setup/01_create_sheet.py` — Google Sheet bootstrap (3 taba: Leads, Sent, Config)
- `setup/02_extend_gmail_scope.py` — OAuth re-consent
- `setup/03_seed_initial_leads.py` — initial lead discovery (Serper + Firecrawl)
- `setup/04_create_routine.py` — CronCreate invocation
- `setup/pilot_send.py` — manual pilot send (3 mailova) before routine activation
- `routine_prompts/daily_outreach.md` — autoritativni prompt embed-an u CronCreate routine
- `templates/*.txt` — 6 Jinja templatesa (EN/ES × charter/crewagency/generic)
- `data/personal_info.yaml` — Franko + cura bio
- `data/config.env` — sheet ID, drive folder ID, geo tier config
