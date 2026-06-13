"""SQLAlchemy 2.0 models mirroring schema.sql."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DECIMAL,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import settings


class Base(DeclarativeBase):
    pass


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_number: Mapped[str] = mapped_column(String(50), unique=True)
    insured_name: Mapped[str] = mapped_column(String(200))
    policy_type: Mapped[str] = mapped_column(String(50))
    state: Mapped[str] = mapped_column(String(2))
    effective_date: Mapped[date] = mapped_column(Date)
    expiration_date: Mapped[date] = mapped_column(Date)
    coverage_limit: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    deductible: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), default=0)
    insurance_company: Mapped[str] = mapped_column(
        String(200), default="Crestview Mutual Insurance"
    )
    coverage_details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    clauses: Mapped[list[PolicyClause]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
    claims: Mapped[list[Claim]] = relationship(back_populates="policy")


class PolicyClause(Base):
    __tablename__ = "policy_clauses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE")
    )
    clause_number: Mapped[str] = mapped_column(String(20))
    clause_title: Mapped[str | None] = mapped_column(String(200))
    clause_text: Mapped[str] = mapped_column(Text)
    clause_type: Mapped[str] = mapped_column(String(50))
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    policy: Mapped[Policy] = relationship(back_populates="clauses")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_number: Mapped[str] = mapped_column(String(50), unique=True)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("policies.id"))
    incident_date: Mapped[date] = mapped_column(Date)
    incident_description: Mapped[str] = mapped_column(Text)
    incident_type: Mapped[str] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(200))
    amount_requested: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    band_room_id: Mapped[str | None] = mapped_column(String(200))
    original_denial_reason: Mapped[str | None] = mapped_column(Text)
    supporting_docs: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    policy: Mapped[Policy | None] = relationship(back_populates="claims")
    messages: Mapped[list[AgentMessage]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    resolution: Mapped[Resolution | None] = relationship(
        back_populates="claim", cascade="all, delete-orphan", uselist=False
    )


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE")
    )
    band_message_id: Mapped[str | None] = mapped_column(String(200))
    agent_slug: Mapped[str] = mapped_column(String(50))
    agent_display_name: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(50), default="message")
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    claim: Mapped[Claim] = relationship(back_populates="messages")


class Resolution(Base):
    __tablename__ = "resolutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE")
    )
    decision: Mapped[str] = mapped_column(String(30))
    approved_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    legal_reasoning: Mapped[str] = mapped_column(Text)
    cited_clauses: Mapped[list] = mapped_column(JSONB, default=list)
    audit_trail: Mapped[dict] = mapped_column(JSONB, default=dict)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    claim: Mapped[Claim] = relationship(back_populates="resolution")
