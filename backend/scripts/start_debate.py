"""Kick off a real Band debate for a seeded claim and stream the transcript to the console.

Prereq: the agents are running (python -m agents.run_agents) in another terminal.

    python scripts/start_debate.py                 # defaults to CLM-2024-04471 (David Chen)
    python scripts/start_debate.py CLM-2024-04471

This is a test harness for Step 4. The production flow (POST /api/claims + SSE) lands in Step 5.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Windows consoles default to cp1252; the transcript has §, em-dashes, and emoji.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from database.connection import AsyncSessionLocal, engine  # noqa: E402
from database.models import Claim  # noqa: E402
from rooms.message_listener import clean_mentions  # noqa: E402
from rooms.room_manager import RoomManager  # noqa: E402

POLL_SECONDS = 3
MAX_WAIT_SECONDS = 180


def build_case_brief(claim: Claim) -> str:
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


async def main(claim_number: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Claim)
            .options(selectinload(Claim.policy))
            .where(Claim.claim_number == claim_number)
        )
        claim = result.scalar_one_or_none()
        if claim is None:
            sys.exit(f"Claim {claim_number} not found. Run seed_data.py first.")
        brief = build_case_brief(claim)

    room = RoomManager()
    print(f"Creating adjudication room for {claim_number} ...")
    room_id = await room.create_room()
    await room.add_agents(room_id)
    opening_id = await room.post_initial_claim(room_id, brief)
    print(f"Room {room_id} created. Case file posted. Watch it live at app.band.ai\n")
    print("=" * 70)

    seen: set[str] = set()
    waited = 0
    while waited < MAX_WAIT_SECONDS:
        for msg in await room.get_transcript(room_id):
            if msg.id in seen:
                continue
            seen.add(msg.id)
            who = "📋 Case File" if msg.id == opening_id else msg.sender_name
            print(f"\n[{who}]\n{clean_mentions(msg.content)}")
            if msg.id != opening_id and "DECISION:" in msg.content.upper():
                print("\n" + "=" * 70 + "\n✅ Resolution reached.")
                await engine.dispose()
                return
        await asyncio.sleep(POLL_SECONDS)
        waited += POLL_SECONDS

    print(f"\n(stopped after {MAX_WAIT_SECONDS}s — {len(seen)} messages seen)")
    await engine.dispose()


if __name__ == "__main__":
    claim_no = sys.argv[1] if len(sys.argv) > 1 else "CLM-2024-04471"
    asyncio.run(main(claim_no))
