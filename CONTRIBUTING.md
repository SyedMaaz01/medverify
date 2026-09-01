# Contributing to MedVerify

Thank you for your interest in contributing to MedVerify!

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report:
1. Check the [issues](https://github.com/your-org/medverify/issues) to see if the issue already exists
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Code samples or screenshots if applicable
   - Your environment (OS, Python/Node version, etc.)

### Suggesting Features

We welcome feature suggestions! Please create an issue with:
- Clear description of the feature
- Use case / why it's valuable
- Any relevant examples or mockups

### Pull Requests

1. **Fork the repository** and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow the development setup** in README.md

3. **Write tests** for new functionality

4. **Ensure all tests pass**:
   ```bash
   # Backend
   pytest tests/ -v
   
   # Frontend
   cd frontend && npm test
   ```

5. **Run linting**:
   ```bash
   # Backend
   ruff check .
   
   # Frontend
   cd frontend && npm run lint
   ```

6. **Commit your changes** with clear messages:
   ```bash
   git commit -m "Add: Brief description of the feature"
   ```

7. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Open a Pull Request** against the `main` branch

## Development Guidelines

### Python Backend

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions small and focused (single responsibility)
- Add tests for new functionality (pytest)

### React Frontend

- Use TypeScript for type safety
- Follow existing component patterns
- Use existing UI components from the design system
- Keep components small and reusable
- Add tests for complex logic

### Git Commit Messages

Format: `type: Short description`

Types:
- `Add:` New feature
- `Fix:` Bug fix
- `Refactor:` Code refactoring
- `Docs:` Documentation changes
- `Test:` Test additions/changes
- `Chore:` Maintenance tasks

Example:
```
Add: User 2FA setup functionality
Fix: Resolved race condition in batch scanning
Refactor: Extract QR code generation into separate module
```

## Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - Feature branches
- `fix/*` - Bug fix branches
- `hotfix/*` - Production emergency fixes

## Questions?

Feel free to:
- Open an issue for questions
- Join our discussions
- Email the maintainers

Thank you for contributing! 🎉
