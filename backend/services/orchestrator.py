"""Coordinator-driven debate orchestrator — the heart of Recourse.

Band agents only see messages they sent or were @mentioned in, so the @mention chain doesn't
carry the full thread forward. This orchestrator (acting as the Coordinator) instead DRIVES
each turn and PASSES ACCUMULATED CONTEXT to every agent, with per-turn retries for the flaky
free-tier turns. It persists each agent reply to agent_messages so the SSE endpoint can stream
it, and extracts Sam's structured resolution into the resolutions table.

    Case File → @Blake → @Morgan(+Blake) → @Alex(+Blake,Morgan) → @Sam(+full debate) → resolution
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import uuid
from decimal import Decimal, InvalidOperation

logger = logging.getLogger("recourse.orchestrator")

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import settings
from database.connection import AsyncSessionLocal
from database.models import AgentMessage, Claim, Resolution
from rooms.message_listener import clean_mentions
from rooms.room_manager import RoomManager

# (slug, display name, instruction for that turn)
TURNS: list[tuple[str, str, str]] = [
    ("blake", "Blake", "begin your coverage analysis"),
    ("morgan", "Morgan", "quote the exact policy clauses that apply and whether they support or challenge the verdict"),
    ("alex", "Alex", "challenge the denial from the insured's perspective — find exceptions, ambiguities, or bad-faith indicators"),
    ("sam", "Sam", "weigh the full debate and issue the final structured resolution"),
]

# Per-turn wait tuning. Agents hand off to each other directly via @mention (primary
# trigger); the backend only re-nudges as a safety net if a turn stalls.
_POLL_SECONDS = 3
# Window must exceed the agents' idle_resync (12s) so a missed-WS handoff self-recovers before
# the backend gives up. Fast turns still return early (the poll loop exits as soon as a reply
# appears), so this only extends patience for stalled turns.
_DEFAULT_WINDOW = 40
_MAX_RETRIES = 1         # one safety-net re-nudge, then move on
# _prewarm_featherless() still fires at case open to reduce the chance Alex is cold; if it
# stalls anyway, _run_alex_turn fails over to the reliable provider.


async def _prewarm_featherless() -> None:
    """Wake Featherless' serverless model at case open so Alex's turn doesn't hit a cold start.

    Fire-and-forget: warms during Blake's and Morgan's turns (~40-90s) so the model is hot by
    the time Alex is @mentioned. Best effort — any failure is swallowed; the longer Alex window
    and safety-net re-nudge still cover a cold start.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(
                f"{settings.featherless_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.featherless_api_key}"},
                json={
                    "model": settings.featherless_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
    except Exception:
        pass


def build_case_brief(claim: Claim) -> str:
    """Render the opening case file from a claim + its policy."""
    policy = claim.policy
    docs = "\n".join(
        f"  - [{d.get('type')}] {d.get('ref')}: {d.get('summary')}"
        for d in (claim.supporting_docs or [])
    )
    return (
        f"CASE FILE — Claim {claim.claim_number} (Policy {policy.policy_number}, "
        f"{policy.insured_name}, {policy.insurance_company})\n"
        f"Incident: {claim.incident_type} on {claim.incident_date} at {claim.location}.\n"
        f"{claim.incident_description}\n"
        f"Amount requested: ${claim.amount_requested:,.2f}.\n"
        f"ORIGINAL DENIAL: {claim.original_denial_reason}\n"
        f"Supporting documents:\n{docs}\n\n"
        f"This denial is disputed. @Blake, begin your coverage analysis."
    )


def _build_nudge(name: str, context: list[tuple[str, str]], instruction: str) -> str:
    """Assemble accumulated debate + the turn instruction for the next agent."""
    thread = "\n\n".join(f"[{who}]:\n{text}" for who, text in context)
    return (
        f"@{name} — Adjudication in progress. Here is the debate so far:\n\n"
        f"{thread}\n\n"
        f"{name}, {instruction}."
    )


async def _persist(
    session, claim_id: uuid.UUID, band_id: str, slug: str, name: str,
    content: str, message_type: str,
) -> None:
    session.add(AgentMessage(
        claim_id=claim_id, band_message_id=band_id, agent_slug=slug,
        agent_display_name=name, content=content, message_type=message_type,
    ))
    await session.commit()


async def _await_agent_reply(
    room: RoomManager,
    room_id: str,
    slug: str,
    name: str,
    instruction: str,
    seen: set[str],
    context: list[tuple[str, str]],
    window: int = _DEFAULT_WINDOW,
) -> object | None:
    """Wait for `slug` to post (triggered by the prior agent's @mention).

    On timeout the backend steps in as a safety net and re-nudges with the accumulated
    context so the debate recovers instead of stalling. None if it never replies.
    """
    for attempt in range(_MAX_RETRIES + 1):
        waited = 0
        while waited < window:
            for msg in await room.get_transcript(room_id):
                if msg.id in seen:
                    continue
                s, _ = _sender_slug(msg.sender_id, msg.sender_name)
                if s == slug:
                    return msg
            await asyncio.sleep(_POLL_SECONDS)
            waited += _POLL_SECONDS
        if attempt < _MAX_RETRIES:
            await room.post_message(room_id, _build_nudge(name, context, instruction), slug)
    return None


def _sender_slug(sender_id: str, sender_name: str | None) -> tuple[str, str]:
    from rooms.message_listener import sender_to_slug
    return sender_to_slug(sender_id, sender_name)


# Sam's structured resolution parsing.
_DECISION_RE = re.compile(r"DECISION:\s*\**\s*(APPROVED|DENIED|PARTIAL)", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"APPROVED AMOUNT:\s*\**\s*\$?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_CLAUSE_RE = re.compile(r"§\s?(\d+\.\d+)")


def _parse_resolution(text: str) -> dict:
    decision = (m.group(1).upper() if (m := _DECISION_RE.search(text)) else "UNCLEAR")
    amount = None
    if (m := _AMOUNT_RE.search(text)):
        try:
            amount = Decimal(m.group(1).replace(",", ""))
        except InvalidOperation:
            amount = None
    clauses = sorted({f"§{c}" for c in _CLAUSE_RE.findall(text)})
    return {"decision": decision, "approved_amount": amount, "cited_clauses": clauses}


async def run_debate(claim_id: uuid.UUID) -> None:
    """Drive the full adjudication for a claim. Runs as a background task."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Claim).options(selectinload(Claim.policy)).where(Claim.id == claim_id)
        )
        claim = result.scalar_one()

        room = RoomManager()
        room_id = await room.create_room()
        await room.add_agents(room_id)
        claim.band_room_id = room_id
        claim.status = "in_review"
        await session.commit()

        # Warm Featherless now so Alex's turn (a minute or two out) doesn't pay a cold start.
        asyncio.create_task(_prewarm_featherless())

        brief = build_case_brief(claim)
        opening_id = await room.post_initial_claim(room_id, brief)
        # The Coordinator (5th agent) opens the case by posting the case file and @mentioning Blake.
        await _persist(session, claim_id, opening_id, "coordinator", "Coordinator", brief, "case_file")

        context: list[tuple[str, str]] = [("Case File", brief)]
        seen: set[str] = {opening_id}

        # Blake is triggered by the case file's @mention; Morgan by Blake's. The backend only
        # re-nudges on timeout. Alex (flaky Featherless) and Sam (the final ruling) get dedicated
        # handling — Alex with a failover, Sam with full context and a parseable-resolution check.
        for slug, name, instruction in TURNS[:2]:  # Blake, Morgan
            msg = await _await_agent_reply(
                room, room_id, slug, name, instruction, seen, context, _DEFAULT_WINDOW
            )
            if msg is None:
                await _persist(
                    session, claim_id, f"missing-{slug}-{room_id}", slug, name,
                    f"({name} did not respond after retries.)", "error",
                )
                continue
            seen.add(msg.id)
            content = clean_mentions(msg.content)
            await _persist(session, claim_id, msg.id, slug, name, content, "message")
            context.append((name, content))

        await _run_alex_turn(session, claim_id, room, room_id, seen, context)
        final_text = await _run_sam_turn(session, claim, room, room_id, seen, context)
        await _finalize(session, claim, final_text)


_ALEX_INSTRUCTION = TURNS[2][2]


def _is_agent_error(content: str) -> bool:
    """A Band/adapter platform error posted in place of a real reply (e.g. the LLM call threw)."""
    c = (content or "").lower()
    return "internal error" in c or "see agent logs" in c


async def _run_alex_turn(
    session, claim_id: uuid.UUID, room: RoomManager, room_id: str,
    seen: set[str], context: list[tuple[str, str]],
) -> None:
    """Alex runs on Featherless' free tier and can stall. Give it a fair window (with one
    re-nudge); if it still hasn't posted, fail over to the reliable provider so the debate never
    dead-airs. Alex remains a Featherless agent — this is a backend resilience layer for the SLA.
    """
    msg = await _poll_for_reply(room, room_id, "alex", seen, 30)
    if msg is not None and _is_agent_error(msg.content):
        seen.add(msg.id)  # platform error posted as a "reply" — treat as no reply, fail over
        msg = None
    if msg is None:
        await room.post_message(room_id, _build_nudge("Alex", context, _ALEX_INSTRUCTION), "alex")
        msg = await _poll_for_reply(room, room_id, "alex", seen, 35)
        if msg is not None and _is_agent_error(msg.content):
            seen.add(msg.id)
            msg = None

    if msg is not None:
        seen.add(msg.id)
        content = clean_mentions(msg.content)
        await _persist(session, claim_id, msg.id, "alex", "Alex", content, "message")
        context.append(("Alex", content))
        return

    # Failover: Featherless stalled — synthesize Alex's challenge on the reliable provider.
    content = await _generate_alex_failover(context)
    await _persist(session, claim_id, f"alex-failover-{room_id}", "alex", "Alex", content, "message")
    context.append(("Alex", content))


async def _generate_alex_failover(context: list[tuple[str, str]]) -> str:
    """Generate Alex's devil's-advocate turn on the reliable provider when Featherless stalls."""
    from agents.base_agent import build_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    system = (
        "You are Alex, the Devil's Advocate on an insurance adjudication panel — combative and "
        "insured-first. Challenge the denial: surface exceptions to exclusions (especially "
        "collision-caused-failure carve-outs), ambiguities to read in the insured's favour, and "
        "inconsistencies between the denial and the evidence. Reference the specific documents "
        "(police report, mechanic report) and clause numbers already raised in the debate. "
        "Start with 'Wait.' Keep it under 180 words. Plain prose, no preamble."
    )
    thread = "\n\n".join(f"[{who}]:\n{text}" for who, text in context)
    try:
        llm = build_llm("aimlapi")
        resp = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=f"The debate so far:\n\n{thread}\n\nWrite Alex's challenge now."),
        ])
        text = (resp.content or "").strip()
        if text:
            return text
    except Exception:
        logger.warning("Alex failover (aimlapi) also failed; using a neutral placeholder")
    # Neutral fallback — never fabricate specific clause numbers/evidence, since this turn may
    # belong to ANY claim (not just the seeded collision case). Keeps the audit trail honest.
    return (
        "Wait — this denial deserves scrutiny. Weigh whether any coverage clause or exception "
        "raised in the debate applies to this loss, and whether the supporting evidence "
        "contradicts the stated grounds, before the claim is dismissed on the exclusion alone."
    )


async def _poll_for_reply(
    room: RoomManager, room_id: str, slug: str, seen: set[str], window: int,
) -> object | None:
    """Poll the transcript for the next unseen message from `slug`. No nudging — the caller
    owns when/what to (re)post. None if nothing arrives within `window` seconds."""
    waited = 0
    while waited < window:
        for msg in await room.get_transcript(room_id):
            if msg.id in seen:
                continue
            s, _ = _sender_slug(msg.sender_id, msg.sender_name)
            if s == slug:
                return msg
        await asyncio.sleep(_POLL_SECONDS)
        waited += _POLL_SECONDS
    return None


async def _run_sam_turn(
    session, claim: Claim, room: RoomManager, room_id: str,
    seen: set[str], context: list[tuple[str, str]],
) -> str:
    """Coordinator compiles the full record (with the claim financials) and routes it to Sam.

    Band only shows an agent the messages it was @mentioned in, so Sam must receive the ENTIRE
    debate AND the dollar figures in this one routing message — otherwise it rules blind and
    invents an amount / misreads the panel. We send the full record to Band (Sam's input) but
    persist a concise Coordinator routing note for the UI and audit log.

    Sam (gpt-4o) occasionally acknowledges instead of ruling; if the first reply isn't a real
    DECISION we re-nudge once, strictly. Whatever Sam returns last is recorded so the UI never
    stalls.
    """
    amount = claim.amount_requested
    deductible = claim.policy.deductible if claim.policy else Decimal("0")
    payable = max(amount - deductible, Decimal("0"))
    thread = "\n\n".join(f"[{who}]:\n{text}" for who, text in context)

    routed_to_sam = (
        f"@Sam — the panel has finished. As Coordinator I am routing the complete record to you "
        f"for the binding resolution.\n\n"
        f"CLAIM FINANCIALS: amount requested ${amount:,.2f}; policy deductible ${deductible:,.2f}. "
        f"If coverage applies in full, the payable amount is ${payable:,.2f} (requested − deductible).\n\n"
        f"FULL DEBATE RECORD:\n{thread}\n\n"
        f"Issue the final structured resolution now. Base the APPROVED AMOUNT on the figures "
        f"above. Summarize each panelist's ACTUAL position faithfully — do not flip or invent it."
    )
    display = (
        f"Debate complete. Compiling the full record and routing it to @Sam for the binding "
        f"resolution. (Claim ${amount:,.2f} · deductible ${deductible:,.2f} · "
        f"payable in full ${payable:,.2f}.)"
    )
    cid = await room.post_message(room_id, routed_to_sam, "sam")
    seen.add(cid)
    await _persist(session, claim.id, cid, "coordinator", "Coordinator", display, "message")

    strict = _build_nudge(
        "Sam", context,
        "output ONLY the final resolution NOW, beginning with 'DECISION:' and following the exact "
        "structured format — do not acknowledge or say you will review; rule now using the "
        "financials and debate already provided",
    )
    last = ""
    for attempt in range(2):
        msg = await _poll_for_reply(room, room_id, "sam", seen, _DEFAULT_WINDOW)
        if msg is not None:
            seen.add(msg.id)
            content = clean_mentions(msg.content)
            if _parse_resolution(content)["decision"] != "UNCLEAR":
                await _persist(session, claim.id, msg.id, "sam", "Sam", content, "resolution")
                return content
            last = content  # acknowledgment / non-ruling — try the strict re-nudge
        if attempt == 0:
            await room.post_message(room_id, strict, "sam")

    if last:
        await _persist(session, claim.id, f"sam-final-{room_id}", "sam", "Sam", last, "resolution")
        return last
    await _persist(
        session, claim.id, f"missing-sam-{room_id}", "sam", "Sam",
        "(Sam did not respond after retries.)", "error",
    )
    return ""


async def _finalize(session, claim: Claim, resolution_text: str) -> None:
    """Create the Resolution row from Sam's output and set the claim status."""
    if not resolution_text:
        claim.status = "denied"  # debate stalled with no resolution
        await session.commit()
        return

    parsed = _parse_resolution(resolution_text)
    status_map = {"APPROVED": "approved", "DENIED": "denied", "PARTIAL": "partial"}
    # Default to a terminal status (never "in_review") so the SSE stream closes and the UI
    # stops spinning even if Sam's text couldn't be parsed into a clear decision.
    claim.status = status_map.get(parsed["decision"], "denied")

    # Tamper-evident audit hash: sha256 over the ordered transcript. Any later edit to the
    # debate record changes the hash, so the resolution carries a verifiable fingerprint.
    rows = (await session.execute(
        select(AgentMessage)
        .where(AgentMessage.claim_id == claim.id)
        .order_by(AgentMessage.sent_at)
    )).scalars().all()
    transcript_blob = "\n".join(f"{m.agent_slug}:{m.content}" for m in rows)
    transcript_sha256 = hashlib.sha256(transcript_blob.encode("utf-8")).hexdigest()

    session.add(Resolution(
        claim_id=claim.id,
        decision=parsed["decision"],
        approved_amount=parsed["approved_amount"],
        legal_reasoning=resolution_text,
        cited_clauses=parsed["cited_clauses"],
        audit_trail={
            "room_id": claim.band_room_id,
            "transcript_sha256": transcript_sha256,
            "message_count": len(rows),
            "hash_algorithm": "sha256",
        },
    ))
    await session.commit()
