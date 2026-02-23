#!/usr/bin/env python3
"""
IDE Agent Wizard - Test Suite
=============================
Automated tests for v2.0.0

Usage:
    python tests/run_tests.py
    python tests/run_tests.py --quick      # Skip slow tests
    python tests/run_tests.py --docker     # Include Docker tests
"""

import sys
import os
import subprocess
import json
import time
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test Configuration
TEST_PORTS = {
    "kimi_agent": 8083,      # Production: 8081
    "web_ui": 8084,          # Production: 8082
}

TEST_CONTAINERS = {
    "kimi": "ide-agent-test-kimi",
    "web": "ide-agent-test-web"
}

# Colors for output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"

def log(msg, color=Colors.BLUE):
    print(f"{color}{msg}{Colors.END}")

def success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

# ============== TESTS ==============

def test_file_structure():
    """Test that all required files exist."""
    log("\n📁 Testing file structure...")
    
    required_files = [
        "setup.sh",
        "reset.sh",
        "init.yaml.example",
        ".env.example",
        "requirements.txt",
        "scripts/setup_wizard.py",
        "core/memory.py",
        "core/connectors/ide_connector.py",
        "bot/telegram_bot.py",
        "docker/docker-compose.yml",
        "docker/web-ui/app.py",
        "docker/kimi-agent-patch/app.py",
        "templates/general/SOUL.md",
        "docs/README.md",
    ]
    
    root = Path(__file__).parent.parent
    all_ok = True
    
    for file in required_files:
        path = root / file
        if path.exists():
            success(f"{file} exists")
        else:
            error(f"{file} missing")
            all_ok = False
    
    return all_ok

def test_python_syntax():
    """Test that Python files have valid syntax."""
    log("\n🐍 Testing Python syntax...")
    
    root = Path(__file__).parent.parent
    py_files = list(root.rglob("*.py"))
    
    all_ok = True
    for py_file in py_files:
        # Skip __pycache__
        if "__pycache__" in str(py_file):
            continue
        
        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", str(py_file)],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                success(f"{py_file.name} - OK")
            else:
                error(f"{py_file.name} - Syntax error")
                all_ok = False
        except Exception as e:
            error(f"{py_file.name} - {e}")
            all_ok = False
    
    return all_ok

def test_docker_compose_syntax():
    """Test Docker Compose files are valid."""
    log("\n🐳 Testing Docker Compose syntax...")
    
    compose_files = [
        "docker/docker-compose.yml",
        "tests/docker-compose.test.yml"
    ]
    
    root = Path(__file__).parent.parent
    all_ok = True
    
    for compose_file in compose_files:
        path = root / compose_file
        if not path.exists():
            warning(f"{compose_file} not found, skipping")
            continue
        
        try:
            # Create dummy .env if needed
            env_file = root / ".env"
            env_created = False
            if not env_file.exists():
                env_file.write_text("# Test env\nKIMI_API_KEY=test\n")
                env_created = True
            
            result = subprocess.run(
                ["docker", "compose", "-f", str(path), "config"],
                capture_output=True,
                timeout=10
            )
            
            # Cleanup dummy .env
            if env_created:
                env_file.unlink()
            
            # Check if valid (ignore warnings)
            stderr = result.stderr.decode()
            if result.returncode == 0 or "services:" in result.stdout.decode():
                success(f"{compose_file} - Valid")
            else:
                error(f"{compose_file} - Invalid")
                print(stderr)
                all_ok = False
        except Exception as e:
            error(f"{compose_file} - {e}")
            all_ok = False
    
    return all_ok

def test_port_availability():
    """Test that test ports are available."""
    log("\n🔌 Testing port availability...")
    
    import socket
    
    all_ok = True
    for service, port in TEST_PORTS.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("0.0.0.0", port))
            success(f"Port {port} ({service}) - Available")
        except socket.error:
            error(f"Port {port} ({service}) - In use!")
            all_ok = False
        finally:
            sock.close()
    
    return all_ok

