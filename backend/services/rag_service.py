"""Embeddings + semantic clause retrieval over pgvector.

The sentence-transformers model is loaded lazily (first call) so importing this
module stays cheap. all-MiniLM-L6-v2 produces 384-dim vectors.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import PolicyClause

_model = None


def _get_model():
    """Load the embedding model once and reuse it."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_text(text: str) -> list[float]:
    """Return a 384-dim embedding for a single string."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a batch of strings."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


async def search_clauses(
    session: AsyncSession,
    query: str,
    policy_id: uuid.UUID | None = None,
    limit: int = 5,
) -> list[dict]:
    """Semantic search over policy clauses, ordered by cosine distance.

    Returns dicts with clause metadata + a similarity score (1 - distance).
    Morgan and Alex use this to ground their arguments in real clause text.
    """
    query_embedding = embed_text(query)

    distance = PolicyClause.embedding.cosine_distance(query_embedding)
    stmt = select(PolicyClause, distance.label("distance"))
    if policy_id is not None:
        stmt = stmt.where(PolicyClause.policy_id == policy_id)
    stmt = stmt.order_by(distance).limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "clause_number": clause.clause_number,
            "clause_title": clause.clause_title,
            "clause_text": clause.clause_text,
            "clause_type": clause.clause_type,
            "similarity": round(1.0 - float(dist), 4),
        }
        for clause, dist in rows
    ]
