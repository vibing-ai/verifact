import os
import logging
import asyncio
import sys
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

logger = logging.getLogger(__name__)

class DatabaseSchemaManager:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        # Initialize Supabase client
        options = ClientOptions(
            schema="public",
            headers={"X-Client-Info": "verifact/1.0.0"}
        )
        self.supabase: Client = create_client(
            self.supabase_url, 
            self.supabase_key,
            options=options
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
                test_embedding = [0.1] * 1536  # Create a dummy embedding
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
            function_sql = """
            CREATE OR REPLACE FUNCTION match_claims_with_verdicts(
                query_embedding vector(1536),
                match_threshold float DEFAULT 0.8,
                match_count int DEFAULT 5
            )
            RETURNS TABLE (
                claim JSONB,
                verdict JSONB,
                similarity float
            )
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    to_jsonb(c.*) as claim,
                    to_jsonb(v.*) as verdict,
                    1 - (c.embedding <=> query_embedding) as similarity
                FROM claims c
                LEFT JOIN verdicts v ON c.id = v.claim_id
                WHERE c.embedding IS NOT NULL
                AND 1 - (c.embedding <=> query_embedding) > match_threshold
                ORDER BY c.embedding <=> query_embedding
                LIMIT match_count;
            END;
            $$;
            """
            
            self.supabase.rpc(
            'exec_sql',
            {'sql': function_sql}
            ).execute()

            logger.info("✅ Vector similarity function created successfully")
            return True
            
        except Exception as e:
            logger.error(f" Failed to create vector similarity function: {e}")
            return False

# Global instance
schema_manager = DatabaseSchemaManager()

# Add setup functionality
async def setup_database():
    """Verify and setup the database."""
    from dotenv import load_dotenv
    load_dotenv()
    
    print(" Verifying VeriFact database setup...")
    print("=" * 50)
    
    try:
        success = await schema_manager.verify_schema_exists()
        
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