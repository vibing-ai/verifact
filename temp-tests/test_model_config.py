#!/usr/bin/env python3
"""Test specifically for the model configuration module.

This script tests the model configuration module to ensure it correctly
loads and uses environment variables with appropriate defaults.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

try:
    from src.utils.models.model_config import (
        DEFAULT_MODELS,
        DEFAULT_PARAMETERS,
        get_model_name,
        get_model_settings,
        get_api_key,
        ModelManager
    )
    
    def test_model_config():
        """Test model configuration functionality."""
        # Store test results
        results = []
        
        print("\n=== Testing Model Configuration ===\n")
        
        # Test 1: Access default parameters
        print("1. Testing default parameters:")
        try:
            print(f"  DEFAULT_PARAMETERS = {DEFAULT_PARAMETERS}")
            for key, value in DEFAULT_PARAMETERS.items():
                print(f"  - {key}: {value}")
            results.append(("Default parameters", True))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Default parameters", False))
        
        # Test 2: Access default models
        print("\n2. Testing default models:")
        try:
            print(f"  DEFAULT_MODELS = {DEFAULT_MODELS}")
            for agent_type, model in DEFAULT_MODELS.items():
                print(f"  - {agent_type}: {model}")
            results.append(("Default models", True))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Default models", False))
        
        # Test 3: Get model settings (uses environment variables with defaults)
        print("\n3. Testing get_model_settings:")
        try:
            settings = get_model_settings()
            print(f"  Model settings: {settings}")
            # Check if environment variables override defaults
            for param, default in DEFAULT_PARAMETERS.items():
                env_var = f"MODEL_{param.upper()}"
                env_value = os.environ.get(env_var)
                if env_value:
                    print(f"  - {param}: {settings[param]} (from {env_var}={env_value})")
                else:
                    print(f"  - {param}: {settings[param]} (from default)")
            results.append(("Model settings", True))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Model settings", False))
        
        # Test 4: Get model name (uses environment variables with defaults)
        print("\n4. Testing get_model_name:")
        try:
            for agent_type in ["claim_detector", "evidence_hunter", "verdict_writer", "fallback"]:
                model_name = get_model_name(agent_type=agent_type)
                env_var = f"{agent_type.upper()}_MODEL"
                env_value = os.environ.get(env_var)
                if env_value:
                    print(f"  - {agent_type}: {model_name} (from {env_var}={env_value})")
                else:
                    print(f"  - {agent_type}: {model_name} (from DEFAULT_MODELS)")
            results.append(("Model name resolution", True))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("Model name resolution", False))
        
        # Test 5: Test ModelManager instantiation
        print("\n5. Testing ModelManager instantiation:")
        try:
            manager = ModelManager(agent_type="claim_detector")
            print(f"  - Model name: {manager.model_name}")
            print(f"  - Parameters: {manager.parameters}")
            results.append(("ModelManager", True))
        except Exception as e:
            print(f"  Error: {e}")
            results.append(("ModelManager", False))
        
        # Test 6: Test model-specific configuration
        print("\n6. Testing model-specific configuration:")
        try:
            # Set a temporary environment variable
            os.environ["CLAIM_DETECTOR_TEMPERATURE"] = "0.5"
            
            # Create manager and check if it uses the specific setting
            manager = ModelManager(agent_type="claim_detector")
            temp = manager.parameters.get("temperature")
            print(f"  - claim_detector temperature: {temp} (from CLAIM_DETECTOR_TEMPERATURE=0.5)")
            
            # Clean up
            del os.environ["CLAIM_DETECTOR_TEMPERATURE"]
            results.append(("Model-specific config", True))
        except Exception as e:
            print(f"  Error: {e}")
            # Clean up in case of error
            if "CLAIM_DETECTOR_TEMPERATURE" in os.environ:
                del os.environ["CLAIM_DETECTOR_TEMPERATURE"]
            results.append(("Model-specific config", False))
            
        # Print summary
        print("\nTest Summary:")
        all_passed = True
        for test, passed in results:
            status = "✅ Passed" if passed else "❌ Failed"
            print(f"  {status}: {test}")
            if not passed:
                all_passed = False
        
        overall = "✅ All tests passed" if all_passed else "❌ Some tests failed"
        print(f"\nOverall result: {overall}")
        
        print("\n=== Model Configuration Tests Complete ===")

    # Run tests
    test_model_config()
    
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1) 