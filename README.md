# Recourse — Adversarial Claims Adjudication

> A panel of AI agents puts every disputed insurance claim on trial — and dynamically
> **recruits a sixth investigator the moment fraud is alleged**. The debate **becomes** the
> legally-defensible audit trail. A human officer keeps the final word.

**Band of Agents Hackathon · lablab.ai · Track 3: Regulated & High-Stakes**

![Live](https://img.shields.io/badge/demo-live-15803d?style=flat-square)
![Hackathon](https://img.shields.io/badge/Band%20of%20Agents-Track%203-0e7490?style=flat-square)
![Agents](https://img.shields.io/badge/agents-6%20·%20dynamic%20recruitment-b45309?style=flat-square)
![Stack](https://img.shields.io/badge/Band%20·%20Next.js%20·%20FastAPI%20·%20pgvector-2d5bff?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-555?style=flat-square)

- 🔗 **Live app** — [recourseband.duckdns.org](https://recourseband.duckdns.org)
- 🎬 **Commercial** — [youtu.be/io2CgqYpSek](https://youtu.be/io2CgqYpSek)
- 🖥️ **Live walkthrough** — [youtu.be/kY6AXSlKqhk](https://youtu.be/kY6AXSlKqhk)
- 📑 **Pitch deck** — [`deck/deck_v4.pdf`](deck/deck_v4.pdf)

![Recourse — live adversarial adjudication: agents debate, the Coordinator recruits Quinn (SIU), and a signed verdict lands](docs/hero.gif)

> _The live adjudication room: five agents debate, the Coordinator recruits Quinn (SIU) when fraud is alleged, and a signed verdict lands — a real run on the production app._

## What it does

Crestview Mutual (a fictional insurer) denied a claim. Instead of one overworked
reviewer deciding the appeal alone, **Recourse convenes a panel of specialist agents in a
single Band room** — five standing, plus a sixth investigator on call — and lets them argue it out:

| Agent | Role | Job |
|-------|------|-----|
| **Coordinator** | Orchestrator | Opens the case, convenes the room, routes every handoff |
| **Blake** | Claims Evaluator | Argues the merits — builds the case *for* the insured |
| **Morgan** | Policy Analyst | Cites the exact governing clauses (§7.3, §12.1 …) via RAG |
| **Alex** | Devil's Advocate | Fights to deny — so no weakness goes unexamined |
| **Sam** | Resolution Notary | Writes the final, signed, reasoned resolution |
| **Quinn** ◉ | Special Investigations Unit | **Not a standing panelist** — the Coordinator *recruits* Quinn into the live room (Band `add_participant`) **only when fraud or misrepresentation is alleged**, so a claim is never denied on unproven suspicion |

**Dynamic agent discovery** — Quinn is summoned mid-debate, on demand, not pre-wired into
every case. When no fraud is alleged the panel stays at five; when the denial rests on a
fraud/misrepresentation claim, the Coordinator pulls in the investigator to test it.

The entire conversation is persisted, ordered, and **SHA-256 hashed** — tamper-evident
on the record. A human claims officer then **approves or overrides** the resolution, and
the closed case is downloadable as a **signed Adjudication Record**.

## See it in action

| | |
|:---|:---|
| ![Dynamic recruitment](docs/shot-recruit.png)<br>**Dynamic recruitment** — the Coordinator pulls Quinn (SIU) into the live room, mid-debate, only when fraud is alleged | ![Signed verdict](docs/shot-verdict.png)<br>**Signed verdict** — APPROVED with cited clauses, the SIU finding, and the human officer's sign-off |
| ![Signed record](docs/shot-record.png)<br>**Signed record** — a printable, regulator-filable Adjudication Record | ![JSON export](docs/shot-json.png)<br>**JSON export** — the full transcript + SHA-256 hash, machine-verifiable |

Each case also carries **clickable evidence** (police / fire-marshal reports, scene photos) the
panel reasons over — so nothing is invented.

## The demo — three cases

Recruitment is *discriminating*: a clean dispute runs five agents; a fraud allegation pulls in the
sixth. Two cases are seeded **pending** so anyone can run a full debate end-to-end.

| Case | Claim | What happens |
|------|-------|--------------|
| **David Chen** | $12,000 collision, denied | *pending · run it live* — **5 agents**, no fraud → Quinn not recruited |
| **Lisa Park** | $4,200 theft, denied as undisclosed commercial use | *pending · run it live* — **6 agents**, fraud alleged → **Quinn recruited live** |
| **Marcus Reyes** | $9,300 fire, denied as a staged loss | *closed showcase* — pre-adjudicated, full 6-agent transcript, officer-signed |

## Architecture

![Architecture — one Band room, a streaming spine, a durable record](docs/architecture.png)

- **Frontend** — Next.js 14, TypeScript, Tailwind; neo-brutalist "Verdict" design.
- **Backend** — FastAPI, async SQLAlchemy, SSE; a Coordinator-driven turn engine.
- **RAG** — policy clauses embedded with `all-MiniLM-L6-v2` (384-dim), pgvector cosine search.
- **Agents** — a long-lived worker (`agents.run_agents`) keeps the 5 standing Band agents
  connected, plus Quinn on call (recruited into the room only when fraud is alleged).

## Local development

Postgres runs on host port **5433** locally (to avoid clashing with a native install).

### Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
docker compose up -d db                            # from repo root: Postgres 16 + pgvector (5433)
.venv\Scripts\python database/seed_data.py         # seeds the 3-case demo (2 pending + 1 closed w/ Quinn)
uvicorn main:app --reload                          # http://localhost:8000/api/health
```

### Agents (needed for a *live* debate)
```bash
cd backend && .venv\Scripts\python -m agents.run_agents
```

### Frontend
```bash
cd frontend
npm install
npm run dev                                        # http://localhost:3000
```

Copy `backend/.env.example` → `backend/.env` and fill in the Band / AI-ML / Featherless keys.

### Tests
```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -q     # 40 unit tests — fraud-recruitment gate, payout, SHA-256 hash, verdict parsing
```
The suite covers the logic that must be provably correct: `_alleges_fraud` (the SIU-recruitment
trigger), the deterministic payout, the tamper-evident transcript hash, and verdict parsing — all
pure functions, so it needs no database, Band connection, or network.

## Deployment

Production runs as a **Docker Compose stack on a VPS** (`db` · `backend` · `agents` ·
`frontend` · `caddy`), behind **OpenLiteSpeed** as the public reverse proxy with
Let's Encrypt TLS and a DuckDNS domain. The stack lives in [`deploy/`](deploy/):

```bash
cd deploy
cp .env.example .env        # fill in secrets
docker compose up -d --build
docker compose run --rm backend python database/seed_data.py   # seed the 3-case demo
```

> **Quinn is feature-flagged.** Set `BAND_QUINN_AGENT_ID` / `BAND_QUINN_API_KEY` /
> `BAND_QUINN_HANDLE` in `deploy/.env` to enable live recruitment of the 6th agent. Leave
> them blank and the panel runs as the standing five — zero risk, no code change.
>
> `DEPLOY.md` documents an alternative managed-PaaS path (Supabase / Railway / Vercel);
> the live deployment above uses the self-hosted Docker stack in `deploy/`.

## Build status

- [x] Scaffolding, database (schema, models, RAG over pgvector, seed)
- [x] Band SDK + Room Manager + Coordinator orchestration
- [x] The 5 standing agents (Coordinator + Blake, Morgan, Alex, Sam)
- [x] **Quinn (6th agent) — dynamically recruited mid-debate when fraud is alleged**
- [x] FastAPI backend + debate orchestrator + SSE
- [x] Frontend (dashboard, live debate room, resolution panel, signed-record download)
- [x] **Unit tests** — 40 passing: fraud-recruitment gate, payout math, SHA-256 audit hash, verdict parsing
- [x] **Deployed live** + demo video + pitch deck

## License

MIT
