# Changelog

All notable changes to the Sumano Operations Management System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup and scaffolding
- Django backend project (`ops_backend`)
- Docker and Docker Compose configuration
- CI/CD pipeline with GitHub Actions
- PDF generation capabilities with WeasyPrint
- Security scanning with pip-audit
- Pre-commit hooks for code quality
- Comprehensive documentation (README.md, .env.example)
- Canonical naming enforcement

## [0.2.0] - 2024-01-XX

### Added
- PostgreSQL 14 database configuration
- ServiceProject model for Sumano Tech service delivery tracking
- Service type categorization (web development, mobile apps, OMS, portals, audits)
- Database connection tests with pytest
- MVP foundation for client service delivery tracking

### Infrastructure
- Docker containerization with Python 3.11
- System dependencies for PDF generation (libcairo2, libpango-1.0-0, libgdk-pixbuf2.0-0)
- CI pipeline stages: lint → tests → build → PDF smoke-test
- Dependency vulnerability scanning

## [0.1.0] - 2024-01-XX

### Added
- Initial project initialization (Prompt 0)
- Repository structure and naming conventions
- Development environment setup
- Documentation foundation
