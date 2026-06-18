"""Drives a Band adjudication room via the Agent API (works on the Pro plan).

The Human API is Enterprise-only, so the backend drives the room through the COORDINATOR
agent — a dedicated 5th identity — which creates the room, adds the 4 adjudicators, and posts
the opening case file that @mentions Blake. From there the adjudicators hand off to each other
directly via @mention (Blake→Morgan→Alex→Sam→Coordinator); the backend only re-nudges as a
safety net if a turn stalls.

Band's visibility rule: an agent only sees messages it sent or was @mentioned in. So the
full transcript (the audit trail) is reconstructed by unioning every agent's chat context,
deduped by message id and ordered by time.
"""
from __future__ import annotations

from datetime import datetime, timezone

from band.client.rest import (
    AsyncRestClient,
    ChatMessageRequest,
    ChatMessageRequestMentionsItem,
    ChatRoomRequest,
    ParticipantRequest,
)
from thenvoi_rest.core.api_error import ApiError

from config import settings

_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


class RoomManager:
    """Orchestrates one debate room using Band Agent API credentials."""

    def __init__(self) -> None:
        orchestrator = settings.orchestrator
        if not orchestrator["api_key"] or not orchestrator["agent_id"]:
            raise RuntimeError(
                "Missing Coordinator credentials. Set BAND_COORDINATOR_AGENT_ID / "
                "BAND_COORDINATOR_API_KEY in .env (create the agent in the Band dashboard)."
            )
        self.orchestrator = orchestrator
        # The Coordinator drives the room (create/add/post).
        self.client = AsyncRestClient(
            base_url=settings.band_rest_url, api_key=orchestrator["api_key"]
        )
        # One reader per identity (4 adjudicators + coordinator), for unioning chat
        # context into the full transcript.
        self._readers = {
            slug: AsyncRestClient(
                base_url=settings.band_rest_url, api_key=cfg["api_key"]
            )
            for slug, cfg in {**settings.band_agents, "coordinator": orchestrator}.items()
        }
        # Quinn (SIU) is recruited dynamically; add its reader so its reply is unioned into the
        # transcript. Only when configured (feature-flagged).
        if settings.quinn_enabled:
            self._readers["quinn"] = AsyncRestClient(
                base_url=settings.band_rest_url, api_key=settings.quinn["api_key"]
            )

    async def create_room(self, task_id: str | None = None) -> str:
        resp = await self.client.agent_api_chats.create_agent_chat(
            chat=ChatRoomRequest(task_id=task_id)
        )
        return resp.data.id

    async def add_agents(self, room_id: str) -> list[str]:
        """Add the 4 debating agents to the room (idempotent: 409 = already present)."""
        added: list[str] = []
        for slug, cfg in settings.band_agents.items():
            try:
                await self.client.agent_api_participants.add_agent_chat_participant(
                    room_id,
                    participant=ParticipantRequest(
                        participant_id=cfg["agent_id"], role="member"
                    ),
                )
            except ApiError as exc:
                if exc.status_code != 409:  # 409 = already a participant
                    raise
            added.append(slug)
        return added

    async def recruit_quinn(self, room_id: str) -> None:
        """Dynamically add the SIU investigator (Quinn) to an in-flight room (add_participant).

        This is Band dynamic agent discovery: a specialist is pulled into the live debate only
        when the case warrants it (a fraud/misrepresentation allegation), rather than every case
        carrying the standing panel. Idempotent (409 = already present)."""
        q = settings.quinn
        try:
            await self.client.agent_api_participants.add_agent_chat_participant(
                room_id,
                participant=ParticipantRequest(participant_id=q["agent_id"], role="member"),
            )
        except ApiError as exc:
            if exc.status_code != 409:
                raise

    async def post_message(self, room_id: str, content: str, mention_slug: str) -> str:
        """Post a message that @mentions one agent (by slug). Returns the message id."""
        agent = settings.band_agents.get(mention_slug)
        if agent is None and mention_slug == "quinn":
            agent = settings.quinn
        if agent is None:
            raise KeyError(f"Unknown mention slug: {mention_slug!r}")
        resp = await self.client.agent_api_messages.create_agent_chat_message(
            room_id,
            message=ChatMessageRequest(
                content=content,
                mentions=[
                    ChatMessageRequestMentionsItem(
                        id=agent["agent_id"], handle=agent["handle"], name=agent["name"]
                    )
                ],
            ),
        )
        return resp.data.id

    async def post_initial_claim(self, room_id: str, claim_brief: str) -> str:
        """Coordinator posts the case file and @mentions Blake to start the debate."""
        return await self.post_message(room_id, claim_brief, "blake")

    async def get_transcript(self, room_id: str) -> list:
        """Full ordered transcript = union of every identity's chat context.

        Returns ChatMessage-shaped objects (id, content, sender_id, sender_name,
        sender_type, message_type, inserted_at), oldest first.
        """
        by_id: dict[str, object] = {}
        for client in self._readers.values():
            try:
                ctx = await client.agent_api_context.get_agent_chat_context(
                    room_id, page_size=200
                )
            except Exception:
                continue  # a reader with nothing visible yet
            for item in ctx.data:
                by_id[item.id] = item
        messages = list(by_id.values())
        messages.sort(key=lambda m: getattr(m, "inserted_at", None) or _EPOCH)
        return messages

    async def list_participants(self, room_id: str) -> list:
        resp = await self.client.agent_api_participants.list_agent_chat_participants(
            room_id
        )
        return list(resp.data)