def test_docker_containers():
    """Test Docker containers can start and respond."""
    log("\n🐳 Testing Docker containers...")
    
    compose_file = Path(__file__).parent / "docker-compose.test.yml"
    if not compose_file.exists():
        warning("docker-compose.test.yml not found, skipping")
        return True
    
    all_ok = True
    
    try:
        # Start containers
        log("  Starting test containers...")
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "--profile", "test", "up", "-d"],
            capture_output=True,
            timeout=60
        )
        
        if result.returncode != 0:
            error("Failed to start containers")
            print(result.stderr.decode())
            return False
        
        # Wait for containers to be ready
        log("  Waiting for containers...")
        time.sleep(5)
        
        # Test Kimi Agent (port 8083)
        try:
            import httpx
            response = httpx.get(f"http://localhost:{TEST_PORTS['kimi_agent']}/health", timeout=10)
            if response.status_code == 200:
                success("Kimi Agent (test port 8083) - Responding")
            else:
                error(f"Kimi Agent - Status {response.status_code}")
                all_ok = False
        except Exception as e:
            error(f"Kimi Agent - {e}")
            all_ok = False
        
        # Stop containers
        log("  Stopping test containers...")
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "--profile", "test", "down"],
            capture_output=True,
            timeout=30
        )
        
    except Exception as e:
        error(f"Docker test failed: {e}")
        all_ok = False
        # Cleanup
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "--profile", "test", "down"],
            capture_output=True
        )
    
    return all_ok

def test_setup_wizard():
    """Test setup wizard can load (dry run)."""
    log("\n🧙 Testing setup wizard...")
    
    try:
        # Try to import the module
        from scripts.setup_wizard import SetupWizard
        success("SetupWizard imports successfully")
        
        # Create instance (don't run)
        wizard = SetupWizard()
        success("SetupWizard instantiates")
        
        return True
    except Exception as e:
        error(f"Setup wizard test failed: {e}")
        return False

def test_core_modules():
    """Test core modules can be imported."""
    log("\n⚙️  Testing core modules...")
    
    modules = [
        ("core.memory", "MemoryStore"),
        ("core.connectors.ide_connector", "IDEConnector"),
        ("core.providers.kimi_provider", None),
        ("core.providers.anthropic_provider", None),
    ]
    
    all_ok = True
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name or "__init__"])
            if class_name:
                getattr(module, class_name)
                success(f"{module_name}.{class_name} - OK")
            else:
                success(f"{module_name} - OK")
        except Exception as e:
            error(f"{module_name} - {e}")
            all_ok = False
    
    return all_ok

def test_no_sensitive_files():
    """Test that no sensitive files are in the release."""
    log("\n🔒 Testing for sensitive files...")
    
    root = Path(__file__).parent.parent
    
    sensitive_patterns = [
        "init.yaml",      # Should be .example
        ".env",           # Should be .example
        "workspace/",     # User data
        ".venv/",         # Virtual env
        "__pycache__/",   # Cache
        "*.pyc",
    ]
    
    all_ok = True
    for pattern in sensitive_patterns:
        # Check if pattern exists
        if pattern.endswith("/"):
            # Directory
            path = root / pattern.rstrip("/")
            if path.exists():
                error(f"{pattern} should not exist in release")
                all_ok = False
            else:
                success(f"{pattern} - Not present")
        else:
            # File
            if pattern.startswith("*"):
                # Glob pattern
                matches = list(root.glob(pattern))
                if matches:
                    error(f"{pattern} files found: {matches}")
                    all_ok = False
                else:
                    success(f"{pattern} - No matches")
            else:
                path = root / pattern
                if path.exists():
                    error(f"{pattern} should not exist in release")
                    all_ok = False
                else:
                    success(f"{pattern} - Not present")
    
    return all_ok

# ============== MAIN ==============

def main():
    parser = argparse.ArgumentParser(description="IDE Agent Wizard Test Suite")
    parser.add_argument("--quick", action="store_true", help="Skip slow tests (Docker)")
    parser.add_argument("--docker", action="store_true", help="Include Docker tests")
    args = parser.parse_args()
    
    log("=" * 60)
    log("IDE AGENT WIZARD - TEST SUITE v2.0.0")
    log("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Syntax", test_python_syntax),
        ("Docker Compose Syntax", test_docker_compose_syntax),
        ("Port Availability", test_port_availability),
        ("Setup Wizard", test_setup_wizard),
        ("Core Modules", test_core_modules),
        ("Security Check", test_no_sensitive_files),
    ]
    
    if args.docker:
        tests.append(("Docker Containers", test_docker_containers))
    elif not args.quick:
        warning("Skipping Docker tests (use --docker to include)")
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        if result:
            success(f"{name}")
        else:
            error(f"{name}")
    
    log("=" * 60)
    log(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        log("\n🎉 ALL TESTS PASSED!", Colors.GREEN)
        return 0
    else:
        log(f"\n❌ {failed} TEST(S) FAILED", Colors.RED)
        return 1

if __name__ == "__main__":
    sys.exit(main())
