"""Seed the demo data: David Chen / Crestview Mutual (the main case) + a control case.

Idempotent — re-runnable. Applies schema.sql, wipes existing rows, then inserts
the policy, its 6 clauses (with embeddings), the disputed claim, and a control claim.

Run from the backend/ directory:
    python database/seed_data.py
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Allow `python database/seed_data.py` from backend/ to resolve `config`, `database`, etc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from database.connection import AsyncSessionLocal, engine  # noqa: E402
from database.models import (  # noqa: E402
    AgentMessage,
    Claim,
    Policy,
    PolicyClause,
    Resolution,
)
from services.rag_service import embed_batch  # noqa: E402

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"

# --- David Chen policy clauses (the ones the agents debate) ---
CLAUSES: list[dict] = [
    {
        "clause_number": "§2.1",
        "clause_title": "Collision Coverage",
        "clause_type": "coverage",
        "clause_text": (
            "Collision coverage applies to direct physical damage to the insured "
            "vehicle resulting from contact with another vehicle, object, or road "
            "surface, up to the policy limit after deductible."
        ),
    },
    {
        "clause_number": "§5.2",
        "clause_title": "Comprehensive Coverage",
        "clause_type": "coverage",
        "clause_text": (
            "Comprehensive coverage applies to non-collision losses including theft, "
            "vandalism, fire, flood, and falling objects."
        ),
    },
    {
        "clause_number": "§7.3",
        "clause_title": "Mechanical Failure Exclusion",
        "clause_type": "exclusion",
        "clause_text": (
            "Mechanical failure, electrical failure, wear and tear, or gradual "
            "deterioration of any vehicle component is expressly excluded from both "
            "collision and comprehensive coverage, regardless of when such failure "
            "manifests."
        ),
    },
    {
        "clause_number": "§7.4",
        "clause_title": "General Exclusions",
        "clause_type": "exclusion",
        "clause_text": (
            "Intentional damage, racing, or use of the vehicle for commercial "
            "purposes not disclosed at policy inception are excluded."
        ),
    },
    {
        "clause_number": "§9.1",
        "clause_title": "Claim Filing Conditions",
        "clause_type": "condition",
        "clause_text": (
            "Insured must file a claim within 30 days of the loss event. Supporting "
            "documentation including police reports, photographs, and repair estimates "
            "must be submitted within 60 days."
        ),
    },
    {
        "clause_number": "§12.1",
        "clause_title": "Collision-Caused Mechanical Failure Exception",
        "clause_type": "exception",
        "clause_text": (
            "Notwithstanding §7.3, mechanical or electrical failure that is directly "
            "and proximately caused by a covered collision event — as evidenced by "
            "police report, independent adjuster assessment, or certified mechanic "
            "report — shall be considered eligible for coverage under §2.1."
        ),
    },
]

SUPPORTING_DOCS = [
    {
        "type": "police_report",
        "ref": "FHP-2024-10153",
        "url": "/docs/FHP-2024-10153.html",
        "summary": (
            "Collision with guardrail on I-95. Witness confirms vehicle was in motion "
            "when guardrail contact occurred. Engine failure documented post-impact."
        ),
    },
    {
        "type": "mechanic_report",
        "ref": "BM-AUTO-2024-089",
        "url": "/docs/BM-AUTO-2024-089.html",
        "summary": (
            "Engine seized due to catastrophic impact damage to oil pan and crankshaft. "
            "Failure consistent with high-force collision, not pre-existing mechanical issue."
        ),
    },
    {
        "type": "photos",
        "ref": "CLM-2024-04471-imgs",
        "url": "/docs/CLM-2024-04471-photos.html",
        "summary": (
            "4 photos showing front-end crushing consistent with 35mph guardrail impact."
        ),
    },
]


# --- David Chen: a CLOSED case, pre-adjudicated & officer-ratified ---------------
# Seeded with the full debate + signed resolution so a judge opening it sees a complete,
# tamper-evident verdict the instant the page loads (no 1-2 min live wait). Lisa Park stays
# PENDING (an "open" case) for a live run that also showcases dynamic SIU recruitment.
DAVID_ROOM_ID = "rm_dc_adjudicated_0001"

DAVID_RESOLUTION_TEXT = (
    "DECISION: APPROVED\n"
    "APPROVED AMOUNT: $12,000.00\n\n"
    "LEGAL REASONING:\n"
    "The claim is approved based on the exception in §12.1, which allows coverage of "
    "mechanical failures directly and proximately caused by a covered collision event. The "
    "certified mechanic report BM-AUTO-2024-089 and police report FHP-2024-10153 confirm the "
    "engine seizure resulted from collision impact, not a pre-existing issue — negating the "
    "application of §7.3 (Mechanical Failure Exclusion).\n\n"
    "DEBATE SUMMARY:\n"
    "- Blake: Coverage analysis was initially unclear (~60% confidence) given the potential "
    "applicability of §7.3.\n"
    "- Morgan: Asserted that §7.3 does not apply because the §12.1 exception controls, "
    "supporting coverage.\n"
    "- Alex: Argued the denial overlooked §12.1 and advocated for approval on the evidence.\n\n"
    "CONFIDENCE: HIGH\n"
    "RECOMMENDATION TO CLAIMS OFFICER: Approve the claim for $12,000.00 — the evidence and "
    "policy language support coverage under the collision clause."
)

# (slug, display_name, message_type, content) — ordered debate transcript.
DAVID_DEBATE: list[tuple[str, str, str, str]] = [
    (
        "coordinator", "Coordinator", "case_file",
        "CASE FILE — Claim CLM-2024-04471 (Policy CPP-2024-8821, David Chen, Crestview Mutual "
        "Insurance)\nIncident: collision on 2024-10-15 at I-95 North, near Fort Lauderdale, FL.\n"
        "Vehicle struck guardrail at ~35 mph; airbags deployed; front-end and engine compartment "
        "sustained severe damage; engine seized following impact. Police report FHP-2024-10153 "
        "documents the accident; a witness confirms the vehicle lost control on guardrail contact "
        "before the engine ceased operation.\nAmount requested: $12,500.00.\n"
        "ORIGINAL DENIAL: denied per §7.3 — Mechanical Failure Exclusion; adjuster alleges "
        "mechanical failure preceded the collision.\nSupporting documents: FHP-2024-10153 "
        "(police report), BM-AUTO-2024-089 (certified mechanic report), CLM-2024-04471-imgs "
        "(photos).\n\nThis denial is disputed. @Blake, begin your coverage analysis.",
    ),
    (
        "blake", "Blake", "message",
        "This is a covered collision under §2.1 — direct physical damage from contact with the "
        "guardrail. The denial rests entirely on §7.3, but the sequence matters: the engine "
        "seized FOLLOWING the impact, not before it. The mechanic report (BM-AUTO-2024-089) "
        "attributes the seizure to catastrophic impact damage to the oil pan and crankshaft — "
        "consistent with a high-force collision, not pre-existing wear. My confidence that "
        "coverage applies is moderate (~60%) pending the exact reading of §7.3 against any "
        "collision-caused-failure carve-out. Handing off to @Morgan for the controlling clauses.",
    ),
    (
        "morgan", "Morgan", "message",
        "§7.3 excludes mechanical or electrical failure. BUT §12.1 — the Collision-Caused "
        "Mechanical Failure Exception — states that, notwithstanding §7.3, mechanical failure "
        "directly and proximately caused by a covered collision event, as evidenced by police "
        "report, adjuster assessment, or certified mechanic report, SHALL be eligible under §2.1. "
        "Here both FHP-2024-10153 and BM-AUTO-2024-089 establish the seizure was collision-caused. "
        "§12.1 controls and restores coverage; the denial cited §7.3 in isolation and overlooked "
        "§12.1. @Alex, pressure-test this.",
    ),
    (
        "alex", "Alex", "message",
        "Wait — before we approve, the burden is on the evidence, and here it holds. The denial "
        "overlooked §12.1, the exception that decides this. The mechanic and police reports both "
        "confirm the seizure was caused by collision impact, not pre-existing wear — exactly the "
        "trigger §12.1 requires. The photos (CLM-2024-04471-imgs) show front-end crushing "
        "consistent with a 35 mph guardrail impact, corroborating the witness. Nothing in the file "
        "shows prior mechanical issues. The denial leaned on §7.3 alone and ignored the controlling "
        "exception. Approve under §12.1, less the deductible.",
    ),
    (
        "coordinator", "Coordinator", "message",
        "Debate complete. Compiling the full record and routing it to @Sam for the binding "
        "resolution. (Claim $12,500.00 · deductible $500.00 · payable in full $12,000.00.)",
    ),
    ("sam", "Sam", "resolution", DAVID_RESOLUTION_TEXT),
]


def _attach_completed_debate(claim: Claim) -> None:
    """Pre-populate a claim as a fully-adjudicated, officer-ratified (CLOSED) case: the ordered
    debate transcript, the SHA-256 tamper-evident hash over it, and the signed resolution. Lets a
    judge see a complete verdict instantly; the live debate path is untouched."""
    base = datetime(2025, 11, 3, 15, 35, 0, tzinfo=timezone.utc)
    messages = [
        AgentMessage(
            agent_slug=slug,
            agent_display_name=name,
            message_type=mtype,
            content=content,
            sent_at=base + timedelta(seconds=i * 8),
        )
        for i, (slug, name, mtype, content) in enumerate(DAVID_DEBATE)
    ]
    claim.messages = messages
    blob = "\n".join(f"{m.agent_slug}:{m.content}" for m in messages)
    sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    claim.resolution = Resolution(
        decision="APPROVED",
        approved_amount=Decimal("12000.00"),
        legal_reasoning=DAVID_RESOLUTION_TEXT,
        cited_clauses=["§7.3", "§12.1"],
        audit_trail={
            "room_id": DAVID_ROOM_ID,
            "transcript_sha256": sha,
            "message_count": len(messages),
            "hash_algorithm": "sha256",
        },
        approved_by="Kevin Soto (Claims Officer)",
        approved_at=base + timedelta(minutes=3),
    )


async def apply_schema() -> None:
    """Run schema.sql statement-by-statement (asyncpg can't batch-execute)."""
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    async with engine.begin() as conn:
        for stmt in statements:
            await conn.exec_driver_sql(stmt)
    print(f"  schema applied ({len(statements)} statements)")


async def wipe() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE resolutions, agent_messages, claims, "
                "policy_clauses, policies RESTART IDENTITY CASCADE"
            )
        )
    print("  existing data wiped")


