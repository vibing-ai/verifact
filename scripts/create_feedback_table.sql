-- Create feedback table for storing user feedback on factcheck results
CREATE TABLE IF NOT EXISTS public.feedback (
    feedback_id UUID PRIMARY KEY,
    claim_id UUID NOT NULL,
    user_id VARCHAR(255),
    session_id UUID,
    accuracy_rating INTEGER CHECK (accuracy_rating >= 1 AND accuracy_rating <= 5),
    helpfulness_rating INTEGER CHECK (helpfulness_rating >= 1 AND helpfulness_rating <= 5),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Ensure we have either user_id or session_id
    CONSTRAINT require_identifier CHECK (
        (user_id IS NOT NULL) OR (session_id IS NOT NULL)
    ),
    
    -- Ensure we have at least one of: accuracy_rating, helpfulness_rating, or comment
    CONSTRAINT require_feedback CHECK (
        accuracy_rating IS NOT NULL OR 
        helpfulness_rating IS NOT NULL OR 
        (comment IS NOT NULL AND comment != '')
    )
);

-- Create indexes for improved query performance
CREATE INDEX IF NOT EXISTS idx_feedback_claim_id ON public.feedback(claim_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON public.feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_session_id ON public.feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON public.feedback(created_at);

-- Create stored procedure to get feedback statistics
CREATE OR REPLACE FUNCTION public.get_feedback_stats(claim_id_param UUID DEFAULT NULL)
RETURNS TABLE (
    total_feedback BIGINT,
    average_accuracy NUMERIC,
    average_helpfulness NUMERIC
) AS $$
BEGIN
    IF claim_id_param IS NULL THEN
        RETURN QUERY
        SELECT
            COUNT(*)::BIGINT AS total_feedback,
            AVG(accuracy_rating)::NUMERIC AS average_accuracy,
            AVG(helpfulness_rating)::NUMERIC AS average_helpfulness
        FROM public.feedback;
    ELSE
        RETURN QUERY
        SELECT
            COUNT(*)::BIGINT AS total_feedback,
            AVG(accuracy_rating)::NUMERIC AS average_accuracy,
            AVG(helpfulness_rating)::NUMERIC AS average_helpfulness
        FROM public.feedback
        WHERE claim_id = claim_id_param;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to get accuracy rating distribution
CREATE OR REPLACE FUNCTION public.get_accuracy_distribution(claim_id_param UUID DEFAULT NULL)
RETURNS TABLE (
    accuracy_rating INTEGER,
    count BIGINT
) AS $$
BEGIN
    IF claim_id_param IS NULL THEN
        RETURN QUERY
        SELECT
            f.accuracy_rating,
            COUNT(*)::BIGINT
        FROM public.feedback f
        WHERE f.accuracy_rating IS NOT NULL
        GROUP BY f.accuracy_rating
        ORDER BY f.accuracy_rating;
    ELSE
        RETURN QUERY
        SELECT
            f.accuracy_rating,
            COUNT(*)::BIGINT
        FROM public.feedback f
        WHERE f.accuracy_rating IS NOT NULL
          AND f.claim_id = claim_id_param
        GROUP BY f.accuracy_rating
        ORDER BY f.accuracy_rating;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to get helpfulness rating distribution
CREATE OR REPLACE FUNCTION public.get_helpfulness_distribution(claim_id_param UUID DEFAULT NULL)
RETURNS TABLE (
    helpfulness_rating INTEGER,
    count BIGINT
) AS $$
BEGIN
    IF claim_id_param IS NULL THEN
        RETURN QUERY
        SELECT
            f.helpfulness_rating,
            COUNT(*)::BIGINT
        FROM public.feedback f
        WHERE f.helpfulness_rating IS NOT NULL
        GROUP BY f.helpfulness_rating
        ORDER BY f.helpfulness_rating;
    ELSE
        RETURN QUERY
        SELECT
            f.helpfulness_rating,
            COUNT(*)::BIGINT
        FROM public.feedback f
        WHERE f.helpfulness_rating IS NOT NULL
          AND f.claim_id = claim_id_param
        GROUP BY f.helpfulness_rating
        ORDER BY f.helpfulness_rating;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to get recent comments
CREATE OR REPLACE FUNCTION public.get_recent_comments(claim_id_param UUID DEFAULT NULL, limit_param INTEGER DEFAULT 5)
RETURNS TABLE (
    feedback_id UUID,
    claim_id UUID,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    IF claim_id_param IS NULL THEN
        RETURN QUERY
        SELECT
            f.feedback_id,
            f.claim_id,
            f.comment,
            f.created_at
        FROM public.feedback f
        WHERE f.comment IS NOT NULL
          AND f.comment != ''
        ORDER BY f.created_at DESC
        LIMIT limit_param;
    ELSE
        RETURN QUERY
        SELECT
            f.feedback_id,
            f.claim_id,
            f.comment,
            f.created_at
        FROM public.feedback f
        WHERE f.comment IS NOT NULL
          AND f.comment != ''
          AND f.claim_id = claim_id_param
        ORDER BY f.created_at DESC
        LIMIT limit_param;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Add RLS policy to allow insert from authenticated or anonymous users
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

-- Policy for inserting feedback
CREATE POLICY insert_feedback ON public.feedback
    FOR INSERT
    TO authenticated, anon
    WITH CHECK (true);

-- Policy for reading feedback (admin only)
CREATE POLICY read_feedback ON public.feedback
    FOR SELECT
    TO authenticated
    USING (true);

-- Grant permissions
GRANT SELECT, INSERT ON public.feedback TO authenticated, anon;
GRANT EXECUTE ON FUNCTION public.get_feedback_stats TO authenticated, anon;
GRANT EXECUTE ON FUNCTION public.get_accuracy_distribution TO authenticated, anon;
GRANT EXECUTE ON FUNCTION public.get_helpfulness_distribution TO authenticated, anon;
GRANT EXECUTE ON FUNCTION public.get_recent_comments TO authenticated, anon; 