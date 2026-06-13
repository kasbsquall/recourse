# Recourse — Deployment Guide

Production target: **Supabase** (Postgres + pgvector) · **Railway** (backend + agents) · **Vercel** (frontend).
The GitHub repo is the source for all three.

> Architecture note: the 5 Band agents are long-lived WebSocket clients. The FastAPI backend
> drives a debate by talking to Band's Agent API as the **Coordinator**; the adjudicators reply
> only while their agent processes are connected to Band. So the agents must be **running
> somewhere** (Railway worker, or your laptop) for a *live* debate. A deployed claim that's
> already resolved always renders (transcript + resolution + audit export) regardless.

---

## 1. Supabase (database)
1. Create a project → copy the connection string (Project Settings → Database).
2. SQL editor → run `create extension if not exists vector;`
3. SQL editor → paste and run `backend/database/schema.sql`.
4. Seed once, locally, pointed at Supabase:
   - In `backend/.env`, set `DATABASE_URL` to the Supabase string **rewritten to** `postgresql+asyncpg://...`
   - If using the pooler (port 6543), append `?prepared_statement_cache_size=0` (asyncpg + pgbouncer).
   - Run `cd backend && .venv\Scripts\python database/seed_data.py`

## 2. Railway (backend API)
1. New Project → Deploy from the GitHub repo → root directory `backend`.
2. It uses `backend/Procfile` (`uvicorn main:app --host 0.0.0.0 --port $PORT`) and Python 3.12
   (`backend/.python-version`).
3. Add env vars (from your `.env`): `DATABASE_URL` (Supabase), all `BAND_*`, `AIMLAPI_*`,
   `FEATHERLESS_*`, and `CORS_ORIGINS=https://<your-vercel-domain>` (exact origin, no trailing slash).
4. Note: `sentence-transformers`/torch is heavy — first cold start downloads the model. If the
   build/boot times out, that's the cause (the embedding model is only needed at seed/RAG time).

## 3. Railway (agents) — for a self-contained live URL
Add a **second service** from the same repo, root `backend`, start command:
```
python -m agents.run_agents
```
It's a worker (no HTTP port). Same env vars as the backend (the `BAND_*` keys).
*Alternative for the demo:* skip this and run the agents on your laptop
(`cd backend && .venv\Scripts\python -m agents.run_agents`) while you record.

## 4. Vercel (frontend)
1. Add New Project → import the repo → root directory `frontend`.
2. Env var: `NEXT_PUBLIC_API_URL=https://<your-railway-backend-domain>`
3. Deploy (Next.js 14 auto-detected). The Vercel URL is your live Application URL.

## 5. Wire-up checks
- `GET https://<railway>/api/health` → `{"status":"ok"}`
- Open the Vercel URL → dashboard loads claims (CORS OK).
- If agents are running: open a pending claim → "Open Adjudication Room" → live debate.

## Local development
See `README.md`. Four terminals from repo root: `docker compose up -d db`,
`cd backend && .venv\Scripts\python -m agents.run_agents`,
`cd backend && .venv\Scripts\python -m uvicorn main:app --port 8000`,
`cd frontend && npm run dev`.
