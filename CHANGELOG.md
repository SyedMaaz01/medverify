# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-31

### Added
- Initial production-ready release
- QR code generation with RSA-signed verification codes
- Medicine batch registration for manufacturers
- Verification portal for scanning/validating codes
- Admin dashboard for monitoring suspicious activity
- Multi-tenant architecture supporting multiple manufacturers
- JWT authentication with RS256 asymmetric signing
- TOTP 2FA support for admin accounts
- Argon2 password hashing
- Rate limiting on all endpoints
- PostgreSQL and SQLite database support
- Redis caching and rate limiting
- Docker and Docker Compose deployment
- CI/CD pipeline with GitHub Actions
- Prometheus metrics and structured logging
- OpenAPI/Swagger documentation

### Security
- Privilege escalation prevention in admin endpoints
- Configurable CORS origins
- Warning for insecure SECRET_KEY fallback
- Input validation with Pydantic models
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via React default escaping
