"""Coordinator-driven debate orchestrator — the heart of Recourse.

Band agents only see messages they sent or were @mentioned in, so the @mention chain doesn't
carry the full thread forward. This orchestrator (acting as the Coordinator) instead DRIVES
each turn and PASSES ACCUMULATED CONTEXT to every agent, with per-turn retries for the flaky
free-tier turns. It persists each agent reply to agent_messages so the SSE endpoint can stream
it, and extracts Sam's structured resolution into the resolutions table.

    Case File → @Blake → @Morgan(+Blake) → @Alex(+Blake,Morgan) → @Sam(+full debate) → resolution
"""
from __future__ import annotations

import hashlib
import re
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import selectinload

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
_WINDOW_SECONDS = 40
_MAX_RETRIES = 1         # one safety-net re-nudge, then move on


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
        f"This denial is disputed. Blake, begin your coverage analysis."
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
) -> object | None:
    """Wait for `slug` to post (triggered by the prior agent's @mention).

    On timeout the backend steps in as a safety net and re-nudges with the accumulated
    context so the debate recovers instead of stalling. None if it never replies.
    """
    import asyncio

    for attempt in range(_MAX_RETRIES + 1):
        waited = 0
        while waited < _WINDOW_SECONDS:
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

        brief = build_case_brief(claim)
        opening_id = await room.post_initial_claim(room_id, brief)
        # The Coordinator (5th agent) opens the case by posting the case file and @mentioning Blake.
        await _persist(session, claim_id, opening_id, "coordinator", "Coordinator", brief, "case_file")

        context: list[tuple[str, str]] = [("Case File", brief)]
        seen: set[str] = {opening_id}
        final_text = ""

        for slug, name, instruction in TURNS:
            # Blake is triggered by the case file's @mention; each later agent is triggered
            # by the previous agent's @mention. The backend only re-nudges on timeout.
            msg = await _await_agent_reply(
                room, room_id, slug, name, instruction, seen, context
            )
            if msg is None:
                await _persist(
                    session, claim_id, f"missing-{slug}-{room_id}", slug, name,
                    f"({name} did not respond after retries.)", "error",
                )
                continue
            seen.add(msg.id)
            content = clean_mentions(msg.content)
            mtype = "resolution" if slug == "sam" else "message"
            await _persist(session, claim_id, msg.id, slug, name, content, mtype)
            context.append((name, content))
            if slug == "sam":
                final_text = content

        await _finalize(session, claim, final_text)


async def _finalize(session, claim: Claim, resolution_text: str) -> None:
    """Create the Resolution row from Sam's output and set the claim status."""
    if not resolution_text:
        claim.status = "denied"  # debate stalled with no resolution
        await session.commit()
        return

    parsed = _parse_resolution(resolution_text)
    status_map = {"APPROVED": "approved", "DENIED": "denied", "PARTIAL": "partial"}
    claim.status = status_map.get(parsed["decision"], "in_review")

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
