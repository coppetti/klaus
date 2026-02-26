#!/usr/bin/env python3
"""
Test Runner for IDE Agent Wizard
================================
Run all tests: python tests/run_tests.py
Run unit tests only: python tests/run_tests.py --unit
Run integration tests: python tests/run_tests.py --integration
"""

import sys
import os
import argparse
import unittest

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_tests(test_type="all", verbose=False):
    """Run test suite."""
    
    # Discover tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    if test_type in ("all", "unit"):
        try:
            unit_tests = loader.discover(
                os.path.join(test_dir, "unit"),
                pattern="test_*.py"
            )
            suite.addTests(unit_tests)
            print(f"✅ Loaded unit tests")
        except Exception as e:
            print(f"⚠️  Could not load unit tests: {e}")
    
    if test_type in ("all", "integration"):
        try:
            integration_tests = loader.discover(
                os.path.join(test_dir, "integration"),
                pattern="test_*.py"
            )
            suite.addTests(integration_tests)
            print(f"✅ Loaded integration tests")
        except Exception as e:
            print(f"⚠️  Could not load integration tests: {e}")
    
    # Run tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description="Run IDE Agent Wizard tests")
    parser.add_argument(
        "--unit", 
        action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--integration",
        action="store_true", 
        help="Run integration tests only"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Determine test type
    test_type = "all"
    if args.unit:
        test_type = "unit"
    elif args.integration:
        test_type = "integration"
    
    print(f"🧪 Running {test_type} tests...")
    print("=" * 50)
    
    exit_code = run_tests(test_type, args.verbose)
    
    print("=" * 50)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
