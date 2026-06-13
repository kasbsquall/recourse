"""LangChain tools the agents call to ground their arguments in real data.

These run inside the agent processes (same env as the backend), querying the local DB
and the pgvector clause index. Async tools — LangGraph invokes them with `ainvoke`.
"""
from __future__ import annotations

from langchain_core.tools import tool
from sqlalchemy import select

from database.connection import AsyncSessionLocal
from database.models import Claim, Policy
from services.rag_service import search_clauses as _rag_search


@tool
async def search_policy_clauses(query: str) -> str:
    """Search the insurance policy for clauses relevant to the query.

    Returns the most semantically relevant clauses with their exact numbers, titles,
    type (coverage/exclusion/condition/exception), and verbatim text. Use this to quote
    policy language precisely or to find exceptions that may apply.
    """
    async with AsyncSessionLocal() as session:
        hits = await _rag_search(session, query, limit=4)
    if not hits:
        return "No matching clauses found."
    return "\n\n".join(
        f"{h['clause_number']} — {h['clause_title']} [{h['clause_type']}]:\n"
        f"\"{h['clause_text']}\""
        for h in hits
    )


@tool
async def lookup_policy(policy_number: str) -> str:
    """Look up a policy by number: coverage type, limit, deductible, dates, and state."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Policy).where(Policy.policy_number == policy_number)
        )
        policy = result.scalar_one_or_none()
    if policy is None:
        return f"No policy found with number {policy_number}."
    return (
        f"Policy {policy.policy_number} — {policy.insured_name} ({policy.insurance_company})\n"
        f"Type: {policy.policy_type} | State: {policy.state}\n"
        f"Coverage limit: ${policy.coverage_limit:,.2f} | Deductible: ${policy.deductible:,.2f}\n"
        f"Effective: {policy.effective_date} to {policy.expiration_date}"
    )


@tool
async def get_claim_details(claim_number: str) -> str:
    """Retrieve a claim's incident facts, amount, original denial reason, and supporting documents."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Claim).where(Claim.claim_number == claim_number)
        )
        claim = result.scalar_one_or_none()
    if claim is None:
        return f"No claim found with number {claim_number}."
    docs = "\n".join(
        f"  - [{d.get('type')}] {d.get('ref')}: {d.get('summary')}"
        for d in (claim.supporting_docs or [])
    ) or "  (none on file)"
    return (
        f"Claim {claim.claim_number} ({claim.incident_type}) — requested ${claim.amount_requested:,.2f}\n"
        f"Incident date: {claim.incident_date} | Location: {claim.location}\n"
        f"Description: {claim.incident_description}\n"
        f"Original denial: {claim.original_denial_reason}\n"
        f"Supporting documents:\n{docs}"
    )
