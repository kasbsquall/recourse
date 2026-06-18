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
        "images": [
            {"src": "/docs/crash-1.jpg", "caption": "Front-end crush — driver side quarter"},
            {"src": "/docs/crash-2.jpg", "caption": "Engine compartment — impact damage to oil pan"},
            {"src": "/docs/crash-3.jpg", "caption": "Guardrail contact point — I-95 MM26"},
            {"src": "/docs/crash-4.jpg", "caption": "Deployed airbags — cabin"},
        ],
        "summary": (
            "4 photos showing front-end crushing consistent with 35mph guardrail impact."
        ),
    },
]


# --- The CLOSED showcase case: Marcus Reyes (fire claim, denied over a suspected staged loss) ---
# This is the pre-adjudicated, officer-ratified case a judge sees the INSTANT the page loads —
# and it deliberately runs the FULL six-agent flow INCLUDING the dynamic SIU recruitment: a
# misrepresentation/"staged loss" allegation pulls @Quinn (Special Investigations Unit) into the
# room, who finds the allegation unsubstantiated. David Chen and Lisa Park stay PENDING (open) so
# judges can run a debate live (Lisa's "undisclosed commercial use" denial recruits Quinn live).
MARCUS_ROOM_ID = "rm_mr_adjudicated_0007"

MARCUS_RESOLUTION_TEXT = (
    "DECISION: APPROVED\n"
    "APPROVED AMOUNT: $9,300.00\n\n"
    "LEGAL REASONING:\n"
    "The vehicle fire is a covered comprehensive loss under §5.2. The denial relied on the §7.4 "
    "exclusion for intentional damage, alleging a staged/misrepresented loss — but that exclusion "
    "requires evidence of intent, and the Special Investigations Unit found none. The fire marshal "
    "report FMO-2024-0832 attributes the fire to an electrical fault in the wiring harness, with no "
    "accelerants detected and no signs of forced entry. The misrepresentation allegation is "
    "unsubstantiated, so §7.4 does not apply and coverage stands under §5.2.\n\n"
    "DEBATE SUMMARY:\n"
    "- Blake: Treated the fire as a covered §5.2 comprehensive loss; flagged the denial as "
    "resting on suspicion rather than evidence (~60% confidence pending SIU review).\n"
    "- Morgan: Confirmed §5.2 covers fire and that §7.4 excludes only proven intentional damage.\n"
    "- Alex: Argued the denial inverted the burden of proof onto the insured.\n"
    "- Quinn: Investigated the misrepresentation allegation and found it unsubstantiated — "
    "electrical origin, no accelerants, no motive — so it cannot defeat coverage.\n\n"
    "CONFIDENCE: HIGH\n"
    "RECOMMENDATION TO CLAIMS OFFICER: Approve the claim for $9,300.00 — a covered fire loss with "
    "no substantiated evidence of misrepresentation."
)

