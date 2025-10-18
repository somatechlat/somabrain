# Development Manual

**Purpose**: This manual explains how to build, modify, and contribute to the SomaBrain codebase.

**Audience**: Software engineers, contributors, and technical stakeholders working on SomaBrain.

**Prerequisites**: Python 3.10+, Docker, Git, and familiarity with FastAPI and hyperdimensional computing concepts.

---

## Quick Navigation

- [Local Setup](local-setup.md) - One-page development environment setup
- [Coding Standards](coding-standards.md) - Python style guide and linting rules
- [Testing Guidelines](testing-guidelines.md) - Test strategy and framework usage
- [API Reference](api-reference.md) - Complete endpoint documentation
- [Architecture Decisions](architecture-decisions/) - Accepted ADRs guiding the codebase
- [Contribution Process](contribution-process.md) - Pull request workflow and code review
- [Documentation Guide](documentation-guide.md) - Standards for creating and maintaining docs

---

## Codebase Overview

SomaBrain is structured as a modern Python application:

```
somabrain/
├── app.py              # FastAPI application and endpoints
├── memory_client.py    # HTTP memory service connector
├── quantum.py          # BHDC hypervector binding/unbinding
├── scoring.py          # Unified scoring with density matrix
├── mt_wm.py           # Multi-tenant working memory
├── salience.py        # Frequent-directions salience tracking
└── ...
```

**Key Design Principles**:
- **Mathematical Correctness**: No mocking, all algorithms use real math
- **Backend Enforcement**: Production code paths require external backing services
- **Observable**: Comprehensive metrics and structured logging
- **Testable**: Property tests for mathematical invariants

## Development Workflow

- Make code changes in feature branches (unless main-only is required).
- Use `pytest` for tests: `pytest tests/`
- Use `make lint` and `make format` for code quality (if Makefile present).
- Update this guide as you improve the workflow.

1. **Environment Setup**: Follow [Local Setup](local-setup.md) for development environment
2. **Code Style**: Adhere to [Coding Standards](coding-standards.md) (ruff, mypy)
3. **Testing**: Write tests per [Testing Guidelines](testing-guidelines.md)
4. **Contribution**: Submit changes via [Contribution Process](contribution-process.md)

## Mathematical Components

Core mathematical modules:
- `quantum.py`: Binary hyperdimensional computing (BHDC) operations
- `memory/density.py`: Density matrix maintenance and PSD projection
- `salience.py`: Frequent-directions sketching for diversity
- `scoring.py`: Multi-component scoring with bounded weights

---

**Verification**: Run `ruff check . && mypy somabrain && pytest` before submitting PRs.

**Common Errors**: See [Testing Guidelines](testing-guidelines.md) for test failure troubleshooting.

**References**:
- [Architecture Documentation](../technical-manual/architecture.md) for system design
- [User Manual](../user-manual/index.md) for feature behavior
- [Onboarding Manual](../onboarding-manual/index.md) for new contributor guide
