-- Recourse database schema. Idempotent: safe to run repeatedly.
-- Auto-applied by docker-compose on a fresh DB volume, and re-applied by seed_data.py.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_number VARCHAR(50) UNIQUE NOT NULL,
    insured_name VARCHAR(200) NOT NULL,
    policy_type VARCHAR(50) NOT NULL,
    state VARCHAR(2) NOT NULL,
    effective_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    coverage_limit DECIMAL(12,2) NOT NULL,
    deductible DECIMAL(12,2) NOT NULL DEFAULT 0,
    insurance_company VARCHAR(200) NOT NULL DEFAULT 'Crestview Mutual Insurance',
    coverage_details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policy_clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES policies(id) ON DELETE CASCADE,
    clause_number VARCHAR(20) NOT NULL,
    clause_title VARCHAR(200),
    clause_text TEXT NOT NULL,
    clause_type VARCHAR(50) NOT NULL,
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policy_clauses_embedding
    ON policy_clauses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_number VARCHAR(50) UNIQUE NOT NULL,
    policy_id UUID REFERENCES policies(id),
    incident_date DATE NOT NULL,
    incident_description TEXT NOT NULL,
    incident_type VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    amount_requested DECIMAL(12,2) NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    band_room_id VARCHAR(200),
    original_denial_reason TEXT,
    supporting_docs JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID REFERENCES claims(id) ON DELETE CASCADE,
    band_message_id VARCHAR(200),
    agent_slug VARCHAR(50) NOT NULL,
    agent_display_name VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'message',
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS resolutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID REFERENCES claims(id) ON DELETE CASCADE,
    decision VARCHAR(30) NOT NULL,
    approved_amount DECIMAL(12,2),
    legal_reasoning TEXT NOT NULL,
    cited_clauses JSONB NOT NULL DEFAULT '[]',
    audit_trail JSONB NOT NULL DEFAULT '{}',
    approved_by VARCHAR(200),
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
