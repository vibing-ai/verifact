#!/usr/bin/env python3
"""Check environment variables and configuration for VeriFact."""

import os
import sys
import logging
import importlib.util

def check_env_variables():
    """Check if required environment variables are set."""
    print("\n== Environment Variables ==")
    
    required_vars = [
        "OPENAI_API_KEY",          # For OpenAI API
        "OPENROUTER_API_KEY",      # For OpenRouter
        "SERPER_API_KEY",          # For search
        "SUPABASE_URL",            # For database
        "SUPABASE_KEY",            # For database
        "REDIS_URL"                # For caching
    ]
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '****'
            print(f"✅ {var} is set: {masked}")
        else:
            print(f"❌ {var} is not set")

def check_python_version():
    """Check Python version."""
    print("\n== Python Version ==")
    version = sys.version
    print(f"Python: {version}")
    
    # Check if Python version is adequate
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 9:
        print("✅ Python version is adequate (3.9+)")
    else:
        print(f"❌ Python version may be too old: {major}.{minor} (3.9+ recommended)")

def check_installed_packages():
    """Check if required packages are installed."""
    print("\n== Required Packages ==")
    
    required_packages = [
        "openai",
        "pydantic",
        "fastapi",
        "agents",
        "uvicorn",
        "supabase",
        "chainlit",
        "httpx",
        "redis"
    ]
    
    for package in required_packages:
        spec = importlib.util.find_spec(package)
        if spec:
            try:
                mod = importlib.import_module(package)
                version = getattr(mod, "__version__", "unknown")
                print(f"✅ {package} is installed (version: {version})")
            except ImportError:
                print(f"✅ {package} is importable but version unknown")
        else:
            print(f"❌ {package} is not installed")

def check_logging_config():
    """Check logging configuration."""
    print("\n== Logging Configuration ==")
    
    # Get current logging level
    root_logger = logging.getLogger()
    print(f"Root logger level: {logging.getLevelName(root_logger.level)}")
    
    # Check handlers
    handlers = root_logger.handlers
    print(f"Number of handlers: {len(handlers)}")
    for i, handler in enumerate(handlers):
        print(f"  Handler {i+1}: {type(handler).__name__}")
        
    # Check logging format
    formatter = getattr(handlers[0], 'formatter', None) if handlers else None
    if formatter:
        print(f"Formatter: {formatter._fmt}")
    else:
        print("No formatter found")
        
    # Test a simple log
    try:
        print("\nTesting log output:")
        logging.info("Test log message")
        print("✅ Logging appears to work")
    except Exception as e:
        print(f"❌ Error during logging: {e}")

def check_database_connection():
    """Check database connection."""
    print("\n== Database Connection ==")
    
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")):
        print("❌ Skipping database check as credentials are not set")
        return
        
    try:
        # Import here to avoid import errors if not installed
        from supabase import create_client
        
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        client = create_client(url, key)
        
        # Try a simple query
        response = client.table("claims").select("count(*)", count="exact").execute()
        
        print(f"✅ Successfully connected to Supabase")
        print(f"  Count query result: {response}")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

if __name__ == "__main__":
    print("=== VeriFact Environment Check ===")
    check_python_version()
    check_env_variables()
    check_installed_packages()
    check_logging_config()
    check_database_connection()
    print("\n=== Check Complete ===") 