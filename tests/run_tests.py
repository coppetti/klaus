#!/usr/bin/env python3
"""
Test Runner for Klaus
=====================

Usage:
    python tests/run_tests.py              # Run all tests
    python tests/run_tests.py unit         # Run unit tests only
    python tests/run_tests.py integration  # Run integration tests only
    python tests/run_tests.py e2e          # Run E2E tests only
    python tests/run_tests.py coverage     # Run with coverage report
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Klaus Test Runner")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "e2e", "coverage"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-x", "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    pytest_base = "python -m pytest"
    
    if args.verbose:
        pytest_base += " -v"
    if args.fail_fast:
        pytest_base += " -x"
    
    test_dir = Path(__file__).parent
    returncode = 0
    
    if args.test_type == "all":
        print("🧪 Running ALL tests...")
        cmd = f"{pytest_base} {test_dir} --tb=short"
        returncode = run_command(cmd, "All Tests")
        
    elif args.test_type == "unit":
        print("🔬 Running UNIT tests...")
        cmd = f"{pytest_base} {test_dir}/unit --tb=short"
        returncode = run_command(cmd, "Unit Tests")
        
    elif args.test_type == "integration":
        print("🔗 Running INTEGRATION tests...")
        cmd = f"{pytest_base} {test_dir}/integration --tb=short"
        returncode = run_command(cmd, "Integration Tests")
        
    elif args.test_type == "e2e":
        print("🎭 Running E2E tests...")
        cmd = f"{pytest_base} {test_dir}/e2e --tb=short"
        returncode = run_command(cmd, "E2E Tests")
        
    elif args.test_type == "coverage":
        print("📊 Running tests with COVERAGE...")
        cmd = (
            f"{pytest_base} {test_dir} "
            f"--cov=core "
            f"--cov=docker/web-ui "
            f"--cov-report=html:coverage_html "
            f"--cov-report=term-missing "
            f"--tb=short"
        )
        returncode = run_command(cmd, "Tests with Coverage")
        
        if returncode == 0:
            print("\n✅ Coverage report generated in: coverage_html/index.html")
    
    print(f"\n{'='*60}")
    if returncode == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with code: {returncode}")
    print(f"{'='*60}\n")
    
    return returncode


if __name__ == "__main__":
    sys.exit(main())
