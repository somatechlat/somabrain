# Development Manual

**Purpose**: This manual explains how to build, modify, and contribute to the SomaBrain codebase.

**Audience**: Software engineers, contributors, and technical stakeholders working on SomaBrain.

**Prerequisites**: Python 3.10+, Docker, Git, and familiarity with FastAPI and hyperdimensional computing concepts.

---

## Quick Navigation

- {doc}`local-setup` - One-page development environment setup
- {doc}`coding-standards` - Python style guide and linting rules
- {doc}`testing-guidelines` - Test strategy and framework usage
- {doc}`api-reference` - Complete endpoint documentation
- {doc}`contribution-process` - Pull request workflow and code review

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

1. **Environment Setup**: Follow {doc}`local-setup` for development environment
2. **Code Style**: Adhere to {doc}`coding-standards` (ruff, mypy)
3. **Testing**: Write tests per {doc}`testing-guidelines`
4. **Contribution**: Submit changes via {doc}`contribution-process`

## Mathematical Components

Core mathematical modules:
- `quantum.py`: Binary hyperdimensional computing (BHDC) operations
- `memory/density.py`: Density matrix maintenance and PSD projection
- `salience.py`: Frequent-directions sketching for diversity
- `scoring.py`: Multi-component scoring with bounded weights

---

**Verification**: Run `ruff check . && mypy somabrain && pytest` before submitting PRs.

**Common Errors**: See {doc}`testing-guidelines` for test failure troubleshooting.



```{toctree}
:maxdepth: 1
:caption: Development Topics
:hidden:

local-setup.md
coding-standards.md
testing-guidelines.md
api-reference.md
contribution-process.md
first-contribution.md
migrations.md
VIBE_CODING_RULES.md
adaptation-config.md
```

