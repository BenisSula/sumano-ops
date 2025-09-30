#!/usr/bin/env python3
"""
Test script to validate the Sumano OMS setup.
This script checks if all required components are properly configured.
"""
import os
import sys
import subprocess
from pathlib import Path


def check_file_exists(file_path, description):
    """Check if a file exists and print status."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - NOT FOUND")
        return False


def check_directory_exists(dir_path, description):
    """Check if a directory exists and print status."""
    if os.path.isdir(dir_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} - NOT FOUND")
        return False


def check_canonical_naming():
    """Check if canonical naming is enforced."""
    print("\n🔍 Checking Canonical Naming...")
    
    checks = [
        (check_directory_exists, "ops_backend/", "Django project directory"),
        (check_directory_exists, "ops_backend/ops_backend/", "Django project package"),
        (check_file_exists, "ops_backend/manage.py", "Django manage.py"),
        (check_file_exists, "docker-compose.yml", "Docker Compose file"),
        (check_file_exists, "Dockerfile", "Dockerfile"),
    ]
    
    all_passed = True
    for check_func, path, description in checks:
        if not check_func(path, description):
            all_passed = False
    
    # Check docker-compose.yml for canonical service name
    try:
        with open("docker-compose.yml", "r") as f:
            content = f.read()
            if "ops_backend:" in content:
                print("✅ Docker service name: ops_backend")
            else:
                print("❌ Docker service name: NOT FOUND or INCORRECT")
                all_passed = False
    except FileNotFoundError:
        print("❌ Cannot check docker-compose.yml - file not found")
        all_passed = False
    
    return all_passed


def check_python_dependencies():
    """Check if Python dependencies can be installed."""
    print("\n🐍 Checking Python Dependencies...")
    
    try:
        # Try to read requirements.txt
        with open("ops_backend/requirements.txt", "r") as f:
            requirements = f.read()
            if "Django==4.2.7" in requirements:
                print("✅ Django 4.2.7 in requirements.txt")
            else:
                print("❌ Django 4.2.7 not found in requirements.txt")
                return False
            
            if "WeasyPrint==60.2" in requirements:
                print("✅ WeasyPrint 60.2 in requirements.txt")
            else:
                print("❌ WeasyPrint 60.2 not found in requirements.txt")
                return False
        
        return True
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False


def check_docker_setup():
    """Check if Docker setup is correct."""
    print("\n🐳 Checking Docker Setup...")
    
    checks = [
        (check_file_exists, "Dockerfile", "Dockerfile"),
        (check_file_exists, "docker-compose.yml", "Docker Compose file"),
    ]
    
    all_passed = True
    for check_func, path, description in checks:
        if not check_func(path, description):
            all_passed = False
    
    # Check Dockerfile for required dependencies
    try:
        with open("Dockerfile", "r") as f:
            content = f.read()
            required_deps = [
                "libcairo2",
                "libpango-1.0-0", 
                "libgdk-pixbuf2.0-0"
            ]
            
            for dep in required_deps:
                if dep in content:
                    print(f"✅ System dependency: {dep}")
                else:
                    print(f"❌ System dependency: {dep} - NOT FOUND")
                    all_passed = False
    except FileNotFoundError:
        print("❌ Cannot check Dockerfile - file not found")
        all_passed = False
    
    return all_passed


def check_ci_pipeline():
    """Check if CI pipeline is configured."""
    print("\n🔄 Checking CI/CD Pipeline...")
    
    checks = [
        (check_directory_exists, ".github/", "GitHub Actions directory"),
        (check_directory_exists, ".github/workflows/", "GitHub Actions workflows"),
        (check_file_exists, ".github/workflows/ci.yml", "CI workflow file"),
        (check_file_exists, ".pre-commit-config.yaml", "Pre-commit configuration"),
    ]
    
    all_passed = True
    for check_func, path, description in checks:
        if not check_func(path, description):
            all_passed = False
    
    # Check CI workflow for required stages
    try:
        with open(".github/workflows/ci.yml", "r") as f:
            content = f.read()
            required_stages = [
                "lint",
                "test", 
                "build",
                "pdf-smoke-test"
            ]
            
            for stage in required_stages:
                if stage in content:
                    print(f"✅ CI stage: {stage}")
                else:
                    print(f"❌ CI stage: {stage} - NOT FOUND")
                    all_passed = False
    except FileNotFoundError:
        print("❌ Cannot check CI workflow - file not found")
        all_passed = False
    
    return all_passed


def check_documentation():
    """Check if documentation is present."""
    print("\n📚 Checking Documentation...")
    
    checks = [
        (check_file_exists, "README.md", "README.md"),
        (check_file_exists, "CHANGELOG.md", "CHANGELOG.md"),
        (check_file_exists, "env.example", "Environment example file"),
        (check_file_exists, ".gitignore", ".gitignore"),
    ]
    
    all_passed = True
    for check_func, path, description in checks:
        if not check_func(path, description):
            all_passed = False
    
    return all_passed


def main():
    """Main test function."""
    print("🚀 Sumano OMS Setup Validation")
    print("=" * 50)
    
    all_checks = [
        check_canonical_naming,
        check_python_dependencies,
        check_docker_setup,
        check_ci_pipeline,
        check_documentation,
    ]
    
    passed_checks = 0
    total_checks = len(all_checks)
    
    for check in all_checks:
        if check():
            passed_checks += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("🎉 All checks passed! Setup is complete.")
        return 0
    else:
        print("⚠️  Some checks failed. Please review the setup.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
