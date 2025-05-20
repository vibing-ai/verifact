#!/usr/bin/env python3
"""
API Testing Script for VeriFact

This script tests the VeriFact API endpoints to ensure they're working correctly.
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path


def test_api():
    """Test the VeriFact API endpoints."""
    print("\n=== Testing VeriFact API ===\n")
    
    api_url = "http://localhost:8000"
    results = {
        "timestamp": datetime.now().isoformat(),
        "endpoints": {},
        "issues": []
    }
    
    # First check if API is running
    print("Checking if API server is running...")
    try:
        response = requests.get(f"{api_url}/docs")
        api_running = response.status_code == 200
        results["api_running"] = api_running
        
        if not api_running:
            print("❌ API server is not running!")
            results["issues"].append("API server is not running")
            print("Start the API server with: uvicorn src.main:app --reload")
            save_results(results)
            return
        else:
            print("✅ API server is running")
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        results["api_running"] = False
        results["issues"].append(f"Connection error: {str(e)}")
        save_results(results)
        return
    
    # Test endpoints
    test_endpoints(api_url, results)
    
    # Save results
    save_results(results)
    
    print("\n=== API Testing Complete ===")


def test_endpoints(api_url, results):
    """Test the various API endpoints."""
    
    # 1. Test factcheck endpoint
    print("\nTesting POST /api/v1/factcheck...")
    
    test_data = {
        "text": "The Earth is approximately 4.54 billion years old. Water covers about 71% of the Earth's surface.",
        "options": {
            "min_check_worthiness": 0.7
        }
    }
    
    endpoint_result = test_endpoint(
        "POST", 
        f"{api_url}/api/v1/factcheck",
        json=test_data
    )
    
    results["endpoints"]["factcheck"] = endpoint_result
    
    # 2. Test health endpoint
    print("\nTesting GET /health...")
    
    health_result = test_endpoint(
        "GET",
        f"{api_url}/health"
    )
    
    results["endpoints"]["health"] = health_result
    
    # 3. If batch endpoint exists, test it
    print("\nTesting POST /api/v1/factcheck/batch...")
    
    batch_test_data = {
        "texts": [
            "The Earth is approximately 4.54 billion years old.",
            "Water covers about 71% of the Earth's surface."
        ],
        "options": {
            "min_check_worthiness": 0.7
        }
    }
    
    batch_result = test_endpoint(
        "POST", 
        f"{api_url}/api/v1/factcheck/batch",
        json=batch_test_data
    )
    
    results["endpoints"]["factcheck_batch"] = batch_result


def test_endpoint(method, url, **kwargs):
    """Test a specific endpoint and return the results."""
    result = {
        "url": url,
        "method": method,
        "status_code": None,
        "response_time": None,
        "success": False,
        "error": None,
        "response_sample": None
    }
    
    try:
        start_time = time.time()
        
        if method.upper() == "GET":
            response = requests.get(url, **kwargs)
        elif method.upper() == "POST":
            response = requests.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        duration = time.time() - start_time
        
        result["status_code"] = response.status_code
        result["response_time"] = duration
        result["success"] = 200 <= response.status_code < 300
        
        # Try to parse response as JSON
        try:
            response_data = response.json()
            # Store a sample of the response (limited size)
            if isinstance(response_data, dict):
                # For dictionaries, keep a few key fields
                sample = {k: response_data[k] for k in list(response_data.keys())[:5]}
                result["response_sample"] = sample
            elif isinstance(response_data, list):
                # For lists, keep the first few items
                result["response_sample"] = response_data[:2]
            else:
                result["response_sample"] = str(response_data)[:200]
        except:
            # Not JSON, store a snippet of the text
            result["response_sample"] = response.text[:200]
        
        # Report result
        if result["success"]:
            print(f"✅ {method} {url} - {response.status_code} in {duration:.2f}s")
        else:
            print(f"❌ {method} {url} - {response.status_code} in {duration:.2f}s")
            print(f"   Response: {response.text[:100]}...")
        
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
        print(f"❌ {method} {url} - Error: {e}")
    
    return result


def save_results(results):
    """Save test results to a file."""
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"api_test_{timestamp}.json"
    
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nTest results saved to {report_path}")


if __name__ == "__main__":
    test_api() 