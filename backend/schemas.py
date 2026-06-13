"""Pydantic response/request models for the API."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    policy_number: str
    insured_name: str
    policy_type: str
    state: str
    coverage_limit: Decimal
    deductible: Decimal
    insurance_company: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_slug: str
    agent_display_name: str
    content: str
    message_type: str
    sent_at: datetime | None


class ResolutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    decision: str
    approved_amount: Decimal | None
    legal_reasoning: str
    cited_clauses: list
    audit_trail: dict
    approved_by: str | None
    approved_at: datetime | None


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    claim_number: str
    incident_date: date
    incident_type: str
    location: str | None
    amount_requested: Decimal
    status: str
    original_denial_reason: str | None
    band_room_id: str | None
    created_at: datetime
    insured_name: str | None = None


class ClaimDetailOut(ClaimOut):
    incident_description: str
    supporting_docs: list
    policy: PolicyOut | None
    messages: list[MessageOut]
    resolution: ResolutionOut | None


class CreateClaimIn(BaseModel):
    policy_id: uuid.UUID
    incident_date: date
    incident_type: str
    location: str | None = None
    incident_description: str
    amount_requested: Decimal
    original_denial_reason: str | None = None


class ApproveIn(BaseModel):
    approved_by: str = "Claims Officer"


class ReviseIn(BaseModel):
    note: str | None = None
