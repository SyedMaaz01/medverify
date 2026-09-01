# MedVerify - Pharmaceutical Batch Verification System

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-purple.svg)](https://fastapi.tiangolo.com/)
[![React + TypeScript](https://img.shields.io/badge/React-TypeScript-blue.svg)](https://react.dev/)

**A production-grade medicine batch authenticity verification system via QR codes.**

[Features](#features) • [Architecture](#architecture) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## 🎯 Overview

MedVerify is an open-source platform that enables pharmaceutical manufacturers, regulators, and consumers to verify the authenticity of medicines through QR code scanning. Each batch of medicines is assigned a cryptographically signed verification code that can be scanned to confirm authenticity, check expiry dates, and report suspicious activity.

### Key Problems We Solve

- **Counterfeit Medicines** - Provide a verifiable chain of authenticity for every batch
- **Supply Chain Transparency** - Track scans from different locations to detect diversion
- **Regulatory Compliance** - Help pharmaceutical companies meet DRAP (Drug Regulatory Authority of Pakistan) requirements
- **Consumer Confidence** - Allow end-users to verify medicines before consumption

---

## ✨ Features

### Core Functionality
- **QR Code Generation** - Generate unique, cryptographically signed QR codes for each medicine batch
- **Verification Portal** - Scan or manually enter codes to verify medicine authenticity
- **Admin Dashboard** - Monitor suspicious activity, manage batches, and resolve flags
- **Multi-tenant Architecture** - Support multiple pharmaceutical manufacturers

### Security
- **JWT Authentication** - RS256 asymmetric token signing
- **TOTP 2FA** - Time-based one-time passwords for admin accounts
- **Argon2/Bcrypt** - Industry-standard password hashing
- **Rate Limiting** - Protection against brute-force attacks
- **Input Validation** - Pydantic models for all API inputs

### Developer Experience
- **RESTful API** - OpenAPI/Swagger documentation at `/docs`
- **TypeScript Frontend** - React with full type safety
- **Async Database** - SQLAlchemy 2.0 with async support
- **Structured Logging** - JSON logs with request tracing
- **Prometheus Metrics** - `/metrics` endpoint for monitoring

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│                   SPA served via Nginx/CDN                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Python)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │   Auth   │  │ Register │  │  Admin   │  │   Verification   │ │
│  │   API    │  │   API    │  │   API    │  │       API        │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────┐                 ┌─────────────────┐
│  PostgreSQL DB  │                 │     Redis       │
│  (Production)   │                 │  (Rate Limit)   │
└─────────────────┘                 └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DRAP External API (Optional)                 │
│              Validate manufacturer licenses externally            │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Tailwind CSS, React Router |
| **Backend** | FastAPI, Python 3.12+, SQLAlchemy 2.0 |
| **Database** | PostgreSQL (production), SQLite (development) |
| **Cache/Rate Limit** | Redis |
| **Authentication** | JWT (RS256), Argon2, TOTP |
| **QR Codes** | QR code generation with digital signatures |
| **Monitoring** | Prometheus, OpenTelemetry, Structlog |
| **Deployment** | Docker, Docker Compose, Kubernetes |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ (optional, SQLite for dev)
- Redis 7+ (optional, for rate limiting)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/medverify.git
cd medverify
```

### 2. Backend Setup

```bash
cd medverify

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Initialize database (SQLite for development)
python -c "from medverify.models import Base; from medverify.core.config import async_engine; import asyncio; asyncio.run(Base.metadata.create_all(async_engine))"

# Create admin user
python scripts/seed_admin.py
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local

# Start development server
npm run dev
```

### 4. Run the Application

```bash
# Terminal 1 - Backend
cd medverify
uvicorn medverify.main:app --reload --port 8000

# Terminal 2 - Frontend
cd medverify/frontend
npm run dev
```

Access the application at:
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Demo Credentials

After running `python scripts/seed_admin.py`:

| Role | DRAP License | Password |
|------|--------------|----------|
| Admin | `ADMIN-001` | `Admin@12345` |
| Manufacturer | `DEMO-LIC-0001` | (set during registration) |

---

## 🐳 Docker Deployment

### Development with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Build

```bash
# Build images
docker build -t medverify-backend ./medverify
docker build -t medverify-frontend ./medverify/frontend

# Run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📁 Project Structure

```
medverify/
├── api/                    # API route handlers
│   ├── admin.py           # Admin endpoints
│   ├── auth.py            # Authentication endpoints
│   └── registration.py    # Batch registration endpoints
├── core/                   # Core functionality
│   ├── auth.py            # Authentication utilities
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connection
│   ├── drap.py            # DRAP API integration
│   ├── email.py           # Email service
│   ├── keys.py            # RSA key management
│   ├── qr.py              # QR code generation
│   ├── rate_limit.py      # Rate limiting
│   └── security.py        # Security utilities
├── models.py               # SQLAlchemy models
├── schemas.py              # Pydantic schemas
├── main.py                # FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Backend Docker image
├── docker-compose.yml     # Development stack
├── .env.example          # Environment template
├── init-scripts/         # Database initialization
│   └── 01-init.sql
├── frontend/             # React frontend
│   ├── src/
│   │   ├── api.ts       # API client
│   │   ├── App.tsx      # Main app component
│   │   ├── i18n.ts      # Internationalization
│   │   ├── components/ # Reusable components
│   │   └── pages/       # Page components
│   ├── package.json     # Node dependencies
│   ├── nginx.conf       # Production nginx config
│   └── Dockerfile       # Frontend Docker image
├── scripts/              # Utility scripts
│   └── seed_admin.py    # Create admin user
├── tests/               # Test suite
│   ├── test_auth.py
│   ├── test_verification.py
│   ├── test_security.py
│   └── test_fraud.py
└── .github/workflows/   # CI/CD workflows
    └── ci.yml
```

---

## 📖 Documentation

- [API Documentation](https://medverify.app/docs) - Interactive API docs
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment instructions
- [Security Policy](SECURITY.md) - Security reporting and practices
- [Contributing Guide](CONTRIBUTING.md) - How to contribute

---

## 🔒 Security

See [SECURITY.md](SECURITY.md) for details on our security practices and how to report vulnerabilities.

### Key Security Features

- ✅ Argon2 password hashing (memory-hard, resistant to GPU/ASIC attacks)
- ✅ RS256 JWT signing (asymmetric, private key never exposed)
- ✅ TOTP 2FA support
- ✅ Rate limiting on all endpoints
- ✅ CORS configuration
- ✅ Input validation with Pydantic
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS prevention (React default escaping)

---

## 🧪 Testing

```bash
# Backend tests
cd medverify
pytest tests/ -v --cov=medverify --cov-report=html

# Frontend tests
cd frontend
npm test -- --coverage

# Linting
cd medverify && ruff check .
cd frontend && npm run lint
```

---

## 📊 Monitoring

The application exposes several endpoints for monitoring:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic health check |
| `GET /health/ready` | Readiness check (includes DB) |
| `GET /metrics` | Prometheus metrics |

### Key Metrics

- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency histogram
- Database connection pool stats

---

## 🌐 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (REQUIRED in production) | - |
| `SQLALCHEMY_DATABASE_URL` | Database connection string | SQLite dev |
| `REDIS_URL` | Redis connection string | localhost:6379 |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | localhost:3000 |
| `SMTP_HOST` | SMTP server for emails | localhost |
| `FRONTEND_URL` | Frontend URL for email links | http://localhost:3000 |
| `ENABLE_2FA` | Enable TOTP 2FA | true |

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [DRAP](https://www.drap.gov.pk/) - Drug Regulatory Authority of Pakistan
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library
- All our contributors and supporters

---

<div align="center">

**Made with ❤️ for safer medicines**

</div>
