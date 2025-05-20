-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create claims table
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text TEXT NOT NULL,
    context TEXT,
    checkworthy BOOLEAN DEFAULT TRUE,
    domain TEXT,
    entities JSONB DEFAULT '[]',
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_text TEXT,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create evidence table
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    source TEXT NOT NULL,
    source_name TEXT,
    source_type TEXT DEFAULT 'unknown',
    relevance FLOAT NOT NULL,
    stance TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE,
    credibility FLOAT,
    excerpt_context TEXT,
    retrieval_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create verdicts table
CREATE TABLE IF NOT EXISTS verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    verdict TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    explanation TEXT NOT NULL,
    sources JSONB NOT NULL,
    evidence_summary TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create embeddings table for vector storage
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- For backward compatibility (can be removed later)
CREATE TABLE IF NOT EXISTS factchecks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim TEXT NOT NULL,
    verdict TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    explanation TEXT NOT NULL,
    sources JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS claims_domain_idx ON claims(domain);
CREATE INDEX IF NOT EXISTS claims_created_at_idx ON claims(created_at DESC);
CREATE INDEX IF NOT EXISTS evidence_claim_id_idx ON evidence(claim_id);
CREATE INDEX IF NOT EXISTS verdicts_claim_id_idx ON verdicts(claim_id);
CREATE INDEX IF NOT EXISTS verdicts_verdict_idx ON verdicts(verdict);

-- Create index on embeddings for similarity search
CREATE INDEX IF NOT EXISTS embeddings_vector_idx ON embeddings 
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Create index for metadata search on embeddings
CREATE INDEX IF NOT EXISTS embeddings_metadata_idx ON embeddings USING GIN (metadata);

-- Create function for similarity search with filters
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding VECTOR(1536),
    match_threshold FLOAT,
    match_count INT,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF filter_metadata IS NULL THEN
        RETURN QUERY
        SELECT
            e.id,
            e.content,
            e.metadata,
            1 - (e.embedding <-> query_embedding) AS similarity
        FROM
            embeddings e
        WHERE
            1 - (e.embedding <-> query_embedding) > match_threshold
        ORDER BY
            similarity DESC
        LIMIT
            match_count;
    ELSE
        RETURN QUERY
        SELECT
            e.id,
            e.content,
            e.metadata,
            1 - (e.embedding <-> query_embedding) AS similarity
        FROM
            embeddings e
        WHERE
            1 - (e.embedding <-> query_embedding) > match_threshold
            AND e.metadata @> filter_metadata
        ORDER BY
            similarity DESC
        LIMIT
            match_count;
    END IF;
END;
$$;

-- Create function for finding similar claims
CREATE OR REPLACE FUNCTION find_similar_claims(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.8,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    claim_id UUID,
    claim_text TEXT,
    verdict TEXT,
    confidence FLOAT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        (e.metadata->>'claim_id')::UUID AS claim_id,
        e.content AS claim_text,
        v.verdict,
        v.confidence,
        1 - (e.embedding <-> query_embedding) AS similarity
    FROM
        embeddings e
    LEFT JOIN
        verdicts v ON v.claim_id = (e.metadata->>'claim_id')::UUID
    WHERE
        1 - (e.embedding <-> query_embedding) > match_threshold
        AND e.metadata->>'type' = 'claim'
    ORDER BY
        similarity DESC
    LIMIT
        match_count;
END;
$$;

-- Create view for factcheck results
CREATE OR REPLACE VIEW factcheck_results AS
SELECT
    c.id AS claim_id,
    c.text AS claim_text,
    c.domain,
    c.context,
    c.source_url,
    v.id AS verdict_id,
    v.verdict,
    v.confidence,
    v.explanation,
    v.sources,
    v.evidence_summary,
    v.generated_at,
    (
        SELECT json_agg(json_build_object(
            'id', e.id,
            'text', e.text,
            'source', e.source,
            'source_name', e.source_name,
            'relevance', e.relevance,
            'stance', e.stance
        ))
        FROM evidence e
        WHERE e.claim_id = c.id
    ) AS evidence,
    c.created_at
FROM
    claims c
LEFT JOIN
    verdicts v ON c.id = v.claim_id; 