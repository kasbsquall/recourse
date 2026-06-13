"""Drain each agent's unprocessed message backlog across all its Band chats.

Failed/partial test debates leave messages in pending/processing state that mention the
agents. On restart the agents try to chew through all of it, starving fresh debates. This
marks that backlog processed so the agents start clean.

    python scripts/drain_backlog.py

Not needed in normal operation (completed debates leave no backlog) — it's a test-hygiene tool.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from band.client.rest import AsyncRestClient  # noqa: E402

from config import settings  # noqa: E402


async def drain_agent(slug: str, cfg: dict) -> int:
    client = AsyncRestClient(base_url=settings.band_rest_url, api_key=cfg["api_key"])
    chats = await client.agent_api_chats.list_agent_chats()
    drained = 0
    for chat in chats.data:
        for status in ("pending", "processing"):
            try:
                msgs = await client.agent_api_messages.list_agent_messages(
                    chat.id, status=status, page_size=200
                )
            except Exception:
                continue
            for msg in msgs.data:
                try:
                    await client.agent_api_messages.mark_agent_message_processed(
                        chat.id, msg.id
                    )
                    drained += 1
                except Exception:
                    pass
    print(f"  {slug}: drained {drained} backlog message(s) across {len(chats.data)} chats")
    return drained


async def main() -> None:
    print("Draining agent backlogs ...")
    total = 0
    for slug, cfg in settings.band_agents.items():
        total += await drain_agent(slug, cfg)
    print(f"Done. {total} message(s) marked processed.")


if __name__ == "__main__":
    asyncio.run(main())
