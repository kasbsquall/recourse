"""Recourse FastAPI backend: claims, the Coordinator-driven debate, SSE streaming, approval."""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from config import settings
from database.connection import AsyncSessionLocal, get_session
from database.models import AgentMessage, Claim, Policy, Resolution
from schemas import (
    ApproveIn,
    ClaimDetailOut,
    ClaimOut,
    CreateClaimIn,
    MessageOut,
    OverrideIn,
    PolicyOut,
    ReviseIn,
)
from services.orchestrator import run_debate

logger = logging.getLogger("recourse.api")

app = FastAPI(title="Recourse API", version="1.0.0")
# Fail safe, not open: if CORS_ORIGINS is unset, default to localhost (dev) instead of "*".
# Set CORS_ORIGINS=https://your-frontend in the deploy environment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_TERMINAL = {"approved", "denied", "partial"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "recourse-api", "version": "1.0.0"}


@app.get("/api/policies", response_model=list[PolicyOut])
async def list_policies(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Policy).order_by(Policy.created_at))).scalars().all()
    return list(rows)


@app.get("/api/claims", response_model=list[ClaimOut])
async def list_claims(
    status: str | None = None, session: AsyncSession = Depends(get_session)
):
    stmt = select(Claim).options(selectinload(Claim.policy)).order_by(
        Claim.created_at.desc()
    )
    if status:
        stmt = stmt.where(Claim.status == status)
    claims = list((await session.execute(stmt)).scalars().all())
    for c in claims:  # surface insured name for the dashboard list
        c.insured_name = c.policy.insured_name if c.policy else None
    return claims


