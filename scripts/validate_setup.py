#!/usr/bin/env python3
"""
Simple validation script for Sumano OMS setup.
Checks file structure and configuration without requiring Python installation.
"""
import os
from pathlib import Path


def check_structure():
    """Check if the project structure is correct."""
    print("🔍 Validating Sumano OMS Project Structure...")
    print("=" * 50)
    
    # Required files and directories
    required_items = [
        # Core Django files
        ("ops_backend/", "Django project directory"),
        ("ops_backend/manage.py", "Django manage.py"),
        ("ops_backend/requirements.txt", "Python requirements"),
        ("ops_backend/ops_backend/", "Django project package"),
        ("ops_backend/ops_backend/__init__.py", "Django package init"),
        ("ops_backend/ops_backend/urls.py", "Django URL configuration"),
        ("ops_backend/ops_backend/wsgi.py", "Django WSGI configuration"),
        ("ops_backend/ops_backend/asgi.py", "Django ASGI configuration"),
        
        # Settings
        ("ops_backend/ops_backend/settings/", "Django settings directory"),
        ("ops_backend/ops_backend/settings/base.py", "Base settings"),
        ("ops_backend/ops_backend/settings/development.py", "Development settings"),
        ("ops_backend/ops_backend/settings/production.py", "Production settings"),
        
        # Core app
        ("ops_backend/apps/", "Apps directory"),
        ("ops_backend/apps/core/", "Core app directory"),
        ("ops_backend/apps/core/apps.py", "Core app configuration"),
        ("ops_backend/apps/core/views/", "Core views directory"),
        ("ops_backend/apps/core/urls/", "Core URLs directory"),
        ("ops_backend/apps/core/tests/", "Core tests directory"),
        
        # Docker configuration
        ("Dockerfile", "Docker configuration"),
        ("docker-compose.yml", "Docker Compose configuration"),
        
        # CI/CD
        (".github/workflows/", "GitHub Actions workflows"),
        (".github/workflows/ci.yml", "CI/CD pipeline"),
        (".pre-commit-config.yaml", "Pre-commit hooks"),
        
        # Documentation
        ("README.md", "Project README"),
        ("CHANGELOG.md", "Project changelog"),
        ("env.example", "Environment variables example"),
        (".gitignore", "Git ignore file"),
    ]
    
    passed = 0
    total = len(required_items)
    
    for path, description in required_items:
        if os.path.exists(path):
            print(f"✅ {description}: {path}")
            passed += 1
        else:
            print(f"❌ {description}: {path} - NOT FOUND")
    
    print("\n" + "=" * 50)
    print(f"📊 Structure Check: {passed}/{total} items found")
    
    return passed == total


def check_canonical_naming():
    """Check canonical naming conventions."""
    print("\n🏷️  Validating Canonical Naming...")
    print("=" * 50)
    
    naming_checks = [
        ("ops_backend/", "Django project directory name"),
        ("ops_backend/ops_backend/", "Django project package name"),
    ]
    
    # Check docker-compose.yml for service name
    docker_service_check = False
    try:
        with open("docker-compose.yml", "r") as f:
            content = f.read()
            if "ops_backend:" in content:
                docker_service_check = True
                print("✅ Docker service name: ops_backend")
            else:
                print("❌ Docker service name: NOT FOUND or INCORRECT")
    except FileNotFoundError:
        print("❌ Cannot check docker-compose.yml")
    
    passed = 0
    total = len(naming_checks) + 1
    
    for path, description in naming_checks:
        if os.path.exists(path):
            print(f"✅ {description}: {path}")
            passed += 1
        else:
            print(f"❌ {description}: {path} - NOT FOUND")
    
    if docker_service_check:
        passed += 1
    
    print(f"\n📊 Naming Check: {passed}/{total} checks passed")
    
    return passed == total


def check_dependencies():
    """Check if required dependencies are specified."""
    print("\n📦 Validating Dependencies...")
    print("=" * 50)
    
    try:
        with open("ops_backend/requirements.txt", "r") as f:
            content = f.read()
            
        required_deps = [
            "Django==4.2.7",
            "WeasyPrint==60.2",
            "djangorestframework==3.14.0",
            "django-cors-headers==4.3.1",
            "gunicorn==21.2.0",
            "pip-audit==2.6.1",
        ]
        
        passed = 0
        total = len(required_deps)
        
        for dep in required_deps:
            if dep in content:
                print(f"✅ {dep}")
                passed += 1
            else:
                print(f"❌ {dep} - NOT FOUND")
        
        print(f"\n📊 Dependencies Check: {passed}/{total} dependencies found")
        
        return passed == total
        
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False


def check_ci_pipeline():
    """Check CI pipeline configuration."""
    print("\n🔄 Validating CI/CD Pipeline...")
    print("=" * 50)
    
    try:
        with open(".github/workflows/ci.yml", "r") as f:
            content = f.read()
        
        required_stages = [
            "lint",
            "test",
            "build", 
            "pdf-smoke-test",
            "security-audit",
            "canonical-naming-check"
        ]
        
        passed = 0
        total = len(required_stages)
        
        for stage in required_stages:
            if stage in content:
                print(f"✅ CI stage: {stage}")
                passed += 1
            else:
                print(f"❌ CI stage: {stage} - NOT FOUND")
        
        print(f"\n📊 CI Pipeline Check: {passed}/{total} stages found")
        
        return passed == total
        
    except FileNotFoundError:
        print("❌ CI workflow file not found")
        return False


def main():
    """Main validation function."""
    print("🚀 Sumano OMS Setup Validation")
    print("Repository: sumano-ops")
    print("Django Project: ops_backend")
    print("Docker Service: ops_backend")
    print()
    
    checks = [
        check_structure,
        check_canonical_naming,
        check_dependencies,
        check_ci_pipeline,
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    for check in checks:
        if check():
            passed_checks += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 FINAL RESULTS: {passed_checks}/{total_checks} validation checks passed")
    
    if passed_checks == total_checks:
        print("\n🎉 SUCCESS! Sumano OMS setup is complete and valid.")
        print("\nNext steps:")
        print("1. Copy env.example to .env and configure your environment")
        print("2. Run: docker-compose up --build")
        print("3. Access: http://localhost:8000/health/")
        print("4. Test PDF generation: http://localhost:8000/api/pdf/test/")
        return True
    else:
        print("\n⚠️  Some validation checks failed. Please review the setup.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
