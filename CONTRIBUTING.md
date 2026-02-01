# Contributing to Google Drive to S3 Webhook Pipeline

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Pull Requests](#submitting-pull-requests)
- [Coding Standards](#coding-standards)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. Please be respectful, inclusive, and professional in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/customer-care-call-processor.git
   cd customer-care-call-processor
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/olajio/customer-care-call-processor.git
   ```

## Development Setup

### Prerequisites

- Python 3.9+
- AWS CLI configured with credentials
- Terraform 1.0+
- Make (optional, but recommended)

### Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov pytest-mock moto black flake8 mypy
```

### Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your configuration values

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-filter` - New features
- `fix/webhook-validation` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/lambda-handler` - Code refactoring

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```bash
git commit -m "feat(webhook): add file size validation"
git commit -m "fix(s3): handle multipart upload errors"
git commit -m "docs: update deployment instructions"
```

## Testing

### Run All Tests

```bash
make test
```

Or manually:
```bash
pytest tests/ -v --cov=src/lambda
```

### Run Specific Tests

```bash
# Unit tests only
pytest tests/test_webhook_handler.py -v

# Integration tests
pytest tests/integration/ -v
```

### Write Tests

- Place unit tests in `tests/`
- Place integration tests in `tests/integration/`
- Aim for >80% code coverage
- Mock external services (AWS, Google Drive)

Example test:
```python
def test_validate_webhook_signature():
    headers = {'X-Goog-Channel-Token': 'test-token'}
    assert validate_webhook_signature(headers, 'test-token') is True
```

## Code Quality

### Linting

```bash
# Run all linters
make lint

# Or individually
flake8 src/ tests/
black --check src/ tests/
mypy src/lambda/
```

### Formatting

```bash
# Auto-format code
make format

# Or manually
black src/ tests/
```

## Submitting Pull Requests

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests and linters**:
   ```bash
   make test
   make lint
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature
   ```

4. **Create Pull Request** on GitHub:
   - Use a descriptive title
   - Reference any related issues
   - Describe what changed and why
   - Include screenshots if UI-related

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated (for notable changes)
- [ ] Commits follow conventional commits format
- [ ] PR description is clear and complete

## Coding Standards

### Python

- Follow [PEP 8](https://pep8.org/)
- Use type hints where possible
- Maximum line length: 120 characters
- Use docstrings for functions and classes
- Prefer composition over inheritance

Example:
```python
def process_file(file_id: str, metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Process a single file from Google Drive.
    
    Args:
        file_id: Google Drive file ID
        metadata: File metadata dictionary
        
    Returns:
        Processing result with status and message
    """
    # Implementation
```

### Terraform

- Use consistent naming conventions
- Add descriptions to all variables
- Tag all resources
- Use modules for reusable components

### Documentation

- Keep README.md up to date
- Document all configuration options
- Include examples for common use cases
- Update architecture diagrams when needed

## Reporting Issues

### Bug Reports

Include:
- Description of the issue
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, Python version, etc.)
- Error messages and logs
- Screenshots (if applicable)

### Feature Requests

Include:
- Clear description of the feature
- Use case and motivation
- Proposed solution (if any)
- Alternative solutions considered

## Questions?

- Open a GitHub Discussion for general questions
- Tag maintainers in issues for specific technical questions
- Check existing documentation and issues first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🎉