# (slug, display_name, message_type, content) — ordered debate transcript, INCLUDING Quinn (SIU).
MARCUS_DEBATE: list[tuple[str, str, str, str]] = [
    (
        "coordinator", "Coordinator", "case_file",
        "CASE FILE — Claim CLM-2024-05120 (Policy CPP-2024-6610, Marcus Reyes, Crestview Mutual "
        "Insurance)\nIncident: vehicle fire on 2024-08-22 in Tampa, FL.\nThe parked vehicle caught "
        "fire overnight and was a total loss. Fire marshal report FMO-2024-0832 documents the "
        "scene.\nAmount requested: $9,800.00.\n"
        "ORIGINAL DENIAL: denied per §7.4 — General Exclusions; adjuster alleges a possible "
        "staged/intentional loss (misrepresentation), citing that the claim was filed shortly "
        "after a routine coverage update.\nSupporting documents: FMO-2024-0832 (fire marshal "
        "report — electrical origin, no accelerants), CLM-2024-05120-imgs (scene photos).\n\n"
        "This denial is disputed. @Blake, begin your coverage analysis.",
    ),
    (
        "blake", "Blake", "message",
        "A vehicle fire is a covered comprehensive loss under §5.2 — fire is named explicitly. The "
        "denial doesn't dispute that; it rests on §7.4 (intentional damage) via a *suspicion* of a "
        "staged loss. But the fire marshal report (FMO-2024-0832) puts the origin as electrical, "
        "with no accelerants — that points to an accidental loss, not arson. My confidence is "
        "moderate (~60%) until the misrepresentation allegation is actually examined. @Morgan, the "
        "controlling clauses.",
    ),
    (
        "morgan", "Morgan", "message",
        "§5.2 (Comprehensive Coverage) expressly covers fire. §7.4 (General Exclusions) excludes "
        "*intentional* damage — but an exclusion the insurer invokes must be proven by the insurer; "
        "the burden does not shift to the insured. Nothing quoted establishes intent. The timing of "
        "a routine coverage update is not evidence of misrepresentation. On the policy language "
        "alone, §5.2 controls unless §7.4 intent is substantiated. @Alex, pressure-test this.",
    ),
    (
        "alex", "Alex", "message",
        "Wait — this denial inverts the burden of proof. The insurer alleges a staged loss but "
        "offers no accelerant, no motive, no forced entry — only the timing of a paperwork update. "
        "The fire marshal already attributed the fire to an electrical fault. You don't get to "
        "deny a covered fire on a hunch. If there's a fraud theory, it has to be investigated and "
        "evidenced — not assumed. Returning the floor to @Coordinator.",
    ),
    (
        "coordinator", "Coordinator", "message",
        "An allegation of a **staged/misrepresented loss** is in play and turns on evidence, not "
        "argument. **Recruiting** @Quinn (Special Investigations Unit) into the room to examine "
        "whether the allegation is substantiated before the panel rules.",
    ),
    (
        "quinn", "Quinn", "message",
        "I examined the staged-loss allegation against what is actually in the file, and it does not "
        "hold up. The fire marshal report FMO-2024-0832 attributes the fire to an electrical fault "
        "in the wiring harness — no accelerants, no forced entry, no signs of tampering. There are "
        "no motive or financial-distress indicators on record, and no prior similar claims. The "
        "allegation rests entirely on the timing of a routine coverage update, which is "
        "circumstantial, not evidence. Because §7.4 requires proven intent and there is none, it "
        "cannot apply — the fire remains a covered loss under §5.2. Returning the floor to "
        "@Coordinator.",
    ),
    (
        "coordinator", "Coordinator", "message",
        "Investigation complete. Compiling the full record and routing it to @Sam for the binding "
        "resolution. (Claim $9,800.00 · deductible $500.00 · payable in full **$9,300.00**.)",
    ),
    ("sam", "Sam", "resolution", MARCUS_RESOLUTION_TEXT),
]


