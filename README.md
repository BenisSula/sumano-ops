# Sumano Operations Management System (OMS)

A comprehensive operations management system for Sumano Tech's service delivery tracking and project management. Built with Django backend and designed to support our technology services (web development, mobile apps, OMS, portals, and audits).

## Project Structure

```
sumano-ops/
├── ops_backend/          # Django backend application
├── frontend/             # React frontend application
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile           # Docker configuration for backend
├── .env.example         # Environment variables template
├── CHANGELOG.md         # Project changelog
└── README.md           # This file
```

## Tech Stack

- **Backend**: Python 3.11, Django 4.x, Django REST Framework
- **Database**: PostgreSQL 14
- **Frontend**: React 18, React Router DOM, Axios (future)
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **PDF Generation**: WeasyPrint
- **Security**: pip-audit for dependency scanning

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 14+ (included in Docker setup)
- Node.js 18+ (for future frontend development)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sumano-ops
   ```

2. **Quick Start (Recommended)**
   ```bash
   # Windows
   scripts\start_dev.bat
   
   # Linux/Mac
   chmod +x scripts/start_dev.sh
   ./scripts/start_dev.sh
   ```

3. **Manual Setup**
   ```bash
   # Environment Configuration
   cp env.example .env
   # Edit .env with your configuration
   
   # Start with Docker Compose
   docker-compose up --build
   ```

4. **Access the Application**
   - Backend API: http://localhost:8000
   - Health Check: http://localhost:8000/health/
   - PDF Test: http://localhost:8000/api/pdf/test/
   - PostgreSQL Database: localhost:5432 (user: postgres, password: postgres, db: sumano_ops)

### Local Development

#### Backend Development
```bash
cd ops_backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment variables
cp ../env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

#### Frontend Development
```bash
cd frontend
npm install
npm start
```

## MVP Features

This backend skeleton provides the foundation for Sumano Tech's service delivery tracking:

### Service Delivery Tracking
- **ServiceProject Model**: Track all client service delivery projects
- **Service Types**: Web Development, Mobile Apps, Operations Systems, Portals, Audits
- **Project Status**: Planning, In Progress, Testing, Delivered, Ongoing Support, Completed
- **Client Management**: Track client names and project details

### Core Infrastructure
- Django REST Framework for API development
- PostgreSQL database for reliable data storage
- Docker containerization for consistent deployment
- Comprehensive testing with pytest
- Code quality tools (flake8, black)

## CI/CD Pipeline

The project includes a comprehensive CI/CD pipeline with the following stages:

1. **Lint**: Code formatting and style checks
2. **Tests**: Unit and integration tests
3. **Build**: Docker image build verification
4. **PDF Smoke Test**: Validates PDF generation functionality
5. **Security**: Dependency vulnerability scanning with pip-audit

### PDF Smoke Test

The CI pipeline includes a PDF smoke test that generates a "Hello OMS" PDF to validate the WeasyPrint installation and PDF generation capabilities.

## Canonical Naming

This project enforces strict canonical naming conventions:

- Repository: `sumano-ops`
- Django project: `ops_backend`
- Docker service: `ops_backend`

Any deviation from these names will cause CI failures to prevent naming drift.

## Security

- No secrets stored in the repository
- Environment variables managed through `.env` files
- Dependencies scanned with `pip-audit`
- Pre-commit hooks configured for code quality

## Validation

To validate your setup is working correctly:

```bash
# Run the validation script
python scripts/validate_setup.py

# Or test specific components
docker-compose up --build
curl http://localhost:8000/health/
curl -o test.pdf http://localhost:8000/api/pdf/test/
```

## Contributing

1. Follow the canonical naming conventions
2. Ensure all CI checks pass
3. Update the CHANGELOG.md for significant changes
4. Write tests for new features

## License

[Add your license information here]
