"""Mirror a Band room transcript into the local DB (the cached audit trail).

The SSE endpoint (Step 5) reads from agent_messages; this listener keeps that table in
sync with the live Band room by reconstructing the transcript (union of agent contexts,
via RoomManager.get_transcript) and inserting any messages not already cached.
"""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import AgentMessage
from rooms.room_manager import RoomManager

# Band sender id -> (slug, display name): the 4 adjudicators + the coordinator.
_AGENT_BY_ID = {
    cfg["agent_id"]: (slug, cfg["name"])
    for slug, cfg in settings.band_agents.items()
}
_coordinator = settings.coordinator
if _coordinator["agent_id"]:
    _AGENT_BY_ID[_coordinator["agent_id"]] = ("coordinator", _coordinator["name"])

# uuid -> @Name, to turn Band's `@[[uuid]]` mention encoding into readable handles.
_NAME_BY_ID = {aid: name for aid, (slug, name) in _AGENT_BY_ID.items()}
_MENTION_RE = re.compile(r"@\[\[([0-9a-fA-F-]+)\]\]")


def clean_mentions(content: str) -> str:
    """Replace `@[[uuid]]` tokens with `@Name` for a human-readable transcript."""
    return _MENTION_RE.sub(
        lambda m: "@" + _NAME_BY_ID.get(m.group(1), "agent"), content
    ).strip()


def sender_to_slug(sender_id: str, sender_name: str | None) -> tuple[str, str]:
    if sender_id in _AGENT_BY_ID:
        return _AGENT_BY_ID[sender_id]
    return "human_officer", sender_name or "Claims Officer"


async def persist_new_messages(
    session: AsyncSession,
    claim_id: uuid.UUID,
    room_id: str,
    room: RoomManager | None = None,
    opening_message_id: str | None = None,
) -> list[AgentMessage]:
    """Insert any transcript messages not already cached; return the new rows (oldest first).

    `opening_message_id` is the case-file message posted by the orchestrator (Sam) — it is
    rendered as the Claims Officer's intake, not as an agent turn.
    """
    room = room or RoomManager()

    existing = await session.execute(
        select(AgentMessage.band_message_id).where(AgentMessage.claim_id == claim_id)
    )
    seen = {row[0] for row in existing.all() if row[0]}

    transcript = await room.get_transcript(room_id)
    new_rows: list[AgentMessage] = []
    for msg in transcript:
        if msg.id in seen:
            continue
        if msg.id == opening_message_id:
            slug, display = "human_officer", "Claims Officer"
        else:
            slug, display = sender_to_slug(msg.sender_id, msg.sender_name)
        row = AgentMessage(
            claim_id=claim_id,
            band_message_id=msg.id,
            agent_slug=slug,
            agent_display_name=display,
            content=clean_mentions(msg.content),
            message_type=getattr(msg, "message_type", None) or "message",
            sent_at=getattr(msg, "inserted_at", None),
        )
        session.add(row)
        new_rows.append(row)

    if new_rows:
        await session.commit()
        for row in new_rows:
            await session.refresh(row)
    return new_rows


def is_resolution(message: AgentMessage) -> bool:
    """True once Sam has issued the final decision — signals the debate is done."""
    return message.agent_slug == "sam" and "DECISION:" in message.content.upper()
