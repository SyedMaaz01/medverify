# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | ✅ Currently Supported |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**DO NOT create a public GitHub issue for security vulnerabilities.**

Instead, please send details to:

- **Email**: security@medverify.app
- **Expected Response Time**: 24-48 hours
- **Expected Resolution**: We will work with you to understand and address the issue promptly

### What to Include

When reporting, please include:

1. **Description** - Clear description of the vulnerability
2. **Steps to Reproduce** - Detailed steps to reproduce the issue
3. **Impact** - Potential security impact of the vulnerability
4. **Suggested Fix** - If you have any suggestions for fixing the issue

### What We Promise

- **Acknowledgment** - We will acknowledge receipt of your report within 24 hours
- **Transparency** - We will keep you informed about our progress
- **Credit** - With your permission, we will credit you in our security advisory (if desired)
- **Good Faith** - We will not pursue legal action against researchers who report vulnerabilities in good faith

## Security Best Practices

When deploying MedVerify, please follow these security best practices:

### Required for Production

- [ ] Set a strong, unique `SECRET_KEY` environment variable
- [ ] Configure `CORS_ORIGINS` to restrict allowed origins
- [ ] Use HTTPS/TLS in production
- [ ] Secure your database (PostgreSQL with strong credentials)
- [ ] Enable Redis authentication if using rate limiting
- [ ] Review and configure email/SMTP security settings

### Recommended

- [ ] Enable 2FA for all admin accounts
- [ ] Use a secrets manager for production credentials
- [ ] Configure firewall rules to restrict access
- [ ] Set up monitoring and alerting for suspicious activity
- [ ] Regular security audits of your deployment

## Security Features

MedVerify includes several built-in security features:

| Feature | Description | Default |
|---------|-------------|---------|
| Password Hashing | Argon2/Bcrypt with per-user salts | ✅ Enabled |
| JWT Signing | RS256 asymmetric algorithm | ✅ Enabled |
| 2FA Support | TOTP time-based one-time passwords | ✅ Available |
| Rate Limiting | Request throttling per IP/user | ✅ Enabled |
| Input Validation | Pydantic models for all inputs | ✅ Enabled |
| SQL Injection Prevention | SQLAlchemy ORM with parameterized queries | ✅ Enabled |
| XSS Prevention | React auto-escaping | ✅ Enabled |
| CORS Protection | Configurable allowed origins | ✅ Configured |

## Security Updates

Security updates will be released as patch versions (e.g., 1.0.1) and announced via:

- GitHub Security Advisories
- Release notes on GitHub

We recommend watching the repository for updates.

---

Thank you for helping keep MedVerify and its users safe!