async def seed() -> None:
    print("Embedding clauses (loads the model on first run, may take a moment)...")
    embeddings = embed_batch([c["clause_text"] for c in CLAUSES])
    print(f"  {len(embeddings)} embeddings generated ({len(embeddings[0])} dims)")

    async with AsyncSessionLocal() as session:
        # --- Main case: David Chen ---
        david_policy = Policy(
            policy_number="CPP-2024-8821",
            insured_name="David Chen",
            policy_type="Auto / Collision + Comprehensive",
            state="FL",
            effective_date=date(2024, 1, 1),
            expiration_date=date(2024, 12, 31),
            coverage_limit=Decimal("50000.00"),
            deductible=Decimal("500.00"),
            insurance_company="Crestview Mutual Insurance",
            coverage_details={"collision": True, "comprehensive": True},
        )
        david_policy.clauses = [
            PolicyClause(
                clause_number=c["clause_number"],
                clause_title=c["clause_title"],
                clause_text=c["clause_text"],
                clause_type=c["clause_type"],
                embedding=emb,
            )
            for c, emb in zip(CLAUSES, embeddings)
        ]
        david_claim = Claim(
            claim_number="CLM-2024-04471",
            incident_date=date(2024, 10, 15),
            incident_type="collision",
            location="I-95 North, near Fort Lauderdale, FL",
            amount_requested=Decimal("12500.00"),
            status="approved",  # CLOSED — already adjudicated & officer-ratified (instant view)
            band_room_id=DAVID_ROOM_ID,
            original_denial_reason=(
                "Claim denied per §7.3 — Mechanical Failure Exclusion. Adjuster "
                "assessment indicates mechanical failure preceded collision event."
            ),
            incident_description=(
                "Vehicle struck guardrail at approximately 35 mph. Airbags deployed. "
                "Front-end and engine compartment sustained severe damage. Engine "
                "seized following impact. Police report FHP-2024-10153 documents the "
                "accident. Witness statement from Marcus T. (FHP report page 2) confirms "
                "vehicle lost control upon guardrail contact before engine ceased operation."
            ),
            supporting_docs=SUPPORTING_DOCS,
        )
        _attach_completed_debate(david_claim)  # full transcript + signed resolution
        david_policy.claims = [david_claim]
        session.add(david_policy)

        # --- Second disputed case: Lisa Park (theft denied over an alleged commercial-use
        # exclusion — a different adversarial scenario judges can run end-to-end). ---
        lisa_policy = Policy(
            policy_number="CPP-2024-7741",
            insured_name="Lisa Park",
            policy_type="Auto / Collision + Comprehensive",
            state="FL",
            effective_date=date(2024, 1, 1),
            expiration_date=date(2024, 12, 31),
            coverage_limit=Decimal("50000.00"),
            deductible=Decimal("500.00"),
            insurance_company="Crestview Mutual Insurance",
            coverage_details={"collision": True, "comprehensive": True},
        )
        # Same policy clause set (reuse the embeddings) so Morgan's RAG search works for Lisa too.
        lisa_policy.clauses = [
            PolicyClause(
                clause_number=c["clause_number"],
                clause_title=c["clause_title"],
                clause_text=c["clause_text"],
                clause_type=c["clause_type"],
                embedding=emb,
            )
            for c, emb in zip(CLAUSES, embeddings)
        ]
        lisa_policy.claims = [
            Claim(
                claim_number="CLM-2024-03988",
                incident_date=date(2024, 9, 2),
                incident_type="theft",
                location="Miami, FL",
                amount_requested=Decimal("4200.00"),
                status="pending",
                original_denial_reason=(
                    "Claim denied per §7.4 — General Exclusions. Adjuster alleges the vehicle was "
                    "used for undisclosed commercial (rideshare) purposes, voiding comprehensive "
                    "coverage."
                ),
                incident_description=(
                    "Vehicle stereo and catalytic converter stolen overnight from the vehicle while "
                    "parked outside the insured's residence. Police report filed within 24 hours. "
                    "The insured disputes the commercial-use allegation, stating the vehicle is for "
                    "personal use only. Theft is a comprehensive-coverage event under §5.2."
                ),
                supporting_docs=[
                    {
                        "type": "police_report",
                        "ref": "MPD-2024-5567",
                        "summary": (
                            "Overnight theft of stereo and catalytic converter from a parked "
                            "vehicle outside the residence; reported within 24h; no indication of "
                            "commercial use."
                        ),
                    },
                    {
                        "type": "adjuster_note",
                        "ref": "ADJ-2024-3310",
                        "summary": (
                            "Denial cites suspected undisclosed rideshare use — but no rideshare "
                            "records, trip logs, or commercial markings are offered as evidence."
                        ),
                    },
                ],
            )
        ]
        session.add(lisa_policy)

        await session.commit()
        print(
            "  inserted: 2 policies, 12 clauses, "
            "1 CLOSED case (David Chen, approved+signed) + 1 OPEN case (Lisa Park, pending)"
        )


async def main() -> None:
    print("=== Recourse seed ===")
    await apply_schema()
    await wipe()
    await seed()
    await engine.dispose()
    print("Done. Demo data ready (David Chen CLM-2024-04471 + Lisa Park CLM-2024-03988).")


if __name__ == "__main__":
    asyncio.run(main())
