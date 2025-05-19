-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create factchecks table
CREATE TABLE IF NOT EXISTS factchecks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim TEXT NOT NULL,
    verdict TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    explanation TEXT NOT NULL,
    sources JSONB NOT NULL,
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

-- Create index on embeddings for similarity search
CREATE INDEX IF NOT EXISTS embeddings_vector_idx ON embeddings 
USING ivfflat (embedding vector_l2_ops);

-- Create function for similarity search
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding VECTOR(1536),
    match_threshold FLOAT,
    match_count INT
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
END;
$$; 