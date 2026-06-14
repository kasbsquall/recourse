"""Seed the demo data: David Chen / Crestview Mutual (the main case) + a control case.

Idempotent — re-runnable. Applies schema.sql, wipes existing rows, then inserts
the policy, its 6 clauses (with embeddings), the disputed claim, and a control claim.

Run from the backend/ directory:
    python database/seed_data.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Allow `python database/seed_data.py` from backend/ to resolve `config`, `database`, etc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from database.connection import AsyncSessionLocal, engine  # noqa: E402
from database.models import Claim, Policy, PolicyClause  # noqa: E402
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
        david_policy.claims = [
            Claim(
                claim_number="CLM-2024-04471",
                incident_date=date(2024, 10, 15),
                incident_type="collision",
                location="I-95 North, near Fort Lauderdale, FL",
                amount_requested=Decimal("12500.00"),
                status="pending",
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
        ]
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
        print("  inserted: 2 policies, 12 clauses, 2 pending claims")


async def main() -> None:
    print("=== Recourse seed ===")
    await apply_schema()
    await wipe()
    await seed()
    await engine.dispose()
    print("Done. Demo data ready (David Chen CLM-2024-04471 + Lisa Park CLM-2024-03988).")


if __name__ == "__main__":
    asyncio.run(main())
