#!/usr/bin/env python3
"""Test accessing environment variables through actual application code.

This script verifies that the application code can properly access
environment variables, with or without defaults.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables before importing any application code
load_dotenv()

try:
    # Add the current directory to Python path so imports work correctly
    sys.path.insert(0, os.getcwd())
    
    # Import application modules that use environment variables
    from src.utils.models.model_config import (
        get_model_name,
        get_model_settings,
        get_api_key,
        ModelManager,
        DEFAULT_MODELS,
        DEFAULT_PARAMETERS
    )
    
    print("\n=== Testing Environment Variable Access in Application ===\n")
    
    # Test model configuration
    print("Testing model configuration access:")
    
    # Get model settings
    model_settings = get_model_settings()
    print(f"  Model settings: {model_settings}")
    
    # Test model name resolution for each agent type
    print("\nTesting model name resolution:")
    for agent_type in ["claim_detector", "evidence_hunter", "verdict_writer", "fallback"]:
        model_name = get_model_name(agent_type=agent_type)
        env_var = f"{agent_type.upper()}_MODEL"
        env_value = os.environ.get(env_var)
        
        if env_value:
            print(f"  {agent_type}: {model_name} (from environment variable {env_var})")
        else:
            print(f"  {agent_type}: {model_name} (from DEFAULT_MODELS)")
    
    # Test API keys
    print("\nTesting API keys:")
    try:
        openrouter_key = get_api_key("openrouter")
        print(f"  OpenRouter API key: {openrouter_key[:5]}*****")
    except Exception as e:
        print(f"  Error getting OpenRouter API key: {str(e)}")
    
    try:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            print(f"  OpenAI API key: {openai_key[:5]}*****")
        else:
            print("  OpenAI API key is not set")
    except Exception as e:
        print(f"  Error getting OpenAI API key: {str(e)}")
    
    # Create ModelManager instance
    print("\nTesting ModelManager instantiation:")
    try:
        manager = ModelManager(agent_type="claim_detector")
        print(f"  ModelManager created successfully for claim_detector")
        print(f"  Model name: {manager.model_name}")
        print(f"  Parameters: {manager.parameters}")
        
        # Test token usage tracking
        print("\nTesting token usage tracking:")
        print(f"  Initial token usage: {manager.get_token_usage()}")
        
    except Exception as e:
        print(f"  Error creating ModelManager: {str(e)}")
    
    # Test database configuration
    print("\nTesting database configuration:")
    try:
        from src.utils.db.db import get_supabase_client
        
        client = get_supabase_client()
        print("  Supabase client created successfully")
    except Exception as e:
        print(f"  Error creating Supabase client: {str(e)}")
    
    # Test Redis configuration
    print("\nTesting Redis configuration:")
    try:
        from src.utils.cache.redis import RedisCache
        
        cache = RedisCache()
        print("  Redis cache created successfully")
        print(f"  Redis URL: {os.environ.get('REDIS_URL')}")
        redis_enabled = os.environ.get("REDIS_ENABLED", "True").lower() == "true"
        print(f"  Redis enabled: {redis_enabled}")
    except Exception as e:
        print(f"  Error creating Redis cache: {str(e)}")
    
    print("\n=== Environment Variable Access Test Complete ===")
    
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1) 