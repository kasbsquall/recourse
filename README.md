# Recourse — Adversarial Claims Adjudication

> 4 AI agents debate your insurance claim denial in 90 seconds and generate a
> legally-defensible resolution — the conversation **is** the audit trail.

Band of Agents Hackathon · lablab.ai · Track 3: Regulated & High-Stakes

## Architecture

```
Next.js 14 (Vercel)  ──►  FastAPI (Railway)  ──►  PostgreSQL + pgvector (Supabase)
                               │
                               └──►  Band (4 agents)  +  AI/ML API  +  Featherless AI
```

The 4 agents — **Blake** (Claims Evaluator), **Morgan** (Policy Analyst),
**Alex** (Devil's Advocate), and **Sam** (Resolution Notary) — debate each claim
in a Band adjudication room. A human claims officer approves the final resolution.

## Local development

### Backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
docker compose up -d db          # from repo root: Postgres 16 + pgvector
uvicorn main:app --reload        # http://localhost:8000/api/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

Copy `.env.example` to `.env` and fill in credentials (see the 7 intervention
points in the build spec).

## Build status

- [x] **Step 1** — Scaffolding (folders, docker-compose, requirements, Next.js)
- [x] **Step 2** — Database (schema, models, RAG over pgvector, seed)
- [x] **Step 3** — Band SDK + Room Manager (Agent API, Coordinator orchestration)
- [x] **Step 4** — The 5 agents (Coordinator + Blake, Morgan, Alex, Sam)
- [x] **Step 5** — FastAPI backend + Coordinator-driven debate orchestrator + SSE
- [x] **Step 6** — Frontend UI (dashboard, live debate room, resolution panel)
- [ ] Step 7 — Deploy (Supabase / Railway / Vercel) + demo video + submission

## License

MIT
