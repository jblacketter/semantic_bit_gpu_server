#!/usr/bin/env python3
"""
Semantic Bit GPU Server - Automated Smoke Tests
Phase A.5: Pre-flight verification before integration work

This script exercises all endpoints and verifies:
- Status codes match expectations
- Response headers are present
- Error formats are consistent
- Image generation works

Run this AFTER manual testing (Phase B) as the gating check.
"""

import sys
import httpx
import time
from pathlib import Path
from typing import Dict, Any


class SmokeTestRunner:
    """Automated smoke test runner for GPU server"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=60.0)
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0

    def log(self, message: str, level: str = "INFO"):
        """Print formatted log message"""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️ ",
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️ "
        }.get(level, "  ")
        print(f"[{timestamp}] {prefix} {message}")

    def assert_equals(self, actual, expected, test_name: str):
        """Assert equality and track test result"""
        self.tests_run += 1
        if actual == expected:
            self.tests_passed += 1
            self.log(f"{test_name}: PASS", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"{test_name}: FAIL (expected {expected}, got {actual})", "FAIL")
            return False

    def assert_in(self, item, container, test_name: str):
        """Assert item in container and track test result"""
        self.tests_run += 1
        if item in container:
            self.tests_passed += 1
            self.log(f"{test_name}: PASS", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"{test_name}: FAIL ({item} not in {container})", "FAIL")
            return False

    def assert_true(self, condition: bool, test_name: str):
        """Assert condition is true and track test result"""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"{test_name}: PASS", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"{test_name}: FAIL", "FAIL")
            return False

    def test_root_endpoint(self):
        """Test GET / - API information"""
        self.log("Testing GET /", "INFO")
        response = self.client.get(f"{self.base_url}/")

        self.assert_equals(response.status_code, 200, "Root: Status 200")

        data = response.json()
        self.assert_equals(data.get("service"), "Semantic Bit GPU Server", "Root: Service name")
        self.assert_in("endpoints", data, "Root: Has endpoints field")

    def test_health_endpoint(self):
        """Test GET /health - Health check"""
        self.log("Testing GET /health", "INFO")
        response = self.client.get(f"{self.base_url}/health")

        self.assert_equals(response.status_code, 200, "Health: Status 200")

        data = response.json()
        self.assert_equals(data.get("status"), "healthy", "Health: Status healthy")
        self.assert_true(data.get("model_loaded", False), "Health: Model loaded")
        self.assert_in("generator_info", data, "Health: Has generator_info")

    def test_generate_valid(self):
        """Test POST /generate with valid parameters"""
        self.log("Testing POST /generate (valid params)", "INFO")

        request_data = {
            "prompt": "a red apple on a white table, studio lighting",
            "num_inference_steps": 28,
            "guidance_scale": 7.0,
            "height": 512,
            "width": 512,
            "seed": 42,
            "scheduler": "dpmsolver++"
        }

        start_time = time.time()
        response = self.client.post(
            f"{self.base_url}/generate",
            json=request_data
        )
        elapsed = time.time() - start_time

        self.assert_equals(response.status_code, 200, "Generate: Status 200")
        self.assert_equals(response.headers.get("content-type"), "image/png", "Generate: Content-Type PNG")

        # Check metadata headers
        self.assert_true("x-seed" in response.headers, "Generate: Has X-Seed header")
        self.assert_true("x-steps" in response.headers, "Generate: Has X-Steps header")
        self.assert_true("x-guidance" in response.headers, "Generate: Has X-Guidance header")
        self.assert_true("x-scheduler" in response.headers, "Generate: Has X-Scheduler header")
        self.assert_true("x-device" in response.headers, "Generate: Has X-Device header")
        self.assert_true("x-generation-time" in response.headers, "Generate: Has X-Generation-Time header")
        self.assert_equals(response.headers.get("cache-control"), "no-store", "Generate: Cache-Control no-store")

        # Verify header values
        self.assert_equals(response.headers.get("x-seed"), "42", "Generate: Seed matches")
        self.assert_equals(response.headers.get("x-steps"), "28", "Generate: Steps matches")
        self.assert_equals(response.headers.get("x-scheduler"), "dpmsolver++", "Generate: Scheduler matches")

        # Check image is valid
        self.assert_true(len(response.content) > 1000, "Generate: Image has reasonable size")
        self.assert_true(response.content.startswith(b'\x89PNG'), "Generate: Image is PNG")

        self.log(f"Generation took {elapsed:.2f}s", "INFO")

    def test_generate_validation_error(self):
        """Test POST /generate with invalid parameters (bounds check)"""
        self.log("Testing POST /generate (validation error)", "INFO")

        # Steps too low
        request_data = {
            "prompt": "test",
            "num_inference_steps": 2  # Min is 5
        }

        response = self.client.post(
            f"{self.base_url}/generate",
            json=request_data
        )

        self.assert_equals(response.status_code, 422, "Validation: Status 422")
        self.assert_equals(response.headers.get("content-type"), "application/json", "Validation: Content-Type JSON")

        data = response.json()
        self.assert_equals(data.get("error"), "ValidationError", "Validation: Error type")
        self.assert_equals(data.get("code"), 422, "Validation: Error code")
        self.assert_in("detail", data, "Validation: Has detail")
        self.assert_in("meta", data, "Validation: Has meta")

    def test_generate_dimension_not_multiple_of_8(self):
        """Test POST /generate with dimensions not multiple of 8"""
        self.log("Testing POST /generate (dimension validation)", "INFO")

        request_data = {
            "prompt": "test",
            "height": 513  # Not multiple of 8
        }

        response = self.client.post(
            f"{self.base_url}/generate",
            json=request_data
        )

        self.assert_equals(response.status_code, 422, "Dimension: Status 422")

        data = response.json()
        self.assert_equals(data.get("error"), "ValidationError", "Dimension: Error type")

    def test_seed_reproducibility(self):
        """Test that same seed produces identical images"""
        self.log("Testing seed reproducibility", "INFO")

        request_data = {
            "prompt": "a small cactus in a terracotta pot",
            "seed": 999,
            "num_inference_steps": 20  # Faster for testing
        }

        # Generate first image
        response1 = self.client.post(f"{self.base_url}/generate", json=request_data)
        self.assert_equals(response1.status_code, 200, "Seed1: Status 200")

        # Generate second image with same seed
        response2 = self.client.post(f"{self.base_url}/generate", json=request_data)
        self.assert_equals(response2.status_code, 200, "Seed2: Status 200")

        # Compare images
        self.assert_equals(response1.content, response2.content, "Seed: Images identical")

    def run_all_tests(self):
        """Run complete smoke test suite"""
        self.log("=" * 60)
        self.log("Semantic Bit GPU Server - Smoke Tests")
        self.log("=" * 60)
        self.log("")

        try:
            # Test server is reachable
            self.log("Checking if server is running...", "INFO")
            try:
                response = self.client.get(f"{self.base_url}/")
                self.log(f"Server is reachable at {self.base_url}", "INFO")
            except httpx.ConnectError:
                self.log(f"FATAL: Cannot connect to {self.base_url}", "FAIL")
                self.log("Make sure the server is running: uvicorn server.main:app --host 0.0.0.0 --port 8000", "WARN")
                return False

            self.log("")

            # Run tests
            self.test_root_endpoint()
            self.log("")

            self.test_health_endpoint()
            self.log("")

            self.test_generate_valid()
            self.log("")

            self.test_generate_validation_error()
            self.log("")

            self.test_generate_dimension_not_multiple_of_8()
            self.log("")

            self.test_seed_reproducibility()
            self.log("")

        except Exception as e:
            self.log(f"FATAL ERROR: {e}", "FAIL")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.client.close()

        # Print summary
        self.log("=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total:  {self.tests_run}")
        self.log(f"Passed: {self.tests_passed} ✅")
        self.log(f"Failed: {self.tests_failed} ❌")

        if self.tests_failed == 0:
            self.log("")
            self.log("🎉 ALL TESTS PASSED - GPU Server is ready for integration!", "PASS")
            self.log("")
            return True
        else:
            self.log("")
            self.log(f"❌ {self.tests_failed} TESTS FAILED - Fix issues before proceeding", "FAIL")
            self.log("")
            return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="GPU Server Smoke Tests")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="GPU server base URL (default: http://localhost:8000)"
    )
    args = parser.parse_args()

    runner = SmokeTestRunner(base_url=args.url)
    success = runner.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
