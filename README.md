# Vagdevi Junior College - Timetable System

A digital version of the college's paper timetable sheets: same grid, same
notation (subject over lecturer code, split periods, SH, combined classes),
but with clash prevention across all campuses, an auto-assign engine, and
live workload sheets.

## Run it (development)

Backend (needs Python 3.10+):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend (needs Node 18+), in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

| Login | Password | Can do |
|---|---|---|
| `admin` | `admin123` | Everything, incl. salary/interview data, structure changes, clearing campuses |
| `operator` | `operator123` | Fill timetables, manage requirements, view staff (no sensitive fields) |

Change these passwords before real use (admin can add users via
`POST /api/auth/users`).

The database is a single `backend/vagdevi.db` SQLite file, created and
seeded on first boot with everything digitized from your sheets: 4
campuses, both period grids, all subjects, the section lists, lecturer
codes from the AC Campus sheet, the English allocation from the
handwritten note, 6 JLs, and the subject-load requirements. Edit any of it
in the app - the seed is just a starting point. (Lecturer full names were
guessed from codes; fix them in the Staff page.)

## What's where (so you can change one thing without touching the rest)

```
backend/app/
  database.py     DB connection only (swap SQLite -> Postgres via env var)
  models.py       tables, nothing else
  schemas.py      what the API sends/receives; operator vs admin staff DTOs
  auth.py         passwords, tokens, role checks (require_user/require_admin)
  clash.py        THE clash rules - one file, used by everything
  engine.py       auto-assign algorithm
  seed.py         first-boot data
  routers/
    auth_routes.py   login, user creation
    structure.py     campuses, periods, subjects, sections CRUD
    staff_routes.py  lecturer/JL profiles with data isolation
    timetable.py     grid fetch, booking with 409 clash errors, lock, clear
    planning.py      requirements, auto-assign preview/commit, workload

frontend/src/
  api.js              every network call goes through here
  styles.css          all design tokens at the top - recolor the app there
  App.jsx             tabs + auth shell
  components/
    TimetablePage.jsx  the grid + auto-assign panel
    CellEditor.jsx     booking modal (splits, combine, SH, lock)
    RequirementsPage.jsx  the subject-load sheet (drives auto-assign)
    WorkloadPage.jsx   lecturer load + required-vs-scheduled
    StaffPage.jsx, SectionsPage.jsx, CampusPage.jsx, Login.jsx
```

Want to change clash rules? `clash.py`. Different auto-assign behavior?
`engine.py`. New staff field? `models.py` + `schemas.py` + StaffPage.
Nothing else needs touching.

## How the important parts work

**Clash prevention.** Every booking checks the lecturer AND every section
involved. Slots store real start/end times, so checks are time-overlap
based: KSR teaching 8.00-8.45 at AC Campus is blocked from a Saraswathi
8.10-9.00 period automatically, even though the campuses have different
grids. Split periods: half A and half B coexist in the same slot; a FULL
booking conflicts with both. Clashes return HTTP 409 with a plain-English
explanation, which the app shows in red in the cell editor.

**Auto-assign.** Preview first, nothing saved; then Apply commits in one
transaction (any conflict rolls the whole thing back). It places the
heaviest-loaded sections first, spreads subjects across the day, pairs
half-periods (the ENG/SAN pattern), balances lecturers by load with
full-timers favored, fills leftover slots as Study Hours assigned to the
least-loaded free JL, and reports anything it could not place instead of
silently dropping it. Manual bookings are locked by default and survive
auto-assign and "Clear campus".

**Data isolation.** Operators never receive salary_discussed,
date_of_interview, or campaign_village_town: the operator response schema
does not contain those fields, and operator writes to them are ignored
server-side. Role checks live in auth dependencies, not in the frontend.

## Deploying (the Vercel + Render plan)

Backend on Render (or Railway):
- Root dir `backend`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add a Postgres instance, set `DATABASE_URL` to its URL
  (use the `postgresql+psycopg://` scheme and add `psycopg[binary]` to
  requirements.txt)
- Set `SECRET_KEY` (long random string) and
  `CORS_ORIGINS=https://your-app.vercel.app`

Frontend on Vercel:
- Root dir `frontend`, framework Vite
- Env var `VITE_API_URL=https://your-api.onrender.com`

## Extension points (deliberately left simple)

- **Day-of-week schedules**: the timetable currently repeats daily, like
  your sheets. To vary by day, add `day_of_week` to TimeSlot or TTSession
  and include it in `clash.py`.
- **Travel buffer**: cross-campus clash is exact-overlap today. To require
  e.g. 15 min travel time between campuses, pad the overlap check in
  `clash.py` when the two slots are on different campuses.
- **Auto-merging BIPC sections** (VJM into VJE1 for Phy/Che): book it once
  manually with "Combine with" and lock it; the engine respects it. A rule
  for the engine to do this itself would go in `engine.py`.

To run locally
http://localhost:5173 
