# MedLens

Organises clinical information from uploaded medical reports into a
structured, traceable, reviewable record. It is not a diagnostic or
treatment tool.

## Current state — Phase 2 complete

- Registration, login, JWT, protected routes, roles (clinician / admin)
- FastAPI backend, React + Vite + Tailwind frontend, Postgres
- **74 passing tests** (55 safety core, 19 auth)

## Run it

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"   # paste into JWT_SECRET
docker compose up --build                                      # :8000

docker compose exec backend alembic upgrade head               # create tables
```

Second terminal:

```bash
cd frontend && npm install && npm run dev                      # :5173
```

## Test

```bash
cd backend && python -m pytest -q
```

## Safety design

Low/Normal/High status is produced in exactly one place:
`app/services/range_evaluator.py`. It runs only on reference ranges that
`app/services/evidence_guard.py` has found verbatim in the uploaded
document. There is no table of standard reference ranges anywhere in this
codebase, and a test asserts that none is ever added.
