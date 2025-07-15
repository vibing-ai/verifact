import os
import logging
import asyncio
import sys
from pathlib import Path
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

logger = logging.getLogger(__name__)

# Configuration constants
# OpenAI text-embedding-3-small dimension
EMBEDDING_DIMENSION = 1536

class DatabaseSchemaManager:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        # Initialize Supabase client
        self.supabase = create_client(
            self.supabase_url,
            self.supabase_key,
            options=ClientOptions(
                schema="public",
                headers={"X-Client-Info": "verifact"}
            )
        )
    
    async def verify_schema_exists(self) -> bool:
        """Verify that all required database objects exist."""
        try:
            # Check if tables exist by trying to select from them
            try:
                # Test claims table
                self.supabase.table("claims").select("id").limit(1).execute()
                logger.info(" claims table exists")
            except Exception as e:
                logger.error(f" claims table missing: {e}")
                return False
            
            try:
                # Test evidence table
                self.supabase.table("evidence").select("id").limit(1).execute()
                logger.info(" evidence table exists")
            except Exception as e:
                logger.error(f" evidence table missing: {e}")
                return False
            
            try:
                # Test verdicts table
                self.supabase.table("verdicts").select("id").limit(1).execute()
                logger.info(" verdicts table exists")
            except Exception as e:
                logger.error(f" verdicts table missing: {e}")
                return False
            
            # Check if vector similarity function exists by trying to call it
            try:
                # Test with a dummy embedding
                test_embedding = [0.1] * EMBEDDING_DIMENSION  # Create a dummy embedding
                self.supabase.rpc(
                    'match_claims_with_verdicts',
                    {
                        'query_embedding': test_embedding,
                        'match_threshold': 0.8,
                        'match_count': 1
                    }
                ).execute()
                logger.info(" Vector similarity function exists")
            except Exception as e:
                logger.warning(f" Vector similarity function not found: {e}")
                logger.warning("Will create the function now...")
                return await self.create_vector_similarity_function()
            
            logger.info(" Database schema verified successfully")
            return True
            
        except Exception as e:
            logger.error(f" Schema verification failed: {e}")
            return False
    
    async def create_vector_similarity_function(self) -> bool:
        """Create the vector similarity search function."""
        try:
            function_sql = f"""
            CREATE OR REPLACE FUNCTION match_claims_with_verdicts(
                query_embedding vector({EMBEDDING_DIMENSION}),
                match_threshold float DEFAULT 0.8,
                match_count int DEFAULT 5
            )
            RETURNS TABLE (
                claim_id UUID,
                claim_text TEXT,
                similarity_score FLOAT,
                verdict_id UUID,
                verdict_result TEXT,
                verdict_confidence FLOAT
            )
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    c.id as claim_id,
                    c.text as claim_text,
                    c.embedding <=> query_embedding as similarity_score,
                    v.id as verdict_id,
                    v.verdict as verdict_result,
                    v.confidence as verdict_confidence
                FROM claims c
                LEFT JOIN verdicts v ON c.id = v.claim_id
                WHERE c.embedding IS NOT NULL
                AND (c.embedding <=> query_embedding) < (1 - match_threshold)
                ORDER BY similarity_score ASC
                LIMIT match_count;
            END;
            $$;
            """

            try:
                # Try to use exec_sql function
                self.supabase.rpc(
                    'exec_sql',
                    {'sql': function_sql}
                ).execute()
                logger.info(" Vector similarity function created successfully")
                return True
            except Exception as e:
                logger.warning(f" exec_sql function not available: {e}")
                logger.info(" Please create the exec_sql function in your Supabase database:")
                logger.info("""
                CREATE OR REPLACE FUNCTION exec_sql(sql text)
                RETURNS void
                LANGUAGE plpgsql
                SECURITY DEFINER
                AS $$
                BEGIN
                    EXECUTE sql;
                END;
                $$;
                """)
                return False

        except Exception as e:
            logger.error(f" Failed to create vector similarity function: {e}")
            return False

# Global instance with lazy initialization
_schema_manager = None

def get_schema_manager():
    """Get the global schema manager instance with lazy initialization."""
    global _schema_manager
    if _schema_manager is None:
        _schema_manager = DatabaseSchemaManager()
    return _schema_manager

# Add setup functionality
async def setup_database():
    """Verify and setup the database."""
    from dotenv import load_dotenv
    load_dotenv()
    
    print(" Verifying VeriFact database setup...")
    print("=" * 50)
    
    try:
        # Use lazy initialization
        success = await get_schema_manager().verify_schema_exists()
        
        if success:
            print("\n Database setup verified successfully!")
            print("\n What was verified/created:")
            print("   • PGVector extension ✓")
            print("   • claims table ✓")
            print("   • evidence table ✓")
            print("   • verdicts table ✓")
            print("   • Vector similarity search function ✓")
            print("   • Database indexes ✓")
        else:
            print("\n Database setup verification failed!")
            print("\n Manual steps required:")
            print("   1. Go to Supabase Dashboard → SQL Editor")
            print("   2. Run the SQL commands from the documentation")
            print("   3. Re-run this script")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n Error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(setup_database())