def _attach_completed_debate(
    claim: Claim,
    debate: list[tuple[str, str, str, str]],
    resolution_text: str,
    *,
    decision: str,
    amount: Decimal,
    clauses: list[str],
    room_id: str,
) -> None:
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
        for i, (slug, name, mtype, content) in enumerate(debate)
    ]
    claim.messages = messages
    blob = "\n".join(f"{m.agent_slug}:{m.content}" for m in messages)
    sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    claim.resolution = Resolution(
        decision=decision,
        approved_amount=amount,
        legal_reasoning=resolution_text,
        cited_clauses=clauses,
        audit_trail={
            "room_id": room_id,
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
        david_policy.claims = [
            Claim(
                claim_number="CLM-2024-04471",
                incident_date=date(2024, 10, 15),
                incident_type="collision",
                location="I-95 North, near Fort Lauderdale, FL",
                amount_requested=Decimal("12500.00"),
                status="pending",  # OPEN — the straightforward case, run live (no SIU needed)
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
                        "url": "/docs/MPD-2024-5567.html",
                        "summary": (
                            "Overnight theft of stereo and catalytic converter from a parked "
                            "vehicle outside the residence; reported within 24h; no indication of "
                            "commercial use."
                        ),
                    },
                    {
                        "type": "adjuster_note",
                        "ref": "ADJ-2024-3310",
                        "url": "/docs/ADJ-2024-3310.html",
                        "summary": (
                            "Denial cites suspected undisclosed rideshare use — but no rideshare "
                            "records, trip logs, or commercial markings are offered as evidence."
                        ),
                    },
                    {
                        "type": "photos",
                        "ref": "CLM-2024-03988-imgs",
                        "url": "/docs/CLM-2024-03988-photos.html",
                        "images": [
                            {"src": "/docs/theft-1.jpg", "caption": "Dashboard — stereo head unit removed, harness exposed"},
                            {"src": "/docs/theft-2.jpg", "caption": "Exhaust — catalytic converter cut out (fresh saw marks)"},
                            {"src": "/docs/theft-3.jpg", "caption": "Vehicle at residence — ordinary personal car, no rideshare livery"},
                        ],
                        "summary": (
                            "3 photos: stereo removed from dash, catalytic converter cut from the "
                            "exhaust, pried passenger window — no rideshare livery on the vehicle."
                        ),
                    },
                ],
            )
        ]
        session.add(lisa_policy)

        # --- CLOSED showcase: Marcus Reyes (fire / staged-loss fraud) — pre-adjudicated WITH the
        # dynamic SIU recruitment (Quinn) so a judge sees the full six-agent flow instantly. ---
        marcus_policy = Policy(
            policy_number="CPP-2024-6610",
            insured_name="Marcus Reyes",
            policy_type="Auto / Collision + Comprehensive",
            state="FL",
            effective_date=date(2024, 1, 1),
            expiration_date=date(2024, 12, 31),
            coverage_limit=Decimal("50000.00"),
            deductible=Decimal("500.00"),
            insurance_company="Crestview Mutual Insurance",
            coverage_details={"collision": True, "comprehensive": True},
        )
        marcus_policy.clauses = [
            PolicyClause(
                clause_number=c["clause_number"],
                clause_title=c["clause_title"],
                clause_text=c["clause_text"],
                clause_type=c["clause_type"],
                embedding=emb,
            )
            for c, emb in zip(CLAUSES, embeddings)
        ]
        marcus_claim = Claim(
            claim_number="CLM-2024-05120",
            incident_date=date(2024, 8, 22),
            incident_type="fire",
            location="Tampa, FL",
            amount_requested=Decimal("9800.00"),
            status="approved",  # CLOSED — instant showcase (full 6-agent flow incl. SIU)
            band_room_id=MARCUS_ROOM_ID,
            original_denial_reason=(
                "Claim denied per §7.4 — General Exclusions. Adjuster alleges a possible "
                "staged/intentional loss (misrepresentation), citing that the claim was filed "
                "shortly after a routine coverage update."
            ),
            incident_description=(
                "The parked vehicle caught fire overnight and was a total loss. Fire marshal "
                "report FMO-2024-0832 attributes the fire to an electrical fault in the wiring "
                "harness, with no accelerants detected and no signs of forced entry. The insured "
                "disputes the staged-loss allegation."
            ),
            supporting_docs=[
                {
                    "type": "fire_marshal_report",
                    "ref": "FMO-2024-0832",
                    "url": "/docs/FMO-2024-0832.html",
                    "summary": (
                        "Fire origin: electrical fault in the wiring harness. No accelerants "
                        "detected; no signs of forced entry or tampering. Consistent with an "
                        "accidental loss."
                    ),
                },
                {
                    "type": "photos",
                    "ref": "CLM-2024-05120-imgs",
                    "url": "/docs/CLM-2024-05120-photos.html",
                    "images": [
                        {"src": "/docs/fire-1.jpg", "caption": "Total-loss vehicle — overnight fire, parked at residence"},
                        {"src": "/docs/fire-2.jpg", "caption": "Engine bay — origin at driver-side wiring harness (electrical)"},
                        {"src": "/docs/fire-3.jpg", "caption": "Cabin / dash burn — no pour patterns or accelerant trails"},
                    ],
                    "summary": "Scene photos showing engine-bay origin burn pattern.",
                },
            ],
        )
        _attach_completed_debate(
            marcus_claim,
            MARCUS_DEBATE,
            MARCUS_RESOLUTION_TEXT,
            decision="APPROVED",
            amount=Decimal("9300.00"),
            clauses=["§5.2", "§7.4"],
            room_id=MARCUS_ROOM_ID,
        )
        marcus_policy.claims = [marcus_claim]
        session.add(marcus_policy)

        await session.commit()
        print(
            "  inserted: 3 policies, 18 clauses, "
            "2 OPEN cases (David Chen, Lisa Park — pending) + "
            "1 CLOSED showcase with SIU (Marcus Reyes, approved+signed, includes Quinn)"
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