async def _load_claim_detail(session: AsyncSession, claim_id: uuid.UUID) -> Claim:
    result = await session.execute(
        select(Claim)
        .options(
            selectinload(Claim.policy),
            selectinload(Claim.messages),
            selectinload(Claim.resolution),
        )
        .where(Claim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@app.get("/api/claims/{claim_id}", response_model=ClaimDetailOut)
async def get_claim(claim_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    claim = await _load_claim_detail(session, claim_id)
    claim.messages.sort(key=lambda m: m.sent_at or claim.created_at)
    return claim


@app.post("/api/claims", response_model=ClaimOut, status_code=201)
async def create_claim(body: CreateClaimIn, session: AsyncSession = Depends(get_session)):
    policy = await session.get(Policy, body.policy_id)
    if policy is None:
        raise HTTPException(status_code=400, detail="Unknown policy_id")
    count = (await session.execute(select(func.count()).select_from(Claim))).scalar() or 0
    claim = Claim(
        claim_number=f"CLM-NEW-{count + 1:05d}",
        policy_id=body.policy_id,
        incident_date=body.incident_date,
        incident_type=body.incident_type,
        location=body.location,
        incident_description=body.incident_description,
        amount_requested=body.amount_requested,
        original_denial_reason=body.original_denial_reason,
        status="pending",
    )
    session.add(claim)
    await session.commit()
    await session.refresh(claim)
    return claim


@app.post("/api/claims/{claim_id}/adjudicate", response_model=ClaimOut)
async def adjudicate(claim_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Start (or restart) the multi-agent debate for a claim. Runs in the background."""
    claim = await session.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status == "in_review":
        # A debate is already running; a second one would race and duplicate the resolution.
        raise HTTPException(status_code=409, detail="Adjudication already in progress")
    # Clear any prior run so re-adjudication starts clean.
    await session.execute(delete(AgentMessage).where(AgentMessage.claim_id == claim_id))
    await session.execute(delete(Resolution).where(Resolution.claim_id == claim_id))
    claim.status = "in_review"
    await session.commit()
    await session.refresh(claim)

    asyncio.create_task(_run_debate_safe(claim_id))
    return claim


async def _run_debate_safe(claim_id: uuid.UUID) -> None:
    try:
        await run_debate(claim_id)
    except Exception:
        logger.exception("Debate failed for claim %s", claim_id)
        async with AsyncSessionLocal() as s:
            claim = await s.get(Claim, claim_id)
            if claim and claim.status == "in_review":
                claim.status = "pending"
                await s.commit()


@app.get("/api/claims/{claim_id}/stream")
async def stream_claim(claim_id: uuid.UUID):
    """SSE: emit each new debate message as it is persisted, until the claim resolves."""

    async def event_generator():
        seen: set[str] = set()
        idle = 0
        max_idle = 180  # tolerate a slow agent turn (free-tier retries) before closing
        while idle < max_idle:
            async with AsyncSessionLocal() as session:
                claim = await session.get(Claim, claim_id)
                if claim is None:
                    yield {"event": "error", "data": "claim not found"}
                    return
                rows = (
                    await session.execute(
                        select(AgentMessage)
                        .where(AgentMessage.claim_id == claim_id)
                        .order_by(AgentMessage.sent_at)
                    )
                ).scalars().all()
                new = [r for r in rows if str(r.id) not in seen]
                for r in new:
                    seen.add(str(r.id))
                    yield {
                        "event": "message",
                        "data": MessageOut.model_validate(r).model_dump_json(),
                    }
                if new:
                    idle = 0
                else:
                    idle += 2
                if claim.status in _TERMINAL and not new:
                    yield {"event": "done", "data": claim.status}
                    return
            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


@app.post("/api/claims/{claim_id}/approve", response_model=ClaimDetailOut)
async def approve(
    claim_id: uuid.UUID, body: ApproveIn, session: AsyncSession = Depends(get_session)
):
    from datetime import datetime, timezone

    claim = await _load_claim_detail(session, claim_id)
    if claim.resolution is None:
        raise HTTPException(status_code=409, detail="No resolution to approve yet")
    claim.resolution.approved_by = body.approved_by
    claim.resolution.approved_at = datetime.now(timezone.utc)
    await session.commit()
    return await _load_claim_detail(session, claim_id)


@app.post("/api/claims/{claim_id}/override", response_model=ClaimDetailOut)
async def override_decision(
    claim_id: uuid.UUID, body: OverrideIn, session: AsyncSession = Depends(get_session)
):
    """Human officer overrides the panel's recommendation and denies the claim. The panel's
    recommendation is preserved in the resolution; the override is recorded in the audit trail."""
    from datetime import datetime, timezone

    claim = await _load_claim_detail(session, claim_id)
    if claim.resolution is None:
        raise HTTPException(status_code=409, detail="No resolution to override yet")
    now = datetime.now(timezone.utc)
    claim.resolution.approved_by = body.officer
    claim.resolution.approved_at = now
    audit = dict(claim.resolution.audit_trail or {})
    audit["officer_override"] = {
        "action": "denied",
        "by": body.officer,
        "reason": body.reason,
        "at": now.isoformat(),
        "panel_decision": claim.resolution.decision,
        "panel_amount": (
            float(claim.resolution.approved_amount)
            if claim.resolution.approved_amount is not None
            else None
        ),
    }
    claim.resolution.audit_trail = audit
    claim.status = "denied"
    await session.commit()
    return await _load_claim_detail(session, claim_id)


@app.post("/api/claims/{claim_id}/revise", response_model=ClaimOut)
async def revise(
    claim_id: uuid.UUID, body: ReviseIn, session: AsyncSession = Depends(get_session)
):
    claim = await session.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    claim.status = "pending"
    await session.commit()
    await session.refresh(claim)
    return claim


@app.get("/api/claims/{claim_id}/audit")
async def export_audit(claim_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Export the full audit trail (claim + debate transcript + resolution) as JSON.

    Includes the claim financials so a downloaded record can show the deterministic payout math
    (payable = amount requested − deductible) without a second request.
    """
    from datetime import datetime, timezone

    claim = await _load_claim_detail(session, claim_id)
    claim.messages.sort(key=lambda m: m.sent_at or claim.created_at)
    policy = claim.policy
    deductible = float(policy.deductible) if policy and policy.deductible is not None else None
    requested = float(claim.amount_requested) if claim.amount_requested is not None else None
    return {
        "claim_number": claim.claim_number,
        "status": claim.status,
        "band_room_id": claim.band_room_id,
        "policy_number": policy.policy_number if policy else None,
        "insured_name": policy.insured_name if policy else None,
        "insurance_company": policy.insurance_company if policy else None,
        "incident_type": claim.incident_type,
        "incident_date": claim.incident_date.isoformat() if claim.incident_date else None,
        "location": claim.location,
        "amount_requested": requested,
        "deductible": deductible,
        "payable_if_covered": (
            max(requested - deductible, 0.0)
            if requested is not None and deductible is not None
            else None
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "transcript": [
            {
                "agent": m.agent_display_name,
                "slug": m.agent_slug,
                "type": m.message_type,
                "content": m.content,
                "at": m.sent_at.isoformat() if m.sent_at else None,
            }
            for m in claim.messages
        ],
        "resolution": (
            {
                "decision": claim.resolution.decision,
                "approved_amount": (
                    float(claim.resolution.approved_amount)
                    if claim.resolution.approved_amount is not None
                    else None
                ),
                "cited_clauses": claim.resolution.cited_clauses,
                "legal_reasoning": claim.resolution.legal_reasoning,
                "audit_trail": claim.resolution.audit_trail,
                "approved_by": claim.resolution.approved_by,
                "approved_at": (
                    claim.resolution.approved_at.isoformat()
                    if claim.resolution.approved_at
                    else None
                ),
            }
            if claim.resolution
            else None
        ),
    }
