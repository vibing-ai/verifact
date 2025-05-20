#!/usr/bin/env python3
"""VeriFact End-to-End Testing Script

This script executes a comprehensive testing plan for the VeriFact factchecking platform,
verifying all components are correctly implemented and functioning together.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest


class VerifactTester:
    """Class to orchestrate VeriFact testing."""

    def __init__(self):
        """Initialize the tester."""
        self.results = {
            "environment_checks": {},
            "component_tests": {},
            "integration_tests": {},
            "api_tests": {},
            "ui_tests": {},
            "system_tests": {},
            "performance_metrics": {},
            "issues": [],
            "recommendations": [],
        }
        self.start_time = datetime.now()
        print(f"Starting VeriFact test suite at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def generate_report(self):
        """Generate a test report with findings."""
        self.results["test_duration"] = str(datetime.now() - self.start_time)

        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)

        report_path = (
            report_dir / f"verifact_test_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nTest report saved to {report_path}")

        # Print summary to console
        self._print_summary()

        return report_path

    def _print_summary(self):
        """Print a summary of test results to the console."""
        print("\n" + "=" * 80)
        print(f"VeriFact Test Summary ({self.results['test_duration']} duration)")
        print("=" * 80)

        for section, results in self.results.items():
            if section not in ["issues", "recommendations", "test_duration"]:
                if results:
                    passed = sum(1 for r in results.values() if r.get("status") == "PASS")
                    total = len(results)
                    print(f"\n{section.replace('_', ' ').title()}: {passed}/{total} passed")

                    for test_name, test_result in results.items():
                        status = test_result.get("status", "UNKNOWN")
                        status_display = "✅" if status == "PASS" else "❌"
                        print(f"  {status_display} {test_name}")

        if self.results["issues"]:
            print("\nIssues Found:")
            for issue in self.results["issues"]:
                print(f"  - {issue}")

        if self.results["recommendations"]:
            print("\nRecommendations:")
            for rec in self.results["recommendations"]:
                print(f"  - {rec}")

    async def run_all_tests(self):
        """Run all tests in the test suite."""
        # 1. Environment and Configuration Tests
        await self.check_environment()

        # 2. Component Tests
        await self.test_components()

        # 3. Integration Tests
        await self.test_integration()

        # 4. API Tests
        await self.test_api()

        # 5. UI Tests (note: some are manual)
        print("\nSome UI tests require manual verification.")

        # 6. System Tests
        await self.test_system()

        # Generate final report
        return self.generate_report()

    async def check_environment(self):
        """Verify the environment is properly configured."""
        print("\n1. Checking environment and configuration...")

        # Check Python version
        python_version = sys.version
        min_version = (3, 10)
        version_parts = python_version.split()[0].split(".")
        meets_requirement = tuple(map(int, version_parts[:2])) >= min_version

        self.results["environment_checks"]["python_version"] = {
            "version": python_version,
            "requirement": f">= {min_version[0]}.{min_version[1]}",
            "status": "PASS" if meets_requirement else "FAIL",
        }

        if not meets_requirement:
            self.results["issues"].append(
                f"Python version {python_version} does not meet minimum requirement {min_version[0]}.{min_version[1]}"
            )

        # Check .env file
        env_file_exists = os.path.exists(".env")
        self.results["environment_checks"]["env_file"] = {
            "exists": env_file_exists,
            "status": "PASS" if env_file_exists else "FAIL",
        }

        if not env_file_exists:
            self.results["issues"].append("Missing .env file")
            self.results["recommendations"].append(
                "Create a .env file with required configuration (see README.md)"
            )

        # Check API keys
        env_keys = ["OPENROUTER_API_KEY", "SERPER_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]

        for key in env_keys:
            exists = bool(os.environ.get(key, ""))
            self.results["environment_checks"][f"{key}_exists"] = {
                "exists": exists,
                "status": "PASS" if exists else "FAIL",
            }

            if not exists:
                self.results["issues"].append(f"Missing environment variable: {key}")

        # Check dependencies
        try:
            import importlib

            for package in ["openai", "pydantic", "fastapi", "chainlit", "supabase"]:
                try:
                    importlib.import_module(package)
                    self.results["environment_checks"][f"{package}_installed"] = {"status": "PASS"}
                except ImportError:
                    self.results["environment_checks"][f"{package}_installed"] = {"status": "FAIL"}
                    self.results["issues"].append(f"Missing required package: {package}")
                    self.results["recommendations"].append(
                        f"Install {package} with pip install {package}"
                    )
        except Exception as e:
            self.results["environment_checks"]["dependency_check"] = {
                "status": "FAIL",
                "error": str(e),
            }
            self.results["issues"].append(f"Error checking dependencies: {e}")

        # Check Docker configuration
        try:
            import subprocess

            result = subprocess.run(["docker-compose", "config"], capture_output=True, text=True)

            docker_valid = result.returncode == 0
            docker_output = result.stdout if docker_valid else result.stderr

            self.results["environment_checks"]["docker_config"] = {
                "valid": docker_valid,
                "output": docker_output[:500] + ("..." if len(docker_output) > 500 else ""),
                "status": "PASS" if docker_valid else "FAIL",
            }

            if not docker_valid:
                self.results["issues"].append("Docker configuration is invalid")
                self.results["recommendations"].append("Check docker-compose.yml for errors")

        except Exception as e:
            self.results["environment_checks"]["docker_config"] = {
                "status": "FAIL",
                "error": str(e),
            }
            self.results["issues"].append(f"Error checking Docker configuration: {e}")
            self.results["recommendations"].append("Ensure Docker and docker-compose are installed")

    async def test_components(self):
        """Test individual components of the factchecking pipeline."""
        print("\n2. Testing individual components...")

        # Test ClaimDetector
        print("  Testing ClaimDetector...")
        try:
            from src.agents.claim_detector.detector import ClaimDetector

            detector = ClaimDetector()
            test_text = "The Earth is approximately 4.54 billion years old. Water covers about 71% of the Earth's surface."

            start_time = time.time()
            claims = await detector.detect_claims(test_text)
            duration = time.time() - start_time

            self.results["component_tests"]["claim_detector"] = {
                "claims_detected": len(claims),
                "duration_seconds": duration,
                "status": "PASS" if len(claims) > 0 else "FAIL",
            }

            print(f"    Detected {len(claims)} claims in {duration:.2f} seconds")
            for i, claim in enumerate(claims):
                print(f"    Claim {i + 1}: {claim.text} (Checkworthy: {claim.checkworthy})")

        except Exception as e:
            self.results["component_tests"]["claim_detector"] = {"error": str(e), "status": "FAIL"}
            self.results["issues"].append(f"ClaimDetector test failed: {e}")
            print(f"    Error testing ClaimDetector: {e}")

        # Test EvidenceHunter
        print("  Testing EvidenceHunter...")
        try:
            from src.agents.claim_detector.detector import Claim
            from src.agents.evidence_hunter.hunter import EvidenceHunter

            hunter = EvidenceHunter()
            test_claim = Claim(
                text="The Earth is approximately 4.54 billion years old", checkworthy=True
            )

            start_time = time.time()
            evidence = await hunter.gather_evidence(test_claim)
            duration = time.time() - start_time

            self.results["component_tests"]["evidence_hunter"] = {
                "evidence_found": len(evidence),
                "duration_seconds": duration,
                "status": "PASS" if len(evidence) > 0 else "FAIL",
            }

            print(f"    Found {len(evidence)} pieces of evidence in {duration:.2f} seconds")
            for i, e in enumerate(evidence[:3]):  # Show first 3 pieces
                print(f"    Evidence {i + 1}: {e.source}")
                print(f"      Stance: {e.stance}, Relevance: {e.relevance}")
                print(f"      Content: {e.content[:100]}...")

        except Exception as e:
            self.results["component_tests"]["evidence_hunter"] = {"error": str(e), "status": "FAIL"}
            self.results["issues"].append(f"EvidenceHunter test failed: {e}")
            print(f"    Error testing EvidenceHunter: {e}")

        # Test VerdictWriter
        print("  Testing VerdictWriter...")
        try:
            from src.agents.evidence_hunter.hunter import Evidence
            from src.agents.verdict_writer.writer import VerdictWriter

            writer = VerdictWriter()
            test_claim = Claim(
                text="The Earth is approximately 4.54 billion years old", checkworthy=True
            )
            test_evidence = [
                Evidence(
                    content="Scientists have determined that the Earth is 4.54 billion years old with an error range of less than 1 percent.",
                    source="https://example.edu/earth-age",
                    relevance=0.95,
                    stance="supporting",
                ),
                Evidence(
                    content="Based on radiometric dating of meteorites, the age of Earth is estimated to be around 4.54 billion years.",
                    source="https://example.gov/earth-science",
                    relevance=0.93,
                    stance="supporting",
                ),
            ]

            start_time = time.time()
            verdict = await writer.generate_verdict(test_claim, test_evidence)
            duration = time.time() - start_time

            self.results["component_tests"]["verdict_writer"] = {
                "verdict": verdict.verdict,
                "confidence": verdict.confidence,
                "duration_seconds": duration,
                "status": (
                    "PASS"
                    if verdict.verdict
                    in [
                        "TRUE",
                        "LIKELY_TRUE",
                        "PARTLY_TRUE",
                        "UNCERTAIN",
                        "LIKELY_FALSE",
                        "FALSE",
                        "UNVERIFIABLE",
                    ]
                    else "FAIL"
                ),
            }

            print(f"    Generated verdict in {duration:.2f} seconds")
            print(f"    Verdict: {verdict.verdict}, Confidence: {verdict.confidence}")
            print(f"    Explanation: {verdict.explanation[:100]}...")

        except Exception as e:
            self.results["component_tests"]["verdict_writer"] = {"error": str(e), "status": "FAIL"}
            self.results["issues"].append(f"VerdictWriter test failed: {e}")
            print(f"    Error testing VerdictWriter: {e}")

    async def test_integration(self):
        """Test integration between components in the pipeline."""
        print("\n3. Testing pipeline integration...")

        try:
            from src.pipeline.factcheck_pipeline import (
                PipelineConfig,
            )

            config = PipelineConfig()
            from src.pipeline.factcheck_pipeline import create_default_pipeline

            pipeline = create_default_pipeline(config=config)

            test_text = "The Earth is approximately 4.54 billion years old. Water covers about 71% of the Earth's surface."

            start_time = time.time()
            results = await pipeline.process_text(test_text)
            duration = time.time() - start_time

            self.results["integration_tests"]["pipeline"] = {
                "claims_processed": len(results),
                "duration_seconds": duration,
                "status": "PASS" if len(results) > 0 else "FAIL",
            }

            print(f"  Processed {len(results)} claims in {duration:.2f} seconds")
            for i, result in enumerate(results):
                print(f"  Result {i + 1}:")
                print(f"    Claim: {result['claim']['text']}")
                print(f"    Verdict: {result['verdict']}, Confidence: {result['confidence']}")
                print(f"    Evidence pieces: {len(result['evidence'])}")

        except Exception as e:
            self.results["integration_tests"]["pipeline"] = {"error": str(e), "status": "FAIL"}
            self.results["issues"].append(f"Pipeline integration test failed: {e}")
            print(f"  Error testing pipeline integration: {e}")

        # Test batch processing
        try:
            # Re-use pipeline from above
            test_texts = [
                "The Earth is approximately 4.54 billion years old.",
                "Water covers about 71% of the Earth's surface.",
            ]

            start_time = time.time()
            batch_results = await pipeline.process_batch(test_texts)
            duration = time.time() - start_time

            total_claims = sum(len(result) for result in batch_results)

            self.results["integration_tests"]["batch_processing"] = {
                "texts_processed": len(test_texts),
                "claims_processed": total_claims,
                "duration_seconds": duration,
                "status": "PASS" if len(batch_results) == len(test_texts) else "FAIL",
            }

            print(
                f"  Processed {len(test_texts)} texts with {total_claims} claims in {duration:.2f} seconds"
            )

        except Exception as e:
            self.results["integration_tests"]["batch_processing"] = {
                "error": str(e),
                "status": "FAIL",
            }
            self.results["issues"].append(f"Batch processing test failed: {e}")
            print(f"  Error testing batch processing: {e}")

    async def test_api(self):
        """Test the REST API functionality."""
        print("\n4. Testing API endpoints...")

        api_url = "http://localhost:8000"

        # Check if API is running
        try:
            import requests

            print("  Checking if API server is running...")
            response = requests.get(f"{api_url}/docs")
            api_running = response.status_code == 200

            self.results["api_tests"]["api_running"] = {"status": "PASS" if api_running else "FAIL"}

            if not api_running:
                self.results["issues"].append("API server is not running")
                print("  ❌ API server is not running!")
                print("  Start the API server with: uvicorn src.main:app --reload")
                return
            else:
                print("  ✅ API server is running")

            # Test health endpoint
            print("  Testing GET /health...")
            response = requests.get(f"{api_url}/health")

            health_ok = response.status_code == 200
            self.results["api_tests"]["health_endpoint"] = {
                "status_code": response.status_code,
                "response": response.json() if health_ok else response.text,
                "status": "PASS" if health_ok else "FAIL",
            }

            if health_ok:
                print(f"  ✅ Health check passed: {response.status_code}")
            else:
                print(f"  ❌ Health check failed: {response.status_code}")
                self.results["issues"].append("Health endpoint failed")

            # Test factcheck endpoint
            print("  Testing POST /api/v1/factcheck...")

            test_data = {
                "text": "The Earth is approximately 4.54 billion years old.",
                "options": {"min_check_worthiness": 0.7},
            }

            response = requests.post(f"{api_url}/api/v1/factcheck", json=test_data)

            factcheck_ok = response.status_code == 200
            self.results["api_tests"]["factcheck_endpoint"] = {
                "status_code": response.status_code,
                "response_sample": response.json()[:200] if factcheck_ok else response.text[:200],
                "status": "PASS" if factcheck_ok else "FAIL",
            }

            if factcheck_ok:
                print(f"  ✅ Factcheck endpoint passed: {response.status_code}")
                result = response.json()
                print(f"  Claims found: {len(result)}")
            else:
                print(f"  ❌ Factcheck endpoint failed: {response.status_code}")
                self.results["issues"].append("Factcheck endpoint failed")

        except Exception as e:
            self.results["api_tests"]["error"] = {"error": str(e), "status": "FAIL"}
            self.results["issues"].append(f"API test failed: {e}")
            print(f"  Error testing API: {e}")

    async def test_system(self):
        """Run system tests to verify all components work together."""
        print("\n6. Running system tests...")

        # Test the full stack with different types of claims
        claim_types = [
            {
                "name": "true_claim",
                "text": "The Earth orbits around the Sun.",
                "expected_verdict": ["TRUE", "LIKELY_TRUE"],
            },
            {
                "name": "false_claim",
                "text": "The Sun orbits around the Earth.",
                "expected_verdict": ["FALSE", "LIKELY_FALSE"],
            },
            {
                "name": "partially_true_claim",
                "text": "COVID-19 vaccines are 100% effective against all variants.",
                "expected_verdict": ["PARTLY_TRUE", "UNCERTAIN"],
            },
            {
                "name": "unverifiable_claim",
                "text": "There are exactly 12,415 alien civilizations in our galaxy.",
                "expected_verdict": ["UNVERIFIABLE", "UNCERTAIN"],
            },
        ]

        try:
            from src.pipeline.factcheck_pipeline import (
                PipelineConfig,
            )

            config = PipelineConfig()
            from src.pipeline.factcheck_pipeline import create_default_pipeline

            pipeline = create_default_pipeline(config=config)

            for claim in claim_types:
                print(f'  Testing {claim["name"]}: "{claim["text"]}"')

                start_time = time.time()
                results = await pipeline.process_text(claim["text"])
                duration = time.time() - start_time

                if results and len(results) > 0:
                    verdict = results[0]["verdict"]
                    expected = claim["expected_verdict"]

                    passed = verdict in expected

                    self.results["system_tests"][claim["name"]] = {
                        "verdict": verdict,
                        "expected": expected,
                        "duration_seconds": duration,
                        "status": "PASS" if passed else "FAIL",
                    }

                    if passed:
                        print(f"    ✅ Got expected verdict: {verdict}")
                    else:
                        print(f"    ❌ Unexpected verdict: {verdict}, expected one of: {expected}")
                        self.results["issues"].append(
                            f"System test for {claim['name']} failed: got {verdict}, expected one of {expected}"
                        )
                else:
                    self.results["system_tests"][claim["name"]] = {
                        "error": "No results returned",
                        "status": "FAIL",
                    }
                    print("    ❌ No results returned")
                    self.results["issues"].append(
                        f"System test for {claim['name']} failed: no results returned"
                    )

        except Exception as e:
            self.results["system_tests"]["error"] = {"error": str(e), "status": "FAIL"}
            self.results["issues"].append(f"System tests failed: {e}")
            print(f"  Error running system tests: {e}")


@pytest.mark.skip("Full system test - run manually when needed")
async def test_verifact_system():
    """Run the complete VeriFact system test."""
    tester = VerifactTester()
    report_path = await tester.run_all_tests()
    assert report_path.exists(), "Test report should have been generated"


if __name__ == "__main__":
    asyncio.run(test_verifact_system())
